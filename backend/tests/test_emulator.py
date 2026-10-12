import pytest
from app.services.adb import AdbBridge, AdbError, build_dcp_steps
from app.db.session import SessionLocal
from app.models.entities import InventoryScan
from app.services.import_export import extract_accessibility_inventory_candidates, extract_accessibility_objectives, extract_inventory_candidates, parse_dcp_requirements

CALIBRATION = {"screen_width":1080,"screen_height":2400,"open_search_x":940,"open_search_y":2120,"search_field_x":520,"search_field_y":310,"first_result_x":520,"first_result_y":690,"add_player_x":900,"add_player_y":2180,"wait_ms":250}

def feasible_solution(client):
    segment = client.get("/challenges").json()[0]["segments"][0]
    result = client.post(f"/segments/{segment['id']}/optimize", json={"max_solutions":1}).json()["solutions"][0]
    return segment["id"], result["player_ids"]

def test_adb_degrades_without_device(client):
    response = client.get("/emulator/status")
    assert response.status_code == 200
    assert response.json()["enabled"] is True
    assert isinstance(response.json()["devices"], list)

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
    assert len(prepared["steps"]) == 99
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
    assert len(step_logs) == 99

def test_protected_combination_is_rejected(client):
    segment_id, player_ids = feasible_solution(client)
    player_id = player_ids[0]
    client.post(f"/players/{player_id}/protect")
    response = client.post("/emulator/plans", json={"segment_id":segment_id,"player_ids":player_ids})
    assert response.status_code == 422

def test_generated_steps_never_submit_dcp():
    steps = build_dcp_steps(CALIBRATION, [{"name":"Jugador Uno"}])
    assert {step["action"] for step in steps} <= {"tap", "text", "wait"}
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
    assert captured["scan"]["candidate_count"] == 1
    assert "candidates" not in captured["scan"]
    candidate_page = client.get(f"/emulator/scans/{scan['id']}/candidates?offset=0&limit=20").json()
    assert candidate_page["total"] == 1 and candidate_page["items"][0]["candidate_id"] == 1
    summaries = client.get("/emulator/scans").json()
    assert summaries[0]["candidate_count"] == 1 and "candidates" not in summaries[0]
    duplicate = client.post(f"/emulator/scans/{scan['id']}/capture").json()
    assert duplicate["duplicate_capture"] is True
    players = [{"name":"Jugador Real","rating":84,"position":"MC","league":"Liga real","club":"Club real","nationality":"Colombia"}]
    assert client.post(f"/emulator/scans/{scan['id']}/import", json={"players":players,"candidate_ids":[1],"confirmation":"IMPORTAR MAL"}).status_code == 422
    imported = client.post(f"/emulator/scans/{scan['id']}/import", json={"players":players,"candidate_ids":[1],"confirmation":f"REEMPLAZAR DEMO {scan['id']}","archive_demo":True})
    assert imported.status_code == 200
    assert imported.json()["imported"] == 1
    assert imported.json()["demo_archived"] == 132
    available = client.get("/players?limit=500").json()
    assert available["total"] == 1 and available["items"][0]["name"] == "Jugador Real"

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
    assert captured["candidate_count"] == 2 and "candidates" not in captured
    def player(name, rating): return {"name":name,"rating":rating,"position":"MC","league":"Revisada","club":"Revisado","nationality":"Revisada"}
    first = client.post(f"/emulator/scans/{scan['id']}/import", json={"players":[player("Jugador 1",81)],"candidate_ids":[1],"confirmation":f"IMPORTAR {scan['id']}"})
    assert first.status_code == 200
    assert first.json()["scan"]["status"] == "review" and first.json()["scan"]["imported_count"] == 1
    assert first.json()["scan"]["candidate_count"] == 1 and "candidates" not in first.json()["scan"]
    remaining = client.get(f"/emulator/scans/{scan['id']}/candidates").json()
    assert [item["candidate_id"] for item in remaining["items"]] == [2]
    assert client.post(f"/emulator/scans/{scan['id']}/import", json={"players":[player("Jugador 1",81)],"candidate_ids":[1],"confirmation":f"IMPORTAR {scan['id']}"}).status_code == 422
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

