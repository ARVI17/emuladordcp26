"""Synthetic pixels/OCR only. No provider witness or real account operation."""
import io
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
import pytest
from PIL import Image
from sqlalchemy import select, func
from app.db.session import SessionLocal
from app.models.entities import Player, Objective, now
from app.models.assisted import VisualReading, CaptureSession
from app.models.planner import ClubContext, ClubPlan, Reservation

pytestmark = pytest.mark.catalog_boundary
POSITIONS = ['POR','LD','DFC','DFC','LI','MC','MC','MC','ED','DC','EI']


def enter(client, name='Club visual de prueba'):
    result = client.post('/assisted/contexts', json=dict(name=name, phrase='INICIAR LECTURA ASISTIDA'))
    assert result.status_code == 201, result.text
    entry = client.post('/app/entries', json=dict(nonce='visual-entry-'+str(result.json()['id']), mode='assisted', context_id=result.json()['id']))
    assert entry.status_code == 200, entry.text
    client.headers['X-App-Entry'] = str(entry.json()['entry_id'])
    return entry.json()


def capture(client):
    response = client.post('/assisted/sessions', json={'source':'screenshot'})
    assert response.status_code == 201, response.text
    return response.json()['id']


def frame(client, monkeypatch, session, text=None, scope='inventory', page='1', color='white'):
    monkeypatch.setattr('app.services.assisted.ocr_image', lambda _: {'raw_text':text or 'FC27 Mi club\n'+'\n'.join(f'88 {p} Jugador {i}' for i,p in enumerate(POSITIONS))})
    blob = io.BytesIO()
    Image.new('RGB',(100,100),color).save(blob,format='PNG')
    response = client.post(f'/assisted/sessions/{session}/read', data=dict(scope=scope,page=page), files={'file':('test.png',blob.getvalue(),'image/png')})
    assert response.status_code == 200, response.text
    return response.json()


def review_body(reading):
    counts = {}
    cards = []
    for c in reading['original']['cards']:
        p = c['position']
        counts[p] = counts.get(p,0)+1
        cards.append(dict(ordinal=c['ordinal'],name=c['name'],rating=c['rating'],position=p,
            card_type='Oro común',is_loan=False,is_evolution=False,tradable=False,slot=f'{p}-{counts[p]}'))
    return dict(phrase='GUARDAR OBSERVACION',edition='FC27',cards=cards,formation='4-3-3')


def review(client, reading, body=None):
    response = client.post(f'/assisted/readings/{reading["id"]}/review', json=body or review_body(reading))
    assert response.status_code == 200, response.text
    return response.json()


def goal_payload():
    return dict(name='Jugar con media 80',target=1,phrase='REVISAR OBJETIVO', rules=dict(
        source_reference='Captura sintética',source_text='Once inicial: al menos 11 jugadores de media 80 o más',
        observed_at=now().isoformat(),reviewed=True,mode='squad_battles',min_difficulty='professional',
        loans_allowed=False,conditions=[dict(id='rating',source_text='Al menos 11 con media 80',field='rating',comparison='ge',value=80,quantity='min',count=11,scope='starters',reviewed=True)]))


def setup_plan(client, monkeypatch):
    enter(client)
    session = capture(client)
    cards = frame(client,monkeypatch,session,scope='squad')
    saved = review(client,cards)
    main = client.get('/squads/main').json()
    response = client.post('/assisted/main',json=dict(reading_ids=[cards['id']],formation='4-3-3',complete=True,expected_hash=main['state_hash'],phrase='REGISTRAR MI PRINCIPAL'))
    assert response.status_code == 201, response.text
    main = response.json()
    goal = frame(client,monkeypatch,session,text='FC27 Objetivos\nOnce inicial: al menos 11 jugadores de media 80 o más',scope='objective',page='objetivo')
    body = dict(phrase='GUARDAR OBSERVACION',edition='FC27',objective=goal_payload())
    saved_goal = review(client,goal,body)
    proposal = client.post('/objective-planning/preview',json=dict(objective_ids=[saved_goal['reviewed']['objective_id']],formation='4-3-3',bench_size=0))
    assert proposal.status_code == 200, proposal.text
    proposal = proposal.json()['proposals'][0]
    guide = client.post('/assisted/guides',json={'token':proposal['token']})
    assert guide.status_code == 201, guide.text
    return session, guide.json(), main, saved, proposal


