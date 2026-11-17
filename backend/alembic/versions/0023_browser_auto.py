"""Explicit local browser synchronization preference; no EA credentials."""
from alembic import op
import sqlalchemy as sa

revision = '0023'
down_revision = '0022'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('browser_auto_links',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('club_context_id', sa.Integer(), sa.ForeignKey('club_contexts.id'), nullable=False),
        sa.Column('extension_id', sa.String(32), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('protect_main', sa.Boolean(), nullable=False),
        sa.Column('club_fingerprint', sa.String(64)),
        sa.Column('request_id', sa.String(36)),
        sa.Column('grant_id', sa.String(36), sa.ForeignKey('reader_grants.id')),
        sa.Column('requested_at', sa.DateTime(timezone=True)),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('result', sa.JSON(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('club_context_id', name='uq_browser_auto_context'))
    op.create_index('ix_browser_auto_links_club_context_id', 'browser_auto_links', ['club_context_id'])


def downgrade():
    op.drop_index('ix_browser_auto_links_club_context_id', table_name='browser_auto_links')
    op.drop_table('browser_auto_links')
