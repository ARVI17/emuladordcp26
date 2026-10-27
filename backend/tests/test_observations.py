"""Infrastructure evidence, always synthetic. Does not certify an EA profile."""
import copy
from datetime import timedelta
from uuid import uuid4
import pytest
from sqlalchemy import select, func
from app.api.reader import canonical_hash
from app.services.observations import digest_json
from app.models.entities import Player, now
from app.models.reader import ReaderEvent, ReaderObservation
from app.db.session import SessionLocal
from test_reader import paired, batch

pytestmark = pytest.mark.catalog_boundary


def fragments(grant, domain='inventory', records=None):
    if records is None:
        records = batch(grant)['records']
    if domain == 'account':
        pieces = [dict(domain=domain, club_name='Club sintético', balance=0)]
    else:
        pieces = [dict(domain=domain, records=[{**r, 'ordinal':j} if domain in {'inventory','detail','squad'} else r
            for j,r in enumerate(records[i:i+30])]) for i in range(0,len(records),30)]
    common = dict(schema_version=2, reader_version='bounded-region-2', observation_id=str(uuid4()),
        context_binding=grant['context_binding'],stream_id=str(uuid4()),document_ref=str(uuid4()),
        observed_at=now().isoformat(),source_updated_at=None,source_kind='synthetic_dom',
        profile=dict(profile_id=str(uuid4()),revision=1,definition_hash='a'*64,structure_hash='b'*64,
            origin='http://localhost:8090',route='/reader-sample.html',language='es',edition='FC27',omissions={}),
        scope=dict(page=domain,filters='',location='squad' if domain=='squad' else 'club',visible_count=1 if domain=='account' else len(records),virtualized=True,global_complete=False),
        fragment_count=len(pieces),manifest=[digest_json(p) for p in pieces])
    result=[]
    for i,piece in enumerate(pieces):
        event=dict(**common,event_id=str(uuid4()),sequence=i+1,fragment_index=i,payload=piece)
        event['payload_hash']=canonical_hash(event)
        result.append(event)
    return result


def receive(client, headers, events):
    for event in events:
        response=client.post('/reader/events',headers=headers,json=event)
        assert response.status_code==200,response.text
    return response.json()


def review(client, events):
    response=client.post('/reader/observations/'+events[0]['observation_id']+'/review',json=dict(confirmation='REVISAR OBSERVACION DOM',context_confirmed=True))
    assert response.status_code==200,response.text
    return response.json()


def test_fragments_missing_out_of_order_twenty_retries_and_atomic_review(client,monkeypatch):
    grant,headers=paired(client,monkeypatch)
    cards=[dict(batch(grant)['records'][i%11], name=f'Sintética {i}') for i in range(65)]
    events=fragments(grant,records=cards)
    first=receive(client,headers,[events[2]])
    assert first['status']=='partial'
    assert client.post('/reader/observations/'+events[0]['observation_id']+'/review',json=dict(confirmation='REVISAR OBSERVACION DOM',context_confirmed=True)).status_code==409
    for _ in range(20):assert receive(client,headers,[events[2]])==first
    receive(client,headers,events[:2])
    detail=client.get('/reader/observations/'+events[0]['observation_id']).json()
    assert detail['status']=='review_required' and detail['missing_fragments']==[]
    assert client.get('/players').json()['total']==0
    result=review(client,events)
    assert len(result['reading_ids'])==3 and result['pending_records']==[]
    assert client.get('/players').json()['total']==65
    assert review(client,events)['reading_ids']==result['reading_ids']
    assert receive(client,headers,[events[2]])==first  # immutable original partial receipt
    changed=copy.deepcopy(events[0]);changed['payload']['records'][0]['rating']=89;changed['payload_hash']=canonical_hash(changed)
    assert client.post('/reader/events',headers=headers,json=changed).status_code==409
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(ReaderEvent))==3
        assert db.scalar(select(func.count()).select_from(ReaderObservation))==1
    assert not result['global_complete'] and not result['provider_verified']


def test_header_squad_dcp_and_solver_preserve_main_and_unknown_progress(client,monkeypatch):
    grant,headers=paired(client,monkeypatch)
    account=fragments(grant,'account');receive(client,headers,account);review(client,account)
    inventory=fragments(grant);receive(client,headers,inventory);review(client,inventory)
    cards=copy.deepcopy(inventory[0]['payload']['records'])
    slots={}
    for c in cards:
        pos=c['position'];slots[pos]=slots.get(pos,0)+1;c['slot']=f'{pos}-{slots[pos]}'
    squad=fragments(grant,'squad',cards);receive(client,headers,squad);saved=review(client,squad)
    assert saved['reused_copies']==11 and client.get('/players').json()['total']==11
    main=client.get('/squads/main').json()
    response=client.post('/assisted/main',json=dict(reading_ids=saved['reading_ids'],formation='4-3-3',complete=True,expected_hash=main['state_hash'],phrase='REGISTRAR MI PRINCIPAL'))
    assert response.status_code==201,response.text
    main=response.json()
    extra=fragments(grant,records=[dict(c,name='Reserva sintética '+c['name']) for c in cards])
    receive(client,headers,extra);review(client,extra)
    dcp=fragments(grant,'dcp',[dict(title='DCP sintético',requirement_text='Exactamente 11 jugadores. Media mínima 80.')])
    receive(client,headers,dcp);saved=review(client,dcp)
    assert saved['rule_review_required'] and not saved['progress_applied']
    reading=saved['reading_ids'][0]
    assert client.post(f'/assisted/readings/{reading}/simulate-dcp',json={}).status_code==409
    response=client.post(f'/assisted/readings/{reading}/review',json=dict(phrase='GUARDAR OBSERVACION',edition='FC27',cards=[],dcp=dict(
        name='DCP sintético',source_text='Exactamente 11 jugadores. Media mínima 80.',requirements=dict(kind='traditional',squad_size=11,min_rating=80),reviewed=True)))
    assert response.status_code==200,response.text
    proposal=client.post(f'/assisted/readings/{reading}/simulate-dcp',json={})
    assert proposal.status_code==200,proposal.text
    assert proposal.json()['solutions']
    assert all(p['name'].startswith('Reserva sintética') for p in proposal.json()['solutions'][0]['players'])
    assert client.get('/squads/main').json()['state_hash']==main['state_hash']
    assert client.get('/players').json()['total']==22


