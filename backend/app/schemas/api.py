from datetime import datetime
from typing import Annotated, Any, Literal
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

GameVersion = Literal["FC27"]
PlayerID = Annotated[StrictInt, Field(ge=1)]
ATTRIBUTE_KEYS = {"pace", "shooting", "passing", "dribbling", "defending", "physical", "diving", "handling", "kicking", "reflexes", "speed", "positioning"}
POSITION_ALIASES = {"GK":"POR", "RB":"LD", "CB":"DFC", "LB":"LI", "RWB":"CAD", "LWB":"CAI", "CDM":"MCD", "CM":"MC", "CAM":"MCO", "RM":"MD", "LM":"MI", "RW":"ED", "LW":"EI", "ST":"DC", "CF":"SD"}
POSITIONS = {"POR", "LD", "DFC", "LI", "CAD", "CAI", "MCD", "MC", "MCO", "MD", "MI", "ED", "EI", "DC", "SD"}

def normalize_position(value: str) -> str:
    value = POSITION_ALIASES.get(value.strip().upper(), value.strip().upper())
    if value not in POSITIONS:
        raise ValueError("Posición no reconocida; usa una posición de fútbol válida")
    return value

class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class PlayerBase(InputModel):
    game_version: GameVersion = "FC27"
    name: str = Field(min_length=1, max_length=100)
    rating: int = Field(ge=1, le=99)
    position: str = Field(min_length=1, max_length=8)
    league: str = Field(min_length=1, max_length=80)
    club: str = Field(min_length=1, max_length=80)
    nationality: str = Field(min_length=1, max_length=80)
    card_type: str = Field(default="Oro", min_length=1, max_length=40)
    rare: bool = False
    special: bool = False
    tradable: bool = False
    price: int | None = Field(default=None, ge=0, le=100_000_000)
    chemistry: int = Field(default=0, ge=0, le=3)
    protected: bool = False
    favorite: bool = False
    notes: str = Field(default="", max_length=2000)
    athlete_id: str | None = Field(default=None, min_length=1, max_length=120)
    starter: bool = False
    squad_role: str = Field(default="club", min_length=1, max_length=20)
    usefulness: int = Field(default=0, ge=0, le=100)
    duplicate_untradeable: bool = False
    card_id: str | None = Field(default=None, min_length=1, max_length=80)
    base_card_id: str | None = Field(default=None, min_length=1, max_length=80)
    alternate_positions: list[str] = Field(default_factory=list, max_length=15)
    attributes: dict[str, Annotated[int, Field(ge=1, le=99)]] = Field(default_factory=dict)
    playstyles: list[Annotated[str, Field(min_length=1, max_length=60)]] = Field(default_factory=list, max_length=30)
    playstyles_plus: list[Annotated[str, Field(min_length=1, max_length=60)]] = Field(default_factory=list, max_length=5)
    roles: dict[str, str] = Field(default_factory=dict)
    skill_moves: int | None = Field(default=None, ge=1, le=5)
    weak_foot: int | None = Field(default=None, ge=1, le=5)
    is_loan: bool = False
    is_evolution: bool = False
    is_holographic: bool = False
    gallery_score: int | None = Field(default=None, ge=0, le=1_000_000)
    data_source: str = Field(default="manual", min_length=1, max_length=80)
    data_reviewed: bool = True

    @field_validator("position")
    @classmethod
    def valid_position(cls, value): return normalize_position(value)

    @field_validator("alternate_positions")
    @classmethod
    def valid_positions(cls, values): return list(dict.fromkeys(normalize_position(value) for value in values))

    @field_validator("attributes")
    @classmethod
    def known_attributes(cls, values):
        if set(values) - ATTRIBUTE_KEYS:
            raise ValueError("Atributos desconocidos: " + ", ".join(sorted(set(values) - ATTRIBUTE_KEYS)))
        return values

    @field_validator("roles")
    @classmethod
    def valid_roles(cls, values):
        if len(values) > 40 or any(not key.strip() or len(key) > 80 or not value.strip() or len(value) > 40 for key, value in values.items()):
            raise ValueError("Roles inválidos: máximo 40, nombre de hasta 80 y familiaridad de hasta 40 caracteres")
        return {key.strip(): value.strip() for key, value in values.items()}

    @field_validator("playstyles", "playstyles_plus")
    @classmethod
    def distinct_styles(cls, values): return list(dict.fromkeys(values))

    @model_validator(mode="after")
    def edition_limits(self):
        if self.game_version == "FC27" and len(self.playstyles_plus) > 3:
            raise ValueError("FC 27 admite un máximo de tres PlayStyle+ por carta")
        return self

