"""Public variant evidence is distinct from individual owned copies."""
from datetime import datetime
from sqlalchemy import CheckConstraint, DateTime, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class CardVariant(Base):
    __tablename__ = 'card_variants'
    __table_args__ = (
        UniqueConstraint('game_version', 'variant_id', name='uq_catalog_variant_edition'),
        CheckConstraint("game_version = 'FC27'", name='ck_catalog_fc27'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    game_version: Mapped[str] = mapped_column(String(8))
    variant_id: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(100))
    rating: Mapped[int] = mapped_column(Integer)
    position: Mapped[str] = mapped_column(String(8))
    card_type: Mapped[str] = mapped_column(String(40))
    source_url: Mapped[str] = mapped_column(String(500))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    validation_status: Mapped[str] = mapped_column(String(30), default='pending_verification')
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
