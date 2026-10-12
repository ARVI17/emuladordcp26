from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.entities import Squad
from app.schemas.api import InputModel
from app.services.audit import record
from app.services.locks import resource_locks
from app.services.main_squad import main_status, select_main

router = APIRouter(tags=['Plantilla principal'])
DB = Annotated[Session, Depends(get_db)]


class MainSelection(InputModel):
    phrase: str = Field(max_length=100)
    expected_state_hash: str = Field(min_length=64, max_length=64)
    complete: bool


@router.get('/squads/main')
def status(db: DB):
    return main_status(db)


@router.post('/squads/{squad_id}/main')
def protect_main(squad_id: int, payload: MainSelection, db: DB):
    if payload.phrase != f'PROTEGER PRINCIPAL {squad_id}':
        raise HTTPException(422, f'Escribe PROTEGER PRINCIPAL {squad_id} para revisar esta selección.')
    with resource_locks(db, 'inventory'):
        db.expire_all()
        from app.services.contexts import require_module
        require_module(db, 'squads')
        squad = db.get(Squad, squad_id)
        if not squad:
            raise HTTPException(404, 'Plantilla no disponible.')
        result = select_main(db, squad, expected_hash=payload.expected_state_hash, complete=payload.complete)
        record(db, 'select_main', 'squad', squad.id, {'revision': result['revision'], 'preserved_previous_locks': len(result['retained_copy_ids'])})
        db.commit()
        return result
