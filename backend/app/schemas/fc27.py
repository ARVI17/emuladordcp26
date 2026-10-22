"""User-reviewed FC27 definitions. Unknown game formulas stay unknown."""
from datetime import datetime
from typing import Annotated, Literal
from pydantic import Field, field_validator, model_validator
from app.schemas.api import ATTRIBUTE_KEYS, GameVersion, InputModel, PlayerID, normalize_position

Attribute = Annotated[int, Field(ge=1, le=99)]
Boost = Annotated[int, Field(ge=0, le=99)]
SourceURL = Annotated[str, Field(pattern=r"^https://[^\s]+$", max_length=500)]
ShortText = Annotated[str, Field(min_length=1, max_length=80)]

class GalleryRules(InputModel):
    schema_version: Literal[1, 2] = 1
    size: int = Field(default=11, ge=1, le=100)
    min_rating: int = Field(default=1, ge=1, le=99)
    league: ShortText | None = None
    club: ShortText | None = None
    nationality: ShortText | None = None
    card_type: Annotated[str, Field(min_length=1, max_length=40)] | None = None
    holographic_only: bool = False
    unique_players: bool = True
    multiplicity: Literal['athlete', 'variant', 'entry'] | None = None
    source_url: SourceURL | None = None
    observed_at: datetime | None = None
    evidence_status: Literal['legacy', 'scenario', 'documented'] = 'legacy'
    rewards: dict[str, Annotated[int, Field(ge=0, le=1000000)]] = Field(default_factory=dict, max_length=20)
    reward_mode: Literal['cumulative', 'incremental'] = 'cumulative'

    @model_validator(mode='after')
    def versioned(self):
        if self.schema_version == 2 and (self.multiplicity is None or self.evidence_status == 'legacy'):
            raise ValueError('La versión 2 exige multiplicidad y procedencia explícitas')
        if self.evidence_status == 'documented' and (not self.source_url or not self.observed_at):
            raise ValueError('Una regla documentada exige fuente y fecha')
        if self.observed_at and self.observed_at.tzinfo is None:
            raise ValueError('La fecha de la regla requiere zona horaria')
        return self

class GalleryTier(InputModel):
    minimum: int = Field(ge=1, le=100)
    percent_basis_points: int = Field(ge=0, le=1000000)

class GalleryTag(InputModel):
    name: str = Field(min_length=1, max_length=80)
    field: Literal["card_type", "special", "is_holographic", "league", "club", "nationality", "first_owner", "position", "weak_foot", "skill_moves", "athlete_id", "holographic_level"]
    value: str | bool | int | None = None
    minimum: int = Field(ge=1, le=100)
    bonus: int = Field(default=0, ge=0, le=1_000_000)
    mode: Literal['fixed_legacy', 'percentage'] = 'fixed_legacy'
    aggregation: Literal['matched', 'distinct', 'largest_group'] = 'matched'
    tiers: list[GalleryTier] = Field(default_factory=list, max_length=20)
    basis: Literal['matched_items'] = 'matched_items'
    rounding: Literal['floor_per_tag'] = 'floor_per_tag'
    stacking: Literal['additive'] = 'additive'

    @model_validator(mode="after")
    def valid_value(self):
        if self.mode == 'percentage':
            if not self.tiers or self.bonus or self.minimum != self.tiers[0].minimum:
                raise ValueError('El porcentaje requiere tramos y no usa puntos fijos')
            if [t.minimum for t in self.tiers] != sorted({t.minimum for t in self.tiers}):
                raise ValueError('Los tramos deben tener mínimos únicos crecientes')
            if self.aggregation != 'matched':
                if self.value is not None or self.field not in {'nationality','league','club','athlete_id'}:
                    raise ValueError('La agrupación exige un campo de identidad sin valor fijo')
                return self
        elif self.tiers or self.aggregation != 'matched':
            raise ValueError('Los puntos heredados no admiten tramos ni agrupaciones')
        if self.field in ("special", "is_holographic", "first_owner") and not isinstance(self.value, bool):
            raise ValueError("Las etiquetas de especial/holográfica requieren true o false")
        if self.field in ('weak_foot','skill_moves','holographic_level'):
            if type(self.value) != int or not 0 <= self.value <= 100:
                raise ValueError('El atributo requiere un entero válido')
            return self
        if self.field not in ("special", "is_holographic", "first_owner") and (not isinstance(self.value, str) or not self.value.strip() or len(self.value) > 80):
            raise ValueError("La etiqueta requiere un valor de texto de hasta 80 caracteres")
        return self

class GallerySetInput(InputModel):
    game_version: GameVersion = "FC27"
    slug: str | None = Field(default=None, min_length=1, max_length=100, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=5000)
    category: str = Field(default="Personalizado", min_length=1, max_length=40)
    rules: GalleryRules = Field(default_factory=GalleryRules)
    tags: list[GalleryTag] = Field(default_factory=list, max_length=30)
    grade_thresholds: dict[str, Annotated[int, Field(ge=0, le=1_000_000_000)]] = Field(default_factory=dict)
    reward: str = Field(default="", max_length=500)
    source_url: SourceURL | None = None
    rules_reviewed: bool = False

    @model_validator(mode="after")
    def grade_names(self):
        if len(self.grade_thresholds) > 20 or any(not key.strip() or len(key) > 30 for key in self.grade_thresholds):
            raise ValueError("Máximo 20 grados con nombres cortos")
        if any(tag.minimum > self.rules.size for tag in self.tags):
            raise ValueError("Una etiqueta exige más cartas que el tamaño del conjunto")
        if self.rules.schema_version == 1 and any(t.mode != 'fixed_legacy' for t in self.tags):
            raise ValueError('Los porcentajes requieren reglas versión 2')
        if len({t.name for t in self.tags}) != len(self.tags):
            raise ValueError('No repitas etiquetas')
        if self.rules.rewards and set(self.rules.rewards) != set(self.grade_thresholds):
            raise ValueError('Cada grado necesita su recompensa explícita')
        if self.rules.schema_version == 2:
            if len(set(self.grade_thresholds.values())) != len(self.grade_thresholds):
                raise ValueError('Los grados necesitan umbrales distintos')
            if self.rules.rewards and self.rules.reward_mode == 'cumulative':
                values = [self.rules.rewards[k] for k in sorted(self.grade_thresholds,key=self.grade_thresholds.get)]
                if values != sorted(values):
                    raise ValueError('Las recompensas acumuladas no pueden decrecer')
        return self

