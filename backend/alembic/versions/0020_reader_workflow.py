"""Durable, context-bound local analysis and explicitly approved incremental review."""
from alembic import op
import sqlalchemy as sa

revision = '0020'
down_revision = '0019'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('reader_workflows',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('club_context_id', sa.Integer(), nullable=False),
        sa.Column('generation', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('requested_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('main_hash', sa.String(64), nullable=False),
        sa.Column('trusted_profiles', sa.JSON(), nullable=False),
        sa.Column('view_state', sa.JSON(), nullable=False),
        sa.Column('report', sa.JSON(), nullable=False),
        sa.UniqueConstraint('club_context_id', name='uq_reader_workflow_context'))
    op.create_index('ix_reader_workflows_club_context_id', 'reader_workflows', ['club_context_id'])


def downgrade():
    raise RuntimeError('Restore a verified backup; preserve private observations')
