"""Synthetic internal reads: no catalog witnesses, EA access or HTTP proof upload."""
from datetime import timedelta
import pytest
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.entities import Player, now
from app.models.catalog import CardVariant
from app.models.planner import InventorySnapshot
from app.services.sync import RemoteRead
from test_planner import fake_run, publish

pytestmark = pytest.mark.catalog_boundary
POSITIONS = ['POR', 'LD', 'DFC', 'DFC', 'LI', 'MC', 'MC', 'MC', 'ED', 'DC', 'EI']


def item(index, **extra):
    fields = dict(name=f'Nombre localizado {index}', rating=82, position=POSITIONS[index % 11],
        card_type='Etiqueta localizada', league='Liga sintética', club='Club sintético', nationality='Colombia',
        tradable=False, is_loan=False, is_evolution=False, rare=True, special=False, chemistry=0)
    fields.update(extra)
    return dict(copy_id=f'copy-{index}', athlete_id=f'athlete-{index}', variant_id=f'outside-{index}', location='club', fields=fields)


def reading(items, complete=True):
    return RemoteRead(provider='test', subject='subject-a', club_key='club-a', platform='PC', game_version='FC27',
        revision='r', end_revision='r', observed_at=now()-timedelta(seconds=1), coverage={'inventory': {'complete': complete}},
        pagination={'documented_end': True, 'all_locations': True, 'expected_count': len(items)} if complete else {}, items=items)


def test_all_observed_copies_are_admitted_before_pagination_without_catalog_limit(client):
    context, run = fake_run(client)
    items = [item(n) for n in range(45)]
    same = item(0)
    same['copy_id'] = 'second-copy'
    evo = item(0, rating=93, is_evolution=True, base_card_id='outside-0', attributes={'passing': 95})
    evo['copy_id'], evo['variant_id'] = 'evolved-copy', 'individual-evo'
    publish(run, reading([*items, same, evo]))
    pages = [client.get(f'/players?limit=20&offset={offset}').json() for offset in (0, 20, 40)]
    rows = [p for page in pages for p in page['items']]
    assert all(page['total'] == 47 for page in pages) and len({p['id'] for p in rows}) == 47
    assert len([p for p in rows if p['athlete_id'] == 'athlete-0']) == 3
    evolution = next(p for p in rows if p['card_id'] == 'individual-evo')
    assert evolution['rating'] == 93 and evolution['attributes'] == {'passing': 95}
    assert all(p['ownership_source'] == 'observed' for p in rows)
    assert client.get('/dashboard').json()['counts']['players'] == 47
    rec = client.post('/squads/recommend', json={}).json()
    assert rec['complete'] and len(rec['lineup']) == 11
    assert len({p['player']['athlete_id'] for p in rec['lineup']} | {p['athlete_id'] for p in rec['bench']}) == 18
    assert client.get('/dashboard').json()['account']['progress']['objectives'] == 'unavailable'
    with SessionLocal() as db:
        assert db.scalar(select(CardVariant.id).where(CardVariant.variant_id == 'individual-evo')) is None


def test_catalog_expiry_preserves_observed_possession_and_stale_read_still_blocks_actions(client):
    context, run = fake_run(client)
    sid = publish(run, reading([item(n) for n in range(18)]))
    before = client.get('/players').json()['total']
    with SessionLocal() as db:
        for row in db.scalars(select(CardVariant)):
            row.valid_until = now()-timedelta(days=1)
        db.get(InventorySnapshot, sid).observed_at = now()-timedelta(hours=1)
        db.commit()
    assert client.get('/players').json()['total'] == before == 18
    assert client.get('/club/analysis').status_code == 409
    assert client.post('/squads/recommend', json={}).status_code == 409


def test_observed_preferences_are_editable_but_facts_and_evidence_cannot_be_forged(client):
    _, run = fake_run(client)
    publish(run, reading([item(0)]))
    original = client.get('/players').json()['items'][0]
    response = client.patch(f"/players/{original['id']}", json={'notes': 'Preferencia propia', 'favorite': True, 'price': 900})
    assert response.status_code == 200, response.text
    assert response.json()['variant_evidence'] == original['variant_evidence']
    assert client.patch(f"/players/{original['id']}", json={'rating': 99}).status_code == 409
    assert client.patch(f"/players/{original['id']}", json={'validation_status': 'provider_verified'}).status_code == 422
    assert client.post('/players', json={**item(1)['fields'], 'game_version': 'FC27', 'card_id': 'outside-1', 'data_source': 'test'}).status_code == 202
    assert client.get('/players').json()['total'] == 1


def test_missing_metadata_is_not_inferred_from_previous_read_or_used_by_dcp(client):
    context, run = fake_run(client)
    publish(run, reading([item(0, attributes={'passing': 99}, gallery_score=500)]))
    stripped = item(0)
    stripped['fields'] = {key: value for key, value in stripped['fields'].items() if key in {'name', 'rating', 'position', 'tradable', 'is_loan', 'is_evolution'}}
    _, run = fake_run(client, context)
    publish(run, reading([stripped]))
    row = client.get('/players').json()['items'][0]
    assert row['attributes'] == {} and row['gallery_score'] is None and row['league'] == 'No disponible'
    assert {'rare', 'special', 'club', 'league', 'chemistry'}.issubset(row['metadata_pending'])
    assert row['rare'] is None and row['special'] is None and row['chemistry'] is None
    from app.optimizers.sbc import solve, validate_solution
    with SessionLocal() as db:
        p = db.get(Player, row['id'])
        assert solve([p], {'squad_size': 1})
        assert not solve([p], {'squad_size': 1, 'max_leagues': 1})
        assert validate_solution([p], {'squad_size': 1, 'max_leagues': 1})


def test_remote_proof_requires_its_mapping_and_matching_identity(client):
    _, run = fake_run(client)
    publish(run, reading([item(0)]))
    row = client.get('/players').json()['items'][0]
    # Internal tamper simulates a broken row; HTTP cannot write this evidence.
    with SessionLocal() as db:
        p = db.get(Player, row['id'])
        p.rating = 99
        db.commit()
    assert client.get('/players').json()['total'] == 0


def test_gallery_keeps_observed_history_without_catalog_and_never_records_loan_as_owned(client):
    context, run = fake_run(client)
    publish(run, reading([item(0), item(1, is_loan=True)]))
    from app.services.gallery import record_player
    with SessionLocal() as db:
        db.info['club_context_id'] = context
        for p in db.scalars(select(Player).where(Player.club_context_id == context)):
            record_player(db, p)
        db.commit()
    result = client.get('/gallery/entries').json()
    assert len(result['items']) == 1 and result['items'][0]['card_id'] == 'outside-0'
    _, run = fake_run(client, context)
    publish(run, reading([]))
    assert client.get('/players?availability=available').json()['total'] == 0
    assert client.get('/players?availability=absent&limit=1').json()['total'] == 2
    assert client.get('/dashboard').json()['counts']['players'] == 0
    result = client.get('/gallery/entries').json()
    assert len(result['items']) == 1 and not result['items'][0]['owned']