def test_bulk_inventory_reconciles_and_imports_every_unique_candidate(client, monkeypatch):
    class FakeBridge:
        def devices(self): return [{"serial":"host.docker.internal:5555","state":"device","details":"test"}]
        def screen_size(self, serial): return (1080, 2400)
    monkeypatch.setattr("app.api.emulator.AdbBridge", FakeBridge)
    used = client.post("/players", json={"name":"Carta Usada","rating":83,"position":"MC","league":"Real","club":"Real","nationality":"Real"}).json()
    client.delete(f"/players/{used['id']}")
    first = client.post("/emulator/scans").json()
    second = client.post("/emulator/scans").json()
    candidate = lambda cid, name, rating=84: {"candidate_id":cid,"name":name,"rating":rating,"position":"MC","source_page":1,"confidence":{"name":.99,"rating":.99,"position":.99}}
    db = SessionLocal()
    try:
        scan_one = db.get(InventoryScan, first["id"]); scan_two = db.get(InventoryScan, second["id"])
        scan_one.candidates = [candidate(1,"Carta Nueva"),candidate(2,"Carta Nueva"),candidate(3,"Carta Usada",83)]
        scan_one.candidate_count = 3; scan_one.status = "review"
        scan_two.candidates = [candidate(1,"Carta Nueva"),candidate(2,"Otra Carta",85)]
        scan_two.candidate_count = 2; scan_two.status = "review"
        db.commit()
    finally: db.close()
    preview = client.get("/emulator/scans/bulk-preview").json()
    assert preview["detected"] == 5 and preview["unique_new"] == 2
    assert preview["duplicates"] == 2 and preview["already_registered_or_used"] == 1
    assert client.post("/emulator/scans/bulk-import", json={"confirmation":"IMPORTAR MAL"}).status_code == 422
    reconciled = client.post("/emulator/scans/reconcile").json()
    assert reconciled["duplicates_removed"] == 2 and reconciled["registered_or_used_removed"] == 1
    assert reconciled["detected"] == 2 and reconciled["unique_new"] == 2
    imported = client.post("/emulator/scans/bulk-import", json={"confirmation":"IMPORTAR TODO EL CLUB"})
    assert imported.status_code == 200
    assert imported.json()["imported"] == 2 and imported.json()["remaining_review"] == 0
    assert client.get("/emulator/scans/bulk-preview").json()["detected"] == 0
    names = {row["name"] for row in client.get("/players?limit=500").json()["items"]}
    assert {"Carta Nueva","Otra Carta"} <= names and "Carta Usada" not in names

def test_reviewed_dcp_sync_updates_instead_of_duplicating(client):
    payload = {"name":"DCP Real visible","requirements":{"min_rating":84,"squad_size":11},"confirmation":"ACTUALIZAR DCP"}
    first = client.post("/emulator/dcp/sync", json=payload)
    assert first.status_code == 200 and first.json()["action"] == "created"
    payload["requirements"]["min_rating"] = 86
    second = client.post("/emulator/dcp/sync", json=payload)
    assert second.status_code == 200 and second.json()["action"] == "updated"
    matching = [row for row in client.get("/challenges").json() if row["name"] == payload["name"]]
    assert len(matching) == 1 and matching[0]["segments"][0]["requirements"]["min_rating"] == 86
    payload["confirmation"] = "SIN CONFIRMAR"
    assert client.post("/emulator/dcp/sync", json=payload).status_code == 422

def test_visible_objectives_are_reviewed_and_upserted(client, monkeypatch):
    hierarchy = b'''<hierarchy><node text="Objetivos"/><node text="Gana 4 partidos"/><node text="1 / 4"/><node text="Marca 8 goles"/><node text="3/8"/></hierarchy>'''
    assert [row["name"] for row in extract_accessibility_objectives(hierarchy)] == ["Gana 4 partidos", "Marca 8 goles"]
    class FakeBridge:
        def devices(self): return [{"serial":"host.docker.internal:5555","state":"device","details":"test"}]
        def screen_size(self, serial): return (1080, 2400)
        def ui_hierarchy(self, serial): return hierarchy
    monkeypatch.setattr("app.api.emulator.AdbBridge", FakeBridge)
    inspected = client.post("/emulator/objectives/inspect").json()
    assert len(inspected["objectives"]) == 2 and inspected["saved"] is False
    wrong = client.post("/emulator/objectives/sync", json={"objectives":inspected["objectives"],"confirmation":"NO"})
    assert wrong.status_code == 422
    synced = client.post("/emulator/objectives/sync", json={"objectives":inspected["objectives"],"confirmation":"ACTUALIZAR OBJETIVOS"})
    assert synced.status_code == 200 and synced.json()["created"] == 2
    again = client.post("/emulator/objectives/sync", json={"objectives":inspected["objectives"],"confirmation":"ACTUALIZAR OBJETIVOS"}).json()
    assert again["created"] == 0 and again["updated"] == 2

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

