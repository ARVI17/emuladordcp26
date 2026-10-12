"""Synthetic contract regressions; these do not demonstrate an EA integration."""
import pytest
from app.db.session import SessionLocal
from app.models.entities import Profile, now
from app.models.planner import ClubContext, SyncRun
from app.services.sync import RemoteRead
from test_planner import fake_run, remote, publish


@pytest.mark.catalog_boundary
def test_disconnected_account_never_uses_manual_balance(client):
    client.patch('/profile', json={'name': 'Manual', 'coins': 325000})
    account = client.get('/dashboard').json()['account']
    assert account['identity_verified'] is False
    assert account['name'] is None and account['coins'] is None
    assert account['observed_copies'] is None and account['observed_at'] is None
    assert set(account['progress'].values()) == {'unavailable'}
    caps = client.get('/connections/capabilities').json()
    assert caps['authorization_supported'] is False
    assert caps['opening_official_app_links_this_project'] is False
    assert client.post('/connections/ea_community/authorize').status_code == 409


def test_snapshot_name_and_balance_reach_dashboard_together(client):
    context, run = fake_run(client)
    reading = remote(club_name='Nombre remoto sintético', coins=48763)
    snapshot = publish(run, reading)
    # Manual preferences and later mutable context values are not this observation.
    with SessionLocal() as db:
        profile = Profile(club_context_id=context, game_version='FC27', origin='manual', name='Manual', coins=325000)
        db.add(profile)
        db.get(ClubContext, context).coins = 987654
        db.get(ClubContext, context).name = 'Cambio sin nueva lectura'
        db.commit()
    result = client.get('/dashboard').json()
    assert result['mode'] == 'live'
    assert result['account']['name'] == reading.club_name
    assert result['account']['coins'] == 48763
    assert result['account']['snapshot_id'] == snapshot
    assert result['account']['observed_at'] == reading.observed_at.isoformat()
    assert all(v == 'unavailable' for v in result['account']['progress'].values())
    _, run = fake_run(client, context)
    publish(run, remote(complete=False, coins=None, coverage={'inventory': {'complete': False}}))
    assert client.get('/dashboard').json()['account']['coins'] is None


@pytest.mark.catalog_boundary
def test_observed_copy_summary_does_not_disappear_outside_public_catalog(client):
    context, run = fake_run(client)
    # No witness catalog: retain the observation even though calculations remain gated.
    read = RemoteRead(provider='test', subject='subject-a', club_key='club-a', platform='PC', game_version='FC27',
        revision='new', end_revision='new', observed_at=now(),
        coverage={'inventory': {'complete': False}}, pagination={}, items=[{
            'copy_id':'unknown-copy', 'athlete_id':'documented-athlete-code', 'variant_id':'outside-sample',
            'location':'club', 'fields':{'name':'Nombre localizado', 'rating':90, 'position':'MC',
                'card_type':'Oro raro', 'is_evolution':True, 'is_loan':False, 'tradable':False}}])
    publish(run, read)
    account = client.get('/dashboard').json()['account']
    assert account['observed_copies'] == 1 and not account['inventory_complete']
    assert client.get('/club/analysis').status_code == 409
    assert account['coins'] is None
    with SessionLocal() as db:
        row = db.get(SyncRun, run)
        row.manifest = {key:value for key,value in row.manifest.items() if key != 'account'}
        db.commit()
    assert client.get('/dashboard').json()['account']['name'] is None


def test_build_metadata_is_public_and_not_an_ea_status(client):
    client.cookies.clear()
    response = client.get('/build')
    assert response.status_code == 200
    assert response.json()['edition'] == 'FC27'
    assert set(response.json()) == {'edition','revision','built_at','environment','source_dirty'}
    assert response.headers['cache-control'] == 'no-store'


def test_resource_facts_keep_zero_unknown_and_item_types_distinct(client):
    context, run = fake_run(client)
    read = remote(fc_points=0, unassigned_items=[{'item_id': 'a', 'kind': 'player'}, {'item_id': 'b', 'kind': 'consumable'}],
                  coverage={'inventory': {'complete': True}, 'coins': {'complete': True}, 'fc_points': {'complete': True}, 'unassigned': {'complete': True}})
    publish(run, read)
    account = client.get('/dashboard').json()['account']
    assert account['fc_points'] == 0 and account['unassigned_count'] == 2
    assert account['unassigned_types'] == {'player': 1, 'consumable': 1}
    assert account['facts']['unassigned_count']['source'] == 'test'
    assert account['facts']['fc_points']['status'] == 'observed'
    assert client.get('/dashboard').json()['account'] == account  # Polling is not a remote observation.
    _, run = fake_run(client, context)
    publish(run, remote(club_name=None, coverage={'inventory': {'complete': False}}))
    account = client.get('/dashboard').json()['account']
    assert account['name'] is None and account['fc_points'] is None and account['unassigned_count'] is None


def test_read_rejects_unsupported_resource_coverage_and_duplicate_items():
    with pytest.raises(ValueError, match='FC Points'):
        remote(coverage={'fc_points': {'complete': True}})
    with pytest.raises(ValueError, match='Artículos sin asignar'):
        remote(unassigned_items=[{'item_id': 'same', 'kind': 'player'}, {'item_id': 'same', 'kind': 'consumable'}])


def test_public_validation_is_spanish_and_does_not_echo_input(client):
    result = client.patch('/profile', json={'coins': 'not-a-number-private'})
    assert result.status_code == 422
    assert result.json()['errors'][0]['message'] == 'Escribe un número entero'
    assert 'not-a-number-private' not in result.text


def test_authorized_synthetic_adapter_publishes_only_supported_resource_domains(client, monkeypatch):
    from test_planner import wired_adapter
    reading = remote(fc_points=0, unassigned_items=[], coverage={'inventory': {'complete': True}, 'fc_points': {'complete': True}, 'unassigned': {'complete': True}})
    context, adapter = wired_adapter(client, monkeypatch, lambda identity, **kw: reading)
    adapter.coverage = frozenset(reading.coverage)
    response = client.post('/app/entries', json={'nonce': 'resources-synthetic', 'mode': 'live', 'reason': 'retry'})
    assert response.status_code == 200
    client.headers['X-App-Entry'] = str(response.json()['entry_id'])
    account = client.get('/dashboard').json()['account']
    assert account['fc_points'] == 0 and account['unassigned_count'] == 0 and account['coins'] is None
    assert set(account['progress'].values()) == {'unavailable'}
