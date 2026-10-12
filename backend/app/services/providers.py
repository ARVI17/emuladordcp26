"""Extension point for reviewed, app-authorized read adapters. Production registry is empty.

No URLs, scopes, credentials or EA protocol are inferred here. An adapter must bring
documented authorization, a bounded read implementation and integration tests.
"""
from concurrent.futures import ThreadPoolExecutor, TimeoutError as ReadTimeout
from dataclasses import dataclass
from datetime import timedelta
from threading import BoundedSemaphore
from time import monotonic
from typing import Protocol

from fastapi import HTTPException
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.entities import now
from app.models.planner import AppEntry, ClubContext, LocalSession, ProviderConnection, SyncRun
from app.services.audit import record
from app.services.contexts import utc
from app.services.locks import resource_locks
from app.services.sync import RemoteRead, publish_read


@dataclass(frozen=True)
class ClubIdentity:
    provider: str
    subject: str
    club_key: str
    platform: str
    game_version: str


class ReadAdapter(Protocol):
    provider: str
    approval_reference: str
    documentation_url: str
    required_permissions: frozenset[str]
    coverage: frozenset[str]
    timeout_seconds: float

    def read(self, identity: ClubIdentity, *, deadline: float) -> RemoteRead:
        """Read only, honor deadline/pagination, return origin time and stable revision."""
        ...


class ProviderRateLimited(Exception):
    def __init__(self, retry_seconds: int):
        self.retry_seconds = max(1, min(86400, retry_seconds))


ADAPTERS: dict[str, ReadAdapter] = {}  # No mock or unauthorized adapter in production.
_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix='club-read')
_slots = BoundedSemaphore(2)


def authorized_adapter(db, context):
    adapter = ADAPTERS.get(context.provider)
    connection = db.scalar(select(ProviderConnection).where(ProviderConnection.club_context_id == context.id, ProviderConnection.provider == context.provider))
    if not context.verified or not adapter or not connection:
        return None, connection
    if not adapter.approval_reference or not adapter.documentation_url.startswith('https://'):
        return None, connection
    if connection.status != 'connected' or not adapter.required_permissions.issubset(set(connection.permissions)):
        return None, connection
    # The current reconciler publishes only inventory and coins, not remote progress.
    if not adapter.coverage.issubset({'inventory', 'coins'}) or not 0 < adapter.timeout_seconds <= 30:
        return None, connection
    return adapter, connection


def begin_sync(db, session, context):
    adapter, connection = authorized_adapter(db, context)
    if connection and connection.retry_after and utc(connection.retry_after) > now():
        raise HTTPException(429, 'El proveedor requiere esperar', headers={'Retry-After': str(int((utc(connection.retry_after)-now()).total_seconds())+1)})
    if adapter is None:
        raise HTTPException(409, 'Integración pendiente: falta un adaptador autorizado y permisos documentados para esta aplicación')
    with resource_locks(db, 'sync-start:'+str(context.id)):
        db.refresh(context)
        db.refresh(session)
        entry = db.get(AppEntry, session.entry_id)
        if not entry or entry.club_context_id != context.id or utc(session.expires_at) <= now():
            raise HTTPException(409, 'La entrada cambió')
        existing = db.scalar(select(SyncRun).where(SyncRun.entry_id == entry.id, SyncRun.status == 'syncing', SyncRun.generation == context.generation))
        if existing:
            return existing, adapter, False
        context.generation += 1
        run = SyncRun(club_context_id=context.id, entry_id=entry.id, generation=context.generation)
        entry.status = 'syncing'
        db.add(run)
        db.flush()
        record(db, 'start_read', 'sync_run', run.id, {'provider': context.provider})
        db.commit()
        return run, adapter, True


def _failed(run_id, status, message, retry_seconds=None):
    with SessionLocal() as db:
        run = db.get(SyncRun, run_id)
        if run is None or run.status != 'syncing': return
        context = db.get(ClubContext, run.club_context_id)
        db.info['club_context_id'] = context.id
        entry = db.get(AppEntry, run.entry_id)
        session = db.get(LocalSession, entry.session_id)
        run.status, run.error, run.finished_at = status, message, now()
        current = session and session.entry_id == entry.id and session.context_id == context.id and context.generation == run.generation
        if current:
            entry.status = status
            connection = db.scalar(select(ProviderConnection).where(ProviderConnection.provider == context.provider))
            if connection and retry_seconds: connection.retry_after = now()+timedelta(seconds=retry_seconds)
            if connection and status == 'no_permissions': connection.status = 'no_permissions'
        record(db, 'read_failed', 'sync_run', run.id, {'status': status})
        db.commit()


def execute_read(run_id, adapter):
    """Fetch outside DB transactions; only this runner can publish a completed result."""
    try:
        with SessionLocal() as db:
            run = db.get(SyncRun, run_id)
            if not run or run.status != 'syncing': return
            context = db.get(ClubContext, run.club_context_id)
            db.info['club_context_id'] = context.id
            approved, _ = authorized_adapter(db, context)
            if approved is not adapter: raise PermissionError()
            identity = ClubIdentity(context.provider, context.subject, context.club_key, context.platform, context.game_version)
        if not _slots.acquire(blocking=False):
            raise ProviderRateLimited(10)
        try:
            future = _pool.submit(adapter.read, identity, deadline=monotonic()+adapter.timeout_seconds)
        except Exception:
            _slots.release()
            raise
        future.add_done_callback(lambda _: _slots.release())
        try: read = RemoteRead.model_validate(future.result(timeout=adapter.timeout_seconds))
        except ReadTimeout:
            future.cancel()
            raise
        if set(read.coverage) - adapter.coverage:
            raise ValueError('Unsupported coverage')
        with SessionLocal() as db:
            run = db.get(SyncRun, run_id)
            context = db.get(ClubContext, run.club_context_id)
            db.info['club_context_id'] = context.id
            if authorized_adapter(db, context)[0] is not adapter: raise PermissionError()
            publish_read(db, run_id, read)
    except ProviderRateLimited as error:
        _failed(run_id, 'rate_limited', 'El proveedor requiere esperar antes de otra lectura', error.retry_seconds)
    except PermissionError:
        _failed(run_id, 'no_permissions', 'No hay permiso vigente para esta lectura')
    except (ReadTimeout, OSError):
        _failed(run_id, 'offline', 'No se pudo completar la lectura; se conserva la instantánea anterior')
    except Exception:
        # Never persist provider exceptions: they may contain credentials or private bodies.
        _failed(run_id, 'error', 'La lectura no superó la validación; se conserva la instantánea anterior')


def recover_reads():
    with SessionLocal() as db:
        identifiers = list(db.scalars(select(SyncRun.id).where(SyncRun.status == 'syncing')))
    for identifier in identifiers:
        _failed(identifier, 'error', 'La aplicación se reinició durante la lectura; reintenta desde una entrada vigente')
