"""Domain regressions for squad allocation, submissions and reviewed imports."""

from concurrent.futures import ThreadPoolExecutor
from itertools import combinations
from threading import Barrier

import pytest
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.entities import AppSetting, AuditLog, GalleryEntry, Player, Squad, Submission
from app.schemas.api import PlayerCreate
from app.services.squad_analysis import FORMATIONS, athlete_keys, recommend_owned_squad


def card(identifier, position="MC", **overrides):
    values = {
        "name": f"Futbolista {identifier}", "rating": 80, "position": position,
        "league": "Liga de prueba", "club": "Club de prueba", "nationality": "España",
        "game_version": "FC27", "chemistry": 2, "price": 700,
        **overrides,
    }
    return Player(id=identifier, deleted=False, **PlayerCreate.model_validate(values).model_dump())


def create_card(client, **overrides):
    values = {
        "name": "Carta de prueba", "rating": 80, "position": "MC",
        "league": "Liga de prueba", "club": "Club de prueba", "nationality": "España",
        "price": 700, **overrides,
    }
    response = client.post("/players", json=values)
    assert response.status_code == 201, response.text
    return response.json()


def create_segment(client, requirements):
    response = client.post("/challenges", json={
        "name": "DCP de prueba", "segments": [{"name": "Segmento de prueba", "requirements": requirements}],
    })
    assert response.status_code == 201, response.text
    return response.json()["segments"][0]["id"]


def database_snapshot():
    with SessionLocal() as db:
        return {
            "players": [(p.id, p.deleted, p.protected, p.duplicate_untradeable, p.consumed_by_submission_id, p.updated_at)
                        for p in db.scalars(select(Player).order_by(Player.id))],
            "counts": [db.scalar(select(func.count()).select_from(model))
                       for model in (Submission, Squad, AuditLog, AppSetting, GalleryEntry)],
        }


@pytest.mark.parametrize("formation", FORMATIONS)
def test_each_formation_fills_only_eligible_slots(formation):
    players = [card(index, position) for index, position in enumerate(FORMATIONS[formation], 1)]
    result = recommend_owned_squad(players, game_version="FC27", formation=formation)
    assert result["complete"] and not result["gaps"]
    assert len(result["lineup"]) == 11
    assert all(row["position"] == row["player"]["position"] for row in result["lineup"])
    assert result["chemistry_approximate"] is True


def test_assignment_reserves_flexible_midfielder_for_the_only_remaining_position():
    positions = FORMATIONS["4-3-3"]
    players = [card(index, position) for index, position in enumerate(positions, 1)]
    # There is only one primary MC. The stronger MCD must use MC, leaving MCD
    # for the less flexible card, or the eleven cannot be completed.
    players[5] = card(6, "MCD", rating=95, alternate_positions=["MC"])
    players[6] = card(7, "MCD", rating=70)
    result = recommend_owned_squad(players, game_version="FC27")
    assert result["complete"]
    flexible = next(row for row in result["lineup"] if row["player"]["id"] == 6)
    assert flexible["position"] == "MC" and flexible["used_alternate_position"]
    no_alternates = recommend_owned_squad(players, game_version="FC27", use_alternate_positions=False)
    assert not no_alternates["complete"]
    assert [gap["position"] for gap in no_alternates["gaps"]] == ["MC"]


def test_attributes_locked_cards_and_protection_affect_the_recommendation_correctly():
    players = [card(index, position) for index, position in enumerate(FORMATIONS["4-3-3"], 1)]
    players[9] = card(10, "DC", rating=90, attributes={"shooting": 50, "pace": 50})
    players.append(card(12, "DC", rating=87, protected=True, attributes={"shooting": 99, "pace": 99}))
    best = recommend_owned_squad(players, game_version="FC27", bench_size=1)
    assert 12 in [p["id"] for p in best["players"]]
    assert next(row for row in best["lineup"] if row["player"]["id"] == 12)["player"]["effective_protected"]
    assert "tiro 99" in next(row for row in best["lineup"] if row["player"]["id"] == 12)["explanation"]
    locked = recommend_owned_squad(players, game_version="FC27", locked_player_ids=[10], excluded_player_ids=[12])
    assert 10 in [p["id"] for p in locked["players"]]
    assert 12 not in [p["id"] for p in locked["players"] + locked["bench"]]


