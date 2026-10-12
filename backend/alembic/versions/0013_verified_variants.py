"""Keep historical copies; new evidence never retroactively certifies them."""
from alembic import op
import sqlalchemy as sa

revision = '0013'
down_revision = '0012'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if 'card_variants' not in sa.inspect(bind).get_table_names():
        op.create_table('card_variants',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('game_version', sa.String(8), nullable=False),
            sa.Column('variant_id', sa.String(80), nullable=False),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('rating', sa.Integer(), nullable=False),
            sa.Column('position', sa.String(8), nullable=False),
            sa.Column('card_type', sa.String(40), nullable=False),
            sa.Column('source_url', sa.String(500), nullable=False),
            sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('valid_until', sa.DateTime(timezone=True), nullable=False),
            sa.Column('validation_status', sa.String(30), nullable=False),
            sa.Column('evidence', sa.JSON(), nullable=False),
            sa.UniqueConstraint('game_version', 'variant_id', name='uq_catalog_variant_edition'),
            sa.CheckConstraint("game_version = 'FC27'", name='ck_catalog_fc27'))
    existing = {c['name'] for c in sa.inspect(bind).get_columns('players')}
    for column in (
        sa.Column('validation_status', sa.String(30), nullable=False, server_default='pending_verification'),
        sa.Column('catalog_variant_id', sa.Integer(), nullable=True),
        sa.Column('validation_evidence', sa.JSON(), nullable=False, server_default='{}'),
    ):
        if column.name not in existing:
            op.add_column('players', column)


def downgrade():
    raise RuntimeError('Restore a tested backup; do not delete historical copies or source evidence')
