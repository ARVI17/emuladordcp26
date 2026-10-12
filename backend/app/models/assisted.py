"""Private visual observations; no images, account credentials or EA copy IDs."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.models.entities import ClubScoped, now


class CaptureSession(ClubScoped, Base):
    __tablename__ = 'capture_sessions'
    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey('app_entries.id'))
    status: Mapped[str] = mapped_column(String(20), default='active')
    source: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class VisualReading(ClubScoped, Base):
    __tablename__ = 'visual_readings'
    __table_args__ = (UniqueConstraint('club_context_id', 'frame_hash', 'scope', 'page', name='uq_visual_frame'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey('capture_sessions.id'))
    frame_hash: Mapped[str] = mapped_column(String(64))
    scope: Mapped[str] = mapped_column(String(20))
    page: Mapped[str] = mapped_column(String(80))
    filters: Mapped[str] = mapped_column(String(240), default='')
    status: Mapped[str] = mapped_column(String(20), default='pending')
    original: Mapped[dict] = mapped_column(JSON, default=dict)
    reviewed: Mapped[dict] = mapped_column(JSON, default=dict)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class VisualCopy(ClubScoped, Base):
    __tablename__ = 'visual_copies'
    __table_args__ = (UniqueConstraint('reading_id', 'ordinal', name='uq_visual_candidate'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    reading_id: Mapped[int] = mapped_column(ForeignKey('visual_readings.id'))
    ordinal: Mapped[int] = mapped_column(Integer)
    player_id: Mapped[int] = mapped_column(ForeignKey('players.id'), index=True)
    identity_key: Mapped[str] = mapped_column(String(64), index=True)
    state: Mapped[str] = mapped_column(String(20), default='reviewed')
    facts: Mapped[dict] = mapped_column(JSON)
    resolution: Mapped[dict] = mapped_column(JSON, default=dict)
