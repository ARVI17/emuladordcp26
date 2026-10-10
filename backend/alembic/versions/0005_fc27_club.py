"""FC27 editions, detailed cards, historical Gallery and safe execution metadata.

Legacy records remain FC26. No inventory is deleted or silently relabelled.
The initial migration uses live metadata; conditional additions also make a new
installation safe without rewriting any already applied revision.
Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def add_missing(table, columns):
    existing = {col["name"] for col in sa.inspect(op.get_bind()).get_columns(table)}
    for col in columns:
        if col.name not in existing:
            op.add_column(table, col)


def ensure_index(table, name, columns):
    if name not in {idx["name"] for idx in sa.inspect(op.get_bind()).get_indexes(table)}:
        op.create_index(name, table, columns)


def upgrade():
    for table in ("players", "squads", "challenges", "objectives", "submissions", "inventory_scans"):
        add_missing(table, [sa.Column("game_version", sa.String(8), nullable=False, server_default="FC26")])
        if table in ("players", "squads", "challenges", "objectives"):
            ensure_index(table, f"ix_{table}_game_version", ["game_version"])
    add_missing("profiles", [sa.Column("game_version", sa.String(8), nullable=False, server_default="FC27")])
    add_missing("players", [
        sa.Column("card_id", sa.String(80), nullable=True),
        sa.Column("base_card_id", sa.String(80), nullable=True),
        sa.Column("alternate_positions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("attributes", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("playstyles", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("playstyles_plus", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("roles", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("skill_moves", sa.Integer(), nullable=True),
        sa.Column("weak_foot", sa.Integer(), nullable=True),
        sa.Column("is_loan", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_evolution", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_holographic", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("gallery_score", sa.Integer(), nullable=True),
        sa.Column("data_source", sa.String(80), nullable=False, server_default="legacy"),
        sa.Column("data_reviewed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("consumed_by_submission_id", sa.Integer(), nullable=True),
    ])
    ensure_index("players", "ix_players_card_id", ["card_id"])
    ensure_index("players", "ix_players_consumed_by_submission_id", ["consumed_by_submission_id"])
    foreign_keys = sa.inspect(op.get_bind()).get_foreign_keys("players")
    if not any(fk.get("constrained_columns") == ["consumed_by_submission_id"] for fk in foreign_keys):
        with op.batch_alter_table("players") as batch:
            batch.create_foreign_key("fk_player_consumption", "submissions", ["consumed_by_submission_id"], ["id"])
    add_missing("submissions", [sa.Column("score_contribution", sa.Integer(), nullable=False, server_default="0")])
    add_missing("automation_plans", [
        sa.Column("execution_generation", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("worker_active", sa.Boolean(), nullable=False, server_default=sa.false()),
    ])
    # The previous process no longer exists after an upgrade; never resume taps.
    op.execute("UPDATE automation_plans SET status='cancelled', worker_active=false, last_error='Actualización FC 27: crea y revisa un plan nuevo' WHERE status IN ('prepared','queued','running')")
    add_missing("inventory_scans", [
        sa.Column("next_candidate_id", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source_scan_id", sa.Integer(), nullable=True),
        sa.Column("last_page_hash", sa.String(80), nullable=True),
    ])
    scans = sa.table("inventory_scans", sa.column("id", sa.Integer()), sa.column("candidates", sa.JSON()), sa.column("capture_hashes", sa.JSON()), sa.column("imported_count", sa.Integer()), sa.column("next_candidate_id", sa.Integer()), sa.column("last_page_hash", sa.String()))
    for scan in op.get_bind().execute(sa.select(scans.c.id, scans.c.candidates, scans.c.capture_hashes, scans.c.imported_count)):
        ids = [int(item.get("candidate_id", 0)) for item in (scan.candidates or [])]
        hashes = scan.capture_hashes or []
        next_id = max(max(ids, default=0) + 1, (scan.imported_count or 0) + len(ids) + 1)
        op.get_bind().execute(scans.update().where(scans.c.id == scan.id).values(next_candidate_id=next_id, last_page_hash=hashes[-1] if hashes else None))
    # Record consumption ownership from unambiguous legacy snapshots. Ambiguous
    # legacy submissions cannot silently restore cards owned by another record.
    submissions = sa.table("submissions", sa.column("id", sa.Integer()), sa.column("status", sa.String()), sa.column("snapshot", sa.JSON()))
    owners = {}
    for row in op.get_bind().execute(sa.select(submissions).where(submissions.c.status == "confirmed")):
        for player in (row.snapshot or {}).get("players", []):
            player_id = player.get("id")
            if player_id:
                owners.setdefault(int(player_id), []).append(row.id)
    players = sa.table("players", sa.column("id", sa.Integer()), sa.column("deleted", sa.Boolean()), sa.column("consumed_by_submission_id", sa.Integer()))
    for player_id, submission_ids in owners.items():
        if len(submission_ids) == 1:
            op.get_bind().execute(players.update().where(players.c.id == player_id, players.c.deleted.is_(True)).values(consumed_by_submission_id=submission_ids[0]))

    # Explicit table definitions keep this revision stable for future releases.
    op.create_table("gallery_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_version", sa.String(8), nullable=False),
        sa.Column("item_key", sa.String(100), nullable=False),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=True),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("game_version", "item_key", name="uq_gallery_edition_item"))
    op.create_index("ix_gallery_entries_game_version", "gallery_entries", ["game_version"])
    op.create_table("gallery_sets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_version", sa.String(8), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("rules", sa.JSON(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("grade_thresholds", sa.JSON(), nullable=False),
        sa.Column("reward", sa.String(500), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("rules_reviewed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("game_version", "slug", name="uq_gallery_edition_slug"))
    op.create_index("ix_gallery_sets_game_version", "gallery_sets", ["game_version"])
    op.create_table("evolution_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_version", sa.String(8), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("requirements", sa.JSON(), nullable=False),
        sa.Column("paths", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("rules_reviewed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("game_version", "slug", name="uq_evolution_edition_slug"))
    op.create_index("ix_evolution_definitions_game_version", "evolution_definitions", ["game_version"])


def downgrade():
    # Intentional guard: automatic downgrade would destroy recorded Gallery and
    # detailed card information. Restore a pre-upgrade backup if needed.
    raise RuntimeError("FC27 contiene datos nuevos; restaura una copia previa para volver a FC26")