def transition(client, plan, action, **extra):
    response = client.post(f'/assisted/guides/{plan["id"]}/transition',json=dict(action=action,expected_hash=plan['state_hash'],**extra))
    assert response.status_code == 200, response.text
    return response.json()


def test_vertical_review_protect_solve_guide_observe_reconcile(client,monkeypatch):
    session, plan, main, saved, proposal = setup_plan(client,monkeypatch)
    ids = saved['reviewed']['copy_ids']
    assert set(s['player_id'] for s in plan['steps']) == set(ids)
    assert client.get('/squads/main').json()['state_hash'] == main['state_hash']
    assert client.post('/objective-planning/save',json=dict(token=proposal['token'],name='Alternativa observada')).status_code == 201
    assert client.get('/squads/main').json()['state_hash'] == main['state_hash']
    plan = transition(client,plan,'review')
    plan = transition(client,plan,'approve',phrase=f'APROBAR GUIA {plan["id"]}')
    plan = transition(client,plan,'start')
    for _ in ids:
        plan = transition(client,plan,'next')
    plan = transition(client,plan,'declare',note='Declaración sintética, sin operación EA')
    assert plan['status'] == 'result_declared'
    plan = transition(client,plan,'check')
    assert plan['status'] == 'checking'
    result = frame(client,monkeypatch,session,scope='result',page='resultado')
    result_body = review_body(result)
    slots = {s['name']:s['slot'] for s in plan['steps']}
    for card in result_body['cards']:
        card['slot'] = slots[card['name']]
    review(client,result,result_body)
    plan = transition(client,plan,'check',reading_ids=[result['id']])
    assert plan['status'] == 'result_observed'
    plan = transition(client,plan,'reconcile')
    again = transition(client,plan,'check',reading_ids=[result['id']])
    assert again == plan and plan['status'] == 'reconciled'
    assert not plan['approval']['result']['cards_consumed']
    with SessionLocal() as db:
        assert all(not db.get(Player,i).deleted for i in ids)
        assert db.scalar(select(Objective.progress).where(Objective.name=='Jugar con media 80')) == 0
        context = db.get(ClubContext,plan['binding']['context_id'])
        assert not context.verified and context.coins is None


def test_unknowns_repeated_pages_ambiguous_duplicates_and_resolution(client,monkeypatch):
    enter(client)
    session = capture(client)
    reading = frame(client,monkeypatch,session,text='FC27 Mi club\n88 DC Igual')
    body = review_body(reading)
    body['cards'][0]['is_loan'] = None
    saved = review(client,reading,body)
    assert frame(client,monkeypatch,session,text='FC27 Mi club\n88 DC Igual')['repeated']
    assert frame(client,monkeypatch,session,text='FC27 Mi club\n88 DC Igual',color='black')['repeated']
    assert review(client,reading,body)['reviewed']['copy_ids'] == saved['reviewed']['copy_ids']
    player = client.get('/players').json()['items'][0]
    assert player['is_loan'] is None and player['league'] is None and player['card_id'] is None
    assert player['ownership_source'] == 'user_reviewed_visual'
    other = frame(client,monkeypatch,session,text='FC27 Mi club\n88 DC Igual',page='2')
    second = review(client,other)
    ids = saved['reviewed']['copy_ids']+second['reviewed']['copy_ids']
    assert len(client.get('/players?availability=review_required').json()['items']) == 2
    payload=dict(player_ids=ids,decision='distinct_copies',note='Dos copias visibles juntas, revisadas manualmente.',phrase='RESOLVER COPIAS')
    response=client.post('/assisted/copies/resolve',json=payload)
    assert response.status_code == 200,response.text
    assert len(client.get('/players?availability=available').json()['items']) == 2


