"""Synthetic local declarations. No real account, rule or price evidence."""
from datetime import timedelta
from uuid import uuid4
import pytest
from app.models.entities import now
from test_objective_planning import setup_goal
from test_assisted import enter,capture,frame,review

pytestmark=pytest.mark.catalog_boundary


def test_objective_journal_idempotent_correctable_and_no_progress_side_effect(client):
    goal,_=setup_goal(client)
    before=client.get('/objective-planning').json()
    path=f'/objective-journal/{uuid4()}'
    body=dict(expected_revision=0,played_at=(now()-timedelta(minutes=1)).isoformat(),mode='squad_battles',
        difficulty='professional',tasks=[dict(objective_id=goal['id'],action_id='wins',count=1)],note='Partido de prueba declarado')
    first=client.put(path,json=body)
    assert first.status_code==200,first.text
    for _ in range(3):assert client.put(path,json=body).json()==first.json()
    correction={**body,'expected_revision':1,'tasks':[{**body['tasks'][0],'count':0}]}
    changed=client.put(path,json=correction)
    assert changed.status_code==200 and changed.json()['revision']==2
    assert len(changed.json()['history'])==1
    assert client.put(path,json=body).status_code==409
    assert client.get('/objective-planning').json()==before
    assert len(client.get('/objective-journal').json()['items'])==1
    for invalid in [dict(mode='rivals'),dict(difficulty='beginner'),dict(tasks=[{**body['tasks'][0],'count':2}]),dict(game_version='FC26')]:
        assert client.put(f'/objective-journal/{uuid4()}',json={**body,**invalid}).status_code==422


def test_selection_template_fresh_rules_locks_and_single_replacement(client,monkeypatch):
    enter(client);session=capture(client)
    cards=frame(client,monkeypatch,session,text='FC27 Mi club\n88 MC Reserva Uno\n88 MC Reserva Dos\n88 MC Reserva Tres')
    ids=review(client,cards)['reviewed']['copy_ids']
    dcp=frame(client,monkeypatch,session,text='FC27 DCP\nNumero de jugadores: exactamente 2\nMedia: minimo 80',scope='dcp',page='DCP sintético')
    draft=dict(phrase='GUARDAR OBSERVACION',edition='FC27',dcp=dict(name='DCP sintético',source_text=dcp['original']['objective_text'],requirements={'squad_size':2,'min_rating':80},reviewed=True))
    review(client,dcp,draft)
    created=client.post('/dcp/templates',json=dict(name='Reserva reutilizable',reading_id=dcp['id'],filters={'is_loan':False}))
    assert created.status_code==201,created.text
    template=created.json();assert not template['authorizes_consumption']
    before=client.get('/players').json()
    path=f"/dcp/templates/{template['id']}/simulate"
    simulated=client.post(path,json=dict(reading_id=dcp['id'],locked_ids=[ids[0]],exclude_ids=[ids[1]]))
    assert simulated.status_code==200,simulated.text
    assert set(simulated.json()['solutions'][0]['player_ids'])=={ids[0],ids[2]}
    assert client.get('/players').json()==before
    assert client.post(path,json=dict(reading_id=dcp['id'],locked_ids=ids)).status_code==422
    assert client.patch(f'/players/{ids[0]}',json={'favorite':True}).status_code==200
    assert client.post(path,json=dict(reading_id=dcp['id'],locked_ids=[ids[0]])).json()['solutions']==[]
    other=frame(client,monkeypatch,session,text='FC27 DCP\nNumero de jugadores: exactamente 1',scope='dcp',page='reglas nuevas')
    review(client,other,{**draft,'dcp':{**draft['dcp'],'requirements':{'squad_size':1,'min_rating':80}}})
    assert client.post(path,json=dict(reading_id=other['id'])).status_code==409


