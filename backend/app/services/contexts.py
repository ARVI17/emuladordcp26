"""A browser session is local access, never evidence of EA account identity."""
import hashlib
import hmac
from datetime import timedelta, timezone
from fastapi import HTTPException, Request
from sqlalchemy import event, inspect, select, text
from sqlalchemy.orm import Session, with_loader_criteria
from app.models.entities import ClubScoped, Player, now
from app.models.planner import LocalUser, ClubContext, LocalSession, AppEntry, InventorySnapshot

COOKIE = "club_lab_session"


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def ensure_local_context(db):
    if db.get(LocalUser, 1) is None:
        db.add(LocalUser(id=1, name="Propietario local"))
        db.flush()
        if db.get_bind().dialect.name == "postgresql":
            db.execute(text("SELECT setval(pg_get_serial_sequence('local_users','id'), (SELECT max(id) FROM local_users))"))
    if db.get(ClubContext, 1) is None:
        db.add(ClubContext(id=1, owner_id=1, name="Registro local sin vincular", verified=False))
        db.flush()
        if db.get_bind().dialect.name == "postgresql":
            db.execute(text("SELECT setval(pg_get_serial_sequence('club_contexts','id'), (SELECT max(id) FROM club_contexts))"))


def check_origin(request):
    origin = request.headers.get("origin")
    from app.core.config import settings
    same_origin = f"{request.url.scheme}://{request.url.netloc}"
    if origin and origin not in {*settings.allowed_origins, same_origin}:
        raise HTTPException(403, "Origen no permitido")


def session_for(db, request, *, mutate=False):
    token = request.cookies.get(COOKIE, "")
    session = db.get(LocalSession, digest(token)) if token else None
    if session is None or utc(session.expires_at) <= now():
        raise HTTPException(401, "La sesión local caducó. Vuelve a abrir la aplicación.")
    if mutate:
        check_origin(request)
        if not hmac.compare_digest(digest(request.headers.get("X-CSRF-Token", "")), session.csrf_hash):
            raise HTTPException(403, "Reabre la aplicación para revisar esta acción")
    context = db.get(ClubContext, session.context_id)
    if context is None or context.owner_id != session.owner_id or context.game_version != "FC27":
        raise HTTPException(404, "Contexto no disponible")
    db.info.update(club_context_id=context.id, local_session=session, context=context)
    return session, context


MODULE_FIELDS = {
    "squads": {"inventory"}, "analysis": {"inventory"}, "transfers": {"inventory", "coins"},
    "dcp": {"inventory", "dcp"}, "gallery": {"gallery"}, "evolutions": {"inventory", "evolutions"},
    "chat": {"inventory"}, "market": {"inventory", "coins"},
}


def sync_state(db, context, entry=None):
    snapshot = db.get(InventorySnapshot, context.snapshot_id) if context.snapshot_id else None
    fresh = bool(snapshot and now() - utc(snapshot.observed_at) <= timedelta(minutes=15))
    checked = bool(entry and entry.snapshot_id == context.snapshot_id and entry.status in {"ready", "partial"})
    coverage = snapshot.coverage if snapshot else {}
    modules = {}
    for name, fields in MODULE_FIELDS.items():
        missing = sorted(field for field in fields if not coverage.get(field, {}).get("complete"))
        ready = bool(context.verified and checked and fresh and not missing)
        modules[name] = {"ready": ready, "missing": missing, "reason": None if ready else "Falta una lectura autorizada vigente con cobertura suficiente"}
    status = entry.status if entry else "sync_required"
    if checked and not fresh:
        status = "sync_required"
    labels = {"ready": "Verificado", "syncing": "Sincronizando", "partial": "Parcial", "no_permissions": "Sin permisos",
              "sync_required": "Desactualizado", "offline": "Sin conexión", "error": "Error de lectura",
              "review_required": "Requiere revisión", "rate_limited": "Espera requerida", "unavailable": "Integración pendiente"}
    return {"entry_id": entry.id if entry else None, "club_context_id": context.id,
            "game_version": context.game_version,
            "status": status, "label": "Integración pendiente" if not context.verified else labels.get(status, "Requiere revisión"),
            "identity_verified": context.verified, "snapshot_id": snapshot.id if snapshot else None,
            "revision": context.revision, "remote_revision": snapshot.revision if snapshot else None,
            "observed_at": utc(snapshot.observed_at).isoformat() if snapshot else None,
            "imported_at": utc(snapshot.imported_at).isoformat() if snapshot else None,
            "last_attempt": utc(entry.checked_at).isoformat() if entry else None, "coverage": coverage, "modules": modules,
            "next_action": "Se necesita aprobación de EA para esta aplicación y documentación del protocolo, permisos, identidad, copias y paginación.",
            "local_history_available": True}


