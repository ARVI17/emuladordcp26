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
    with TestClient(app) as test_client:
        yield test_client
