"""Shared enforcement for legacy and planner mutation paths."""
from fastapi import HTTPException
from sqlalchemy import event, inspect, select
from sqlalchemy.orm import Session
from app.models.entities import Player, Squad, SquadPlayer, now
from app.models.planner import Reservation
from app.services.contexts import utc


def reserved_ids(db):
    return set(db.scalars(select(Reservation.player_id).where(Reservation.expires_at > now(), Reservation.plan_id != db.info.get("executing_plan", -1))))


@event.listens_for(Session, "before_flush")
def guard_mutations(db, *_):
    # Internal migrations/fixtures use unscoped sessions. All HTTP domain sessions are scoped.
    if "club_context_id" not in db.info or db.info.get("remote_reconciliation"):
        return
    for obj in db.dirty:
        if isinstance(obj, Player):
            state = inspect(obj)
            changed = {attr.key for attr in state.attrs if attr.history.has_changes()}
            dangerous = changed - {"notes", "updated_at"}
            if changed <= {"protected", "favorite", "notes", "updated_at"} and all(getattr(obj, key) for key in changed & {"protected", "favorite"}):
                dangerous = set()
            reservation = db.get(Reservation, obj.id)
            if dangerous and reservation and utc(reservation.expires_at) > now() and reservation.plan_id != db.info.get("executing_plan"):
                raise HTTPException(409, "La carta está reservada por otro plan; revisa o cancela ese plan")
            if "deleted" in changed and obj.deleted:
                from app.services.squad_analysis import effective_protected_ids
                if obj.id in effective_protected_ids(db, obj.game_version) and obj.id not in db.info.get("reviewed_exception_ids", set()):
                    raise HTTPException(409, "La carta está protegida; revisa una acción específica antes de retirarla")
            if any(field in changed and not getattr(obj, field) and state.attrs[field].history.deleted and state.attrs[field].history.deleted[0] for field in ("starter", "favorite", "is_evolution", "protected")):
                if obj.id not in db.info.get("reviewed_exception_ids", set()):
                    raise HTTPException(409, "Desproteger esta carta requiere una revisión específica en Planes")
        elif isinstance(obj, Squad) and inspect(obj).attrs.protected.history.has_changes() and not obj.protected:
            ids = {row.player_id for row in db.scalars(select(SquadPlayer).where(SquadPlayer.squad_id == obj.id))}
            if ids & reserved_ids(db):
                raise HTTPException(409, "La plantilla contiene cartas reservadas")
