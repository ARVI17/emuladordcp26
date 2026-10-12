from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.entities import Player, Squad, Submission
from app.models.squad_safety import MainSquadState
from app.services.locks import resource_locks


def card(client, **extra):
    response = client.post('/players', json=dict(name='Copia para prueba', rating=80, position='MC', league='Liga de prueba', club='Club de prueba', nationality='Colombia', **extra))
    assert response.status_code == 201, response.text
    return response.json()


def segment(client):
    row = client.post('/challenges', json={'name': 'DCP sintético', 'segments': [{'name': 'Una copia', 'requirements': {'squad_size': 1}}]})
    assert row.status_code == 201, row.text
    return row.json()['segments'][0]['id']


def choose_main(client):
    rec = client.post('/squads/recommend', json={'bench_size': 7}).json()
    ids = [m['player']['id'] for m in rec['lineup']]+[p['id'] for p in rec['bench']]
    slots = [m['slot'] for m in rec['lineup']]+[f'BENCH-{n+1}' for n in range(len(rec['bench']))]
    spare = next(p for p in client.get('/players?limit=500').json()['items'] if p['id'] not in ids)
    saved = client.post('/squads', json={'name': 'Principal revisada', 'formation': rec['formation'], 'player_ids': ids+[spare['id']], 'slots': slots+['RESERVE-1']})
    assert saved.status_code == 201, saved.text
    sid = saved.json()['id']
    state = client.get('/squads/main').json()
    chosen = client.post(f'/squads/{sid}/main', json={'expected_state_hash': state['state_hash'], 'complete': True, 'phrase': f'PROTEGER PRINCIPAL {sid}'})
    assert chosen.status_code == 200, chosen.text
    return chosen.json(), saved.json()


def test_principal_covers_starters_bench_reserves_and_legacy_paths(client):
    state, squad = choose_main(client)
    ids = {r['player']['id'] for r in squad['players']}
    assert ids <= set(state['protected_copy_ids'])
    sid = segment(client)
    for member in (squad['players'][0], next(p for p in squad['players'] if p['slot']=='BENCH-1'), next(p for p in squad['players'] if p['slot']=='RESERVE-1')):
        pid = member['player']['id']
        assert client.delete(f'/players/{pid}').status_code == 409
        assert client.post(f'/duplicates/{pid}/used').status_code == 409
        assert client.post(f'/segments/{sid}/confirm', json={'player_ids': [pid]}).status_code == 422
        assert client.post(f'/segments/{sid}/optimize', json={'allow_protected_ids': [pid]}).status_code == 422
    assert client.post(f"/squads/{squad['id']}/protect").status_code == 409
    assert client.patch(f"/squads/{squad['id']}/tactics", json={'instructions': 'Cambio incidental'}).status_code == 409
    assert client.get('/squads/main').json() == state


def test_playing_and_saving_an_alternative_preserves_main_exactly(client):
    state, squad = choose_main(client)
    pid = squad['players'][0]['player']['id']
    rec = client.post('/squads/recommend', json={'locked_player_ids': [pid]}).json()
    assert pid in [p['id'] for p in rec['players']]
    comparison = rec['main_comparison']
    assert comparison['available'] and comparison['additional_cost'] == 0
    assert len(comparison['rows']) == 11 and all(r['delta'] == round(r['proposed_fit']-r['main_fit'], 2) for r in comparison['rows'])
    copy = client.post(f"/squads/{squad['id']}/duplicate")
    assert copy.status_code == 200 and copy.json()['id'] != squad['id']
    assert client.get('/squads/main').json() == state


def test_same_variant_second_copy_is_consumable_and_missing_review_is_rejected(client):
    state, squad = choose_main(client)
    base = squad['players'][0]['player']
    other = client.post('/players', json={k: base[k] for k in ('name', 'rating', 'position', 'league', 'club', 'nationality', 'card_id', 'card_type', 'game_version')}).json()
    assert other['id'] not in state['protected_copy_ids']
    sid = segment(client)
    assert client.post(f'/segments/{sid}/confirm', json={'player_ids': [other['id']]}).status_code == 409
    review = client.post(f'/segments/{sid}/review', json={'player_ids': [other['id']]}).json()
    result = client.post(f'/segments/{sid}/confirm', json={'player_ids': [other['id']], 'review_token': review['review_token']})
    assert result.status_code == 200, result.text
    assert client.get('/squads/main').json() == state


def test_unknown_main_allows_simulation_but_blocks_confirmation(client):
    with SessionLocal() as db:
        db.delete(db.scalar(select(MainSquadState)))
        db.commit()
    p = card(client)
    sid = segment(client)
    preview = client.post(f'/segments/{sid}/optimize', json={})
    assert preview.status_code == 200 and not preview.json()['main']['complete']
    assert preview.json()['warnings']
    assert client.post(f'/segments/{sid}/confirm', json={'player_ids': [p['id']]}).status_code == 409


