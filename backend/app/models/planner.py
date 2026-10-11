"""Local sessions, provider evidence, immutable inputs and durable resource claims."""
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.models.entities import now, ClubScoped


class LocalUser(Base):
    __tablename__ = "local_users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), default="Propietario local")


class ClubContext(Base):
    __tablename__ = "club_contexts"
    __table_args__ = (UniqueConstraint("owner_id", "provider", "subject", "club_key", "platform", "game_version", name="uq_provider_club"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("local_users.id"), default=1)
    name: Mapped[str] = mapped_column(String(100), default="Registro local sin vincular")
    provider: Mapped[str | None] = mapped_column(String(50))
    subject: Mapped[str | None] = mapped_column(String(120))
    club_key: Mapped[str | None] = mapped_column(String(120))
    platform: Mapped[str | None] = mapped_column(String(40))
    game_version: Mapped[str] = mapped_column(String(8), default="FC27")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    revision: Mapped[int] = mapped_column(Integer, default=0)
    snapshot_id: Mapped[int | None] = mapped_column(Integer)
    generation: Mapped[int] = mapped_column(Integer, default=0)
    coins: Mapped[int | None] = mapped_column(Integer)
    budget: Mapped[int | None] = mapped_column(Integer)
    reserve_coins: Mapped[int] = mapped_column(Integer, default=0)


class LocalSession(Base):
    __tablename__ = "local_sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("local_users.id"))
    context_id: Mapped[int] = mapped_column(ForeignKey("club_contexts.id"), default=1)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    entry_id: Mapped[int | None] = mapped_column(Integer)
    mode: Mapped[str] = mapped_column(String(20), default="live")


class AppEntry(ClubScoped, Base):
    __tablename__ = "app_entries"
    __table_args__ = (UniqueConstraint("session_id", "nonce", name="uq_entry_nonce"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("local_sessions.id"))
    nonce: Mapped[str] = mapped_column(String(80))
    reason: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default="sync_required")
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    snapshot_id: Mapped[int | None] = mapped_column(Integer)


class ProviderConnection(ClubScoped, Base):
    __tablename__ = "provider_connections"
    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30), default="unavailable")
    capabilities: Mapped[dict] = mapped_column(JSON, default=dict)
    permissions: Mapped[list] = mapped_column(JSON, default=list)
    retry_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SyncRun(ClubScoped, Base):
    __tablename__ = "sync_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("app_entries.id"))
    generation: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="syncing")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    manifest: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(String(300))


class InventorySnapshot(ClubScoped, Base):
    __tablename__ = "inventory_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("sync_runs.id"), unique=True)
    revision: Mapped[str] = mapped_column(String(120))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    coverage: Mapped[dict] = mapped_column(JSON)
    items: Mapped[list] = mapped_column(JSON)


class ExternalItemMapping(ClubScoped, Base):
    __tablename__ = "external_item_mappings"
    __table_args__ = (UniqueConstraint("club_context_id", "provider", "external_copy_id", name="uq_external_copy"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(50))
    external_copy_id: Mapped[str] = mapped_column(String(120))
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    location: Mapped[str] = mapped_column(String(40))
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    last_snapshot_id: Mapped[int] = mapped_column(ForeignKey("inventory_snapshots.id"))


class ClubPlan(ClubScoped, Base):
    __tablename__ = "club_plans"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(30), default="draft")
    entry_id: Mapped[int] = mapped_column(ForeignKey("app_entries.id"))
    snapshot_id: Mapped[int | None] = mapped_column(Integer)
    revision: Mapped[int] = mapped_column(Integer)
    plan_hash: Mapped[str] = mapped_column(String(64))
    inputs: Mapped[dict] = mapped_column(JSON)
    approval: Mapped[dict] = mapped_column(JSON, default=dict)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PlanAction(ClubScoped, Base):
    __tablename__ = "plan_actions"
    __table_args__ = (UniqueConstraint("plan_id", "ordinal", name="uq_plan_step"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("club_plans.id"))
    ordinal: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(30))
    player_ids: Mapped[list] = mapped_column(JSON)
    details: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    receipt: Mapped[dict] = mapped_column(JSON, default=dict)


class Reservation(ClubScoped, Base):
    __tablename__ = "reservations"
    # A deleted/released claim is removed; its history remains in the audit/plan.
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("club_plans.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MarketQuote(ClubScoped, Base):
    __tablename__ = "market_quotes"
    id: Mapped[int] = mapped_column(primary_key=True)
    game_version: Mapped[str] = mapped_column(String(8))
    variant_id: Mapped[str] = mapped_column(String(120))
    market: Mapped[str] = mapped_column(String(40))
    currency: Mapped[str] = mapped_column(String(20), default="coins")
    amount: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(30))
    source_url: Mapped[str] = mapped_column(String(500))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    coverage: Mapped[str] = mapped_column(String(300))


class TradeRecord(ClubScoped, Base):
    __tablename__ = "trade_records"
    __table_args__ = (UniqueConstraint("club_context_id", "receipt_key", name="uq_trade_receipt"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    game_version: Mapped[str] = mapped_column(String(8), default="FC27")
    market: Mapped[str] = mapped_column(String(40), default="unverified")
    receipt_key: Mapped[str] = mapped_column(String(80))
    variant_id: Mapped[str] = mapped_column(String(120))
    player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"))
    kind: Mapped[str] = mapped_column(String(20))
    amount: Mapped[int] = mapped_column(Integer)
    fees: Mapped[int] = mapped_column(Integer, default=0)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    purchase_record_id: Mapped[int | None] = mapped_column(ForeignKey("trade_records.id"))
    evidence: Mapped[str] = mapped_column(String(300))


class ClubProgress(ClubScoped, Base):
    __tablename__ = "club_progress"
    __table_args__ = (UniqueConstraint("club_context_id", "kind", "definition_key", name="uq_club_progress"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(30))
    definition_key: Mapped[str] = mapped_column(String(120))
    state: Mapped[dict] = mapped_column(JSON, default=dict)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class KnowledgeRevision(Base):
    __tablename__ = "knowledge_revisions"
    id: Mapped[int] = mapped_column(primary_key=True)
    reference_id: Mapped[str] = mapped_column(String(10), index=True)
    evidence: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PublicDefinition(Base):
    __tablename__ = "public_definitions"
    __table_args__ = (UniqueConstraint("kind", "game_version", "slug", "revision", name="uq_public_definition_revision"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(30))
    game_version: Mapped[str] = mapped_column(String(8))
    slug: Mapped[str] = mapped_column(String(100))
    revision: Mapped[int] = mapped_column(Integer)
    body: Mapped[dict] = mapped_column(JSON)
    source_url: Mapped[str] = mapped_column(String(500))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MatchRecord(ClubScoped, Base):
    __tablename__ = "match_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    game_version: Mapped[str] = mapped_column(String(12), default="unverified")
    practice_id: Mapped[int | None] = mapped_column(ForeignKey("practice_sessions.id"))
    played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    tactic: Mapped[str] = mapped_column(String(120))
    minutes: Mapped[int] = mapped_column(Integer)
    chances: Mapped[int] = mapped_column(Integer)
    dangerous_losses: Mapped[int] = mapped_column(Integer)
    conceded: Mapped[int] = mapped_column(Integer)
    change_tested: Mapped[str] = mapped_column(String(300))


class PracticeSession(ClubScoped, Base):
    __tablename__ = "practice_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    game_version: Mapped[str] = mapped_column(String(12))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    agenda: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="planned")
    result: Mapped[dict] = mapped_column(JSON, default=dict)
