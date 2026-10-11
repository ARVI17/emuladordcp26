"""Preserve the edition and observed market of personal trade records.

Revision ID: 0009
Revises: 0008
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("trade_records", sa.Column("game_version", sa.String(8), nullable=False, server_default="FC27"))
    op.add_column("trade_records", sa.Column("market", sa.String(40), nullable=False, server_default="unverified"))


def downgrade():
    raise RuntimeError("Restore a reviewed backup; do not erase the provenance of historical trades")
