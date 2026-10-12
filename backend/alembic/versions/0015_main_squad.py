"""Persist explicit main-squad copy locks; never infer one from legacy flags."""
from alembic import op
import sqlalchemy as sa

revision = '0015'
down_revision = '0014'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('main_squad_states',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('club_context_id', sa.Integer(), nullable=False),
        sa.Column('squad_id', sa.Integer(), sa.ForeignKey('squads.id'), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('snapshot', sa.JSON(), nullable=False),
        sa.Column('locked_copy_ids', sa.JSON(), nullable=False),
        sa.Column('history', sa.JSON(), nullable=False),
        sa.UniqueConstraint('club_context_id', name='uq_main_squad_context'))
    op.create_index('ix_main_squad_states_club_context_id', 'main_squad_states', ['club_context_id'])


def downgrade():
    raise RuntimeError('Restore a verified backup with matching code; preserve structural protections')
