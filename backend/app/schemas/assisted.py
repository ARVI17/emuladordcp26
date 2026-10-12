from datetime import datetime
from typing import Annotated, Literal
from pydantic import Field, field_validator, model_validator
from app.schemas.api import InputModel
from app.schemas.objective_planning import ObjectivePlanningInput

Id = Annotated[int, Field(strict=True, ge=1)]
Short = Annotated[str, Field(min_length=1, max_length=80)]
Position = Literal['POR','LD','DFC','LI','CAD','CAI','MCD','MC','MCO','MD','MI','ED','EI','SD','DC']


class AssistedContextInput(InputModel):
    name: str = Field(min_length=1, max_length=100)
    phrase: Literal['INICIAR LECTURA ASISTIDA']


class CaptureInput(InputModel):
    source: Literal['shared_tab', 'screenshot']


class ReviewedCard(InputModel):
    ordinal: int = Field(ge=0, le=29)
    name: str = Field(min_length=1, max_length=100)
    rating: int = Field(ge=40, le=99)
    position: Position
    card_type: str | None = Field(default=None, min_length=1, max_length=40)
    league: Short | None = None
    club: Short | None = None
    nationality: Short | None = None
    is_loan: bool | None = None
    is_evolution: bool | None = None
    tradable: bool | None = None
    rare: bool | None = None
    special: bool | None = None
    is_holographic: bool | None = None
    gallery_score: int | None = Field(default=None, ge=0, le=2_000_000_000)
    skill_moves: int | None = Field(default=None, ge=1, le=5)
    weak_foot: int | None = Field(default=None, ge=1, le=5)
    alternate_positions: list[Position] | None = Field(default=None, max_length=16)
    attributes: dict[Annotated[str, Field(min_length=1, max_length=40)], Annotated[int, Field(ge=0, le=99)]] | None = Field(default=None, max_length=40)
    location: Literal['club','unassigned','sbc_storage','transfer_list','squad','unknown'] = 'unknown'
    slot: str | None = Field(default=None, max_length=20)
    existing_player_id: Id | None = None


class VisualDcp(InputModel):
    name: str = Field(min_length=1, max_length=120)
    source_text: str = Field(min_length=1, max_length=5000)
    requirements: dict
    expires_at: datetime | None = None
    reviewed: Literal[True]
    @field_validator('requirements')
    @classmethod
    def rules(cls, value):
        from app.schemas.requirements import normalize_requirements
        return normalize_requirements(value)
    @field_validator('expires_at')
    @classmethod
    def date(cls, value):
        if value and value.tzinfo is None:
            raise ValueError('El vencimiento requiere zona horaria')
        return value


class ReadingReview(InputModel):
    phrase: Literal['GUARDAR OBSERVACION']
    edition: Literal['FC27']
    cards: list[ReviewedCard] = Field(default_factory=list, max_length=30)
    objective: ObjectivePlanningInput | None = None
    dcp: VisualDcp | None = None
    club_name: str | None = Field(default=None, min_length=1, max_length=100)
    coins: int | None = Field(default=None, ge=0, le=2_000_000_000)
    unassigned: dict[Literal['players','packs','consumables','other'], Annotated[int, Field(ge=0, le=100000)]] | None = None
    formation: str | None = Field(default=None, max_length=20)

    @model_validator(mode='after')
    def distinct(self):
        if len({c.ordinal for c in self.cards}) != len(self.cards):
            raise ValueError('No repitas una candidata de la lectura')
        return self


class CopyResolution(InputModel):
    player_ids: list[Id] = Field(min_length=2, max_length=30)
    decision: Literal['same_copy', 'distinct_copies']
    keep_player_id: Id | None = None
    note: str = Field(min_length=10, max_length=500)
    phrase: Literal['RESOLVER COPIAS']


class MainObservationInput(InputModel):
    reading_ids: list[Id] = Field(min_length=1, max_length=50)
    formation: str = Field(max_length=20)
    name: str = Field(default='Principal observada', min_length=1, max_length=100)
    expected_hash: str = Field(min_length=64, max_length=64)
    complete: bool
    phrase: Literal['REGISTRAR MI PRINCIPAL']
    @field_validator('formation')
    @classmethod
    def known_formation(cls, value):
        from app.services.squad_analysis import verified_formations
        if value not in verified_formations():
            raise ValueError('Formación pendiente de revisión FC27')
        return value


class GuidedProposalInput(InputModel):
    token: str = Field(min_length=20, max_length=20000)


class GuidedTransition(InputModel):
    action: Literal['review','approve','start','next','pause','cancel','declare','fail','check','reconcile']
    expected_hash: str = Field(min_length=64, max_length=64)
    phrase: str = Field(default='', max_length=80)
    reading_ids: list[Id] = Field(default_factory=list, max_length=50)
    note: str = Field(default='', max_length=500)
