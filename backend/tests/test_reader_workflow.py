"""Synthetic pipeline, never evidence of real EA compatibility or possession."""
import copy
from datetime import timedelta
from uuid import uuid4
import pytest
from app.models.reader import ReaderGrant
from app.models.entities import Player, now
from app.db.session import SessionLocal
from app.api.reader import canonical_hash
from test_reader import paired, batch
from test_observations import fragments, receive

pytestmark = pytest.mark.catalog_boundary


def following(grant, first, *, name=None, conflict=False):
    cards = copy.deepcopy(first[0]['payload']['records'])
    if name:
        cards = [dict(cards[0], name=name)]
    if conflict:
        cards[0]['tradable'] = True
    events = fragments(grant, records=cards)
    for event in events:
        event['profile'] = first[0]['profile']
        event['payload_hash'] = canonical_hash(event)
    return events


def approve(client, events):
    response = client.post('/reader/observations/'+events[0]['observation_id']+'/review', json=dict(
        confirmation='REVISAR OBSERVACION DOM', context_confirmed=True, enable_incremental=True))
    assert response.status_code == 200, response.text


def test_one_action_persists_real_report_and_never_fakes_browser_permission(client, monkeypatch):
    grant, headers = paired(client, monkeypatch)
    r = client.post('/club/analyze', json={})
    assert r.status_code == 200, r.text
    report = r.json()['report']
    assert report['inventory_count'] == 0
    assert report['stages'][0]['status'] == 'blocked'
    assert report['stages'][1]['status'] == 'pending'
    assert report['main']['unchanged'] and not report['main']['complete']
    assert not report['ea_identity_verified'] and not report['global_complete']
    assert report['metrics']['llm_calls'] == 0
    assert client.get('/reader/workflow', headers=headers).json()['id'] == r.json()['id']
    assert client.post('/reader/workflow/view', headers=headers, json=dict(
        code='ready_sample', source='observed_page_dom', profile_verified=True)).status_code == 422
    assert client.post('/reader/workflow/view', headers=headers, json=dict(
        code='authorization_required', source='observed_page_dom', candidate_regions=2)).status_code == 200
    report = client.get('/club/analysis-workflow').json()['report']
    assert report['modules']['gallery']['birmingham']['acquisition_cost'] is None
    assert report['modules']['gallery']['birmingham']['owned_count'] is None


def test_incremental_trust_conflicts_revocation_pause_and_cancel(client, monkeypatch):
    grant, headers = paired(client, monkeypatch)
    client.post('/club/analyze', json={})
    events = fragments(grant)
    receive(client, headers, events)
    assert client.get('/players').json()['total'] == 0
    approve(client, events)
    assert client.get('/players').json()['total'] == 11
    main = client.get('/squads/main').json()
    new = following(grant, events, name='Nueva sintética')
    receipt = receive(client, headers, new)
    assert receipt['status'] == 'reviewed'
    assert client.get('/players').json()['total'] == 12
    for _ in range(20):
        assert receive(client, headers, new) == receipt
    assert client.get('/players').json()['total'] == 12
    repeat = following(grant, events)
    receive(client, headers, repeat)
    assert client.get('/players').json()['total'] == 12
    conflict = following(grant, events, conflict=True)
    receive(client, headers, conflict)
    detail = client.get('/reader/observations/'+conflict[0]['observation_id']).json()
    assert len(detail['pending_records']) == 1
    assert detail['admission'] == 'approved_profile_rules'
    assert client.get('/squads/main').json() == main
    refreshed = client.post('/reader/workflow/refresh', headers=headers, json={})
    assert refreshed.status_code == 200, refreshed.text
    report = refreshed.json()['report']
    assert report['source_counts'] == {'synthetic_dom':12}
    assert any(len(g['squad']['lineup']) == 11 for g in report['modules']['squads']['result']['groups'])
    assert report['main']['unchanged']
    assert client.post('/club/analysis-workflow/action', json={'action':'pause'}).status_code == 200
    paused = following(grant, events, name='No admitir pausada')
    assert receive(client, headers, paused)['status'] == 'review_required'
    assert client.get('/players').json()['total'] == 12
    assert client.post('/club/analysis-workflow/action', json={'action':'resume'}).status_code == 200
    changed_profile = following(grant, events, name='Perfil editado')
    changed_profile[0]['profile'] = {**changed_profile[0]['profile'], 'revision':2}
    changed_profile[0]['payload_hash'] = canonical_hash(changed_profile[0])
    assert receive(client, headers, changed_profile)['status'] == 'review_required'
    assert client.post('/club/analysis-workflow/action', json={'action':'cancel'}).json()['approved_profiles'] == 0
    assert client.post('/reader/workflow/refresh', headers=headers, json={}).status_code == 409
    assert client.post('/reader/grants/'+grant['context_binding']+'/revoke', json={}).status_code == 200
    assert client.get('/reader/workflow', headers=headers).status_code == 401


def test_300_records_fragments_and_incremental_ambiguity_staleness(client, monkeypatch):
    grant, headers = paired(client, monkeypatch)
    seed = fragments(grant)
    receive(client, headers, seed)
    approve(client, seed)
    cards = [dict(batch(grant)['records'][i%11], name=f'Lista sintética {i}') for i in range(300)]
    events = fragments(grant, records=cards)
    for event in events:
        event['profile'] = seed[0]['profile']
        event['payload_hash'] = canonical_hash(event)
    assert len(events) == 10
    receive(client, headers, events[1:])
    assert client.get('/players').json()['total'] == 11
    assert receive(client, headers, events[:1])['status'] == 'reviewed'
    assert client.get('/players').json()['total'] == 311

    # Ambiguous simultaneous rows never become auto-approved physical copies.
    ambiguous = fragments(grant, records=[dict(cards[0], name='Gemela'),dict(cards[0], name='Gemela')])
    ambiguous[0]['profile'] = seed[0]['profile']
    ambiguous[0]['payload_hash'] = canonical_hash(ambiguous[0])
    receive(client, headers, ambiguous)
    detail = client.get('/reader/observations/'+ambiguous[0]['observation_id']).json()
    assert len(detail['pending_records']) == 2
    assert client.get('/players').json()['total'] == 311
    old = following(grant, seed, name='Antigua')
    old[0]['observed_at'] = (now()-timedelta(hours=2)).isoformat()
    old[0]['payload_hash'] = canonical_hash(old[0])
    assert receive(client, headers, old)['status'] == 'historical'
    assert client.get('/players').json()['total'] == 311


def test_new_entry_preserves_checkpoint_but_requires_current_permissions(client, monkeypatch):
    grant, headers = paired(client, monkeypatch)
    first = client.post('/club/analyze', json={}).json()
    client.post('/club/analysis-workflow/action', json={'action':'pause'})
    with SessionLocal() as db:
        context_id = db.get(ReaderGrant, grant['context_binding']).club_context_id
    entry = client.post('/app/entries', json=dict(nonce=str(uuid4()),mode='assisted',context_id=context_id))
    assert entry.status_code == 200, entry.text
    client.headers['X-App-Entry'] = str(entry.json()['entry_id'])
    checkpoint = client.get('/club/analysis-workflow').json()
    assert checkpoint['id'] == first['id'] and checkpoint['status'] == 'paused'
    assert checkpoint['report']['main'] == first['report']['main']
    resumed = client.post('/club/analysis-workflow/action', json={'action':'resume'})
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()['approved_profiles'] == 0
