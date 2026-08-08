from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

def now(): return datetime.now(timezone.utc)

class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), default="Mi club")
    coins: Mapped[int] = mapped_column(Integer, default=250000)
    platform: Mapped[str] = mapped_column(String(30), default="Consola")
    max_budget: Mapped[int] = mapped_column(Integer, default=100000)
    risk_level: Mapped[str] = mapped_column(String(20), default="medio")
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)

class Player(Base):
    __tablename__ = "players"
    id: Mapped[int] = mapped_column(primary_key=True)
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
    price: Mapped[int] = mapped_column(Integer, default=0)
    chemistry: Mapped[int] = mapped_column(Integer, default=0)
    protected: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    starter: Mapped[bool] = mapped_column(Boolean, default=False)
    squad_role: Mapped[str] = mapped_column(String(20), default="club")
    usefulness: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_untradeable: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

class Squad(Base):
    __tablename__ = "squads"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    formation: Mapped[str] = mapped_column(String(20), default="4-3-3")
    primary: Mapped[bool] = mapped_column(Boolean, default=False)
    protected: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    players: Mapped[list["SquadPlayer"]] = relationship(cascade="all, delete-orphan", back_populates="squad")

class SquadPlayer(Base):
    __tablename__ = "squad_players"
    __table_args__ = (UniqueConstraint("squad_id", "slot", name="uq_squad_slot"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    squad_id: Mapped[int] = mapped_column(ForeignKey("squads.id", ondelete="CASCADE"), index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    slot: Mapped[str] = mapped_column(String(20))
    squad: Mapped[Squad] = relationship(back_populates="players")
    player: Mapped[Player] = relationship()

class Challenge(Base):
    __tablename__ = "challenges"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    reward: Mapped[str] = mapped_column(String(120), default="")
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    segments: Mapped[list["Segment"]] = relationship(cascade="all, delete-orphan", back_populates="challenge")

class Segment(Base):
    __tablename__ = "segments"
    id: Mapped[int] = mapped_column(primary_key=True)
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    requirements: Mapped[dict] = mapped_column(JSON, default=dict)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    challenge: Mapped[Challenge] = relationship(back_populates="segments")

class Submission(Base):
    __tablename__ = "submissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    segment_id: Mapped[int] = mapped_column(ForeignKey("segments.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="confirmed")
    total_cost: Mapped[int] = mapped_column(Integer, default=0)
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Objective(Base):
    __tablename__ = "objectives"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(40), default="Objetivo")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    target: Mapped[int] = mapped_column(Integer, default=1)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class AuditLog(Base):
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

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class AutomationPlan(Base):
    __tablename__ = "automation_plans"
    id: Mapped[int] = mapped_column(primary_key=True)
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

class InventoryScan(Base):
    __tablename__ = "inventory_scans"
    id: Mapped[int] = mapped_column(primary_key=True)
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
