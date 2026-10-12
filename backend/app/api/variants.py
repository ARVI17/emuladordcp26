from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.catalog import CardVariant
from app.models.entities import Player
from app.schemas.api import InputModel, PlayerCreate
from app.services.audit import record
from app.services.catalog_validation import active_player_clause, copy_result, validate_copy, variant_conditions
from app.services.gallery import record_player
from app.services.locks import resource_locks
from app.services.squad_analysis import serialize_player

router = APIRouter(tags=['Catálogo FC27 y cuarentena'])


@router.get('/catalog/variants')
def catalog(search: str = Query(default='', max_length=100), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)):
    query = select(CardVariant).where(*variant_conditions(), CardVariant.name.ilike('%'+search+'%')).order_by(CardVariant.name, CardVariant.id)
    rows = list(db.scalars(query.offset(offset).limit(51)))
    return {'items': [{k: getattr(row, k) for k in ('id', 'game_version', 'variant_id', 'name', 'rating', 'position', 'card_type', 'source_url', 'observed_at', 'valid_until', 'validation_status')} for row in rows[:50]],
            'has_more': len(rows) > 50, 'offset': offset, 'ownership': False, 'prices': None}


@router.get('/inventory/quarantine')
def quarantine(offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)):
    conditions = (Player.game_version == 'FC27', Player.deleted.is_(False), Player.data_source != 'demo', ~active_player_clause())
    query = select(Player).where(*conditions).execution_options(include_quarantine=True)
    count = db.scalar(select(func.count(Player.id)).where(*conditions).execution_options(include_quarantine=True))
    rows = list(db.scalars(query.order_by(Player.id).offset(offset).limit(20)))
    return {'items': [{'id': p.id, 'claim': {k: getattr(p, k) for k in PlayerCreate.model_fields},
                       'validation_status': 'pending_verification', 'available': False,
                       'evidence': p.validation_evidence} for p in rows], 'total': count, 'offset': offset,
            'message': 'Declaraciones pendientes, fuera del inventario disponible. Una marca manual no verifica una fuente.'}


class ReviewCopy(InputModel):
    player: PlayerCreate
    source_url: str = Field(pattern='^https://', max_length=500)
    confirmation: str = Field(max_length=80)

    @field_validator('source_url')
    @classmethod
    def public_source(cls, value):
        parsed = urlsplit(value)
        if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('Usa una referencia pública sin credenciales ni parámetros privados')
        return value


@router.post('/inventory/quarantine/{player_id}/review')
def review(player_id: int, payload: ReviewCopy, db: Session = Depends(get_db)):
    with resource_locks(db, 'inventory'):
        db.expire_all()
        player = db.get(Player, player_id, execution_options={'include_quarantine': True})
        if not player or player.deleted or player.game_version != 'FC27' or player.data_source == 'demo':
            raise HTTPException(404, 'Declaración no disponible')
        if payload.confirmation != f'REVISAR FC27 {player_id}':
            raise HTTPException(422, 'Confirma la revisión de esta copia exacta')
        if player.validation_status in ('documented', 'provider_verified') and player.catalog_variant_id:
            # Never use this endpoint to change an already verified/protected copy.
            if db.scalar(select(Player.id).where(Player.id == player_id)):
                raise HTTPException(409, 'La copia ya está activa; usa la edición habitual')
        values = payload.player.model_dump()
        consumed = db.scalar(select(Player.id).where(Player.id != player_id, Player.deleted.is_(True),
            Player.game_version == 'FC27', Player.name == values['name'], Player.rating == values['rating'],
            Player.position == values['position']).execution_options(include_quarantine=True))
        if consumed:
            raise HTTPException(409, 'Coincide con una carta retirada; concilia la identidad antes de activarla')
        for key, value in values.items():
            if key not in {'protected', 'favorite', 'starter', 'notes', 'squad_role', 'usefulness'}:
                setattr(player, key, value)
        accepted = validate_copy(db, player, explicit_edition='game_version' in payload.player.model_fields_set)
        player.validation_evidence = {**player.validation_evidence, 'submitted_source': payload.source_url, 'manual_review_is_official': False}
        if accepted:
            record_player(db, player)
        record(db, 'review_quarantine', 'player', player_id, {'activated': accepted})
        db.commit()
        return serialize_player(player) if accepted else copy_result(player)
