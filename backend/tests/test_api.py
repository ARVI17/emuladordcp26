import io
from app.api.routes import controlled_ai_requirements

def test_health_seed_and_dashboard(client):
    assert client.get("/health").json()["database"] == "ok"
    dashboard = client.get("/dashboard").json()
    assert dashboard["counts"]["players"] == 132
    assert dashboard["counts"]["duplicates"] >= 8

def test_player_crud_and_protection(client):
    payload = {"name":"Prueba Local","rating":84,"position":"MC","league":"Liga Aurora","club":"Costa FC","nationality":"Colombia","card_type":"Oro raro","rare":True,"special":False,"tradable":False,"price":2300,"chemistry":2,"protected":False,"starter":False,"squad_role":"club","usefulness":12,"duplicate_untradeable":False}
    created = client.post("/players", json=payload)
    assert created.status_code == 201
    player_id = created.json()["id"]
    assert client.patch(f"/players/{player_id}", json={"rating":85}).json()["rating"] == 85
    assert client.post(f"/players/{player_id}/protect").json()["protected"] is True
    assert client.delete(f"/players/{player_id}").json()["ok"] is True

def test_squad_create_duplicate_and_protect(client):
    recommended = client.post("/squads/recommend").json()
    ids = [p["id"] for p in recommended["players"]]
    created = client.post("/squads", json={"name":"Equipo de prueba","formation":"4-3-3","player_ids":ids})
    assert created.status_code == 201
    squad_id = created.json()["id"]
    assert client.post(f"/squads/{squad_id}/duplicate").status_code == 200
    protected = client.post(f"/squads/{squad_id}/protect").json()
    assert protected["protected"] is True
    assert all(entry["player"]["protected"] for entry in protected["players"])

def test_objective_progress(client):
    created = client.post("/objectives", json={"name":"Objetivo API","description":"Prueba","category":"Objetivo","progress":0,"target":2})
    assert created.status_code == 201
    objective_id = created.json()["id"]
    assert client.patch(f"/objectives/{objective_id}", json={"progress":2}).json()["completed"] is True

def test_csv_preview_confirm_and_export(client):
    csv_data = "name,rating,position,league,club,nationality,card_type,rare,special,tradable,price,chemistry,protected,duplicate_untradeable\nImportado,83,DC,Liga Aurora,Costa FC,Colombia,Oro raro,true,false,false,1300,2,false,false\n"
    files = {"file": ("club.csv", io.BytesIO(csv_data.encode()), "text/csv")}
    preview = client.post("/players/import", data={"confirm":"false"}, files=files)
    assert preview.status_code == 200 and preview.json()["total"] == 1
    files = {"file": ("club.csv", io.BytesIO(csv_data.encode()), "text/csv")}
    confirmed = client.post("/players/import", data={"confirm":"true"}, files=files)
    assert confirmed.json()["imported"] == 1
    exported = client.get("/players/export?format=csv")
    assert exported.status_code == 200 and b"Importado" in exported.content

def test_works_without_ollama(client):
    status = client.get("/ai/status").json()
    assert status["available"] is False
    answer = client.post("/ai/chat", json={"message":"Resume mi club"}).json()
    assert answer["available"] is False
    assert "continúan funcionando" in answer["answer"]
    history = client.get("/ai/history").json()
    assert [item["role"] for item in history] == ["user", "assistant"]
    assert history[0]["content"] == "Resume mi club"
    controlled = controlled_ai_requirements({"min_rating":84,"required_nation":"Colombia","required_player_ids":[1,2],"texto_interno":"no enviar"})
    assert controlled == {"min_rating":84,"required_nation":"Colombia"}

def test_dcp_assistant_calculates_without_mutating_or_using_ollama(client):
    segment = next(
        segment
        for challenge in client.get("/challenges").json()
        if not challenge["completed"]
        for segment in challenge["segments"]
        if not segment["completed"]
    )
    before = client.get("/dashboard").json()["counts"]
    response = client.post("/ai/dcp/analyze", json={"segment_id":segment["id"],"preserve_starters":True,"max_solutions":2})
    assert response.status_code == 200
    analysis = response.json()
    assert analysis["simulation"] is True and analysis["writes_performed"] is False
    assert analysis["final_submission_automated"] is False
    assert analysis["plan_confirmation_phrase"] == f"CREAR PLAN {segment['id']}"
    assert analysis["solutions"]
    assert all(not player["starter"] and not player["protected"] for solution in analysis["solutions"] for player in solution["players"])
    assert client.get("/dashboard").json()["counts"] == before

def test_dcp_assistant_explains_when_no_solution_exists(client):
    challenge = client.post("/challenges", json={"name":"Asistente imposible","description":"","reward":""}).json()
    segment = client.post(f"/challenges/{challenge['id']}/segments", json={"name":"Media 99","requirements":{"squad_size":11,"min_rating":99}}).json()
    analysis = client.post("/ai/dcp/analyze", json={"segment_id":segment["id"],"preserve_starters":False,"max_solutions":1}).json()
    assert analysis["solutions"] == []
    assert analysis["assistant"]["next_action"] == "review_inventory"
    assert analysis["plan_confirmation_phrase"] is None
