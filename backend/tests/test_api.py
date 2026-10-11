import io

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
    assert client.delete(f"/players/{player_id}").status_code == 409
    assert client.get("/players?search=Prueba%20Local").json()["total"] == 1

def test_squad_create_duplicate_and_protect(client):
    recommended = client.post("/squads/recommend").json()
    ids = [p["id"] for p in recommended["players"]]
    created = client.post("/squads", json={"name":"Equipo de prueba","formation":"4-3-3","player_ids":ids})
    assert created.status_code == 201
    squad_id = created.json()["id"]
    assert client.post(f"/squads/{squad_id}/duplicate").status_code == 200
    protected = client.post(f"/squads/{squad_id}/protect").json()
    assert protected["protected"] is True
    assert all(entry["player"]["effective_protected"] for entry in protected["players"])

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
    confirmed = client.post("/players/import", data={"confirm":"true", "preview_token":preview.json()["preview_token"]}, files=files)
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
