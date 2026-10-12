"""Local contracts. No authorize URL or remote adapter is fabricated."""
import hmac
import secrets
from datetime import timedelta
from typing import Literal
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import raw_db
from app.models.entities import now
from app.models.planner import AppEntry, ClubContext, LocalSession, ProviderConnection, SyncRun
from app.schemas.api import InputModel
from app.services.contexts import COOKIE, check_origin, digest, ensure_local_context, session_for, sync_state, utc
from app.services.editions import ensure_profile
from app.services.locks import resource_locks
from app.services.audit import record

router = APIRouter(tags=["Conexiones y entrada"])
EA_SOURCE = "https://help.ea.com/en/articles/ea-sports-fc/community-api/"
BLOCKER = "EA solo documenta acceso para socios aprobados. Este proyecto no dispone de aprobación ni protocolo de integración, permisos, identidad verificada o paginación documentados."


@router.get("/connections/capabilities")
def capabilities():
    fields = ["identity", "inventory", "copy_ids", "duplicates", "tradability", "loans", "transfer_list", "unassigned", "sbc_storage", "squads", "coins", "evolutions", "dcp", "history", "gallery", "pagination", "remote_revision", "background_refresh"]
    return {"provider": "ea_community", "status": "unavailable", "label": "Integración pendiente",
            "authorization_supported": False, "documentation_url": EA_SOURCE, "reviewed_on": "2026-10-11",
            "blocker": BLOCKER, "capabilities": {field: {"status": "unverified", "evidence": EA_SOURCE, "reason": "No hay concesión documentada para esta aplicación"} for field in fields},
            "approved_partners": ["FUTBIN", "FUT.GG", "FUTWIZ"], "automated_ea_operations": "unsupported",
            "implemented_reconciliation": ["inventory", "coins"],
            "pending_reconciliation": ["squads", "gallery", "dcp", "evolutions", "history"],
            "alternative": "Registro local revisado explícitamente; no verifica la cuenta ni sincroniza el club."}


@router.post("/app/session")
def open_session(request: Request, response: Response, db: Session = Depends(raw_db)):
    check_origin(request)
    with resource_locks(db, "sessions"):
        ensure_local_context(db)
        ensure_profile(db)
        token = request.cookies.get(COOKIE, "")
        session = db.get(LocalSession, digest(token)) if token else None
        # CSRF is derived from server material and a private HttpOnly session cookie.
        from app.api.routes import _import_secret
        if session is None or utc(session.expires_at) <= now():
            token = secrets.token_urlsafe(32)
            csrf = hmac.new(_import_secret(db), token.encode(), "sha256").hexdigest()
            session = LocalSession(id=digest(token), owner_id=1, context_id=1, csrf_hash=digest(csrf), expires_at=now()+timedelta(hours=12))
            db.add(session)
        else:
            csrf = hmac.new(_import_secret(db), token.encode(), "sha256").hexdigest()
        db.commit()
        response.set_cookie(COOKIE, token, httponly=True, samesite="strict", secure=request.url.scheme == "https", max_age=43200, path="/")
        # TestClient/direct development use / as well; production has root_path=/api.
        response.headers["Cache-Control"] = "no-store"
        return {"csrf_token": csrf, "context_id": session.context_id, "mode": session.mode,
                "entry_id": session.entry_id, "expires_at": session.expires_at, "local_session_only": True}


class EntryInput(InputModel):
    nonce: str = Field(min_length=8, max_length=80)
    reason: Literal["open", "resume", "switch", "retry"] = "open"
    mode: Literal["live", "local"] = "live"
    context_id: int | None = Field(default=None, ge=1)


@router.post("/app/entries")
def enter(payload: EntryInput, request: Request, background: BackgroundTasks, db: Session = Depends(raw_db)):
    session, context = session_for(db, request, mutate=True)
    with resource_locks(db, "session:"+session.id):
        db.refresh(session)
        target = db.get(ClubContext, payload.context_id or session.context_id)
        if target is None or target.owner_id != session.owner_id or target.game_version != "FC27":
            raise HTTPException(404, "Contexto no disponible")
        if payload.mode == "local" and target.verified:
            raise HTTPException(409, "El historial de un club vinculado no se convierte en inventario local editable")
        previous = db.scalar(select(AppEntry).where(AppEntry.session_id == session.id, AppEntry.nonce == payload.nonce))
        if previous:
            if previous.id != session.entry_id or previous.club_context_id != target.id or session.mode != payload.mode:
                raise HTTPException(409, "La entrada fue sustituida")
            return {**sync_state(db, target, previous), "mode": session.mode}
        old = db.get(AppEntry, session.entry_id) if session.entry_id else None
        if old and target.id == session.context_id and payload.mode == session.mode and payload.reason == "open" and now()-utc(old.checked_at) < timedelta(seconds=2):
            return {**sync_state(db, target, old), "mode": session.mode}
        context.generation += 1  # Late responses from the previous context cannot publish.
        session.context_id = target.id
        session.mode = payload.mode
        db.info["club_context_id"] = target.id
        entry = AppEntry(session_id=session.id, nonce=payload.nonce, reason=payload.reason, status="unavailable")
        db.add(entry)
        db.flush()
        session.entry_id = entry.id
        # No registered authorized adapter: an entry never certifies local cache as ready.
        record(db, "entry", "app_entry", entry.id, {"mode": payload.mode, "remote_checked": False})
        db.commit()
        from app.services.providers import authorized_adapter, begin_sync, execute_read
        if payload.mode == "live" and authorized_adapter(db, target)[0] is not None:
            try:
                run, adapter, created = begin_sync(db, session, target)
                if created: background.add_task(execute_read, run.id, adapter)
            except HTTPException as error:
                if error.status_code != 429: raise
                entry.status = "rate_limited"
                db.commit()
        return {**sync_state(db, target, entry), "mode": session.mode}