class PlayerCreate(PlayerBase): pass

class PartialInput(InputModel):
    @model_validator(mode="before")
    @classmethod
    def reject_explicit_nulls(cls, values):
        nullable = {"athlete_id", "price", "card_id", "base_card_id", "gallery_score", "skill_moves", "weak_foot"}
        if isinstance(values, dict):
            invalid = [key for key, value in values.items() if value is None and key not in nullable]
            if invalid:
                raise ValueError("Los campos no pueden ser nulos: " + ", ".join(invalid))
        return values

class PlayerUpdate(PartialInput):
    game_version: GameVersion | None = None
    name: str | None = Field(default=None, min_length=1, max_length=100)
    rating: int | None = Field(default=None, ge=1, le=99)
    position: str | None = Field(default=None, min_length=1, max_length=8)
    league: str | None = Field(default=None, min_length=1, max_length=80)
    club: str | None = Field(default=None, min_length=1, max_length=80)
    nationality: str | None = Field(default=None, min_length=1, max_length=80)
    card_type: str | None = Field(default=None, min_length=1, max_length=40)
    rare: bool | None = None
    special: bool | None = None
    tradable: bool | None = None
    price: int | None = Field(default=None, ge=0, le=100_000_000)
    chemistry: int | None = Field(default=None, ge=0, le=3)
    protected: bool | None = None
    favorite: bool | None = None
    notes: str | None = Field(default=None, max_length=2000)
    athlete_id: str | None = Field(default=None, min_length=1, max_length=120)
    starter: bool | None = None
    squad_role: str | None = Field(default=None, min_length=1, max_length=20)
    usefulness: int | None = Field(default=None, ge=0, le=100)
    duplicate_untradeable: bool | None = None
    card_id: str | None = Field(default=None, min_length=1, max_length=80)
    base_card_id: str | None = Field(default=None, min_length=1, max_length=80)
    alternate_positions: list[str] | None = Field(default=None, max_length=15)
    attributes: dict[str, Annotated[int, Field(ge=1, le=99)]] | None = None
    playstyles: list[Annotated[str, Field(min_length=1, max_length=60)]] | None = Field(default=None, max_length=30)
    playstyles_plus: list[Annotated[str, Field(min_length=1, max_length=60)]] | None = Field(default=None, max_length=5)
    roles: dict[str, str] | None = None
    skill_moves: int | None = Field(default=None, ge=1, le=5)
    weak_foot: int | None = Field(default=None, ge=1, le=5)
    is_loan: bool | None = None
    is_evolution: bool | None = None
    is_holographic: bool | None = None
    gallery_score: int | None = Field(default=None, ge=0, le=1_000_000)
    data_source: str | None = Field(default=None, min_length=1, max_length=80)
    data_reviewed: bool | None = None

class PlayerOut(PlayerBase, ORMModel):
    id: int
    deleted: bool
    created_at: datetime

class ProfileUpdate(PartialInput):
    game_version: GameVersion | None = None
    name: str | None = Field(default=None, min_length=1, max_length=80)
    coins: int | None = Field(default=None, ge=0, le=100_000_000)
    platform: str | None = Field(default=None, min_length=1, max_length=30)
    max_budget: int | None = Field(default=None, ge=0, le=100_000_000)
    risk_level: str | None = Field(default=None, pattern="^(bajo|medio|alto)$")
    preferences: dict[str, Any] | None = None

class TacticNotes(InputModel):
    style: str = Field(default="balanced", max_length=30)
    opponent: str = Field(default="", max_length=120)
    instructions: str = Field(default="", max_length=2000)
    practice_focus: str = Field(default="", max_length=500)
    reference_ids: list[Annotated[str, Field(pattern=r"^R(0[1-9]|[1-4][0-9]|50)$")]] = Field(default_factory=list, max_length=10)


class SquadBinding(InputModel):
    entry_id: int
    club_context_id: int
    revision: int
    snapshot_id: int | None
    game_version: GameVersion


