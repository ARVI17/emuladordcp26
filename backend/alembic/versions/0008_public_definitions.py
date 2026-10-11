"""Versioned public definitions never contain club completion or ownership."""
from alembic import op
import sqlalchemy as sa
revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("public_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("game_version", sa.String(8), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("body", sa.JSON(), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("kind", "game_version", "slug", "revision", name="uq_public_definition_revision"))


def downgrade():
    raise RuntimeError("Restaura un respaldo para no perder definiciones históricas")