def test_versions_of_one_athlete_cannot_occupy_two_slots_or_the_bench():
    players = [card(index, position) for index, position in enumerate(FORMATIONS["4-4-2"], 1)]
    players[9] = card(10, "DC", name="Álex Ejemplo", base_card_id="athlete-9")
    players[10] = card(11, "DC", name="A. Ejemplo", base_card_id="athlete-9")
    players.extend([card(12, "DC", name="Alex   Ejemplo"), card(13, "DC", name="Delantero distinto")])
    result = recommend_owned_squad(players, game_version="FC27", formation="4-4-2")
    chosen = {p["id"] for p in result["players"] + result["bench"]}
    by_id = {p.id: p for p in players}
    assert result["complete"]
    assert all(not (athlete_keys(by_id[left]) & athlete_keys(by_id[right])) for left, right in combinations(chosen, 2))
    with pytest.raises(ValueError, match="versiones"):
        recommend_owned_squad(players, game_version="FC27", formation="4-4-2", locked_player_ids=[10, 11])


def test_edition_review_and_loan_filters_are_explicit():
    players = [card(1, "POR"), card(2, "LD", data_reviewed=False), card(3, "LI", is_loan=True)]
    players[0].game_version = "FC26"  # Historical ORM fixture; never public input.
    result = recommend_owned_squad(players, game_version="FC27", include_loans=False)
    assert result["players"] == [] and result["bench"] == []
    assert len(result["gaps"]) == 11
    included = recommend_owned_squad(players, game_version="FC27", include_unreviewed=True)
    assert {p["id"] for p in included["players"]} == {2, 3}


def test_analysis_recommendation_and_optimization_have_no_writes(client):
    segment_id = client.get("/challenges").json()[0]["segments"][0]["id"]
    before = database_snapshot()
    formations = client.get("/squads/formations")
    assert formations.status_code == 200
    assert len(formations.json()["items"]) >= 5
    analysis = client.get("/club/analysis")
    assert analysis.status_code == 200 and analysis.json()["simulation"]
    recommendation = client.post("/squads/recommend?formation=4-4-2")
    assert recommendation.status_code == 200 and recommendation.json()["formation"] == "4-4-2"
    assert client.post(f"/segments/{segment_id}/optimize", json={"max_solutions": 1}).status_code == 200
    assert database_snapshot() == before


def test_manual_and_overlapping_squad_protection_are_independent(client):
    player = create_card(client)
    squads = []
    for name in ("Plantilla A", "Plantilla B"):
        created = client.post("/squads", json={"name": name, "player_ids": [player["id"]], "slots": ["MC-1"]})
        assert created.status_code == 201, created.text
        squads.append(created.json()["id"])
    for squad_id in squads:
        assert client.post(f"/squads/{squad_id}/protect").json()["protected"]
    assert client.post(f"/squads/{squads[1]}/protect").json()["protected"] is False
    inherited = client.get("/players", params={"search": player["name"]}).json()["items"][0]
    assert inherited["protected"] is False and inherited["effective_protected"] is True
    segment_id = create_segment(client, {"squad_size": 1})
    assert client.post(f"/segments/{segment_id}/confirm", json={"player_ids": [player["id"]]}).status_code == 422
    assert client.post(f"/players/{player['id']}/protect").json()["protected"] is True
    client.post(f"/squads/{squads[0]}/protect")
    manual = client.get("/players", params={"search": player["name"]}).json()["items"][0]
    assert manual["protected"] is True and manual["effective_protected"] is True


