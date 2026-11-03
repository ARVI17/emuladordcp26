"""Sesiones revisables de lectura del inventario Companion.

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "inventory_scans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("device_serial", sa.String(120), nullable=False),
        sa.Column("screen_size", sa.JSON(), nullable=False),
        sa.Column("captured_pages", sa.Integer(), nullable=False),
        sa.Column("capture_hashes", sa.JSON(), nullable=False),
        sa.Column("candidates", sa.JSON(), nullable=False),
        sa.Column("imported_player_ids", sa.JSON(), nullable=False),
        sa.Column("imported_count", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_inventory_scans_status", "inventory_scans", ["status"])

def downgrade() -> None:
    op.drop_index("ix_inventory_scans_status", table_name="inventory_scans")
    op.drop_table("inventory_scans")
