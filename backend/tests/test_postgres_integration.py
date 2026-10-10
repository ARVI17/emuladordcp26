"""Runs in CI against an explicitly disposable PostgreSQL database."""
import multiprocessing
import os
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.services.locks import ResourceBusy, resource_locks


def _hold_committed_lease(db_url, resource, ready, release, errors):
    engine = create_engine(db_url)
    try:
        with Session(engine) as db:
            with resource_locks(db, resource, blocking=False):
                db.execute(text('SELECT 1'))
                db.commit()
                ready.set()
                if not release.wait(20): raise TimeoutError('Parent did not release test lease')
    except Exception as exc:
        errors.put(type(exc).__name__ + ': ' + str(exc))
        ready.set()
    finally:
        engine.dispose()


@pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL','').startswith('postgresql'), reason='Requires explicit disposable PostgreSQL TEST_DATABASE_URL')
@pytest.mark.parametrize('resource', ['inventory', 'device:ci-emulator'])
def test_advisory_lease_survives_commit_and_excludes_another_process(resource):
    db_url = os.environ['TEST_DATABASE_URL']
    context = multiprocessing.get_context('spawn')
    ready, release = context.Event(), context.Event()
    errors = context.Queue()
    process = context.Process(target=_hold_committed_lease, args=(db_url,resource,ready,release,errors))
    process.start()
    engine = create_engine(db_url)
    try:
        assert ready.wait(15), 'PostgreSQL test worker did not acquire its lease'
        assert errors.empty(), errors.get(timeout=1) if not errors.empty() else ''
        with Session(engine) as db:
            with pytest.raises(ResourceBusy):
                with resource_locks(db, resource, blocking=False):
                    pytest.fail('Another process acquired an already-held lease')
        release.set()
        process.join(15)
        assert process.exitcode == 0
        with Session(engine) as db:
            with resource_locks(db, resource, blocking=False):
                assert db.execute(text('SELECT 1')).scalar() == 1
    finally:
        release.set()
        process.join(3)
        if process.is_alive():
            process.terminate()
            process.join(3)
        engine.dispose()
