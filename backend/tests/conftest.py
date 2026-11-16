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
    config.addinivalue_line('markers', 'bundled_evidence: inspect the versioned source dates without test rebasing')


@pytest.fixture(scope='session')
def reviewed_public_fixture(tmp_path_factory):
    """Test-only source windows; real clock and all admission guards stay active.

    Public source freshness is checked separately with bundled_evidence. This
    keeps workflow tests deterministic after a release's documentary review ends.
    No production file or personal catalog is changed.
    """
    import json
    from datetime import datetime, timedelta, timezone
    from app.services.public_data import DATA_ROOT
    folder = tmp_path_factory.mktemp('public-evidence')
    start = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    for name in ('fc27_content.json', 'fc27_references.json', 'fc27_variants.json', 'fc27_formations.json'):
        data = json.loads((DATA_ROOT / name).read_text(encoding='utf-8'))
        def rebase(value):
            if isinstance(value, dict):
                for key in ('observed_at', 'verified_at'):
                    if key in value:
                        value[key] = start
                if 'valid_until' in value:
                    value['valid_until'] = end
                for key, child in value.items():
                    if key != 'review_history':
                        rebase(child)
            elif isinstance(value, list):
                for child in value:
                    rebase(child)
        rebase(data)
        (folder / name).write_text(json.dumps(data), encoding='utf-8')
    return folder


@pytest.fixture(autouse=True)
def public_evidence_window(request, monkeypatch, reviewed_public_fixture):
    if not request.node.get_closest_marker('bundled_evidence'):
        monkeypatch.setattr('app.services.public_data.DATA_ROOT', reviewed_public_fixture)


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
    from app.api.emulator import require_adb_permission, companion_fc27_compatible
    # Existing bridge tests exercise mocked commands; production has no permission override.
    if not strict:
        app.dependency_overrides[require_adb_permission] = lambda: None
        app.dependency_overrides[companion_fc27_compatible] = lambda: True
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
