"""Local threshold alerts from manually reviewed quotes only."""
from alembic import op
import sqlalchemy as sa

revision = '0012'
down_revision = '0011'
branch_labels = None
depends_on = None


def upgrade():
    if 'market_alerts' not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table('market_alerts',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('club_context_id', sa.Integer(), nullable=False),
            sa.Column('game_version', sa.String(8), nullable=False),
            sa.Column('variant_id', sa.String(120), nullable=False),
            sa.Column('market', sa.String(40), nullable=False),
            sa.Column('kind', sa.String(30), nullable=False),
            sa.Column('direction', sa.String(10), nullable=False),
            sa.Column('threshold', sa.Integer(), nullable=False),
            sa.Column('enabled', sa.Boolean(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
        op.create_index('ix_market_alerts_club_context_id', 'market_alerts', ['club_context_id'])


def downgrade():
    raise RuntimeError('Restore a reviewed backup to preserve personal alert definitions')
