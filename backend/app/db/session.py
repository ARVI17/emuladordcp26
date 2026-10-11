from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine_options = {"pool_pre_ping": True, "connect_args": connect_args}
if not settings.database_url.startswith("sqlite"):
    engine_options.update(pool_size=settings.database_pool_size, max_overflow=settings.database_max_overflow)
engine = create_engine(settings.database_url, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

def get_db(request: Request):
    db = SessionLocal()
    try:
        from app.services.contexts import bind_request
        bind_request(db, request)
        yield db
    finally: db.close()


def raw_db():
    with SessionLocal() as db:
        yield db
