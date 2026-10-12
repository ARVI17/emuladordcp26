from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

def now(): return datetime.now(timezone.utc)

class ClubScoped:
    club_context_id: Mapped[int] = mapped_column(Integer, default=1, index=True)


class Profile(ClubScoped, Base):
    __tablename__ = "profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), default="Mi club")
    coins: Mapped[int] = mapped_column(Integer, default=250000)
    platform: Mapped[str] = mapped_column(String(30), default="Consola")
    max_budget: Mapped[int] = mapped_column(Integer, default=100000)
    risk_level: Mapped[str] = mapped_column(String(20), default="medio")
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    game_version: Mapped[str] = mapped_column(String(8), default="FC27")

class Player(ClubScoped, Base):
    __tablename__ = "players"
    id: Mapped[int] = mapped_column(primary_key=True)
    validation_status: Mapped[str] = mapped_column(String(30), default="pending_verification", server_default="pending_verification")
    catalog_variant_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    validation_evidence: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    game_version: Mapped[str] = mapped_column(String(8), default="FC27", index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    rating: Mapped[int] = mapped_column(Integer, index=True)
    position: Mapped[str] = mapped_column(String(8), index=True)
    league: Mapped[str] = mapped_column(String(80), index=True)
    club: Mapped[str] = mapped_column(String(80), index=True)
    nationality: Mapped[str] = mapped_column(String(80), index=True)
    card_type: Mapped[str] = mapped_column(String(40), default="Oro común")
    rare: Mapped[bool] = mapped_column(Boolean, default=False)
    special: Mapped[bool] = mapped_column(Boolean, default=False)
    tradable: Mapped[bool] = mapped_column(Boolean, default=False)
    price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chemistry: Mapped[int] = mapped_column(Integer, default=0)
    protected: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    starter: Mapped[bool] = mapped_column(Boolean, default=False)
    squad_role: Mapped[str] = mapped_column(String(20), default="club")
    usefulness: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_untradeable: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    card_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    base_card_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    alternate_positions: Mapped[list] = mapped_column(JSON, default=list)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    playstyles: Mapped[list] = mapped_column(JSON, default=list)
    playstyles_plus: Mapped[list] = mapped_column(JSON, default=list)
    roles: Mapped[dict] = mapped_column(JSON, default=dict)
    skill_moves: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weak_foot: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_loan: Mapped[bool] = mapped_column(Boolean, default=False)
    is_evolution: Mapped[bool] = mapped_column(Boolean, default=False)
    is_holographic: Mapped[bool] = mapped_column(Boolean, default=False)
    gallery_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data_source: Mapped[str] = mapped_column(String(80), default="manual")
    data_reviewed: Mapped[bool] = mapped_column(Boolean, default=True)
    unknown_fields: Mapped[list] = mapped_column(JSON, default=list)
    athlete_id: Mapped[str | None] = mapped_column(String(120))
    favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    availability: Mapped[str] = mapped_column(String(30), default="available")
    consumed_by_submission_id: Mapped[int | None] = mapped_column(
        ForeignKey("submissions.id", name="fk_player_consumption", use_alter=True), nullable=True, index=True
    )
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class Squad(ClubScoped, Base):
    __tablename__ = "squads"
    id: Mapped[int] = mapped_column(primary_key=True)
    game_version: Mapped[str] = mapped_column(String(8), default="FC27", index=True)
    name: Mapped[str] = mapped_column(String(100))
    formation: Mapped[str] = mapped_column(String(20), default="4-3-3")
    primary: Mapped[bool] = mapped_column(Boolean, default=False)
    protected: Mapped[bool] = mapped_column(Boolean, default=False)
    tactic: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    players: Mapped[list["SquadPlayer"]] = relationship(cascade="all, delete-orphan", back_populates="squad")

class SquadPlayer(ClubScoped, Base):
    __tablename__ = "squad_players"
    __table_args__ = (UniqueConstraint("squad_id", "slot", name="uq_squad_slot"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    squad_id: Mapped[int] = mapped_column(ForeignKey("squads.id", ondelete="CASCADE"), index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    slot: Mapped[str] = mapped_column(String(20))
    squad: Mapped[Squad] = relationship(back_populates="players")
    player: Mapped[Player] = relationship()

class Challenge(ClubScoped, Base):
    __tablename__ = "challenges"
    id: Mapped[int] = mapped_column(primary_key=True)
    game_version: Mapped[str] = mapped_column(String(8), default="FC27", index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    reward: Mapped[str] = mapped_column(String(120), default="")
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    segments: Mapped[list["Segment"]] = relationship(cascade="all, delete-orphan", back_populates="challenge")

class Segment(ClubScoped, Base):
    __tablename__ = "segments"
    id: Mapped[int] = mapped_column(primary_key=True)
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    requirements: Mapped[dict] = mapped_column(JSON, default=dict)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    challenge: Mapped[Challenge] = relationship(back_populates="segments")

class Submission(ClubScoped, Base):
    __tablename__ = "submissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    game_version: Mapped[str] = mapped_column(String(8), default="FC27")
    score_contribution: Mapped[int] = mapped_column(Integer, default=0)
    segment_id: Mapped[int] = mapped_column(ForeignKey("segments.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="confirmed")
    total_cost: Mapped[int | None] = mapped_column(Integer, nullable=True)
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Objective(ClubScoped, Base):
    __tablename__ = "objectives"
    id: Mapped[int] = mapped_column(primary_key=True)
    game_version: Mapped[str] = mapped_column(String(8), default="FC27", index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(40), default="Objetivo")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    target: Mapped[int] = mapped_column(Integer, default=1)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class AuditLog(ClubScoped, Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class AppSetting(Base):
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)

class ChatMessage(ClubScoped, Base):
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class AutomationPlan(ClubScoped, Base):
    __tablename__ = "automation_plans"
    id: Mapped[int] = mapped_column(primary_key=True)
    execution_generation: Mapped[int] = mapped_column(Integer, default=0)
    worker_active: Mapped[bool] = mapped_column(Boolean, default=False)
    name: Mapped[str] = mapped_column(String(160))
    plan_type: Mapped[str] = mapped_column(String(40), default="dcp_prepare")
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    device_serial: Mapped[str | None] = mapped_column(String(120), nullable=True)
    segment_id: Mapped[int | None] = mapped_column(ForeignKey("segments.id"), nullable=True, index=True)
    player_ids: Mapped[list] = mapped_column(JSON, default=list)
    solution_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    steps: Mapped[list] = mapped_column(JSON, default=list)
    progress_step: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class InventoryScan(ClubScoped, Base):
    __tablename__ = "inventory_scans"
    id: Mapped[int] = mapped_column(primary_key=True)
    game_version: Mapped[str] = mapped_column(String(8), default="FC27")
    candidate_count: Mapped[int] = mapped_column(Integer, default=0)
    next_candidate_id: Mapped[int] = mapped_column(Integer, default=1)
    source_scan_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_page_hash: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="scanning", index=True)
    device_serial: Mapped[str] = mapped_column(String(120))
    screen_size: Mapped[list] = mapped_column(JSON, default=list)
    captured_pages: Mapped[int] = mapped_column(Integer, default=0)
    capture_hashes: Mapped[list] = mapped_column(JSON, default=list)
    candidates: Mapped[list] = mapped_column(JSON, default=list)
    imported_player_ids: Mapped[list] = mapped_column(JSON, default=list)
    imported_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GalleryEntry(ClubScoped, Base):
    __tablename__ = "gallery_entries"
    __table_args__ = (UniqueConstraint("club_context_id", "game_version", "item_key", name="uq_gallery_edition_item"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    game_version: Mapped[str] = mapped_column(String(8), index=True)
    item_key: Mapped[str] = mapped_column(String(100))
    player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), nullable=True)
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class GallerySet(ClubScoped, Base):
    __tablename__ = "gallery_sets"
    __table_args__ = (UniqueConstraint("club_context_id", "game_version", "slug", name="uq_gallery_edition_slug"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    game_version: Mapped[str] = mapped_column(String(8), index=True)
    slug: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(40), default="Personalizado")
    rules: Mapped[dict] = mapped_column(JSON, default=dict)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    grade_thresholds: Mapped[dict] = mapped_column(JSON, default=dict)
    reward: Mapped[str] = mapped_column(String(500), default="")
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    rules_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class EvolutionDefinition(ClubScoped, Base):
    __tablename__ = "evolution_definitions"
    __table_args__ = (UniqueConstraint("club_context_id", "game_version", "slug", name="uq_evolution_edition_slug"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    game_version: Mapped[str] = mapped_column(String(8), index=True)
    slug: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    requirements: Mapped[dict] = mapped_column(JSON, default=dict)
    paths: Mapped[list] = mapped_column(JSON, default=list)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    rules_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

# Register all tables in the shared metadata (including Alembic and fixtures).
from app.models import planner  # noqa: E402,F401
from app.models import catalog  # noqa: E402,F401
