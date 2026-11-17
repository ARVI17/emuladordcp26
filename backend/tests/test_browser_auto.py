"""Local synthetic DOM snapshots; never evidence of personal EA acceptance."""
from copy import deepcopy
from datetime import timedelta
from uuid import uuid4
import pytest
from app.models.entities import now
from test_assisted import enter

pytestmark = pytest.mark.catalog_boundary
EXTENSION = 'b'*32
POSITIONS = ['POR','LD','DFC','DFC','LI','MC','MC','MC','ED','DC','EI']
SLOTS = ['POR-1','LD-1','DFC-1','DFC-2','LI-1','MC-1','MC-2','MC-3','ED-1','DC-1','EI-1']


def setup(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, 'cors_origins', settings.cors_origins+',http://testserver')
    entry = enter(client)
    response = client.post('/browser-auto/settings', json=dict(extension_id=EXTENSION, enabled=True,
        protect_main=True, confirmation='ACTIVAR LECTURA LOCAL AUTOMATICA'))
    assert response.status_code == 200, response.text
    return entry


def start(client):
    response = client.post('/browser-auto/start', json={})
    assert response.status_code == 200, response.text
    ticket = response.json()
    claimed = client.post('/reader/claim', headers={'X-Reader-Extension':EXTENSION},
        json={k:ticket[k] for k in ('pairing_id','code')})
    assert claimed.status_code == 200, claimed.text
    return ticket, {'X-Reader-Extension':EXTENSION,'Authorization':'Bearer '+claimed.json()['credential']}


def snapshot(ticket):
    cards = [dict(ordinal=i,name=f'Auto sintético {i}',rating=88,position=POSITIONS[i%11],
        card_type='Oro',league='Liga prueba',club='Club prueba',nationality='País prueba',
        is_loan=False,is_evolution=False,tradable=True,location='club',
        attributes={k:80 for k in ('pace','shooting','passing','dribbling','defending','physical')}) for i in range(20)]
    return dict(request_id=ticket['request_id'],reader_version='ea-visible-1',edition='FC27',edition_basis='owner_selected',
        club_fingerprint='a'*64,club_name='Club sintético',observed_at=now().isoformat(),inventory=cards,
        squad=[{**c,'location':'squad','slot':SLOTS[i] if i<11 else f'BENCH-{i-10}'} for i,c in enumerate(cards[:18])],
        formation='4-3-3',active_squad_observed=True,inventory_complete=False)


def post(client, headers, data):
    response = client.post('/browser-auto/publish', headers=headers, json=data)
    assert response.status_code == 200, response.text
    return response.json()


def test_two_reopens_twenty_ids_and_eighteen_protections(client, monkeypatch):
    entry = setup(client, monkeypatch)
    first_ids = None
    previous_observed = None
    for iteration in range(3):
        if iteration:
            reopened = client.post('/app/entries',json={'nonce':str(uuid4()),'mode':'assisted','context_id':entry['club_context_id']})
            assert reopened.status_code == 200
            client.headers['X-App-Entry'] = str(reopened.json()['entry_id'])
            assert client.get('/browser-auto/status').json()['enabled']
        ticket, headers = start(client)
        data = snapshot(ticket)
        # Reordering the list never changes copy correspondence.
        if iteration: data['inventory'].reverse()
        result = post(client, headers, data)
        assert result['status'] == 'updated'
        assert post(client, headers, data)['result'] == result['result']
        cards = client.get('/players?limit=100').json()
        assert cards['total'] == 20
        ids = {c['id'] for c in cards['items']}
        if first_ids is None: first_ids = ids
        assert ids == first_ids
        assert all(c['ownership_source']=='user_authorized_browser' for c in cards['items'])
        main = client.get('/squads/main').json()
        assert main['complete'] and len(main['protected_copy_ids']) == 18
        assert len([m for m in main['snapshot']['members'] if m['slot'].startswith('BENCH-')]) == 7
        assert len([c for c in cards['items'] if c['effective_protected']]) == 18
        for identifier in main['protected_copy_ids']:
            assert client.delete(f'/players/{identifier}').status_code == 409
        observed = result['result']['observed_at']
        assert previous_observed is None or observed > previous_observed
        previous_observed = observed
        changed = deepcopy(data);changed['inventory'][0]['rating']=89
        assert client.post('/browser-auto/publish',headers=headers,json=changed).status_code == 409


