import pytest
from app.services.adb import AdbBridge, AdbError, build_dcp_steps
from app.services.import_export import extract_accessibility_inventory_candidates, extract_inventory_candidates, parse_dcp_requirements

CALIBRATION = {"screen_width":1080,"screen_height":2400,"open_search_x":940,"open_search_y":2120,"search_field_x":520,"search_field_y":310,"first_result_x":520,"first_result_y":690,"add_player_x":900,"add_player_y":2180,"wait_ms":250}

def feasible_solution(client):
    segment = client.get("/challenges").json()[0]["segments"][0]
    result = client.post(f"/segments/{segment['id']}/optimize", json={"max_solutions":1}).json()["solutions"][0]
    return segment["id"], result["player_ids"]

@pytest.mark.parametrize("enabled", [False, True])
def test_adb_degrades_without_device(client, monkeypatch, enabled):
    from app.core.config import settings
    calls = []
    monkeypatch.setattr(settings, "adb_enabled", enabled)
    monkeypatch.setattr(AdbBridge, "devices", lambda self: calls.append("devices") or [])
    response = client.get("/emulator/status")
    assert response.status_code == 200
    assert response.json()["enabled"] is enabled
    assert response.json()["available"] is False
    assert response.json()["devices"] == []
    assert calls == (["devices"] if enabled else [])

def test_invalid_adb_address_is_rejected_before_connection(client):
    response = client.post("/emulator/connect", json={"address":"localhost;rm -rf /"})
    assert response.status_code == 422
    assert client.post("/emulator/connect", json={"address":"localhost:99999"}).status_code == 422
    assert client.post("/emulator/pair", json={"address":"localhost:37001","pairing_code":"clave"}).status_code == 422

def test_adb_pairing_code_is_used_but_never_audited(client, monkeypatch):
    class FakeBridge:
        def pair(self, address, pairing_code):
            assert pairing_code == "123456"
            return f"Successfully paired to {address}"
    monkeypatch.setattr("app.api.emulator.AdbBridge", FakeBridge)
    response = client.post("/emulator/pair", json={"address":"192.168.1.20:37001","pairing_code":"123456"})
    assert response.status_code == 200 and response.json()["pairing_code_stored"] is False
    event = next(row for row in client.get("/audit?limit=20").json() if row["action"] == "pair")
    assert "123456" not in str(event)
    bridge = AdbBridge()
    monkeypatch.setattr(bridge, "_run", lambda *args, **kwargs: "failed with code 123456")
    with pytest.raises(AdbError) as error: bridge.pair("192.168.1.20:37001", "123456")
    assert "123456" not in str(error.value)

def test_ready_adb_device_can_be_selected_explicitly(client, monkeypatch):
    class FakeBridge:
        def devices(self): return [{"serial":"emulator-5554","state":"device","details":"test"}]
    monkeypatch.setattr("app.api.emulator.AdbBridge", FakeBridge)
    response = client.post("/emulator/select", json={"serial":"emulator-5554"})
    assert response.status_code == 200 and response.json()["selected"] is True
    status = client.get("/emulator/status").json()
    assert status["config"]["serial"] == "emulator-5554"

def test_create_and_prepare_automation_plan(client):
    segment_id, player_ids = feasible_solution(client)
    created = client.post("/emulator/plans", json={"segment_id":segment_id,"player_ids":player_ids})
    assert created.status_code == 201
    plan = created.json()
    assert plan["status"] == "draft"
    assert plan["final_submission_automated"] is False
    assert len(plan["solution_snapshot"]["players"]) == 11
    assert client.post(f"/emulator/plans/{plan['id']}/prepare").status_code == 409
    assert client.put("/emulator/calibration", json=CALIBRATION).status_code == 200
    prepared = client.post(f"/emulator/plans/{plan['id']}/prepare").json()
    assert prepared["status"] == "prepared"
    assert prepared["confirmation_phrase"] == f"PREPARAR {plan['id']}"
    assert len(prepared["steps"]) == 110
    wrong = client.post(f"/emulator/plans/{plan['id']}/execute", json={"confirmation":"NO EJECUTAR"})
    assert wrong.status_code == 422
    assert client.post(f"/emulator/plans/{plan['id']}/cancel").json()["status"] == "cancelled"