@router.get("/club-contexts")
def contexts(request: Request, db: Session = Depends(raw_db)):
    session, _ = session_for(db, request)
    return [{"id": row.id, "name": row.name, "verified": row.verified, "game_version": row.game_version, "platform": row.platform} for row in db.scalars(select(ClubContext).where(ClubContext.owner_id == session.owner_id, ClubContext.game_version == "FC27"))]


@router.get("/club-contexts/{context_id}/sync-state")
def state(context_id: int, request: Request, db: Session = Depends(raw_db)):
    session, context = session_for(db, request)
    if context.id != context_id:
        raise HTTPException(404, "Contexto no disponible")
    return {**sync_state(db, context, db.get(AppEntry, session.entry_id) if session.entry_id else None), "mode": session.mode}


@router.post("/connections/{provider}/authorize")
def authorize(provider: str, request: Request, db: Session = Depends(raw_db)):
    session_for(db, request, mutate=True)
    raise HTTPException(409, {"message": "Integración pendiente", "dependency": BLOCKER})


@router.get("/connections/{connection_id}/status")
def connection_status(connection_id: int, request: Request, db: Session = Depends(raw_db)):
    session_for(db, request)
    row = db.get(ProviderConnection, connection_id)
    if row is None:
        raise HTTPException(404, "Conexión no disponible")
    return {"id": row.id, "status": row.status, "capabilities": row.capabilities, "retry_after": row.retry_after}


@router.post("/club-contexts/{context_id}/sync-runs")
def start_sync(context_id: int, request: Request, background: BackgroundTasks, db: Session = Depends(raw_db)):
    session, context = session_for(db, request, mutate=True)
    if context.id != context_id or not session.entry_id:
        raise HTTPException(404, "Contexto o entrada no disponible")
    if request.headers.get("X-App-Entry") != str(session.entry_id):
        raise HTTPException(409, "La entrada fue sustituida")
    from app.services.providers import begin_sync, execute_read
    run, adapter, created = begin_sync(db, session, context)
    if created: background.add_task(execute_read, run.id, adapter)
    return {"id": run.id, "status": run.status, "created": created}


@router.post("/sync-runs/{run_id}/cancel")
def cancel_sync(run_id: int, request: Request, db: Session = Depends(raw_db)):
    session, context = session_for(db, request, mutate=True)
    with resource_locks(db, "sync-start:"+str(context.id)):
        row = db.get(SyncRun, run_id)
        if row is None or row.entry_id != session.entry_id or request.headers.get("X-App-Entry") != str(session.entry_id):
            raise HTTPException(404, "Lectura no disponible en esta entrada")
        if row.status == "syncing":
            row.status, row.finished_at = "cancelled", now()
            context.generation += 1
            db.get(AppEntry, row.entry_id).status = "sync_required"
            record(db, "cancel_read", "sync_run", row.id, {})
            db.commit()
        return {"id": row.id, "status": row.status}


@router.get("/sync-runs/{run_id}")
def sync_run(run_id: int, request: Request, db: Session = Depends(raw_db)):
    session_for(db, request)
    row = db.get(SyncRun, run_id)
    if row is None:
        raise HTTPException(404, "Lectura no disponible")
    return {"id": row.id, "status": row.status, "started_at": row.started_at, "finished_at": row.finished_at, "manifest": row.manifest, "error": row.error}


@router.post("/app/logout")
def logout(request: Request, response: Response, db: Session = Depends(raw_db)):
    session, context = session_for(db, request, mutate=True)
    with resource_locks(db, "session:"+session.id):
        context.generation += 1
        session.expires_at = now()
        session.entry_id = None
        # Entries retain a non-secret session hash for audit; see migration FK policy.
        db.commit()
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}