@pytest.mark.parametrize('text',['Iniciar sesión\nContraseña 123456','FC26 Mi club\n88 DC Otro','Texto ilegible ajeno'])
def test_sensitive_other_edition_and_unrelated_stop_without_storage(client,monkeypatch,text):
    enter(client)
    session=capture(client)
    result=frame(client,monkeypatch,session,text=text)
    assert result['blocked'] and result['stop_capture']
    with SessionLocal() as db:
        assert db.scalar(select(func.count(VisualReading.id))) == 0
        assert db.get(CaptureSession,session).status == 'blocked'


def test_uncertain_receipt_no_repeat_expiry_cancel_and_account_switch(client,monkeypatch):
    session,plan,main,saved,proposal=setup_plan(client,monkeypatch)
    plan=transition(client,plan,'review')
    plan=transition(client,plan,'approve',phrase=f'APROBAR GUIA {plan["id"]}')
    plan=transition(client,plan,'start')
    result=frame(client,monkeypatch,session,text='FC27 Mi club\nMonedas: 500',scope='result',page='saldo')
    review(client,result)
    plan=transition(client,plan,'check',reading_ids=[result['id']])
    assert plan['status']=='uncertain' and not plan['approval']['result']['cards_consumed']
    response=client.post(f'/assisted/guides/{plan["id"]}/transition',json=dict(action='start',expected_hash=plan['state_hash']))
    assert response.status_code==409
    with SessionLocal() as db:
        db.get(ClubPlan,plan['id']).expires_at=now()-timedelta(seconds=1)
        db.commit()
    plan=client.get('/assisted/guides').json()[0]
    plan=transition(client,plan,'cancel',note='No revierte EA')
    assert plan['status']=='cancelled' and not plan['approval']['cancellation']['ea_reversed']
    enter(client,'Otro club')
    assert client.get(f'/assisted/readings/{result["id"]}').status_code==404
    assert client.get('/players').json()['items']==[]
    assert client.get('/assisted/guides').json()==[]


def test_copy_protection_and_reservation_block_legacy_mutations(client,monkeypatch):
    session,plan,main,saved,proposal=setup_plan(client,monkeypatch)
    identifier=saved['reviewed']['copy_ids'][0]
    assert client.delete(f'/players/{identifier}').status_code==409
    assert client.post(f'/plans/{plan["id"]}/cancel').status_code==404
    with SessionLocal() as db:
        db.add(Reservation(player_id=identifier,plan_id=plan['id'],expires_at=now()+timedelta(minutes=20),club_context_id=plan['binding']['context_id']))
        db.commit()
    response=client.post(f'/assisted/guides/{plan["id"]}/transition',json=dict(action='review',expected_hash=plan['state_hash']))
    assert response.status_code==409


def test_concurrent_double_review_keeps_one_copy_set(client,monkeypatch):
    enter(client)
    session=capture(client)
    reading=frame(client,monkeypatch,session)
    def send():
        return client.post(f'/assisted/readings/{reading["id"]}/review',json=review_body(reading))
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses=list(executor.map(lambda _:send(),range(2)))
    assert all(r.status_code in {200,409} for r in responses)
    assert any(r.status_code==200 for r in responses)
    assert len(client.get('/players').json()['items'])==11


