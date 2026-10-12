from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import pytest
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.entities import Objective, now
from catalog_fixture import activate_seed

pytestmark = pytest.mark.catalog_boundary


def draft(**extra):
    value=dict(name='Objetivo sintético de prueba',description='No es un objetivo real de EA',target=3,
        expires_at=(now()+timedelta(hours=2)).isoformat(),phrase='REVISAR OBJETIVO',
        rules=dict(source_reference='Transcripción sintética del propietario',source_text='Ganar tres partidos con esta convocatoria de prueba',
            observed_at=now().isoformat(),reviewed=True,mode='squad_battles',min_difficulty='professional',loans_allowed=False,
            conditions=[],actions=[dict(id='wins',kind='wins',count=3,actor='Equipo',source_text='Ganar tres partidos')]))
    return {**value,**extra}


def setup_goal(client):
    activate_seed()  # Cards only; the newly submitted auxiliary rules receive no witness.
    body=draft()
    created=client.post('/objective-planning',json=body)
    assert created.status_code==201,created.text
    assert not created.json()['definition_verified'] and created.json()['progress']['value'] is None
    return created.json(),body


def preview(client, identifier):
    response=client.post('/objective-planning/preview',json={'objective_ids':[identifier],'bench_size':7})
    assert response.status_code==200,response.text
    assert response.json()['proposals'],response.text
    return response.json()


def test_prepare_export_save_new_alternative_preserves_main_and_unknown_progress(client):
    goal,_=setup_goal(client)
    main=client.get('/squads/main').json()
    before=next(s for s in client.get('/squads').json() if s['id']==main['squad_id'])
    result=preview(client,goal['id'])
    p=result['proposals'][0]
    assert p['squad']['composition_ready'] and not p['active_objective_verified']
    assert not result['progress_changed'] and result['actions_pending'][0]['status']=='pending_match'
    assert goal['id'] not in [g['id'] for g in client.get('/objectives').json()]
    exported=client.post('/objective-planning/export',json={'token':p['token']})
    assert exported.status_code==200 and not exported.json()['progress_changed']
    saved=client.post('/objective-planning/save',json={'token':p['token'],'name':p['name'],'protect':True})
    assert saved.status_code==201,saved.text
    assert saved.json()['id']!=main['squad_id'] and saved.json()['protected'] and not saved.json()['primary']
    assert not saved.json()['applied_in_ea']
    assert client.get('/squads/main').json()==main
    assert next(s for s in client.get('/squads').json() if s['id']==main['squad_id'])==before
    stored=next(s for s in client.get('/squads').json() if s['id']==saved.json()['id'])
    assert stored['objective_context']['objective_ids']==[goal['id']]
    assert stored['objective_context']['status']=='saved_observation'
    after=next(g for g in client.get('/objective-planning').json()['items'] if g['id']==goal['id'])
    assert after==goal
    assert client.post('/objective-planning/save',json={'token':p['token'],'name':'Otra vez'}).status_code==409


@pytest.mark.parametrize('change',['rules','progress','inventory','protection','expiry','token_expiry'])
def test_changes_invalidate_save_and_export(client,monkeypatch,change):
    goal,body=setup_goal(client)
    token=preview(client,goal['id'])['proposals'][0]['token']
    if change=='rules':
        assert client.put(f"/objective-planning/{goal['id']}",json={**body,'target':4}).status_code==200
    elif change=='progress':
        assert client.patch(f"/objective-planning/{goal['id']}/progress",json={'value':1,'note':'Declarado tras jugar','phrase':'REGISTRAR PROGRESO MANUAL'}).status_code==200
    elif change in {'inventory','protection'}:
        pid=client.get('/players?limit=1').json()['items'][0]['id']
        assert client.patch(f'/players/{pid}',json={'price':123} if change=='inventory' else {'favorite':True}).status_code==200
    elif change=='expiry':
        with SessionLocal() as db:
            db.get(Objective,goal['id']).expires_at=now()-timedelta(seconds=1)
            db.commit()
    else:
        from app.services import objective_planning
        stamp=objective_planning.time.time()
        monkeypatch.setattr(objective_planning.time,'time',lambda:stamp+600)
    assert client.post('/objective-planning/save',json={'token':token,'name':'Propuesta anterior'}).status_code==409
    assert client.post('/objective-planning/export',json={'token':token}).status_code==409


def test_conflicting_modes_and_expired_rules_cannot_claim_an_active_ready_team(client):
    goal,body=setup_goal(client)
    other=client.post('/objective-planning',json={**body,'name':'Otra modalidad','rules':{**body['rules'],'mode':'rivals'}}).json()
    response=client.post('/objective-planning/preview',json={'objective_ids':[goal['id'],other['id']]})
    assert response.status_code==200 and response.json()['status']=='conflict'
    assert response.json()['proposals']==[] and len(response.json()['context']['sessions'])==2
    expired=client.post('/objective-planning',json={**body,'expires_at':(now()-timedelta(seconds=1)).isoformat()}).json()
    assert expired['expired']
    assert client.post('/objective-planning/preview',json={'objective_ids':[expired['id']]}).status_code==409


def test_manual_progress_is_labelled_and_can_be_returned_to_unknown(client):
    goal,_=setup_goal(client)
    progress=client.patch(f"/objective-planning/{goal['id']}/progress",json={'value':2,'note':'Contador revisado por mí','phrase':'REGISTRAR PROGRESO MANUAL'})
    assert progress.status_code==200
    assert progress.json()['progress']['value']==2 and progress.json()['progress']['origin']=='manual'
    preview(client,goal['id'])
    cleared=client.patch(f"/objective-planning/{goal['id']}/progress",json={'value':None,'note':'Ya no tengo certeza del contador','phrase':'REGISTRAR PROGRESO MANUAL'})
    assert cleared.json()['progress']['value'] is None and not cleared.json()['completed']


def test_parallel_save_creates_only_one_alternative(client):
    goal,_=setup_goal(client)
    p=preview(client,goal['id'])['proposals'][0]
    def save(_):
        return client.post('/objective-planning/save',json={'token':p['token'],'name':'Objetivos - prueba paralela - FC27'}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        codes=list(pool.map(save,range(2)))
    assert sorted(codes)==[201,409]
    assert len([s for s in client.get('/squads').json() if s['name']=='Objetivos - prueba paralela - FC27'])==1


def test_same_name_is_rejected_and_legacy_counters_without_source_remain_unknown(client):
    goal,_=setup_goal(client)
    main=client.get('/squads/main').json()
    p=preview(client,goal['id'])['proposals'][0]
    assert client.post('/objective-planning/save',json={'token':p['token'],'name':main['snapshot']['name']}).status_code==409
    legacy=client.get('/objectives').json()
    assert legacy and all(row['progress'] is None and row['progress_origin']=='unknown' for row in legacy)
