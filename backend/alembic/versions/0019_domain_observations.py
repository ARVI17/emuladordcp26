"""Atomic, resumable domain observations without changing old receipts."""
from alembic import op
import sqlalchemy as sa

revision = '0019'
down_revision = '0018'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('reader_observations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('club_context_id', sa.Integer(), nullable=False),
        sa.Column('grant_id', sa.String(36), sa.ForeignKey('reader_grants.id'), nullable=False),
        sa.Column('domain', sa.String(20), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('fragments', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(24), nullable=False),
        sa.Column('review_data', sa.JSON(), nullable=False),
        sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_reader_observations_club_context_id', 'reader_observations', ['club_context_id'])


def downgrade():
    raise RuntimeError('Restore a verified backup; preserve private observations')
