"""Paired read-only client, durable events and separate Gallery rule versions."""
from alembic import op
import sqlalchemy as sa

revision = '0018'
down_revision = '0017'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('reader_grants',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('club_context_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(64), sa.ForeignKey('local_sessions.id'), nullable=False),
        sa.Column('generation', sa.Integer(), nullable=False),
        sa.Column('extension_id', sa.String(32), nullable=False),
        sa.Column('code_hash', sa.String(64), nullable=False),
        sa.Column('token_hash', sa.String(64), unique=True),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_reader_grants_club_context_id', 'reader_grants', ['club_context_id'])
    op.create_table('reader_events',
        sa.Column('event_id', sa.String(36), primary_key=True),
        sa.Column('club_context_id', sa.Integer(), nullable=False),
        sa.Column('grant_id', sa.String(36), sa.ForeignKey('reader_grants.id'), nullable=False),
        sa.Column('stream_id', sa.String(36), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('payload_hash', sa.String(64), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('receipt', sa.JSON(), nullable=False),
        sa.Column('review_data', sa.JSON(), nullable=False),
        sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('grant_id', 'stream_id', 'sequence', name='uq_reader_sequence'))
    op.create_index('ix_reader_events_club_context_id', 'reader_events', ['club_context_id'])


def downgrade():
    raise RuntimeError('Restore a verified backup; preserve private observation receipts')