def test_ambiguous_missing_and_retired_are_never_created_or_merged(client, monkeypatch):
    setup(client, monkeypatch)
    ticket, headers = start(client)
    data = snapshot(ticket);data.update(squad=[],formation=None,active_squad_observed=False)
    data['inventory'][1] = {**data['inventory'][0], 'ordinal':1}
    data['inventory'][2]['card_type'] = None
    result = post(client, headers, data)
    assert result['status']=='partial' and len(result['result']['pending'])==3
    assert client.get('/players').json()['total']==17
    identifier = result['result']['inventory_ids'][0]
    assert client.delete(f'/players/{identifier}').status_code==200
    ticket, headers = start(client);data['request_id']=ticket['request_id'];data['observed_at']=now().isoformat()
    result=post(client,headers,data)
    assert any(r['reason']=='copy_unavailable' for r in result['result']['pending'])
    assert client.get('/players').json()['total']==16
    assert not client.get('/squads/main').json()['identified']


def test_cancel_revoke_context_and_failure_preserve_last_snapshot(client, monkeypatch):
    setup(client,monkeypatch)
    ticket,headers=start(client);result=post(client,headers,snapshot(ticket))
    ids=result['result']['inventory_ids']
    next_ticket,next_headers=start(client)
    assert client.post('/browser-auto/publish',headers=headers,json=snapshot(ticket)).status_code==401
    response=client.post('/browser-auto/failure',headers=next_headers,json={'request_id':next_ticket['request_id'],'reason':'login_required'})
    assert response.status_code==200 and response.json()['result']['inventory_ids']==ids
    assert client.post('/browser-auto/publish',headers=next_headers,json=snapshot(next_ticket)).status_code==409
    next_ticket,next_headers=start(client)
    assert client.post('/browser-auto/cancel',json={}).status_code==200
    assert client.post('/browser-auto/publish',headers=next_headers,json=snapshot(next_ticket)).status_code==401
    next_ticket,next_headers=start(client);other=snapshot(next_ticket);other['club_fingerprint']='c'*64
    assert client.post('/browser-auto/publish',headers=next_headers,json=other).status_code==409
    enter(client,'Otro club')
    assert client.post('/browser-auto/publish',headers=next_headers,json=snapshot(next_ticket)).status_code==401
    assert client.get('/players').json()['total']==0


def test_requires_consent_and_does_not_expose_public_ingestion(client,monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings,'cors_origins',settings.cors_origins+',http://testserver')
    enter(client)
    assert client.post('/browser-auto/start',json={}).status_code==409
    assert client.post('/browser-auto/publish',json=snapshot({'request_id':str(uuid4())})).status_code==401
    setup(client,monkeypatch)
    ticket,headers=start(client);data=snapshot(ticket)
    data['observed_at']=(now()-timedelta(minutes=10)).isoformat()
    assert client.post('/browser-auto/publish',headers=headers,json=data).status_code==409
    data=snapshot(ticket);data['inventory'][0]['existing_player_id']=1
    assert client.post('/browser-auto/publish',headers=headers,json=data).status_code==422
    data=snapshot(ticket);data['club_name']='password secreto'
    assert client.post('/browser-auto/publish',headers=headers,json=data).status_code==422
    assert client.get('/players').json()['total']==0


def test_partial_does_not_refresh_main_or_remove_absent_copies_and_preserves_reserves(client,monkeypatch):
    setup(client,monkeypatch)
    ticket,headers=start(client);first=post(client,headers,snapshot(ticket))
    protected=first['result']['protected_copy_ids']
    ticket,headers=start(client);data=snapshot(ticket)
    data.update(squad=[],formation=None,active_squad_observed=False)
    data['inventory'].pop()
    data['inventory'][0]['attributes']['defending']=99
    partial=post(client,headers,data)
    assert partial['status']=='partial' and not partial['result']['main_complete']
    assert partial['result']['protected_copy_ids']==protected
    assert partial['result']['pending']==[dict(scope='inventory',ordinal=0,reason='known_facts_changed')]
    assert client.get('/players').json()['total']==20
    ticket,headers=start(client);data=snapshot(ticket)
    # Reserves can be outside the first twenty. They are additional copies, not duplicates.
    reserves=[deepcopy(data['inventory'][18]),deepcopy(data['inventory'][19])]
    for i in (20,21):
        reserves.append({**deepcopy(data['inventory'][0]),'ordinal':i,'name':f'Reserva sintética {i}'})
    for n,card in enumerate(reserves):
        data['squad'].append({**card,'location':'squad','slot':f'RESERVE-{n+1}'})
    result=post(client,headers,data)
    assert result['status']=='updated' and len(result['result']['protected_copy_ids'])==22
    assert client.get('/players').json()['total']==22
    for identifier in result['result']['protected_copy_ids']:
        assert client.delete(f'/players/{identifier}').status_code==409
