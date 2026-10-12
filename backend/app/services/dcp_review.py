"""Read-only DCP filters and signed proposals, revalidated inside the inventory lock."""
import base64
import hashlib
import hmac
import json
import time
from fastapi import HTTPException
from sqlalchemy import select
from app.models.entities import Player, now
from app.models.planner import ExternalItemMapping, Reservation
from app.schemas.api import DcpFilters


def locations(db):
    return {m.player_id: m.location for m in db.scalars(select(ExternalItemMapping))}


def matches(player, filters, location='local'):
    if not filters.min_rating <= player.rating <= filters.max_rating:
        return False
    for field in ('position', 'league', 'club', 'nationality', 'card_type', 'tradable', 'special'):
        expected = getattr(filters, field)
        if expected is not None and (field in (player.unknown_fields or []) or getattr(player, field) != expected):
            return False
    if filters.duplicate is not None and player.duplicate_untradeable != filters.duplicate:
        return False
    if filters.max_price is not None and (player.price is None or player.price > filters.max_price):
        return False
    if filters.location is not None and filters.location != location:
        return False
    if filters.preset == 'keep_special' and (player.special or player.is_evolution or 'special' in (player.unknown_fields or [])):
        return False
    return True


def exclusion_reason(player, protected, structural):
    if player.id in structural:
        return 'Plantilla principal o reservas conservadas'
    if player.id in protected:
        return 'Protección individual, de equipo o reserva de un plan'
    if player.is_loan:
        return 'Cesión: no se puede consumir'
    if not player.data_reviewed or player.unknown_fields:
        return 'Datos necesarios pendientes de revisión'
    if player.availability != 'available':
        return 'Copia no disponible'
    return None


def eligible(db, players, filters, protected):
    from app.services.main_squad import main_ids
    structural, places = main_ids(db), locations(db)
    return [p for p in players if matches(p, filters, places.get(p.id, 'local')) and not exclusion_reason(p, protected, structural)]


def current_review(db, segment):
    from app.services.planner import inventory_fingerprint
    from app.services.main_squad import fingerprint
    from app.api.routes import requirements_for_batch, score_progress
    context, session = db.info['context'], db.info['local_session']
    claims = [(r.player_id, r.plan_id, str(r.expires_at)) for r in db.scalars(select(Reservation).where(Reservation.expires_at > now()).order_by(Reservation.player_id))]
    return fingerprint(dict(context=context.id, entry=session.entry_id, snapshot=context.snapshot_id, revision=context.revision,
        inventory=inventory_fingerprint(db), reservations=claims, segment=segment.id,
        rules=requirements_for_batch(db, segment), progress=score_progress(db, segment)))


def issue_review(db, segment, ids, filters):
    from app.api.routes import _import_secret
    payload = dict(version=1, state=current_review(db, segment), ids=sorted(ids), filters=filters.model_dump(), expires=int(time.time())+300)
    encoded = base64.urlsafe_b64encode(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).decode().rstrip('=')
    signature = hmac.new(_import_secret(db), encoded.encode(), hashlib.sha256).hexdigest()
    return encoded+'.'+signature


def check_review(db, segment, ids, token):
    from app.api.routes import _import_secret
    try:
        encoded, signature = (token or '').split('.')
        if not hmac.compare_digest(signature, hmac.new(_import_secret(db), encoded.encode(), hashlib.sha256).hexdigest()):
            raise ValueError()
        payload = json.loads(base64.urlsafe_b64decode(encoded+'='*(-len(encoded)%4)))
        if payload['version'] != 1 or payload['expires'] < time.time() or payload['ids'] != sorted(ids) or payload['state'] != current_review(db, segment):
            raise ValueError()
        return DcpFilters.model_validate(payload['filters'])
    except (ValueError, KeyError, TypeError):
        raise HTTPException(409, 'La propuesta no está revisada, caducó o cambiaron datos, requisitos, reservas o principal. Vuelve a calcular.') from None
