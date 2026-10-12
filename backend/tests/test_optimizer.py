from dcp_helpers import reviewed_confirm
def first_feasible_segment(client):
    challenges = client.get("/challenges").json()
    return challenges[0]["segments"][0]["id"]

def test_optimizer_returns_valid_and_excludes_protected(client):
    segment_id = first_feasible_segment(client)
    response = client.post(f"/segments/{segment_id}/optimize", json={"max_solutions":3}).json()
    assert response["solutions"]
    for solution in response["solutions"]:
        assert solution["valid"] is True
        assert solution["violations"] == []
        assert not any(player["protected"] for player in solution["players"])

def test_impossible_segment_is_rejected(client):
    challenge = client.post("/challenges", json={"name":"Imposible","description":"","reward":""}).json()
    segment = client.post(f"/challenges/{challenge['id']}/segments", json={"name":"99","requirements":{"squad_size":11,"min_rating":99}}).json()
    response = client.post(f"/segments/{segment['id']}/optimize", json={"max_solutions":1}).json()
    assert response["solutions"] == []

def test_simulation_confirmation_and_restore(client):
    before = client.get("/dashboard").json()["counts"]["players"]
    segment_id = first_feasible_segment(client)
    simulated = client.post(f"/segments/{segment_id}/optimize", json={"max_solutions":1}).json()
    assert client.get("/dashboard").json()["counts"]["players"] == before
    solution = simulated["solutions"][0]
    confirmed = reviewed_confirm(client, f"/segments/{segment_id}/confirm", json={"player_ids":solution["player_ids"]})
    assert confirmed.status_code == 200
    assert client.get("/dashboard").json()["counts"]["players"] == before - 11
    submission_id = confirmed.json()["submission_id"]
    assert client.post(f"/submissions/{submission_id}/restore").json()["restored"] is True
    assert client.get("/dashboard").json()["counts"]["players"] == before

def test_protected_player_cannot_be_confirmed(client):
    players = client.get("/players?protected=true&limit=11").json()["items"]
    segment_id = first_feasible_segment(client)
    response = reviewed_confirm(client, f"/segments/{segment_id}/confirm", json={"player_ids":[p["id"] for p in players]})
    assert response.status_code == 422

def test_duplicate_bonus_in_solution(client):
    segment_id = first_feasible_segment(client)
    response = client.post(f"/segments/{segment_id}/optimize", json={"max_solutions":3}).json()
    assert any(solution["duplicate_count"] > 0 for solution in response["solutions"])
