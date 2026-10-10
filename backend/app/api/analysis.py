from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.squad_analysis import analyze_club, formations_data

router = APIRouter(tags=["Análisis de club"])


class SquadRecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    formation: Literal["4-3-3", "4-4-2", "4-2-3-1", "4-1-2-1-2", "3-5-2"] = "4-3-3"
    style: Literal["balanced", "attacking", "defensive"] = "balanced"
    locked_player_ids: list[Annotated[int, Field(strict=True, ge=1)]] = Field(default_factory=list, max_length=11)
    excluded_player_ids: list[Annotated[int, Field(strict=True, ge=1)]] = Field(default_factory=list, max_length=5000)
    bench_size: int = Field(default=7, ge=0, le=12)
    include_loans: bool = True
    include_unreviewed: bool = False
    use_alternate_positions: bool = True

    @model_validator(mode="after")
    def consistent_ids(self):
        for values in (self.locked_player_ids, self.excluded_player_ids):
            if len(values) != len(set(values)):
                raise ValueError("Los IDs no pueden repetirse")
        if set(self.locked_player_ids) & set(self.excluded_player_ids):
            raise ValueError("Una carta no puede estar fijada y excluida")
        return self


@router.get("/squads/formations")
def available_formations():
    return formations_data()


@router.get("/club/analysis")
def club_analysis(db: Annotated[Session, Depends(get_db)]):
    return analyze_club(db)
