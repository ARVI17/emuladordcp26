"""Escaneo visual consentido y snapshots locales; no modifica inventario previo."""
from alembic import op
import sqlalchemy as sa

revision = '0021'
down_revision = '0020'
branch_labels = None
depends_on = None


def upgrade():
    # 0017 uses live ORM metadata on fresh installs; preserve that historical migration.
    if 'scan_data' not in {c['name'] for c in sa.inspect(op.get_bind()).get_columns('capture_sessions')}:
        op.add_column('capture_sessions', sa.Column('scan_data', sa.JSON(), nullable=False, server_default='{}'))
    with op.batch_alter_table('capture_sessions') as batch:
        batch.alter_column('scan_data', existing_type=sa.JSON(), server_default=None)
    op.create_table('visual_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('club_context_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('capture_sessions.id'), nullable=False, unique=True),
        sa.Column('previous_id', sa.Integer(), sa.ForeignKey('visual_snapshots.id')),
        sa.Column('before', sa.JSON(), nullable=False),
        sa.Column('after', sa.JSON(), nullable=False),
        sa.Column('changes', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_visual_snapshots_club_context_id', 'visual_snapshots', ['club_context_id'])


def downgrade():
    # Solo en bases de prueba: eliminaría historial nuevo. Preferir restaurar el respaldo.
    op.drop_table('visual_snapshots')
    op.drop_column('capture_sessions', 'scan_data')