def require_module(db, name, *, allow_local=True, expected_plan=None):
    from app.services.editions import current_version
    session = db.info.get("local_session")
    context = db.info.get("context")
    if session is None or context is None:
        raise HTTPException(401, "Se requiere una sesión local")
    if allow_local and session.mode == "local" and not context.verified:
        return {"scope": "local_unlinked", "game_version": current_version(db), "entry_id": session.entry_id, "club_context_id": context.id, "snapshot_id": None, "revision": context.revision}
    entry = db.get(AppEntry, session.entry_id) if session.entry_id else None
    state = sync_state(db, context, entry)
    # Only the already approved batch may continue from its own confirmed effects.
    # Other analyses stay blocked until another authorized remote observation.
    if expected_plan and entry and state["status"] == "review_required" and expected_plan.approval.get("post_action_entry") == entry.id:
        snapshot = db.get(InventorySnapshot, context.snapshot_id) if context.snapshot_id else None
        controlled = (context.verified and expected_plan.entry_id == entry.id and expected_plan.snapshot_id == context.snapshot_id
                      and entry.snapshot_id == context.snapshot_id and snapshot and now()-utc(snapshot.observed_at) <= timedelta(minutes=15)
                      and not state["modules"][name]["missing"])
        if controlled:
            return {key: state[key] for key in ("entry_id", "club_context_id", "snapshot_id", "revision", "remote_revision", "coverage", "game_version")}
    if not state["modules"][name]["ready"]:
        raise HTTPException(409, {"message": "Integración pendiente: no hay datos vigentes del club verificado para este módulo", "state": state})
    return {key: state[key] for key in ("entry_id", "club_context_id", "snapshot_id", "revision", "remote_revision", "coverage", "game_version")}


@event.listens_for(Session, "do_orm_execute")
def scope_reads(execute_state):
    context_id = execute_state.session.info.get("club_context_id")
    if context_id is not None and execute_state.is_select:
        execute_state.statement = execute_state.statement.options(with_loader_criteria(
            ClubScoped, lambda cls: cls.club_context_id == context_id, include_aliases=True))
        # Includes aggregates, aliases and relationship loads. Historical access is
        # internal only (unbound sessions used by backups/migrations).
        from app.db.base import Base
        for mapper in Base.registry.mappers:
            model = mapper.class_
            if hasattr(model, "game_version"):
                execute_state.statement = execute_state.statement.options(
                    with_loader_criteria(model, model.game_version == "FC27", include_aliases=True))
        from app.models.entities import Challenge, Segment, SquadPlayer
        from app.models.planner import ClubPlan
        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(ClubPlan, ClubPlan.inputs['binding']['game_version'].as_string() == 'FC27', include_aliases=True),
            with_loader_criteria(Segment, Segment.challenge_id.in_(select(Challenge.id).where(Challenge.game_version == "FC27")), include_aliases=True),
            with_loader_criteria(SquadPlayer, SquadPlayer.player_id.in_(select(Player.id).where(Player.game_version == "FC27")), include_aliases=True))
        if not execute_state.execution_options.get('include_quarantine'):
            from app.services.catalog_validation import active_player_clause, active_gallery_clause, variant_conditions
            from app.models.catalog import CardVariant
            from app.models.entities import GalleryEntry
            from app.models.planner import MarketQuote, TradeRecord, MarketAlert
            execute_state.statement = execute_state.statement.options(
                with_loader_criteria(Player, active_player_clause(), include_aliases=True),
                with_loader_criteria(GalleryEntry, active_gallery_clause(), include_aliases=True))
            for model in (MarketQuote, TradeRecord, MarketAlert):
                execute_state.statement = execute_state.statement.options(with_loader_criteria(
                    model, model.variant_id.in_(select(CardVariant.variant_id).where(*variant_conditions())), include_aliases=True))


@event.listens_for(Session, "before_flush")
def scope_writes(db, *_):
    context_id = db.info.get("club_context_id")
    if context_id is None:
        return
    for obj in db.new | db.dirty | db.deleted:
        if hasattr(obj, "game_version") and obj.game_version not in (None, "FC27"):
            raise HTTPException(422, "Solo se admiten datos FC27; el histórico permanece aislado")
        if not isinstance(obj, ClubScoped):
            continue
        if obj in db.new and obj.club_context_id is None:
            obj.club_context_id = context_id
        if obj.club_context_id != context_id:
            raise HTTPException(404, "Registro no disponible en este contexto")
    changed = [obj for obj in db.new | db.dirty | db.deleted if isinstance(obj, Player) and (obj in db.new or obj in db.deleted or db.is_modified(obj))]
    if changed:
        context = db.get(ClubContext, context_id)
        context.revision += 1
        if context.verified and not db.info.get("remote_reconciliation"):
            preferences = {"notes", "favorite", "protected", "starter", "usefulness", "squad_role", "updated_at"}
            factual_change = any(obj in db.new or obj in db.deleted or any(a.history.has_changes() and a.key not in preferences for a in inspect(obj).attrs) for obj in changed)
            if factual_change:
                session = db.info.get("local_session")
                entry = db.get(AppEntry, session.entry_id) if session and session.entry_id else None
                if entry:
                    entry.status = "review_required"


def bind_request(db, request: Request):
    path = request.url.path.removeprefix("/api")
    if path == "/health":
        return
    if any(request.query_params.get(key) not in (None, "FC27") for key in ("game_version", "edition")):
        raise HTTPException(422, "Solo FC27 está disponible en la aplicación")
    session, _ = session_for(db, request, mutate=request.method not in {"GET", "HEAD", "OPTIONS"})
    if path.startswith(("/settings", "/audit", "/profile")):
        return
    if not session.entry_id:
        raise HTTPException(409, "Comprueba el estado del club al entrar")
    claimed = request.headers.get("X-App-Entry")
    if claimed != str(session.entry_id):
        raise HTTPException(409, "La entrada cambió. Actualiza esta pestaña.")
    module = next((name for prefix, name in [
        ("/club/analysis", "analysis"), ("/squads/recommend", "squads"),
        ("/segments/", "dcp"), ("/evolutions/preview", "evolutions"), ("/ai/chat", "chat"),
        ("/ai/dcp/analyze", "dcp"), ("/gallery/record-inventory", "gallery"),
    ] if path.startswith(prefix)), None)
    if module:
        require_module(db, module)

from app.services import protection  # noqa: E402,F401