class GalleryScoreUpdate(InputModel):
    gallery_score: int | None = Field(ge=0, le=1_000_000)

class GalleryRecordRequest(InputModel):
    player_ids: list[PlayerID] | None = Field(default=None, max_length=1000)

class EvolutionRequirements(InputModel):
    min_rating: int = Field(default=1, ge=1, le=99)
    max_rating: int = Field(default=99, ge=1, le=99)
    positions: list[str] = Field(default_factory=list, max_length=15)
    max_attributes: dict[str, Attribute] = Field(default_factory=dict)
    max_playstyles: int | None = Field(default=None, ge=0, le=30)
    max_playstyles_plus: int | None = Field(default=None, ge=0, le=5)
    max_skill_moves: int | None = Field(default=None, ge=1, le=5)
    max_weak_foot: int | None = Field(default=None, ge=1, le=5)
    exclude_special: bool = False

    @field_validator("positions")
    @classmethod
    def valid_positions(cls, values): return list(dict.fromkeys(normalize_position(value) for value in values))

    @field_validator("max_attributes")
    @classmethod
    def known_attributes(cls, values):
        if set(values) - ATTRIBUTE_KEYS:
            raise ValueError("Atributos desconocidos")
        return values

    @model_validator(mode="after")
    def valid_rating_range(self):
        if self.min_rating > self.max_rating:
            raise ValueError("La media mínima supera la máxima")
        return self

class EvolutionUpgrades(InputModel):
    rating: Boost = 0
    rating_cap: int = Field(default=99, ge=1, le=99)
    attributes: dict[str, Boost] = Field(default_factory=dict)
    attribute_caps: dict[str, Attribute] = Field(default_factory=dict)
    alternate_positions: list[str] = Field(default_factory=list, max_length=15)
    playstyles: list[Annotated[str, Field(min_length=1, max_length=60)]] = Field(default_factory=list, max_length=30)
    playstyles_plus: list[Annotated[str, Field(min_length=1, max_length=60)]] = Field(default_factory=list, max_length=5)
    roles: dict[str, str] = Field(default_factory=dict)
    skill_moves: int = Field(default=0, ge=0, le=4)
    weak_foot: int = Field(default=0, ge=0, le=4)
    skill_moves_cap: int = Field(default=5, ge=1, le=5)
    weak_foot_cap: int = Field(default=5, ge=1, le=5)

    @field_validator("alternate_positions")
    @classmethod
    def valid_positions(cls, values): return list(dict.fromkeys(normalize_position(value) for value in values))

    @field_validator("attributes", "attribute_caps")
    @classmethod
    def known_attributes(cls, values):
        if set(values) - ATTRIBUTE_KEYS: raise ValueError("Atributos desconocidos")
        return values

    @field_validator("roles")
    @classmethod
    def valid_roles(cls, values):
        if len(values) > 40 or any(not k.strip() or len(k) > 80 or not v.strip() or len(v) > 40 for k,v in values.items()):
            raise ValueError("Roles inválidos")
        return values

class EvolutionPath(InputModel):
    id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    upgrades: EvolutionUpgrades

class EvolutionInput(InputModel):
    game_version: GameVersion = "FC27"
    slug: str | None = Field(default=None, min_length=1, max_length=100, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=5000)
    requirements: EvolutionRequirements
    paths: list[EvolutionPath] = Field(min_length=1, max_length=8)
    expires_at: datetime | None = None
    source_url: SourceURL | None = None
    rules_reviewed: bool = False

    @field_validator("paths")
    @classmethod
    def unique_paths(cls, values):
        if len({path.id for path in values}) != len(values):
            raise ValueError("Cada camino debe tener un ID distinto")
        return values

class EvolutionStep(InputModel):
    evolution_id: PlayerID
    path_id: str = Field(min_length=1, max_length=80)

class EvolutionPreview(InputModel):
    player_id: PlayerID
    steps: list[EvolutionStep] = Field(min_length=1, max_length=5)

    @field_validator("steps")
    @classmethod
    def no_repeat_evo(cls, values):
        if len({step.evolution_id for step in values}) != len(values):
            raise ValueError("Una evolución no se puede aplicar dos veces en la misma cadena")
        return values

class ContentManifest(InputModel):
    schema_version: Literal[1] = 1
    game_version: GameVersion
    published_at: datetime
    source_url: SourceURL | None = None
    sets: list[GallerySetInput] = Field(default_factory=list, max_length=100)
    evolutions: list[EvolutionInput] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def single_edition(self):
        for item in [*self.sets, *self.evolutions]:
            if "game_version" not in item.model_fields_set:
                item.game_version = self.game_version
            if item.game_version != self.game_version:
                raise ValueError("Todos los elementos deben pertenecer a la edición del paquete")
        return self

class ContentImportRequest(InputModel):
    manifest: ContentManifest
    confirm: bool = False
    preview_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
