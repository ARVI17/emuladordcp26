"""Preserve omitted remote facts as unknown, never as false or zero."""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    if "unknown_fields" not in {c["name"] for c in sa.inspect(op.get_bind()).get_columns("players")}:
        op.add_column("players", sa.Column("unknown_fields", sa.JSON(), nullable=False, server_default="[]"))


def downgrade():
    raise RuntimeError("Restaura un respaldo para no perder la procedencia de los datos")
