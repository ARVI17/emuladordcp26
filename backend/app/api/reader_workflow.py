"""Single CTA, durable checkpoint, bounded deterministic local calculations."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.reader import authenticated
from app.schemas.reader_workflow import WorkflowAction, ViewState
from app.services import reader_workflow as workflow
from app.services.audit import record
from app.services.locks import resource_locks
from app.models.entities import now

router = APIRouter(tags=['Analizar mi club'])


def start(db):
    with resource_locks(db, 'inventory', 'workflow:'+str(db.info['context'].id)):
        db.expire_all()
        row = workflow.begin(db)
        result = workflow.calculate(db, row)
        record(db, 'analyze_club', 'reader', 0, {'workflow_id':row.id, 'remote_write':False})
        db.commit()
        return result


@router.post('/club/analyze')
def analyze(db: Session = Depends(get_db)):
    return start(db)


@router.get('/club/analysis-workflow')
def status(db: Session = Depends(get_db)):
    return workflow.serialize(workflow.current(db))


def action(db, payload):
    with resource_locks(db, 'inventory', 'workflow:'+str(db.info['context'].id)):
        db.expire_all()
        row = workflow.current(db)
        if not row:
            raise HTTPException(409, 'Inicia primero Analizar mi club.')
        row.status = {'pause':'paused','resume':'active','cancel':'cancelled'}[payload.action]
        row.updated_at = now()
        if payload.action == 'resume':
            if row.generation != db.info['context'].generation:
                row.generation = db.info['context'].generation
                row.trusted_profiles, row.view_state = {}, {}
            row._generation_valid = True
            row.requested_at = now()
            workflow.calculate(db, row)
        if payload.action == 'cancel':
            row.trusted_profiles = {}
        record(db, 'workflow_'+payload.action, 'reader', 0, {'workflow_id':row.id})
        db.commit()
        return workflow.serialize(row)


@router.post('/club/analysis-workflow/action')
def control(payload: WorkflowAction, db: Session = Depends(get_db)):
    return action(db, payload)


@router.get('/reader/workflow')
def reader_status(auth=Depends(authenticated)):
    db, _grant = auth
    return workflow.serialize(workflow.current(db))


@router.post('/reader/workflow/start')
def reader_start(auth=Depends(authenticated)):
    return start(auth[0])


@router.post('/reader/workflow/action')
def reader_control(payload: WorkflowAction, auth=Depends(authenticated)):
    return action(auth[0], payload)


@router.post('/reader/workflow/view')
def view(payload: ViewState, auth=Depends(authenticated)):
    db, _grant = auth
    with resource_locks(db, 'inventory', 'workflow:'+str(db.info['context'].id)):
        db.expire_all()
        row = workflow.current(db)
        if not row or row.status != 'active' or row.generation != db.info['context'].generation:
            raise HTTPException(409, 'El recorrido está pausado o cancelado.')
        if payload.code == 'ready_sample' and (payload.source not in {'synthetic_dom','user_export_dom'} or not payload.profile_verified):
            raise HTTPException(422, 'El estado requiere una muestra propia con perfil validado; no acredita EA.')
        row.view_state = payload.model_dump()
        row.updated_at = now()
        # Recompute stages and recommendations only after real activity, never from a status GET.
        result = workflow.calculate(db, row)
        db.commit()
        return result


@router.post('/reader/workflow/refresh')
def refresh(auth=Depends(authenticated)):
    db, _grant = auth
    with resource_locks(db, 'inventory', 'workflow:'+str(db.info['context'].id)):
        db.expire_all()
        row = workflow.current(db)
        if not row or row.status != 'active' or row.generation != db.info['context'].generation:
            raise HTTPException(409, 'El recorrido está pausado o cancelado.')
        result = workflow.calculate(db, row)
        db.commit()
        return result