def test_stale_principal_selection_and_dcp_are_rejected(client):
    p = card(client)
    sid = segment(client)
    token = client.post(f'/segments/{sid}/review', json={'player_ids': [p['id']]}).json()['review_token']
    before = client.get('/squads/main').json()
    state, squad = choose_main(client)
    assert client.post(f"/squads/{squad['id']}/main", json={'expected_state_hash': before['state_hash'], 'complete': True, 'phrase': f"PROTEGER PRINCIPAL {squad['id']}"}).status_code == 409
    assert client.post(f'/segments/{sid}/confirm', json={'player_ids': [p['id']], 'review_token': token}).status_code in {409, 422}


def test_protections_survive_quarantine_and_cannot_be_bypassed_by_review_exception(client):
    state, squad = choose_main(client)
    pid = squad['players'][0]['player']['id']
    with SessionLocal() as db:
        p = db.get(Player, pid)
        p.validation_status = 'pending_verification'
        db.commit()
    current = client.get('/squads/main').json()
    assert not current['complete'] and pid in current['protected_copy_ids']
    from fastapi import HTTPException
    import pytest
    with SessionLocal() as db:
        db.info.update(club_context_id=1, reviewed_exception_ids={pid})
        p = db.get(Player, pid, execution_options={'include_quarantine': True})
        p.deleted = True
        with pytest.raises(HTTPException):
            db.commit()


def test_filters_persist_and_unknown_price_or_protections_never_enter(client):
    p = card(client, price=None)
    sid = segment(client)
    filters = {'min_rating': 79, 'max_rating': 81, 'max_price': 1000, 'league': 'Liga de prueba'}
    assert client.put('/dcp/preferences', json=filters).status_code == 200
    assert client.get('/dcp/preferences').json()['max_price'] == 1000
    assert client.post(f'/segments/{sid}/optimize', json={'filters': filters}).json()['solutions'] == []
    assert client.patch(f"/players/{p['id']}", json={'price': 900}).status_code == 200
    solution = client.post(f'/segments/{sid}/optimize', json={'filters': filters}).json()['solutions'][0]
    assert solution['player_ids'] == [p['id']]
    assert client.post(f"/players/{p['id']}/protect").status_code == 200
    assert client.post(f'/segments/{sid}/confirm', json={'player_ids': [p['id']], 'review_token': solution['review_token']}).status_code == 422
    excluded = client.get('/dcp/exclusions?limit=100').json()['items']
    assert any(row['id'] == p['id'] and not row['consumable'] for row in excluded)


def test_concurrent_principal_switch_invalidates_old_confirm_under_postgres_lock(client):
    p = card(client)
    sid = segment(client)
    token = client.post(f'/segments/{sid}/review', json={'player_ids': [p['id']]}).json()['review_token']
    gate = Barrier(2)
    def mutate():
        with SessionLocal() as db, resource_locks(db, 'inventory'):
            row = db.scalar(select(MainSquadState))
            row.revision += 1
            gate.wait(timeout=5)
            db.commit()
    with ThreadPoolExecutor(max_workers=1) as pool:
        writer = pool.submit(mutate)
        gate.wait(timeout=5)
        response = client.post(f'/segments/{sid}/confirm', json={'player_ids': [p['id']], 'review_token': token})
        writer.result()
    assert response.status_code == 409
    with SessionLocal() as db:
        assert not db.get(Player, p['id']).deleted
        assert db.scalar(select(Submission.id).where(Submission.segment_id == sid)) is None


def test_rare_valuable_and_pending_filters_never_unlock_consumption(client):
    from app.services.dcp_review import matches
    from app.schemas.api import DcpFilters
    p = card(client, rare=True, tradable=True, price=None)
    with SessionLocal() as db:
        copy = db.get(Player, p['id'])
        assert matches(copy, DcpFilters(rare=True))
        assert not matches(copy, DcpFilters(rare=False))
        filters = DcpFilters(preset='keep_valuable_tradables', max_price=1000)
        assert not matches(copy, filters)
        copy.price = 999
        assert matches(copy, filters)
        copy.price = 1001
        assert not matches(copy, filters)
        copy.tradable = False
        assert matches(copy, filters)
        copy.validation_status = 'pending_verification'
        db.commit()
    # Inspection of a pending copy never changes its admission or availability.
    assert any(row['id'] == p['id'] and not row['consumable'] for row in client.get('/dcp/exclusions?show_pending=true&limit=100').json()['items'])
    assert all(row['id'] != p['id'] for row in client.get('/players?limit=500').json()['items'])