def test_gallery_scenarios_progress_and_unknown_rewards_are_not_zero(client):
    payload=dict(name='Escenario sintético',rules=dict(schema_version=2,size=1,multiplicity='variant',evidence_status='scenario',observed_at=now().isoformat()),tags=[],grade_thresholds={'C':100},rules_reviewed=True)
    created=client.post('/gallery/sets',json=payload)
    assert created.status_code==201,created.text
    identifier=created.json()['id']
    assert identifier in [s['id'] for s in client.get('/gallery/local-scenarios').json()]
    request=dict(set_ids=[identifier],mode='known_only',allow_scenarios=True)
    assert client.post('/gallery/route-preview',json=request).status_code==409
    progress=dict(attained_grade=None,claimed_grade=None,note='Declaro no haber completado grados',confirmation='REGISTRAR GRADO DECLARADO')
    first=client.put(f'/gallery/sets/{identifier}/declared-progress',json=progress)
    assert first.status_code==200,first.text
    assert client.put(f'/gallery/sets/{identifier}/declared-progress',json=progress).json()==first.json()
    assert client.put(f'/gallery/sets/{identifier}/declared-progress',json={**progress,'attained_grade':'NOT_A_GRADE'}).status_code==422
    route=client.post('/gallery/route-preview',json=request)
    assert route.status_code==200,route.text
    assert route.json()['additional_tokens'] is None
    assert route.json()['finance']['gross_purchases']==0 and not route.json()['writes_performed']
    assert client.post('/gallery/route-preview',json={**request,'allow_scenarios':False}).status_code==409
    invalid={**payload,'rules':{**payload['rules'],'rewards':{'B':15,'S':10}},'grade_thresholds':{'B':100,'S':200}}
    assert client.post('/gallery/sets',json=invalid).status_code==422


def test_gallery_route_uses_documented_variant_quotes_without_creating_ownership(client):
    from catalog_fixture import witness
    from app.models.catalog import CardVariant
    from app.db.session import SessionLocal
    from sqlalchemy import select
    variant=witness(dict(name='Adquisición SINTÉTICA',rating=80,position='MC',league='Prueba',club='Prueba',nationality='CO',is_loan=False,is_evolution=False,gallery_score=1000))['card_id']
    with SessionLocal() as db:
        row=db.scalar(select(CardVariant).where(CardVariant.variant_id==variant))
        row.evidence={**row.evidence,'fields':dict(is_loan=False,is_evolution=False,gallery_score=1000)}
        db.commit()
    quote=dict(variant_id=variant,game_version='FC27',market='Console',kind='listing',observed_at=(now()-timedelta(seconds=2)).isoformat(),expires_at=(now()+timedelta(hours=1)).isoformat(),source_url='https://example.invalid/synthetic',coverage='Cotización sintética para pruebas')
    purchase=client.post('/market/quotes',json={**quote,'amount':10000});assert purchase.status_code==201,purchase.text
    resale=client.post('/market/quotes',json={**quote,'amount':9800});assert resale.status_code==201,resale.text
    definition=dict(name='Conjunto sintético de compra',rules=dict(schema_version=2,size=1,multiplicity='variant',evidence_status='scenario',rewards={'C':5}),tags=[],grade_thresholds={'C':1000},rules_reviewed=True)
    identifier=client.post('/gallery/sets',json=definition).json()['id']
    progress=dict(attained_grade=None,claimed_grade=None,note='Declaro no tener premios',confirmation='REGISTRAR GRADO DECLARADO')
    assert client.put(f'/gallery/sets/{identifier}/declared-progress',json=progress).status_code==200
    request=dict(set_ids=[identifier],mode='token_target',target_tokens=5,allow_scenarios=True,market='Console',available_coins=10000,maximum_capital=10000,maximum_loss=690,fee_basis_points=500,fee_source='Hipótesis sintética del cinco por ciento',candidates=[dict(variant_id=variant,purchase_quote_id=purchase.json()['id'],resale_quote_id=resale.json()['id'],keep=False)])
    before=client.get('/players').json()
    result=client.post('/gallery/route-preview',json=request)
    assert result.status_code==200,result.text
    assert result.json()['finance']['estimated_net_spend']==690
    assert result.json()['additional_tokens']==5
    assert result.json()['sets'][0]['evaluation']['selected_entries'][0]['hypothetical_acquisition']
    assert client.get('/players').json()==before
    assert client.post('/gallery/route-preview',json={**request,'market':'PC'}).status_code==409
    insufficient=client.post('/gallery/route-preview',json={**request,'available_coins':690}).json()
    assert not insufficient.get('target_reached',False)
    assert insufficient.get('finance',{}).get('gross_purchases',0)==0
    from app.models.planner import MarketQuote
    with SessionLocal() as db:
        db.get(MarketQuote,purchase.json()['id']).observed_at=now()-timedelta(hours=25)
        db.commit()
    assert client.post('/gallery/route-preview',json=request).status_code==409