class SquadCreate(InputModel):
    game_version: GameVersion = "FC27"
    name: str = Field(min_length=1, max_length=100)
    formation: str = Field(default="4-3-3", min_length=1, max_length=20)
    player_ids: list[PlayerID] = Field(default_factory=list, max_length=35)
    slots: list[str] | None = Field(default=None, max_length=35)
    tactic: TacticNotes = Field(default_factory=TacticNotes)
    expected_binding: SquadBinding | None = None

class SegmentCreate(InputModel):
    name: str = Field(min_length=1, max_length=120)
    requirements: dict[str, Any]

    @field_validator("requirements")
    @classmethod
    def valid_requirements(cls, value):
        from app.schemas.requirements import normalize_requirements
        return normalize_requirements(value)

class ChallengeCreate(InputModel):
    game_version: GameVersion = "FC27"
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=5000)
    reward: str = Field(default="", max_length=120)
    expires_at: datetime | None = None
    segments: list[SegmentCreate] = Field(default_factory=list, max_length=20)

class DcpFilters(InputModel):
    first_owner: bool | None = None
    is_holographic: bool | None = None
    is_loan: bool | None = None
    is_evolution: bool | None = None
    min_rating: int = Field(default=1, ge=1, le=99)
    max_rating: int = Field(default=99, ge=1, le=99)
    position: str | None = Field(default=None, max_length=8)
    league: str | None = Field(default=None, max_length=80)
    club: str | None = Field(default=None, max_length=80)
    nationality: str | None = Field(default=None, max_length=80)
    card_type: str | None = Field(default=None, max_length=40)
    tradable: bool | None = None
    duplicate: bool | None = None
    special: bool | None = None
    rare: bool | None = None
    max_price: int | None = Field(default=None, ge=0, le=100_000_000)
    location: Literal['club', 'sbc_storage', 'unassigned', 'transfer_list', 'local'] | None = None
    availability: Literal['available', 'all'] = 'available'
    preset: Literal['available', 'duplicates', 'keep_special', 'limit_value', 'keep_valuable_tradables'] = 'available'

    @field_validator('position')
    @classmethod
    def normalized_filter_position(cls, value):
        return normalize_position(value) if value else None

    @model_validator(mode='after')
    def ordered(self):
        if self.min_rating > self.max_rating:
            raise ValueError('La media mínima no puede superar la máxima.')
        if self.preset in {'limit_value', 'keep_valuable_tradables'} and self.max_price is None:
            raise ValueError('Indica el precio conocido máximo para este filtro.')
        return self


class OptimizeRequest(InputModel):
    locked_ids: list[PlayerID] = Field(default_factory=list, max_length=23)
    allow_protected_ids: list[PlayerID] = Field(default_factory=list, max_length=23)
    exclude_ids: list[PlayerID] = Field(default_factory=list, max_length=1000)
    max_solutions: int = Field(default=3, ge=1, le=5)
    filters: DcpFilters = Field(default_factory=DcpFilters)

    @model_validator(mode='after')
    def locked_not_excluded(self):
        if len(set(self.locked_ids)) != len(self.locked_ids) or set(self.locked_ids) & set(self.exclude_ids):
            raise ValueError('Revisa las copias fijadas: no se repiten ni pueden estar excluidas')
        return self

class ConfirmRequest(InputModel):
    player_ids: list[PlayerID] = Field(min_length=1, max_length=23)
    review_token: str | None = Field(default=None, max_length=8000)

    @field_validator("player_ids")
    @classmethod
    def unique_ids(cls, values):
        if len(set(values)) != len(values):
            raise ValueError("Cada copia del inventario debe tener un ID distinto")
        return values

class ObjectiveCreate(InputModel):
    game_version: GameVersion = "FC27"
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=5000)
    category: str = Field(default="Objetivo", min_length=1, max_length=40)
    progress: int = Field(default=0, ge=0, le=1_000_000)
    target: int = Field(default=1, ge=1, le=1_000_000)
    expires_at: datetime | None = None

class ObjectiveUpdate(PartialInput):
    progress: int | None = Field(default=None, ge=0, le=1_000_000)
    target: int | None = Field(default=None, ge=1, le=1_000_000)
    completed: bool | None = None

class ChatRequest(InputModel):
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
