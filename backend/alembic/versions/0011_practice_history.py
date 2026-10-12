"""Edition-separated practice and match evidence; never guess historical edition."""
from alembic import op
import sqlalchemy as sa

revision = '0011'
down_revision = '0010'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if 'practice_sessions' not in sa.inspect(bind).get_table_names():
        op.create_table('practice_sessions',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('club_context_id', sa.Integer(), nullable=False),
            sa.Column('game_version', sa.String(12), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('agenda', sa.JSON(), nullable=False),
            sa.Column('status', sa.String(20), nullable=False),
            sa.Column('result', sa.JSON(), nullable=False))
        op.create_index('ix_practice_sessions_club_context_id', 'practice_sessions', ['club_context_id'])
    columns = {c['name'] for c in sa.inspect(bind).get_columns('match_records')}
    with op.batch_alter_table('match_records') as batch:
        if 'game_version' not in columns:
            batch.add_column(sa.Column('game_version', sa.String(12), nullable=False, server_default='unverified'))
        if 'practice_id' not in columns:
            batch.add_column(sa.Column('practice_id', sa.Integer(), nullable=True))
            batch.create_foreign_key('fk_match_practice', 'practice_sessions', ['practice_id'], ['id'])
    # Only an already verified, edition-bound context can establish old match edition.
    op.execute(sa.text("UPDATE match_records SET game_version = (SELECT game_version FROM club_contexts WHERE club_contexts.id = match_records.club_context_id) WHERE game_version = 'unverified' AND club_context_id IN (SELECT id FROM club_contexts WHERE verified = true AND game_version IN ('FC26','FC27'))"))


def downgrade():
    raise RuntimeError('Restore a reviewed backup; practice and match history must be preserved')
