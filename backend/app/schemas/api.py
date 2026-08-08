from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class PlayerBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    rating: int = Field(ge=1, le=99)
    position: str = Field(min_length=1, max_length=8)
    league: str = Field(min_length=1, max_length=80)
    club: str = Field(min_length=1, max_length=80)
    nationality: str = Field(min_length=1, max_length=80)
    card_type: str = Field(default="Oro común", max_length=40)
    rare: bool = False
    special: bool = False
    tradable: bool = False
    price: int = Field(default=0, ge=0, le=100_000_000)
    chemistry: int = Field(default=0, ge=0, le=3)
    protected: bool = False
    starter: bool = False
    squad_role: str = Field(default="club", max_length=20)
    usefulness: int = Field(default=0, ge=0, le=100)
    duplicate_untradeable: bool = False

    @field_validator("position", "league", "club", "nationality", "card_type", "squad_role")
    @classmethod
    def clean_text(cls, value: str): return value.strip()

class PlayerCreate(PlayerBase): pass
class PlayerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    rating: int | None = Field(default=None, ge=1, le=99)
    position: str | None = None
    league: str | None = None
    club: str | None = None
    nationality: str | None = None
    card_type: str | None = None
    rare: bool | None = None
    special: bool | None = None
    tradable: bool | None = None
    price: int | None = Field(default=None, ge=0)
    chemistry: int | None = Field(default=None, ge=0, le=3)
    protected: bool | None = None
    starter: bool | None = None
    squad_role: str | None = None
    usefulness: int | None = Field(default=None, ge=0, le=100)
    duplicate_untradeable: bool | None = None

class PlayerOut(PlayerBase, ORMModel):
    id: int
    deleted: bool
    created_at: datetime

class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    coins: int | None = Field(default=None, ge=0)
    platform: str | None = None
    max_budget: int | None = Field(default=None, ge=0)
    risk_level: str | None = None
    preferences: dict[str, Any] | None = None

class SquadCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    formation: str = "4-3-3"
    player_ids: list[int] = Field(default_factory=list, max_length=23)

class ChallengeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    reward: str = ""
    expires_at: datetime | None = None

class SegmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    requirements: dict[str, Any]

class OptimizeRequest(BaseModel):
    allow_protected_ids: list[int] = Field(default_factory=list)
    exclude_ids: list[int] = Field(default_factory=list)
    max_solutions: int = Field(default=3, ge=1, le=5)

class ConfirmRequest(BaseModel):
    player_ids: list[int] = Field(min_length=1, max_length=23)

class ObjectiveCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    category: str = "Objetivo"
    progress: int = Field(default=0, ge=0)
    target: int = Field(default=1, ge=1)
    expires_at: datetime | None = None

class ObjectiveUpdate(BaseModel):
    progress: int | None = Field(default=None, ge=0)
    target: int | None = Field(default=None, ge=1)
    completed: bool | None = None

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)

class EmulatorConnectRequest(BaseModel):
    address: str = Field(min_length=3, max_length=120, pattern=r"^[a-zA-Z0-9._-]+:[0-9]{2,5}$")

    @field_validator("address")
    @classmethod
    def valid_port(cls, value: str):
        if not 1 <= int(value.rsplit(":", 1)[1]) <= 65535:
            raise ValueError("El puerto ADB debe estar entre 1 y 65535")
        return value

class EmulatorPairRequest(EmulatorConnectRequest):
    pairing_code: str = Field(pattern=r"^[0-9]{6}$")

class EmulatorSelectRequest(BaseModel):
    serial: str = Field(min_length=1, max_length=120, pattern=r"^[a-zA-Z0-9._:-]+$")

class EmulatorTapRequest(BaseModel):
    x: int = Field(ge=0, le=10000)
    y: int = Field(ge=0, le=10000)

class EmulatorSwipeRequest(BaseModel):
    x1: int = Field(ge=0, le=10000)
    y1: int = Field(ge=0, le=10000)
    x2: int = Field(ge=0, le=10000)
    y2: int = Field(ge=0, le=10000)
    duration_ms: int = Field(default=350, ge=100, le=3000)

class EmulatorCalibration(BaseModel):
    screen_width: int = Field(ge=240, le=10000)
    screen_height: int = Field(ge=320, le=10000)
    open_search_x: int = Field(ge=0, le=10000)
    open_search_y: int = Field(ge=0, le=10000)
    search_field_x: int = Field(ge=0, le=10000)
    search_field_y: int = Field(ge=0, le=10000)
    first_result_x: int = Field(ge=0, le=10000)
    first_result_y: int = Field(ge=0, le=10000)
    add_player_x: int = Field(ge=0, le=10000)
    add_player_y: int = Field(ge=0, le=10000)
    wait_ms: int = Field(default=900, ge=250, le=5000)

    @model_validator(mode="after")
    def coordinates_fit_screen(self):
        if any(value > self.screen_width for value in (self.open_search_x, self.search_field_x, self.first_result_x, self.add_player_x)):
            raise ValueError("Una coordenada X excede el ancho")
        if any(value > self.screen_height for value in (self.open_search_y, self.search_field_y, self.first_result_y, self.add_player_y)):
            raise ValueError("Una coordenada Y excede el alto")
        return self

class AutomationPlanCreate(BaseModel):
    segment_id: int = Field(ge=1)
    player_ids: list[int] = Field(min_length=1, max_length=23)

class AutomationExecuteRequest(BaseModel):
    confirmation: str = Field(min_length=8, max_length=40)

class InventoryScanImportRequest(BaseModel):
    players: list[PlayerCreate] = Field(min_length=1, max_length=500)
    candidate_ids: list[int] = Field(min_length=1, max_length=500)
    confirmation: str = Field(min_length=8, max_length=80)
    archive_demo: bool = False

    @model_validator(mode="after")
    def candidate_ids_match_players(self):
        if len(self.candidate_ids) != len(self.players):
            raise ValueError("Cada jugador debe conservar su candidate_id")
        if len(set(self.candidate_ids)) != len(self.candidate_ids):
            raise ValueError("Los candidate_id no pueden repetirse")
        return self
