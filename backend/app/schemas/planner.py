from datetime import datetime
from typing import Literal
from pydantic import Field, model_validator
from app.schemas.api import InputModel


class ActionInput(InputModel):
    kind: Literal["keep", "sell", "buy", "dcp", "evolution", "unprotect", "gallery"]
    player_ids: list[int] = Field(default_factory=list, max_length=100)
    segment_id: int | None = Field(default=None, ge=1)
    quote_id: int | None = Field(default=None, ge=1)
    max_cost: int = Field(default=0, ge=0, le=100_000_000)
    definition_id: int | None = Field(default=None, ge=1)
    path_id: str | None = Field(default=None, max_length=100)
    note: str = Field(default="", max_length=300)
    accept_irreversible_partial: bool = False
    start_before: datetime | None = None
    complete_before: datetime | None = None

    @model_validator(mode="after")
    def distinct(self):
        for deadline in (self.start_before, self.complete_before):
            if deadline is not None and deadline.tzinfo is None:
                raise ValueError("Los plazos necesitan zona horaria")
        if self.start_before and self.complete_before and self.complete_before < self.start_before:
            raise ValueError("La fecha de completar no puede preceder al límite de inicio")
        if any(i < 1 for i in self.player_ids) or len(self.player_ids) != len(set(self.player_ids)):
            raise ValueError("Las copias deben ser distintas y tener identificadores positivos")
        if self.kind == "buy" and (self.player_ids or not self.quote_id):
            raise ValueError("La compra necesita una cotización, nunca una copia poseída")
        if self.kind != "buy" and not self.player_ids:
            raise ValueError("Selecciona las copias concretas")
        if self.kind == "dcp" and not self.segment_id:
            raise ValueError("Selecciona el segmento")
        if self.kind == "evolution" and (len(self.player_ids) != 1 or not self.definition_id or not self.path_id):
            raise ValueError("Selecciona carta, evolución y camino")
        return self


class PlanInput(InputModel):
    name: str = Field(min_length=1, max_length=120)
    actions: list[ActionInput] = Field(min_length=1, max_length=30)
    budget: int = Field(ge=0, le=100_000_000)
    reserve_coins: int = Field(default=0, ge=0, le=100_000_000)
    expires_minutes: int = Field(default=30, ge=1, le=120)


class PlanReview(InputModel):
    plan_hash: str = Field(pattern="^[0-9a-f]{64}$")
    confirmation: str = Field(max_length=100)


class ActionConfirmation(PlanReview):
    outcome: Literal["confirmed", "uncertain"] = "confirmed"
    actual_amount: int | None = Field(default=None, ge=0, le=100_000_000)
    evidence: str = Field(min_length=3, max_length=300)


class QuoteInput(InputModel):
    game_version: Literal["FC27", "FC26"] = "FC27"
    variant_id: str = Field(min_length=1, max_length=120)
    market: Literal["Console", "PC", "Switch", "Switch2"]
    currency: Literal["coins"] = "coins"
    amount: int = Field(ge=1, le=100_000_000)
    kind: Literal["listing", "bid", "observed_sale", "allowed_range"]
    source_url: str = Field(pattern=r"^https://", max_length=500)
    observed_at: datetime
    expires_at: datetime
    coverage: str = Field(min_length=3, max_length=300)


class TradeInput(InputModel):
    game_version: Literal["FC27", "FC26"] = "FC27"
    market: Literal["Console", "PC", "Switch", "Switch2"]
    receipt_key: str = Field(min_length=8, max_length=80)
    variant_id: str = Field(min_length=1, max_length=120)
    player_id: int | None = Field(default=None, ge=1)
    kind: Literal["bought", "listed", "sold"]
    amount: int = Field(ge=0, le=100_000_000)
    fees: int = Field(default=0, ge=0, le=100_000_000)
    occurred_at: datetime
    purchase_record_id: int | None = Field(default=None, ge=1)
    evidence: str = Field(min_length=3, max_length=300)
    confirmation: str = Field(max_length=100)


class MarketSimulation(InputModel):
    purchase: int = Field(ge=0, le=100_000_000)
    sale: int = Field(ge=0, le=100_000_000)
    adverse_sale: int = Field(ge=0, le=100_000_000)
    other_costs: int = Field(default=0, ge=0, le=100_000_000)
    tax_percent: float = Field(default=5, ge=0, lt=100)
    price_increment: int | None = Field(default=None, ge=1, le=100000)