def test_consumed_players_do_not_count_toward_saved_squad_metrics(client):
    player = create_card(client, rating=88)
    squad = client.post("/squads", json={"name": "Para consumir", "player_ids": [player["id"]], "slots": ["MC-1"]}).json()
    segment_id = create_segment(client, {"squad_size": 1})
    result = client.post(f"/segments/{segment_id}/confirm", json={"player_ids": [player["id"]]})
    assert result.status_code == 200
    saved = next(item for item in client.get("/squads").json() if item["id"] == squad["id"])
    assert saved["players"] == [] and saved["rating"] == 0 and saved["chemistry"] == 0
    assert saved["unavailable_players"] == 1 and not saved["complete"]


def test_legacy_slot_numbering_and_later_position_corrections_are_accounted_for(client):
    recommendation = client.post("/squads/recommend").json()
    created = client.post("/squads", json={
        "name": "Plazas antiguas", "player_ids": [p["id"] for p in recommendation["players"]],
        "slots": [row["slot"] for row in recommendation["lineup"]],
    })
    assert created.status_code == 201 and created.json()["complete"]
    squad_id = created.json()["id"]
    with SessionLocal() as db:
        squad = db.get(Squad, squad_id)
        for index, entry in enumerate(squad.players, 1):
            entry.slot = f"{entry.slot.rsplit('-', 1)[0]}-{index}"
        db.commit()
    saved = next(item for item in client.get("/squads").json() if item["id"] == squad_id)
    assert saved["complete"] and not saved["missing_slots"]
    outfield = next(row for row in recommendation["lineup"] if row["position"] != "POR")
    assert client.patch(f"/players/{outfield['player']['id']}", json={"position": "POR", "alternate_positions": []}).status_code == 200
    changed = next(item for item in client.get("/squads").json() if item["id"] == squad_id)
    assert not changed["complete"] and changed["missing_slots"][0]["position"] == outfield["position"]
    assert any(not entry["position_valid"] for entry in changed["players"])


@pytest.mark.parametrize("requirements", [
    {"min_rating": "x"}, {"excluded_player_ids": "1,2"}, {"kind": []},
    {"squad_size": 1, "min_rare": 2}, {"required_positions": {"NOPE": 1}},
    {"kind": "score", "target_score": 100, "current_score": 50},
])
def test_invalid_requirements_reject_the_entire_challenge(client, requirements):
    before = len(client.get("/challenges").json())
    response = client.post("/challenges", json={
        "name": "No crear parcialmente",
        "segments": [{"name": "Válido", "requirements": {"squad_size": 1}},
                     {"name": "Inválido", "requirements": requirements}],
    })
    assert response.status_code == 422, response.text
    assert len(client.get("/challenges").json()) == before


def test_consumption_rejects_duplicates_unreviewed_loans_and_exclusions(client):
    player = create_card(client)
    segment_id = create_segment(client, {"squad_size": 1})
    assert client.post(f"/segments/{segment_id}/confirm", json={"player_ids": [player["id"], player["id"]]}).status_code == 422
    excluded = create_segment(client, {"squad_size": 1, "excluded_player_ids": [player["id"]]})
    assert client.post(f"/segments/{excluded}/confirm", json={"player_ids": [player["id"]]}).status_code == 422
    for field in ("is_loan", "data_reviewed"):
        bad_value = field == "is_loan"
        assert client.patch(f"/players/{player['id']}", json={field: bad_value}).status_code == 200
        assert client.post(f"/segments/{segment_id}/confirm", json={"player_ids": [player["id"]]}).status_code == 422
        assert client.patch(f"/players/{player['id']}", json={field: not bad_value}).status_code == 200


