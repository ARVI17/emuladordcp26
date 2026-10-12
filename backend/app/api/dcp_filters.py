from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.entities import Player, Segment
from app.schemas.api import ConfirmRequest, DcpFilters
from app.services.audit import record
from app.services.editions import ensure_profile
from app.services.locks import resource_locks
from app.services.squad_analysis import effective_protected_ids, serialize_player
from app.services.main_squad import main_ids, main_status
from app.services.dcp_review import eligible, exclusion_reason, issue_review

router = APIRouter(tags=['Filtros y revisión DCP'])
DB = Annotated[Session, Depends(get_db)]


@router.get('/dcp/preferences')
def preferences(db: DB):
    return DcpFilters.model_validate((ensure_profile(db).preferences or {}).get('dcp_filters', {})).model_dump()


@router.put('/dcp/preferences')
def save_preferences(payload: DcpFilters, db: DB):
    with resource_locks(db, 'inventory'):
        db.expire_all()
        profile = ensure_profile(db)
        profile.preferences = {**(profile.preferences or {}), 'dcp_filters': payload.model_dump()}
        record(db, 'dcp_filters', 'profile', profile.id)
        db.commit()
        return payload.model_dump()


@router.get('/dcp/exclusions')
def exclusions(db: DB, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    protected, structural = effective_protected_ids(db), main_ids(db)
    active = set(db.scalars(select(Player.id)))
    rows = list(db.scalars(select(Player).where(Player.deleted.is_(False)).execution_options(include_quarantine=True).order_by(Player.id)))
    items = []
    for p in rows:
        reason = exclusion_reason(p, protected, structural)
        if not reason and p.id not in active:
            reason = 'Variante pendiente de verificación'
        if reason:
            items.append(dict(id=p.id, name=p.name, rating=p.rating, reason=reason, consumable=False))
    return dict(items=items[offset:offset+limit], total=len(items), offset=offset, limit=limit, main=main_status(db))


@router.post('/segments/{segment_id}/review')
def review_selection(segment_id: int, payload: ConfirmRequest, db: DB):
    from app.api.routes import requirements_for_batch, score_progress
    from app.optimizers.sbc import validate_solution
    with resource_locks(db, 'inventory'):
        db.expire_all()
        segment = db.get(Segment, segment_id)
        if not segment or segment.completed:
            raise HTTPException(409, 'Segmento no disponible.')
        players = list(db.scalars(select(Player).where(Player.id.in_(payload.player_ids), Player.deleted.is_(False))))
        filters = DcpFilters()
        if len(eligible(db, players, filters, effective_protected_ids(db))) != len(payload.player_ids):
            raise HTTPException(422, 'Hay copias protegidas, pendientes o no disponibles.')
        violations = validate_solution(players, requirements_for_batch(db, segment), current_score=score_progress(db, segment))
        if violations:
            raise HTTPException(422, {'message': 'La composición no es válida.', 'violations': violations})
        return dict(simulation=True, review_token=issue_review(db, segment, payload.player_ids, filters), main=main_status(db))
