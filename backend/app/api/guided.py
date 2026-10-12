from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.planner import ClubPlan
from app.schemas.assisted import GuidedProposalInput, GuidedTransition
from app.services.assisted import require_assisted
from app.services.guided import create_guide, own_plan, plan_data, transition
from app.services.locks import resource_locks
from app.services.audit import record

router = APIRouter(prefix='/assisted/guides', tags=['Aplicación manual guiada'])
DB = Annotated[Session, Depends(get_db)]


@router.get('')
def guides(db: DB):
    require_assisted(db)
    return [plan_data(db, p) for p in db.scalars(select(ClubPlan).where(ClubPlan.inputs['mode'].as_string() == 'assisted_guided').order_by(ClubPlan.id.desc()).limit(50))]


@router.post('', status_code=201)
def create(payload: GuidedProposalInput, db: DB):
    with resource_locks(db, 'inventory'):
        db.expire_all()
        result = create_guide(db, payload.token)
        record(db, 'prepare_manual_guide', 'club_plan', result['id'], {'executed_in_ea': False})
        db.commit()
        return result


@router.post('/{identifier}/transition')
def change(identifier: int, payload: GuidedTransition, db: DB):
    with resource_locks(db, 'inventory'):
        db.expire_all()
        plan = own_plan(db, identifier)
        before = plan_data(db, plan)['state_hash']
        result = transition(db, plan, payload)
        if before != result['state_hash']:
            record(db, 'manual_guide_'+payload.action, 'club_plan', plan.id,
                {'status': plan.status, 'remote_write': False, 'reading_ids': payload.reading_ids})
        db.commit()
        return result
