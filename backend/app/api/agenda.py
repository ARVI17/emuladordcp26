from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, model_validator
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.api import InputModel
from app.schemas.planner import PlanInput, ActionInput
from app.services.agenda import agenda, compare
from app.services.locks import resource_locks

router = APIRouter(tags=['Agenda conjunta'])


class CompareInput(InputModel):
    a_id: int = Field(gt=0)
    b_id: int = Field(gt=0)


class AgendaInput(InputModel):
    budget: int = Field(ge=0, le=100_000_000)
    reserve_coins: int = Field(default=0, ge=0, le=100_000_000)
    priority_ids: list[int] = Field(default_factory=list, max_length=20)

    @model_validator(mode='after')
    def distinct(self):
        if len(set(self.priority_ids)) != len(self.priority_ids) or any(i < 1 for i in self.priority_ids):
            raise ValueError('Prioridades distintas con IDs positivos')
        return self


@router.post('/plans/compare')
def compare_routes(payload: CompareInput, db: Session = Depends(get_db)):
    if payload.a_id == payload.b_id:
        raise HTTPException(422, 'Selecciona dos rutas distintas')
    with resource_locks(db, 'inventory'):
        db.expire_all()
        return compare(db, payload.a_id, payload.b_id)


@router.post('/plans/agenda')
def plan_agenda(payload: AgendaInput, db: Session = Depends(get_db)):
    with resource_locks(db, 'inventory'):
        db.expire_all()
        return agenda(db, payload.budget, payload.reserve_coins, payload.priority_ids)


@router.post('/plans/{plan_id}/refresh', status_code=201)
def refresh_plan(plan_id: int, db: Session = Depends(get_db)):
    from app.models.planner import ClubPlan
    from app.api.planner import owned, save_plan
    from app.services.editions import current_version
    with resource_locks(db, 'inventory'):
        db.expire_all()
        original = owned(db, ClubPlan, plan_id)
        if original.status not in {'draft', 'reviewed'} or original.inputs['binding'].get('game_version', 'FC27') != current_version(db):
            raise HTTPException(409, 'Solo se recalculan borradores de la edición activa')
        actions = [{k: v for k, v in a.items() if k in ActionInput.model_fields} for a in original.inputs['actions']]
        payload = PlanInput(name=(original.name[:105]+' · recalculado'), actions=actions, budget=original.inputs['budget'], reserve_coins=original.inputs['reserve_coins'])
        return save_plan(payload, db)
