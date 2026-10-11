import os
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "sqlite+pysqlite:///./test_fc26.db")
os.environ.setdefault("OLLAMA_URL", "http://127.0.0.1:1")

import pytest
from fastapi.testclient import TestClient
from app.db.base import Base
from app.db.seed import seed_database
from app.db.session import engine
from app.main import app

@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    seed_database()
    from app.api.emulator import require_adb_permission
    # Existing bridge tests exercise mocked commands; production has no permission override.
    app.dependency_overrides[require_adb_permission] = lambda: None
    with TestClient(app) as test_client:
        response = test_client.post("/app/session")
        assert response.status_code == 200, response.text
        test_client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
        entry = test_client.post("/app/entries", json={"nonce": "fixture-local-entry", "mode": "local"})
        assert entry.status_code == 200, entry.text
        test_client.headers["X-App-Entry"] = str(entry.json()["entry_id"])
        yield test_client
    app.dependency_overrides.clear()
