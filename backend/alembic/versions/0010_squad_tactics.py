"""Private, reviewed squad tactics and opponent alternatives.

Revision ID: 0010
Revises: 0009
"""
from alembic import op
import sqlalchemy as sa

revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None


def upgrade():
    # Historical 0001 creates its initial tables from current metadata on a fresh DB.
    columns = {c['name']: c for c in sa.inspect(op.get_bind()).get_columns('squads')}
    if 'tactic' not in columns:
        op.add_column('squads', sa.Column('tactic', sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    elif not isinstance(columns['tactic']['type'], sa.JSON):
        raise RuntimeError('Unexpected existing tactic column; review schema before migration')


def downgrade():
    raise RuntimeError('Restore a reviewed backup; do not erase private tactical history')
