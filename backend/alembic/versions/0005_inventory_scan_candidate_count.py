"""Conteo liviano de candidatos para lecturas paginadas.

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "inventory_scans",
        sa.Column("candidate_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.execute(sa.text("UPDATE inventory_scans SET candidate_count = json_array_length(candidates)"))
    op.alter_column("inventory_scans", "candidate_count", server_default=None)


def downgrade() -> None:
    op.drop_column("inventory_scans", "candidate_count")