def test_execution_revalidates_players_before_adb(client):
    segment_id, player_ids = feasible_solution(client)
    plan = client.post("/emulator/plans", json={"segment_id":segment_id,"player_ids":player_ids}).json()
    client.put("/emulator/calibration", json=CALIBRATION)
    client.post(f"/emulator/plans/{plan['id']}/prepare")
    client.post(f"/players/{player_ids[0]}/protect")
    response = client.post(f"/emulator/plans/{plan['id']}/execute", json={"confirmation":f"PREPARAR {plan['id']}"})
    assert response.status_code == 422
    assert "protegidas" in str(response.json())

def test_execution_logs_every_step_and_checks_resolution(client, monkeypatch):
    segment_id, player_ids = feasible_solution(client)
    plan = client.post("/emulator/plans", json={"segment_id":segment_id,"player_ids":player_ids}).json()
    client.put("/emulator/calibration", json=CALIBRATION)
    client.post(f"/emulator/plans/{plan['id']}/prepare")

    class FakeBridge:
        def devices(self): return [{"serial":"host.docker.internal:5555","state":"device","details":"test"}]
        def screen_size(self, serial): return (1080, 2400)

    monkeypatch.setattr("app.api.emulator.AdbBridge", FakeBridge)
    monkeypatch.setattr("app.api.emulator.run_step", lambda bridge, serial, step: None)
    response = client.post(f"/emulator/plans/{plan['id']}/execute", json={"confirmation":f"PREPARAR {plan['id']}"})
    assert response.status_code == 200
    finished = next(row for row in client.get("/emulator/plans").json() if row["id"] == plan["id"])
    assert finished["status"] == "completed"
    step_logs = [row for row in client.get("/audit?limit=200").json() if row["action"] == "execute_step" and row["entity_id"] == plan["id"]]
    assert len(step_logs) == len(finished["steps"])

def test_protected_combination_is_rejected(client):
    segment_id, player_ids = feasible_solution(client)
    player_id = player_ids[0]
    client.post(f"/players/{player_id}/protect")
    response = client.post("/emulator/plans", json={"segment_id":segment_id,"player_ids":player_ids})
    assert response.status_code == 422

def test_generated_steps_never_submit_dcp():
    steps = build_dcp_steps(CALIBRATION, [{"name":"Jugador Uno"}])
    assert {step["action"] for step in steps} <= {"tap", "text", "wait", "clear_text", "select_verified", "add_verified"}
    assert any(step["action"] == "select_verified" for step in steps)
    assert any(step["action"] == "add_verified" for step in steps)
    assert not any("enviar" in step["label"].lower() or "entregar" in step["label"].lower() for step in steps)

def test_inventory_scan_requires_review_and_explicit_import(client, monkeypatch):
    class FakeBridge:
        def devices(self): return [{"serial":"host.docker.internal:5555","state":"device","details":"test"}]
        def screen_size(self, serial): return (1080, 2400)
        def screenshot(self, serial): return b"\x89PNG\r\n\x1a\ncontenido-estable"

    monkeypatch.setattr("app.api.emulator.AdbBridge", FakeBridge)
    monkeypatch.setattr("app.api.emulator.ocr_inventory", lambda content, page: {"raw_text":"84 MC Jugador Real", "candidates":[{"name":"Jugador Real","rating":84,"position":"MC","source_page":page,"confidence":{"name":.8,"rating":.9,"position":.9}}]})
    scan = client.post("/emulator/scans").json()
    assert scan["status"] == "scanning" and scan["images_saved"] is False
    captured = client.post(f"/emulator/scans/{scan['id']}/capture").json()
    assert captured["detected"] == 1
    assert captured["scan"]["candidates"][0]["candidate_id"] == 1
    duplicate = client.post(f"/emulator/scans/{scan['id']}/capture").json()
    assert duplicate["duplicate_capture"] is True
    players = [{"name":"Jugador Real","rating":84,"position":"MC","league":"Liga real","club":"Club real","nationality":"Colombia"}]
    assert client.post(f"/emulator/scans/{scan['id']}/import", json={"players":players,"candidate_ids":[1],"confirmation":"IMPORTAR MAL"}).status_code == 422
    imported = client.post(f"/emulator/scans/{scan['id']}/import", json={"players":players,"candidate_ids":[1],"confirmation":f"REEMPLAZAR DEMO {scan['id']}","archive_demo":True})
    assert imported.status_code == 200
    assert imported.json()["imported"] == 1
    assert imported.json()["demo_archived"] == 0  # Documented synthetic fixtures are not demo rows.
    available = client.get("/players?limit=500").json()
    assert available["total"] == 133 and any(p["name"] == "Jugador Real" for p in available["items"])

