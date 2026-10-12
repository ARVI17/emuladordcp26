"""Explicit personal squad selection, independent from EA's active squad."""
from sqlalchemy import ForeignKey, Integer, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.models.entities import ClubScoped


class MainSquadState(ClubScoped, Base):
    __tablename__ = 'main_squad_states'
    __table_args__ = (UniqueConstraint('club_context_id', name='uq_main_squad_context'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    squad_id: Mapped[int] = mapped_column(ForeignKey('squads.id'))
    revision: Mapped[int] = mapped_column(Integer, default=1)
    snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    locked_copy_ids: Mapped[list] = mapped_column(JSON, default=list)
    history: Mapped[list] = mapped_column(JSON, default=list)