def test_score_progress_is_derived_and_restoration_only_reverses_its_batch(client):
    first = create_card(client, name="Puntos A", gallery_score=40, price=700)
    second = create_card(client, name="Puntos B", gallery_score=60, price=800)
    segment_id = create_segment(client, {"kind": "score", "target_score": 100, "max_items_per_submission": 1})
    optimized = client.post(f"/segments/{segment_id}/optimize", json={"max_solutions": 1}).json()["solutions"][0]
    assert optimized["partial"] and not optimized["will_complete"]
    assert optimized["score_contribution"] == 60 and optimized["remaining_score"] == 40
    assert optimized["total_cost"] == 800
    assert optimized["optimization_score"] != optimized["total_cost"]
    first_result = client.post(f"/segments/{segment_id}/confirm", json={"player_ids": [first["id"]]})
    assert first_result.status_code == 200, first_result.text
    assert not first_result.json()["completed"] and first_result.json()["current_score"] == 40
    assert client.patch(f"/segments/{segment_id}", json={
        "name": "Intento de cambiar progreso", "requirements": {"kind": "score", "target_score": 40},
    }).status_code == 409
    second_result = client.post(f"/segments/{segment_id}/confirm", json={"player_ids": [second["id"]]})
    assert second_result.status_code == 200 and second_result.json()["completed"]
    assert second_result.json()["current_score"] == 100
    submission_id = first_result.json()["submission_id"]
    restored = client.post(f"/submissions/{submission_id}/restore")
    assert restored.status_code == 200 and restored.json()["current_score"] == 60
    assert restored.json()["completed"] is False
    assert client.post(f"/submissions/{submission_id}/restore").status_code == 409
    with SessionLocal() as db:
        assert db.get(Player, first["id"]).deleted is False
        assert db.get(Player, second["id"]).deleted is True
        assert db.get(Player, second["id"]).consumed_by_submission_id == second_result.json()["submission_id"]


def test_score_budget_and_required_players_apply_across_partial_batches(client):
    first = create_card(client, name="Obligatorio", gallery_score=20, price=600)
    second = create_card(client, name="Fuera de presupuesto", gallery_score=20, price=500)
    third = create_card(client, name="Dentro de presupuesto", gallery_score=20, price=400)
    segment_id = create_segment(client, {
        "kind": "score", "target_score": 40, "max_items_per_submission": 1,
        "required_player_ids": [first["id"]], "max_total_value": 1000,
    })
    assert client.post(f"/segments/{segment_id}/confirm", json={"player_ids": [first["id"]]}).status_code == 200
    assert client.post(f"/segments/{segment_id}/confirm", json={"player_ids": [second["id"]]}).status_code == 422
    result = client.post(f"/segments/{segment_id}/confirm", json={"player_ids": [third["id"]]})
    assert result.status_code == 200 and result.json()["completed"]


def test_unknown_gallery_scores_are_not_invented_and_missing_reviews_block_consumption(client):
    player = create_card(client, gallery_score=None)
    segment_id = create_segment(client, {"kind": "score", "target_score": 50, "min_item_rating": 80})
    assert client.post(f"/segments/{segment_id}/optimize", json={}).json()["solutions"] == []
    assert client.post(f"/segments/{segment_id}/confirm", json={"player_ids": [player["id"]]}).status_code == 422
    client.patch(f"/players/{player['id']}", json={"gallery_score": 50, "data_reviewed": False})
    assert client.post(f"/segments/{segment_id}/confirm", json={"player_ids": [player["id"]]}).status_code == 422


def test_two_overlapping_confirms_cannot_both_consume_the_same_card(client):
    player = create_card(client)
    segments = [create_segment(client, {"squad_size": 1}) for _ in range(2)]
    start = Barrier(2)
    def confirm(segment_id):
        start.wait(timeout=5)
        return client.post(f"/segments/{segment_id}/confirm", json={"player_ids": [player["id"]]})
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(confirm, segments))
    assert sum(result.status_code == 200 for result in results) == 1
    assert all(result.status_code in {200, 409, 422} for result in results)
    winner = next(result.json() for result in results if result.status_code == 200)
    with SessionLocal() as db:
        assert db.get(Player, player["id"]).consumed_by_submission_id == winner["submission_id"]
        active = db.scalars(select(Submission).where(Submission.segment_id.in_(segments), Submission.status == "confirmed")).all()
        assert len(active) == 1
    assert client.post(f"/submissions/{winner['submission_id']}/restore").status_code == 200