def test_inventory_scan_imports_reviewed_candidates_in_partial_batches(client, monkeypatch):
    class FakeBridge:
        def devices(self): return [{"serial":"host.docker.internal:5555","state":"device","details":"test"}]
        def screen_size(self, serial): return (1080, 2400)
        def screenshot(self, serial): return b"\x89PNG\r\n\x1a\nparcial"
    candidates = [{"name":f"Jugador {index}","rating":80+index,"position":"MC","source_page":1,"confidence":{"name":.8,"rating":.8,"position":.8}} for index in (1, 2)]
    monkeypatch.setattr("app.api.emulator.AdbBridge", FakeBridge)
    monkeypatch.setattr("app.api.emulator.ocr_inventory", lambda content, page: {"raw_text":"", "candidates":candidates})
    scan = client.post("/emulator/scans").json()
    captured = client.post(f"/emulator/scans/{scan['id']}/capture").json()["scan"]
    def player(name, rating): return {"name":name,"rating":rating,"position":"MC","league":"Revisada","club":"Revisado","nationality":"Revisada"}
    first = client.post(f"/emulator/scans/{scan['id']}/import", json={"players":[player("Jugador 1",81)],"candidate_ids":[1],"confirmation":f"IMPORTAR {scan['id']}"})
    assert first.status_code == 200
    assert first.json()["scan"]["status"] == "review" and first.json()["scan"]["imported_count"] == 1
    assert [item["candidate_id"] for item in first.json()["scan"]["candidates"]] == [2]
    assert client.post(f"/emulator/scans/{scan['id']}/import", json={"players":[player("Jugador 1",81)],"candidate_ids":[1],"confirmation":f"IMPORTAR {scan['id']}"}).status_code == 409
    second = client.post(f"/emulator/scans/{scan['id']}/import", json={"players":[player("Jugador 2",82)],"candidate_ids":[2],"confirmation":f"IMPORTAR {scan['id']}"})
    assert second.status_code == 200
    assert second.json()["scan"]["status"] == "imported" and second.json()["scan"]["imported_count"] == 2

def test_ocr_extractors_return_reviewable_drafts():
    text = """Club\n84\nMC\nJugador Real\n82\nDFC\nDefensa Seguro\n"""
    candidates = extract_inventory_candidates(text, page=3)
    assert len(candidates) == 2
    assert candidates[0]["rating"] == 84 and candidates[0]["source_page"] == 3
    requirements = parse_dcp_requirements("Número de jugadores: 11\nValoración de plantilla: Min. 84\nQuímica total: Min. 22\nRaros: Min. 2")
    assert requirements == {"squad_size":11,"min_rating":84,"min_chemistry":22,"min_rare":2}

def test_accessibility_inventory_extractor_reads_virtualized_companion_rows():
    hierarchy = b'''<?xml version="1.0" encoding="UTF-8"?>
    <hierarchy><node text="Futb. de Mi Club" class="android.widget.TextView" />
      <node class="android.widget.ListView">
        <node bounds="[30,436][691,668]"><node text="99"/><node text="POR"/><node text="Unai Sim&#243;n"/><node text="SAL98"/></node>
        <node bounds="[0,0][0,0]"><node text="97"/><node text="DC"/><node text="14"/><node text="Lookman"/><node text="RIT96"/></node>
      </node>
    </hierarchy>'''
    candidates = extract_accessibility_inventory_candidates(hierarchy, page=4)
    assert [(item["name"], item["rating"], item["position"]) for item in candidates] == [("Unai Simón", 99, "POR"), ("Lookman", 97, "DC")]
    assert candidates[1]["source_page"] == 4 and candidates[1]["confidence"]["name"] == 0.99

def test_accessibility_extractor_rejects_other_screens():
    hierarchy = '<hierarchy><node text="Mercado"/><node class="android.widget.ListView"><node><node text="99"/><node text="DC"/><node text="No importar"/></node></node></hierarchy>'
    assert extract_accessibility_inventory_candidates(hierarchy) == []