def test_dcp_visual_rules_safe_simulation_gallery_history_and_preferences(client,monkeypatch):
    session,plan,main,saved,proposal=setup_plan(client,monkeypatch)
    extra=frame(client,monkeypatch,session,text='FC27 Mi club\n88 DC Suplente Otro',page='otra copia')
    extra=review(client,extra)
    pid=extra['reviewed']['copy_ids'][0]
    dcp=frame(client,monkeypatch,session,text='FC27 DCP\nNumero de jugadores: exactamente 1\nMedia: minimo 80',scope='dcp',page='DCP')
    review(client,dcp,dict(phrase='GUARDAR OBSERVACION',edition='FC27',dcp=dict(name='Prueba DCP visual',source_text=dcp['original']['objective_text'],requirements={'squad_size':1,'min_rating':80},reviewed=True)))
    result=client.post(f'/assisted/readings/{dcp["id"]}/simulate-dcp',json={})
    assert result.status_code==200,result.text
    assert result.json()['solutions'][0]['player_ids']==[pid]
    assert not set(main['protected_copy_ids'])&set(result.json()['solutions'][0]['player_ids'])
    impossible=client.post(f'/assisted/readings/{dcp["id"]}/simulate-dcp',json={'filters':{'min_rating':99}})
    assert impossible.status_code==200 and impossible.json()['solutions']==[]
    assert client.patch(f'/players/{pid}',json={'favorite':True,'notes':'Preferencia local'}).status_code==200
    assert client.patch(f'/players/{pid}',json={'rating':99}).status_code==409
    assert client.post(f'/assisted/readings/{dcp["id"]}/simulate-dcp',json={}).json()['solutions']==[]
    result=client.post('/gallery/record-inventory',json={'player_ids':saved['reviewed']['copy_ids']})
    assert result.status_code==200,result.text
    history=client.get('/gallery/entries').json()
    assert history['total']==11 and all(p['gallery_score'] is None for p in history['items'])
    assert all(p['variant_evidence']['kind']=='visual_copy' for p in history['items'])
    with SessionLocal() as db:
        assert not db.get(Player,pid).deleted


def test_main_discrepancy_and_unknown_variant_duplicate_remain_protected(client,monkeypatch):
    session,plan,main,saved,proposal=setup_plan(client,monkeypatch)
    first=saved['reviewed']['cards'][0]
    read=frame(client,monkeypatch,session,text=f'FC27 Mi club\n{first["rating"]} {first["position"]} {first["name"]}',scope='squad',page='principal cambiada')
    body=review_body(read)
    body['cards'][0].update(existing_player_id=saved['reviewed']['copy_ids'][0],slot='BENCH-1')
    review(client,read,body)
    current=client.get('/squads/main').json()
    assert not current['complete'] and current['snapshot']['needs_review']
    assert set(main['protected_copy_ids'])<=set(current['protected_copy_ids'])
    read=frame(client,monkeypatch,session,text=f'FC27 Mi club\n{first["rating"]} {first["position"]} {first["name"]}',page='variante desconocida')
    body=review_body(read);body['cards'][0]['card_type']=None
    other=review(client,read,body)
    p=client.get('/players?availability=review_required').json()['items']
    assert {c['id'] for c in p} >= {saved['reviewed']['copy_ids'][0],other['reviewed']['copy_ids'][0]}
    assert all(c['effective_protected'] for c in p)


def test_capture_stop_erasure_expiry_and_approval_changes(client,monkeypatch):
    enter(client)
    session=capture(client)
    reading=frame(client,monkeypatch,session)
    assert client.delete(f'/assisted/sessions/{session}/drafts').status_code==200
    assert client.get(f'/assisted/readings/{reading["id"]}').json()['original']=={}
    assert client.post(f'/assisted/readings/{reading["id"]}/review',json=dict(phrase='GUARDAR OBSERVACION',edition='FC27')).status_code==409
    second=frame(client,monkeypatch,session)
    assert second['id']!=reading['id']
    assert client.post(f'/assisted/sessions/{session}/stop').status_code==200
    assert client.post(f'/assisted/readings/{second["id"]}/review',json=review_body(second)).status_code==409
    session=capture(client)
    third=frame(client,monkeypatch,session,page='2')
    with SessionLocal() as db:
        db.get(CaptureSession,session).expires_at=now()-timedelta(seconds=1)
        db.commit()
    assert client.post(f'/assisted/readings/{third["id"]}/review',json=review_body(third)).status_code==409


