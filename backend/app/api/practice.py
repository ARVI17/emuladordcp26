from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.planner import PracticeSession
from app.schemas.api import InputModel
from app.services.audit import record
from app.services.editions import current_version
from app.services.locks import resource_locks
from app.services.practice import catalog, build_agenda

router = APIRouter(tags=['Práctica local'])


class PracticeInput(InputModel):
    focus: Literal['defending', 'switching', 'runs', 'passing', 'crossing', 'playstyles']
    minutes: int = Field(ge=5, le=90)
    platform: Literal['PlayStation', 'Xbox', 'PC', 'Switch']


class PracticeResult(InputModel):
    status: Literal['completed', 'cancelled']
    attempts: int = Field(default=0, ge=0, le=1000)
    successes: int = Field(default=0, ge=0, le=1000)
    minutes: int = Field(default=0, ge=0, le=240)
    next_change: str = Field(default='', max_length=300)

    @model_validator(mode='after')
    def consistent(self):
        if self.successes > self.attempts or (self.status == 'completed' and (not self.attempts or not self.minutes or not self.next_change.strip())):
            raise ValueError('Registra intentos, minutos y un ajuste; aciertos no puede superar intentos')
        return self


def data(row):
    return {k: getattr(row, k) for k in ('id', 'game_version', 'created_at', 'agenda', 'status', 'result')}


@router.get('/practice/catalog')
def practice_catalog(db: Session = Depends(get_db)):
    return catalog() if current_version(db) == 'FC27' else {**catalog(), 'game_version': current_version(db), 'drills': {}, 'notice': 'Archivo histórico: estas prácticas solo se revisaron para FC27.'}


@router.get('/practice/sessions')
def sessions(db: Session = Depends(get_db)):
    if catalog()['review_due']:
        return []
    return [data(r) for r in db.scalars(select(PracticeSession).where(PracticeSession.game_version == current_version(db), PracticeSession.agenda['reviewed_on'].as_string() == catalog()['reviewed_on']).order_by(PracticeSession.id.desc()).limit(50))]


@router.post('/practice/sessions', status_code=201)
def create(payload: PracticeInput, db: Session = Depends(get_db)):
    if current_version(db) != 'FC27':
        raise HTTPException(409, 'Las prácticas disponibles requieren FC27')
    try:
        agenda = build_agenda(payload.focus, payload.minutes, payload.platform)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    row = PracticeSession(game_version='FC27', agenda=agenda)
    db.add(row)
    db.flush()
    record(db, 'plan_practice', 'practice_session', row.id)
    db.commit()
    return data(row)


@router.post('/practice/sessions/{session_id}/result')
def result(session_id: int, payload: PracticeResult, db: Session = Depends(get_db)):
    with resource_locks(db, f'practice:{session_id}'):
        row = db.get(PracticeSession, session_id)
        if not row or row.game_version != current_version(db) or catalog()['review_due'] or row.agenda.get('reviewed_on') != catalog()['reviewed_on']:
            raise HTTPException(404, 'Práctica no disponible en esta edición')
        if row.status != 'planned':
            raise HTTPException(409, 'La práctica ya tiene resultado; crea otra sesión')
        row.status, row.result = payload.status, payload.model_dump(exclude={'status'})
        record(db, 'record_practice', 'practice_session', row.id)
        db.commit()
        return data(row)
