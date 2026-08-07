"""Esquema inicial completo.

Revision ID: 0001
"""
from alembic import op
from app.db.base import Base
from app.models import entities  # noqa: F401

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

INITIAL_TABLES = ["profiles", "players", "squads", "squad_players", "challenges", "segments", "submissions", "objectives", "audit_logs", "app_settings"]

def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), tables=[Base.metadata.tables[name] for name in INITIAL_TABLES])

def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), tables=[Base.metadata.tables[name] for name in reversed(INITIAL_TABLES)])
