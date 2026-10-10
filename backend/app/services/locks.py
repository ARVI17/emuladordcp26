"""Cooperative locks for operations that must remain atomic across commits.

PostgreSQL session advisory locks use a dedicated connection so a domain
transaction can commit without releasing its reservation. SQLite is used only
for local tests and uses process-local reentrant locks with the same API.
"""
from contextlib import contextmanager
import hashlib
import threading

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool


class ResourceBusy(RuntimeError):
    """Another operation owns the requested resource."""


_registry_guard = threading.Lock()
_sqlite_locks: dict[tuple[str, str], threading.RLock] = {}
_lock_engines = {}
_thread_state = threading.local()


def _number(key: str) -> int:
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big", signed=True)


@contextmanager
def resource_locks(db: Session, *keys: str, blocking: bool = True):
    """Reserve named resources, releasing them even when the operation fails.

    Callers acquire the reservation before loading mutable domain objects and
    re-read existing identity-map objects after acquiring it. Multi-resource
    operations pass every key together so acquisition order is deterministic.
    """
    bind = db.get_bind()
    engine = getattr(bind, "engine", bind)
    database = hashlib.sha256(str(engine.url).encode()).hexdigest()
    held = getattr(_thread_state, "held", None)
    if held is None:
        held = _thread_state.held = {}
    requested = [(database, key) for key in sorted(set(keys))]
    acquired = []
    connection = None
    try:
        for identity in requested:
            if identity in held:
                held[identity] += 1
                acquired.append((identity, None))
                continue
            key = identity[1]
            # Wait locally before taking any PostgreSQL connection. The lock
            # connection is outside the ORM pool, so a holder can still get the
            # connection needed to finish its domain transaction.
            with _registry_guard:
                lock = _sqlite_locks.setdefault(identity, threading.RLock())
            if not lock.acquire(blocking=blocking):
                raise ResourceBusy("Hay otra operación en curso; vuelve a intentarlo")
            if engine.dialect.name == "postgresql":
                if connection is None:
                    with _registry_guard:
                        lock_engine = _lock_engines.get(database)
                        if lock_engine is None:
                            lock_engine = create_engine(engine.url, poolclass=NullPool, isolation_level="AUTOCOMMIT")
                            _lock_engines[database] = lock_engine
                    try:
                        connection = lock_engine.connect()
                    except Exception:
                        lock.release()
                        raise
                try:
                    granted = connection.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": _number(key)}).scalar()
                except Exception:
                    lock.release()
                    raise
                if not granted:
                    lock.release()
                    raise ResourceBusy("Hay otra operación en curso; vuelve a intentarlo")
                handle = (connection, _number(key), lock)
            else:
                handle = lock
            held[identity] = 1
            acquired.append((identity, handle))
        yield
    finally:
        for identity, handle in reversed(acquired):
            held[identity] -= 1
            if held[identity]:
                continue
            del held[identity]
            if handle is not None:
                if engine.dialect.name == "postgresql":
                    conn, number, lock = handle
                    try:
                        conn.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": number})
                    except Exception:
                        # A broken connection must not be returned to the pool
                        # with a session-level lock still associated with it.
                        conn.invalidate()
                    finally:
                        lock.release()
                else:
                    handle.release()
        if connection is not None:
            connection.close()
