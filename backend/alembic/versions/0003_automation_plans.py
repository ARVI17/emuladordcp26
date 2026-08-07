"""Planes de automatización asistida ADB.

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "automation_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("plan_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("device_serial", sa.String(120), nullable=True),
        sa.Column("segment_id", sa.Integer(), sa.ForeignKey("segments.id"), nullable=True),
        sa.Column("player_ids", sa.JSON(), nullable=False),
        sa.Column("solution_snapshot", sa.JSON(), nullable=False),
        sa.Column("steps", sa.JSON(), nullable=False),
        sa.Column("progress_step", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_automation_plans_status", "automation_plans", ["status"])
    op.create_index("ix_automation_plans_segment_id", "automation_plans", ["segment_id"])

def downgrade() -> None:
    op.drop_index("ix_automation_plans_segment_id", table_name="automation_plans")
    op.drop_index("ix_automation_plans_status", table_name="automation_plans")
    op.drop_table("automation_plans")