def test_ui_hierarchy_is_bounded_and_removed_from_device(monkeypatch):
    bridge = AdbBridge()
    calls = []
    content = b'<?xml version="1.0"?><hierarchy />'
    def fake_device(serial, command, timeout=12, binary=False):
        calls.append(command)
        return content if command[:2] == ["exec-out", "cat"] else b"" if binary else ""
    monkeypatch.setattr(bridge, "_device", fake_device)
    assert bridge.ui_hierarchy("emulator-5554") == content
    path = calls[0][-1]
    assert path.startswith("/data/local/tmp/emuladordcp26-ui-") and path.endswith(".xml")
    assert calls[-1] == ["shell", "rm", "-f", path]

def test_inventory_advance_validates_navigation_and_changed_page(client, monkeypatch):
    def hierarchy(name, rating, position, next_button=False):
        button = '<node text="Siguiente" class="android.widget.Button" clickable="true" enabled="true" bounds="[800,2000][1080,2100]"/>' if next_button else ''
        return f'''<?xml version="1.0"?><hierarchy><node text="Futb. de Mi Club"/><node class="android.widget.ListView"><node><node text="{rating}"/><node text="{position}"/><node text="{name}"/><node text="RIT90"/></node></node>{button}</hierarchy>'''.encode()
    trees = [hierarchy("Jugador Uno", 90, "MC"), hierarchy("Jugador Uno", 90, "MC"), hierarchy("Jugador Uno", 90, "MC", True), hierarchy("Jugador Dos", 89, "DC")]
    actions = []
    class FakeBridge:
        def devices(self): return [{"serial":"host.docker.internal:5555","state":"device","details":"test"}]
        def screen_size(self, serial): return (1080, 2400)
        def screenshot(self, serial): return b"\x89PNG\r\n\x1a\ncontenido"
        def ui_hierarchy(self, serial): return trees.pop(0)
        def scroll_inventory_list_to_end(self, serial, width, height): actions.append(("scroll", width, height))
        def tap(self, serial, x, y): actions.append(("tap", x, y))
    monkeypatch.setattr("app.api.emulator.AdbBridge", FakeBridge)
    scan = client.post("/emulator/scans").json()
    assert client.post(f"/emulator/scans/{scan['id']}/capture").json()["detected"] == 1
    advanced = client.post(f"/emulator/scans/{scan['id']}/advance")
    assert advanced.status_code == 200
    data = advanced.json()
    assert data["scan"]["captured_pages"] == 2 and data["detected"] == 1
    assert [item["name"] for item in data["scan"]["candidates"]] == ["Jugador Uno", "Jugador Dos"]
    assert actions == [("scroll", 1080, 2400), ("tap", 940, 2050)]

def test_inventory_scan_can_continue_after_bounded_thousand_candidates(client, monkeypatch):
    screenshots = iter(range(1, 51))
    class FakeBridge:
        def devices(self): return [{"serial":"host.docker.internal:5555","state":"device","details":"test"}]
        def screen_size(self, serial): return (1080, 2400)
        def screenshot(self, serial): return b"\x89PNG\r\n\x1a\n" + str(next(screenshots)).encode()
    monkeypatch.setattr("app.api.emulator.AdbBridge", FakeBridge)
    monkeypatch.setattr("app.api.emulator.ocr_inventory", lambda content, page: {"raw_text":"", "candidates":[{"name":f"Jugador {page}-{index}","rating":80,"position":"MC","source_page":page,"confidence":{"name":.8,"rating":.8,"position":.8}} for index in range(20)]})
    scan = client.post("/emulator/scans").json()
    assert client.post(f"/emulator/scans/{scan['id']}/continue").status_code == 409
    for _ in range(50):
        captured = client.post(f"/emulator/scans/{scan['id']}/capture")
        assert captured.status_code == 200
    full = captured.json()["scan"]
    assert full["captured_pages"] == 50 and full["candidate_count"] == 1000 and len(full["candidates"]) == 20
    last = client.get(f"/emulator/scans/{scan['id']}?offset=980").json()
    assert len(last["candidates"]) == 20 and last["candidates"][0]["candidate_id"] == 981
    summary = client.get('/emulator/scans').json()[0]
    assert summary['candidates'] == [] and summary['candidate_count'] == 1000
    continuation = client.post(f"/emulator/scans/{scan['id']}/continue")
    assert continuation.status_code == 201
    assert continuation.json()["captured_pages"] == 0 and continuation.json()["candidates"] == []