def test_restore_prevalidates_all_card_owners_before_changing_any_card(client):
    first = create_card(client, name="Primero restaurable")
    second = create_card(client, name="Segundo con propietario distinto")
    segment_id = create_segment(client, {"squad_size": 2})
    response = client.post(f"/segments/{segment_id}/confirm", json={"player_ids": [first["id"], second["id"]]})
    assert response.status_code == 200
    owner = response.json()["submission_id"]
    with SessionLocal() as db:
        conflicting = Submission(segment_id=segment_id, game_version="FC27", status="confirmed", total_cost=0,
                                 snapshot={"players": {str(second["id"]): {"deleted": False}}})
        db.add(conflicting)
        db.flush()
        db.get(Player, second["id"]).consumed_by_submission_id = conflicting.id
        db.commit()
    assert client.post(f"/submissions/{owner}/restore").status_code == 409
    with SessionLocal() as db:
        assert db.get(Player, first["id"]).deleted is True
        assert db.get(Submission, owner).status == "confirmed"


def test_active_edition_isolates_lists_recommendation_confirmation_and_history(client):
    active = create_card(client, name="Solo FC27")
    historical = create_card(client, name="Solo historico")
    segment_id = create_segment(client, {"squad_size": 1})
    with SessionLocal() as db:
        db.get(Player, historical['id']).game_version = 'FC26'
        db.commit()
    assert client.patch('/profile', json={'game_version': 'FC26'}).status_code == 422
    assert historical['id'] not in [p['id'] for p in client.get('/players?limit=500').json()['items']]
    assert client.get('/players?game_version=FC26').status_code == 422
    assert client.get('/club/analysis').json()['game_version'] == 'FC27'
    assert historical['id'] not in [p['id'] for p in client.post('/squads/recommend').json()['players']]
    assert client.post(f"/segments/{segment_id}/confirm", json={'player_ids': [historical['id']]}).status_code == 422
    assert client.post(f"/segments/{segment_id}/confirm", json={'player_ids': [active['id']]}).status_code == 200
    with SessionLocal() as db:
        assert db.get(Player, historical['id']).game_version == 'FC26'
        assert not db.get(Player, historical['id']).deleted


def test_import_confirmation_is_bound_to_file_edition_and_one_use(client):
    content = b"name,rating,position,league,club,nationality\nImportado,83,DC,Liga,Club,Colombia\n"
    def upload(data=None, file_content=content):
        return client.post("/players/import", data=data or {"confirm": "false"},
                           files={"file": ("club.csv", file_content, "text/csv")})
    before = database_snapshot()
    preview = upload()
    assert preview.status_code == 200
    assert database_snapshot() == before
    token = preview.json()["preview_token"]
    assert upload({"confirm": "true"}).status_code == 422
    assert upload({"confirm": "true", "preview_token": token}, content.replace(b"83", b"84")).status_code == 422
    assert upload({"confirm": "true", "preview_token": token + "tampered"}).status_code == 422
    assert client.patch("/profile", json={"game_version": "FC26"}).status_code == 422
    confirmed = upload({"confirm": "true", "preview_token": token})
    assert confirmed.status_code == 200 and confirmed.json()["imported"] == 1
    replay = upload({"confirm": "true", "preview_token": token})
    assert replay.status_code == 200 and replay.json()["already_imported"]
    assert replay.json()["imported"] == 0 and replay.json()["original_imported"] == 1
    assert client.get("/players", params={"search": "Importado"}).json()["total"] == 1
    assert all(not key.startswith("_") for key in client.get("/settings").json())
    assert client.put("/settings/_import_signing_key", json={"secret": "replacement"}).status_code == 422


@pytest.mark.parametrize("patch", [{"rating": None}, {"attributes": {"inventado": 70}}, {"position": "ZZZ"}, {"playstyles_plus": ["A", "B", "C", "D"]}])
def test_invalid_partial_updates_reject_without_mutating_player(client, patch):
    player = create_card(client)
    response = client.patch(f"/players/{player['id']}", json=patch)
    assert response.status_code == 422, response.text
    stored = client.get("/players", params={"search": player["name"]}).json()["items"][0]
    assert stored["rating"] == player["rating"] and stored["position"] == player["position"]
