"""Validated local SBC requirements; no rule or score is inferred from EA data."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PlayerId = Annotated[int, Field(strict=True, ge=1)]
Count = Annotated[int, Field(strict=True, ge=0, le=23)]
Amount = Annotated[int, Field(strict=True, ge=0, le=2_000_000_000)]
POSITIONS = {"POR", "LD", "DFC", "LI", "CAD", "CAI", "MCD", "MC", "MCO", "MD", "MI", "ED", "EI", "SD", "DC"}


class CommonRequirements(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    required_player_ids: list[PlayerId] = Field(default_factory=list, max_length=23)
    excluded_player_ids: list[PlayerId] = Field(default_factory=list, max_length=5000)
    max_total_value: Amount | None = None

    @model_validator(mode="after")
    def ids_are_consistent(self):
        for values in (self.required_player_ids, self.excluded_player_ids):
            if len(values) != len(set(values)):
                raise ValueError("Los IDs de jugadores no pueden repetirse")
        if set(self.required_player_ids) & set(self.excluded_player_ids):
            raise ValueError("Un jugador no puede ser obligatorio y estar excluido")
        return self


class TraditionalRequirements(CommonRequirements):
    kind: Literal["traditional"] = "traditional"
    squad_size: Annotated[int, Field(strict=True, ge=1, le=23)] = 11
    min_rating: Annotated[int, Field(strict=True, ge=0, le=99)] = 0
    rating_strategy: Literal["floor_average", "round_half_up", "ceiling"] = "floor_average"
    min_chemistry: Annotated[int, Field(strict=True, ge=0, le=69)] = 0
    min_rare: Count = 0
    min_special: Count = 0
    min_leagues: Count | None = None
    max_leagues: Count | None = None
    min_clubs: Count | None = None
    max_clubs: Count | None = None
    min_nations: Count | None = None
    max_nations: Count | None = None
    required_league: str | None = Field(default=None, min_length=1, max_length=80)
    min_from_league: Annotated[int, Field(strict=True, ge=1, le=23)] = 1
    required_club: str | None = Field(default=None, min_length=1, max_length=80)
    min_from_club: Annotated[int, Field(strict=True, ge=1, le=23)] = 1
    required_nation: str | None = Field(default=None, min_length=1, max_length=80)
    min_from_nation: Annotated[int, Field(strict=True, ge=1, le=23)] = 1
    required_card_type: str | None = Field(default=None, min_length=1, max_length=40)
    min_card_type: Annotated[int, Field(strict=True, ge=1, le=23)] = 1
    required_positions: dict[str, Annotated[int, Field(strict=True, ge=1, le=23)]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def counts_fit_squad(self):
        if self.min_chemistry > self.squad_size * 3:
            raise ValueError("La química registrada no puede superar tres puntos por jugador")
        for field in ("min_rare", "min_special", "min_leagues", "min_clubs", "min_nations"):
            value = getattr(self, field)
            if value is not None and value > self.squad_size:
                raise ValueError(f"{field} excede el tamaño de plantilla")
        for group in ("leagues", "clubs", "nations"):
            minimum, maximum = getattr(self, f"min_{group}"), getattr(self, f"max_{group}")
            if minimum is not None and maximum is not None and minimum > maximum:
                raise ValueError(f"El mínimo de {group} supera el máximo")
        for value_key, count_key in (("required_league", "min_from_league"), ("required_club", "min_from_club"), ("required_nation", "min_from_nation"), ("required_card_type", "min_card_type")):
            if getattr(self, value_key) and getattr(self, count_key) > self.squad_size:
                raise ValueError(f"{count_key} excede el tamaño de plantilla")
            if count_key in self.model_fields_set and not getattr(self, value_key):
                raise ValueError(f"{count_key} requiere {value_key}")
        if any(position not in POSITIONS for position in self.required_positions):
            raise ValueError("Una posición requerida no está reconocida")
        if sum(self.required_positions.values()) > self.squad_size:
            raise ValueError("Las posiciones requeridas exceden el tamaño de plantilla")
        if len(self.required_player_ids) > self.squad_size:
            raise ValueError("Hay más jugadores obligatorios que plazas")
        return self


class ScoreRequirements(CommonRequirements):
    kind: Literal["score"] = "score"
    target_score: Annotated[int, Field(strict=True, ge=1, le=2_000_000_000)]
    min_item_rating: Annotated[int, Field(strict=True, ge=1, le=99)] = 1
    max_items_per_submission: Annotated[int, Field(strict=True, ge=1, le=23)] = 23

    @model_validator(mode="after")
    def required_items_fit_batch(self):
        if len(self.required_player_ids) > self.max_items_per_submission:
            raise ValueError("Hay más jugadores obligatorios que plazas por entrega")
        return self


def normalize_requirements(value: dict) -> dict:
    """Normalize once for both solving and confirmation, rejecting unknown rules.

    Progress is never accepted from a client. A legacy explicit zero may be
    omitted, but positive current_score must come from confirmed submissions.
    """
    if not isinstance(value, dict):
        raise ValueError("Los requisitos deben ser un objeto")
    cleaned = dict(value)
    if "current_score" in cleaned:
        if cleaned.pop("current_score") != 0:
            raise ValueError("El progreso se calcula a partir de las entregas confirmadas")
    kind = cleaned.get("kind", "traditional")
    if not isinstance(kind, str) or kind not in {"traditional", "score"}:
        raise ValueError("Tipo de DCP no reconocido")
    model = ScoreRequirements if kind == "score" else TraditionalRequirements
    # Excluding unset defaults preserves the legacy compact JSON contract, while
    # all supplied values still pass the full validated model.
    parsed = model.model_validate(cleaned)
    result = parsed.model_dump(exclude_unset=True, exclude_none=True)
    result["kind"] = parsed.kind
    return result
