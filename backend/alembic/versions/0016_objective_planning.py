"""Auxiliary objective rules and explicitly sourced progress, preserving history."""
from alembic import op
import sqlalchemy as sa

revision = '0016'
down_revision = '0015'
branch_labels = None
depends_on = None


def upgrade():
    # Revision 0001 uses current metadata for a brand-new database. Existing
    # installations still need these columns; neither path rewrites progress.
    existing = {column['name'] for column in sa.inspect(op.get_bind()).get_columns('objectives')}
    for column in (
        sa.Column('planning_rules', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('planning_revision', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('planning_history', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('progress_evidence', sa.JSON(), nullable=False, server_default='{}'),
    ):
        if column.name not in existing:
            op.add_column('objectives', column)
    if 'objective_context' not in {column['name'] for column in sa.inspect(op.get_bind()).get_columns('squads')}:
        op.add_column('squads', sa.Column('objective_context', sa.JSON(), nullable=False, server_default='{}'))


def downgrade():
    raise RuntimeError('Restore a verified backup with matching code; preserve objective rules and progress evidence')
