"""Preserve unverified definitions/profile balances outside active FC27 views."""
from alembic import op
import sqlalchemy as sa

revision = '0014'
down_revision = '0013'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    for table in ('challenges', 'objectives', 'gallery_sets', 'evolution_definitions', 'public_definitions'):
        columns = {c['name'] for c in sa.inspect(bind).get_columns(table)}
        if 'validation_status' not in columns:
            op.add_column(table, sa.Column('validation_status', sa.String(30), nullable=False, server_default='pending_verification'))
        if 'validation_evidence' not in columns:
            op.add_column(table, sa.Column('validation_evidence', sa.JSON(), nullable=False, server_default='{}'))
    for table in ('profiles', 'squads'):
        if 'origin' not in {c['name'] for c in sa.inspect(bind).get_columns(table)}:
            op.add_column(table, sa.Column('origin', sa.String(30), nullable=False, server_default='unverified'))


def downgrade():
    raise RuntimeError('Restore a tested backup with matching code; historical values must be preserved')