def test_manual_observation_reads_only_visible_inventory_and_deduplicates(client, monkeypatch):
    visible = b'''<?xml version="1.0"?><hierarchy><node text="Futb. de Mi Club"/><node class="android.widget.ListView"><node><node text="88"/><node text="MC"/><node text="Jugador Visible"/><node text="RIT90"/></node></node></hierarchy>'''
    other_screen = b'<hierarchy><node text="Inicio"/></hierarchy>'
    hierarchies = [visible, visible, other_screen]
    class FakeBridge:
        def devices(self): return [{"serial":"host.docker.internal:5555","state":"device","details":"test"}]
        def screen_size(self, serial): return (1080, 2400)
        def ui_hierarchy(self, serial): return hierarchies.pop(0)
    monkeypatch.setattr("app.api.emulator.AdbBridge", FakeBridge)
    scan = client.post("/emulator/scans").json()
    first = client.post(f"/emulator/scans/{scan['id']}/observe").json()
    assert first["visible_inventory"] is True and first["detected"] == 1
    assert first["scan"]["candidate_count"] == 1 and first["source"] == "accessibility"
    duplicate = client.post(f"/emulator/scans/{scan['id']}/observe").json()
    assert duplicate["duplicate_capture"] is True and duplicate["detected"] == 0
    waiting = client.post(f"/emulator/scans/{scan['id']}/observe").json()
    assert waiting["visible_inventory"] is False and waiting["scan"]["candidate_count"] == 1
    segment_id = next(segment["id"] for challenge in client.get("/challenges").json() for segment in challenge["segments"] if not segment["completed"])
    analysis = client.post("/ai/dcp/analyze", json={"segment_id":segment_id,"preserve_starters":True,"max_solutions":1}).json()
    assert analysis["inventory_summary"]["pending_review"] == 1
    assert analysis["uses_reviewed_inventory_only"] is True and analysis["live_sync_scope"] == "visible_companion_screen"
    logs = [row for row in client.get("/audit?limit=100").json() if row["action"] == "observe_capture" and row["entity_id"] == scan["id"]]
    assert len(logs) == 1 and logs[0]["details"]["manual"] is True

def test_ui_hierarchy_is_bounded_and_removed_from_device(monkeypatch):
    bridge = AdbBridge()
    calls = []
    content = b'<?xml version="1.0"?><hierarchy />'
    def fake_device(serial, command, timeout=12, binary=False):
        calls.append(command)
        return content if command[:2] == ["exec-out", "cat"] else b"" if binary else ""
    monkeypatch.setattr(bridge, "_device", fake_device)
    assert bridge.ui_hierarchy("emulator-5554") == content
    assert calls[-1] == ["shell", "rm", "-f", "/data/local/tmp/emuladordcp26-ui.xml"]

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
    assert data["scan"]["candidate_count"] == 2 and "candidates" not in data["scan"]
    candidate_page = client.get(f"/emulator/scans/{scan['id']}/candidates").json()
    assert [item["name"] for item in candidate_page["items"]] == ["Jugador Uno", "Jugador Dos"]
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
    assert full["captured_pages"] == 50 and full["candidate_count"] == 1000
    last_page = client.get(f"/emulator/scans/{scan['id']}/candidates?offset=980&limit=50").json()
    assert last_page["total"] == 1000 and len(last_page["items"]) == 20
    assert client.get(f"/emulator/scans/{scan['id']}/candidates?limit=51").status_code == 422
    continuation = client.post(f"/emulator/scans/{scan['id']}/continue")
    assert continuation.status_code == 201
    assert continuation.json()["captured_pages"] == 0 and continuation.json()["candidate_count"] == 0
