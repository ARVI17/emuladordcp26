from app.services.adb import build_dcp_steps

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