def test_reobservation_no_copy_multiplication_no_resurrection_no_silent_conflicts(client,monkeypatch):
    grant,headers=paired(client,monkeypatch)
    first=fragments(grant);receive(client,headers,first);review(client,first)
    second=fragments(grant);receive(client,headers,second);assert review(client,second)['reused_copies']==11
    players=client.get('/players').json()['items']
    with SessionLocal() as db:
        db.get(Player,players[0]['id']).deleted=True
        db.commit()
    third=fragments(grant);receive(client,headers,third);result=review(client,third)
    assert len(result['pending_records'])==1
    assert client.get('/players').json()['total']==10
    duplicates=fragments(grant,records=[first[0]['payload']['records'][1]]*2)
    receive(client,headers,duplicates);assert len(review(client,duplicates)['pending_records'])==2
    assert client.get('/players').json()['total']==10


def test_missing_fields_keep_earlier_evidence_and_conflicting_facts_stay_pending(client,monkeypatch):
    grant,headers=paired(client,monkeypatch)
    card={**batch(grant)['records'][0], 'league':'Liga sintética', 'first_owner':True}
    first=fragments(grant,records=[card]);receive(client,headers,first);review(client,first)
    second=fragments(grant,records=[{**card,'league':None,'first_owner':None}])
    receive(client,headers,second);assert review(client,second)['reused_copies']==1
    identifier=client.get('/players').json()['items'][0]['id']
    with SessionLocal() as db:
        p=db.get(Player,identifier)
        assert p.league=='Liga sintética' and 'league' not in p.unknown_fields
        assert p.validation_evidence['additional_facts']['first_owner'] is True
        assert p.validation_evidence['field_observed_at']['league']==first[0]['observed_at']
        assert p.validation_evidence['field_observed_at']['first_owner']==first[0]['observed_at']
    conflict=fragments(grant,records=[{**card,'first_owner':False}]);receive(client,headers,conflict)
    assert review(client,conflict)['pending_records'][0]['fields']==['first_owner']
    assert client.get('/players').json()['total']==1


def test_profile_source_context_manifest_and_revocation_are_enforced(client,monkeypatch):
    grant,headers=paired(client,monkeypatch)
    event=fragments(grant)[0]
    for mutation in [dict(source_kind='observed_page_dom'),dict(context_binding=str(uuid4())),dict(manifest=['c'*64]),dict(source_updated_at=now().isoformat())]:
        bad={**event,**mutation};bad['payload_hash']=canonical_hash(bad)
        assert client.post('/reader/events',headers=headers,json=bad).status_code in {409,422}
    receive(client,headers,[event])
    assert client.post('/reader/grants/'+grant['context_binding']+'/revoke',json={}).status_code==200
    assert client.post('/reader/events',headers=headers,json=event).status_code==401
    assert client.post('/reader/observations/'+event['observation_id']+'/review',json=dict(confirmation='REVISAR OBSERVACION DOM',context_confirmed=True)).status_code==409


def test_account_change_rolls_back_observation_review(client,monkeypatch):
    grant,headers=paired(client,monkeypatch)
    first=fragments(grant,'account');receive(client,headers,first);review(client,first)
    second=fragments(grant,'account');second[0]['payload']['club_name']='Otro club'
    second[0]['manifest']=[digest_json(second[0]['payload'])];second[0]['payload_hash']=canonical_hash(second[0])
    receive(client,headers,second)
    result=client.post('/reader/observations/'+second[0]['observation_id']+'/review',json=dict(confirmation='REVISAR OBSERVACION DOM',context_confirmed=True))
    assert result.status_code==409
    detail=client.get('/reader/observations/'+second[0]['observation_id']).json()
    assert detail['status']=='review_required' and 'reading_ids' not in detail


def test_old_observation_retained_without_new_fake_date(client,monkeypatch):
    grant,headers=paired(client,monkeypatch)
    event=fragments(grant)[0];event['observed_at']=(now()-timedelta(hours=1)).isoformat();event['payload_hash']=canonical_hash(event)
    assert receive(client,headers,[event])['status']=='historical'
    response=client.get('/reader/observations/'+event['observation_id']).json()
    from datetime import datetime
    assert datetime.fromisoformat(response['observed_at'])==datetime.fromisoformat(event['observed_at'])
    assert client.get('/players').json()['total']==0
