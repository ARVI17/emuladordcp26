"""Private reviewed visual evidence, independent of provider authorization."""
from alembic import op
from app.models.assisted import CaptureSession, VisualReading, VisualCopy

revision = '0017'
down_revision = '0016'
branch_labels = None
depends_on = None


def upgrade():
    for model in (CaptureSession, VisualReading, VisualCopy):
        model.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    raise RuntimeError('Restore a verified backup; preserve private visual evidence')
