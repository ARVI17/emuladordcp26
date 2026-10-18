"""Synthetic DOM contracts; these tests do not certify an EA extractor."""
import copy
from datetime import timedelta
from uuid import uuid4
import pytest
from sqlalchemy import select, func
from app.models.entities import Player, now
from app.models.reader import ReaderEvent
from app.db.session import SessionLocal
from app.api.reader import canonical_hash

pytestmark = pytest.mark.catalog_boundary
EXTENSION = 'a'*32


def paired(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings,'cors_origins',settings.cors_origins+',http://testserver')
    context=client.post('/assisted/contexts',json={'name':'DOM sintético','phrase':'INICIAR LECTURA ASISTIDA'}).json()
    entry=client.post('/app/entries',json={'nonce':str(uuid4()),'mode':'assisted','context_id':context['id']}).json()
    client.headers['X-App-Entry']=str(entry['entry_id'])
    pairing=client.post('/reader/pairings',json={'extension_id':EXTENSION,'confirmation':'EMPAREJAR LECTOR'})
    assert pairing.status_code==201,pairing.text
    claimed=client.post('/reader/claim',headers={'X-Reader-Extension':EXTENSION},json={k:pairing.json()[k] for k in ('pairing_id','code')})
    assert claimed.status_code==200,claimed.text
    return claimed.json(), {'X-Reader-Extension':EXTENSION,'Authorization':'Bearer '+claimed.json()['credential']}


def batch(grant, sequence=1, stream=None):
    positions=['POR','LD','DFC','DFC','LI','MC','MC','MC','ED','DC','EI']
    value=dict(event_id=str(uuid4()),schema_version=1,reader_version='semantic-sample-1',context_binding=grant['context_binding'],
        stream_id=stream or str(uuid4()),sequence=sequence,document_ref=str(uuid4()),view='inventory',
        scope=dict(page='synthetic-1',filters='',location='club',visible_count=11,loading=False,virtualized=True,terminal_observed=False,global_complete=False),
        observed_at=now().isoformat(),source_kind='synthetic_dom',edition='FC27',
        records=[dict(ordinal=i,name=f'Muestra DOM {i}',rating=88,position=p,is_loan=False,is_evolution=False,tradable=False,card_type='Oro',location='club',evidence={'name':'synthetic:text'}) for i,p in enumerate(positions)],
        unknown_fields=['card_id','copy_id','price'],completeness_evidence='visible_subset')
    value['payload_hash']=canonical_hash(value)
    return value


def test_atomic_receipts_twenty_retries_review_and_real_solver(client,monkeypatch):
    grant,headers=paired(client,monkeypatch)
    event=batch(grant)
    receipt=client.post('/reader/events',headers=headers,json=event)
    assert receipt.status_code==200,receipt.text
    assert client.get('/players').json()['total']==0
    for _ in range(20): assert client.post('/reader/events',headers=headers,json=event).json()==receipt.json()
    changed=copy.deepcopy(event);changed['records'][0]['rating']=89;changed['payload_hash']=canonical_hash(changed)
    assert client.post('/reader/events',headers=headers,json=changed).status_code==409
    reviewed=client.post('/reader/events/'+event['event_id']+'/review',json={'confirmation':'REVISAR LOTE DOM'})
    assert reviewed.status_code==200,reviewed.text
    assert client.get('/players').json()['total']==11
    assert client.post('/reader/events',headers=headers,json=event).json()==receipt.json()
    listed=client.get('/reader/status')
    assert listed.status_code==200,listed.text
    listed_event=listed.json()['events'][0]
    assert listed_event['status']=='reviewed'
    assert listed_event['reading_id']==reviewed.json()['reading_id']
    assert listed_event['event_id']==event['event_id']
    from datetime import datetime
    assert datetime.fromisoformat(listed_event['observed_at'])==datetime.fromisoformat(event['observed_at'])
    for _ in range(2): assert client.post('/reader/events/'+event['event_id']+'/review',json={'confirmation':'REVISAR LOTE DOM'}).status_code==200
    proposal=client.get('/reader/proposal',headers=headers)
    assert proposal.status_code==200,proposal.text
    assert any(len(g['squad']['lineup'])==11 for g in proposal.json()['proposal']['groups'])
    assert not proposal.json()['writes_performed']
    assert proposal.json()['data_sources']==['synthetic_dom']
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(ReaderEvent))==1
        players=list(db.scalars(select(Player).where(Player.data_source=='visual_assisted')))
        assert len(players)==11
        assert all(p.validation_evidence['ea_copy_id'] is None for p in players)
    assert client.post('/reader/grants/'+grant['context_binding']+'/revoke',json={}).status_code==200
    assert client.post('/reader/events',headers=headers,json=event).status_code==401