def test_cancel_does_not_allow_repeating_unknown_result_and_old_approval_cannot_advance(client,monkeypatch):
    session,plan,main,saved,proposal=setup_plan(client,monkeypatch)
    plan=transition(client,plan,'review')
    plan=transition(client,plan,'approve',phrase=f'APROBAR GUIA {plan["id"]}')
    plan=transition(client,plan,'start')
    old_hash=plan['state_hash']
    plan=transition(client,plan,'next')
    response=client.post(f'/assisted/guides/{plan["id"]}/transition',json=dict(action='next',expected_hash=old_hash))
    assert response.status_code==409
    plan=transition(client,plan,'cancel')
    assert plan['approval']['outcome_unknown']
    # Even a recomputed claim with a different timestamp cannot repeat this operation.
    with SessionLocal() as db:
        row=db.get(ClubPlan,plan['id']);row.inputs={**row.inputs,'source':'different-token-digest'};db.commit()
    response=client.post('/assisted/guides',json={'token':proposal['token']})
    assert response.status_code==409
    # Later evidence is useful even after the approval expired; it grants no new steps.
    with SessionLocal() as db:
        db.get(ClubPlan,plan['id']).expires_at=now()-timedelta(minutes=1);db.commit()
    plan=client.get('/assisted/guides').json()[0]
    result=frame(client,monkeypatch,session,scope='result',page='resultado tardío')
    body=review_body(result);slots={s['name']:s['slot'] for s in plan['steps']}
    for card in body['cards']:card['slot']=slots[card['name']]
    review(client,result,body)
    plan=transition(client,plan,'check',reading_ids=[result['id']])
    assert plan['status']=='result_observed' and plan['approval']['result']['approval_current'] is False
    plan=transition(client,plan,'reconcile')
    assert plan['approval']['outcome_unknown'] is False


def test_uncertain_position_preserves_original_and_requires_review(client,monkeypatch):
    enter(client)
    reading=frame(client,monkeypatch,capture(client),text='FC27 Mi club\n88 El Extremo de prueba')
    card=reading['original']['cards'][0]
    assert card['position']=='EI' and card['original_position']=='El'
    assert card['confidence']['position']==0.45 and card['warning']
    assert client.get('/players').json()['items']==[]


def test_failed_manual_step_stays_unknown_and_cannot_restart(client,monkeypatch):
    session,plan,main,saved,proposal=setup_plan(client,monkeypatch)
    plan=transition(client,plan,'review')
    plan=transition(client,plan,'approve',phrase=f'APROBAR GUIA {plan["id"]}')
    plan=transition(client,plan,'start')
    plan=transition(client,plan,'fail',note='La pantalla no coincide con el paso previsto')
    assert plan['status']=='failed' and plan['approval']['outcome_unknown']
    assert not plan['approval']['failure']['provider_verified']
    response=client.post(f'/assisted/guides/{plan["id"]}/transition',json=dict(action='start',expected_hash=plan['state_hash']))
    assert response.status_code==409
    assert client.get('/squads/main').json()['state_hash']==main['state_hash']


def test_fresh_capture_replaces_unreviewable_draft_but_not_reviewed_evidence(client,monkeypatch):
    enter(client)
    first=frame(client,monkeypatch,capture(client))
    session=capture(client)
    second=frame(client,monkeypatch,session)
    assert second['id']!=first['id'] and not second['repeated']
    assert client.get(f'/assisted/readings/{first["id"]}').json()['status']=='erased'
    reviewed=review(client,second)
    third=frame(client,monkeypatch,capture(client))
    assert third['repeated'] and third['id']==second['id']
    assert third['observed_at']==reviewed['observed_at']
    assert len(client.get('/players').json()['items'])==11
