import os
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "sqlite+pysqlite:///./test_fc26.db")
os.environ.setdefault("OLLAMA_URL", "http://127.0.0.1:1")

import pytest
from fastapi.testclient import TestClient
from app.db.base import Base
from app.db.seed import seed_database
from app.db.session import engine
from app.main import app

class FixtureClient(TestClient):
    def request(self, method, url, **kwargs):
        from catalog_fixture import prepare_payload
        if 'json' in kwargs:
            kwargs['json'] = prepare_payload(url, method, kwargs['json'])
        return super().request(method, url, **kwargs)


def pytest_configure(config):
    config.addinivalue_line('markers', 'catalog_boundary: real catalog validation without synthetic witnesses')


@pytest.fixture()
def client(request):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    seed_database()
    strict = bool(request.node.get_closest_marker('catalog_boundary'))
    if not strict:
        from sqlalchemy import event
        from sqlalchemy.orm import Session
        from catalog_fixture import activate_seed, witness_definitions
        activate_seed()
        event.listen(Session, 'before_flush', witness_definitions)
    from app.api.emulator import require_adb_permission
    # Existing bridge tests exercise mocked commands; production has no permission override.
    app.dependency_overrides[require_adb_permission] = lambda: None
    with (TestClient if strict else FixtureClient)(app) as test_client:
        response = test_client.post("/app/session")
        assert response.status_code == 200, response.text
        test_client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
        entry = test_client.post("/app/entries", json={"nonce": "fixture-local-entry", "mode": "local"})
        assert entry.status_code == 200, entry.text
        test_client.headers["X-App-Entry"] = str(entry.json()["entry_id"])
        yield test_client
    app.dependency_overrides.clear()
    if not strict:
        event.remove(Session, 'before_flush', witness_definitions)