def test_context_origin_sequence_and_no_privileged_routes(client,monkeypatch):
    grant,headers=paired(client,monkeypatch)
    event=batch(grant,sequence=2)
    assert client.post('/reader/events',headers={**headers,'Origin':'https://evil.example'},json=event).status_code==403
    assert client.post('/reader/events',headers={**headers,'Host':'evil.example'},json=event).status_code==403
    assert client.post('/reader/events',headers=headers,json=event).status_code==200
    old=batch(grant,sequence=1,stream=event['stream_id'])
    assert client.post('/reader/events',headers=headers,json=old).json()['status']=='historical'
    assert client.post('/reader/events/'+old['event_id']+'/review',json={'confirmation':'REVISAR LOTE DOM'}).status_code==409
    wrong=batch(grant);wrong['edition']='FC26';wrong['payload_hash']=canonical_hash(wrong)
    assert client.post('/reader/events',headers=headers,json=wrong).status_code==422
    wrong=batch(grant);wrong['records'][0]['name']='Bearer secret';wrong['payload_hash']=canonical_hash(wrong)
    assert client.post('/reader/events',headers=headers,json=wrong).status_code==422
    client.post('/app/entries',json={'nonce':str(uuid4()),'mode':'local','context_id':1})
    assert client.post('/reader/events',headers=headers,json=event).status_code==401
    client.cookies.clear()
    assert client.post('/players/1/protect',headers=headers,json={}).status_code==401


def test_pair_attempt_limit_and_csrf(client,monkeypatch):
    grant,headers=paired(client,monkeypatch)
    assert client.post('/reader/pairings',headers={'X-CSRF-Token':'wrong'},json={'extension_id':EXTENSION,'confirmation':'EMPAREJAR LECTOR'}).status_code==403
    pair=client.post('/reader/pairings',json={'extension_id':EXTENSION,'confirmation':'EMPAREJAR LECTOR'}).json()
    wrong='000000' if pair['code']!='000000' else '111111'
    for _ in range(5): assert client.post('/reader/claim',headers={'X-Reader-Extension':EXTENSION},json={'pairing_id':pair['pairing_id'],'code':wrong}).status_code==401
    assert client.post('/reader/claim',headers={'X-Reader-Extension':EXTENSION},json={'pairing_id':pair['pairing_id'],'code':pair['code']}).status_code==401


def test_old_batches_and_ambiguous_duplicates_never_create_spendable_copies(client,monkeypatch):
    grant,headers=paired(client,monkeypatch)
    event=batch(grant)
    for seq in (1,2):
        event['event_id']=str(uuid4());event['sequence']=seq;event['payload_hash']=canonical_hash(event)
        assert client.post('/reader/events',headers=headers,json=event).status_code==200
        response=client.post('/reader/events/'+event['event_id']+'/review',json={'confirmation':'REVISAR LOTE DOM'})
        assert response.status_code==200,response.text
    with SessionLocal() as db:
        assert all(p.availability=='review_required' for p in db.scalars(select(Player).where(Player.data_source=='visual_assisted')))
    stale=batch(grant);stale['observed_at']=(now()-timedelta(hours=1)).isoformat();stale['payload_hash']=canonical_hash(stale)
    assert client.post('/reader/events',headers=headers,json=stale).json()['status']=='historical'
