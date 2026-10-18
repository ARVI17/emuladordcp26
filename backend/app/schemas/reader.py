from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID
from pydantic import Field, field_validator, model_validator
from app.schemas.api import InputModel
from app.schemas.assisted import ReviewedCard


class PairingInput(InputModel):
    extension_id: str = Field(pattern=r'^[a-p]{32}$')
    confirmation: Literal['EMPAREJAR LECTOR']


class PairingClaim(InputModel):
    pairing_id: UUID
    code: str = Field(pattern=r'^\d{6}$')


class DomCard(ReviewedCard):
    # Visual row ordinals are evidence inside one observation, never copy IDs.
    first_owner: bool | None = None
    holographic_level: int | None = Field(default=None, ge=0, le=100)
    acquisition_origin: str | None = Field(default=None, max_length=80)
    variant_label: str | None = Field(default=None, max_length=80)
    evidence: dict[str, Annotated[str, Field(max_length=120)]] = Field(default_factory=dict, max_length=30)

    @model_validator(mode='after')
    def no_claimed_copy(self):
        if self.existing_player_id is not None:
            raise ValueError('La página no puede asignar identidades locales ni IDs de copia EA')
        return self


class Coverage(InputModel):
    page: str = Field(min_length=1, max_length=80)
    filters: str = Field(default='', max_length=240)
    location: Literal['club','squad','unassigned','sbc_storage','transfer_list','unknown'] = 'unknown'
    visible_count: int = Field(ge=0, le=30)
    loading: Literal[False] = False
    virtualized: bool | None = None
    terminal_observed: bool = False
    global_complete: Literal[False] = False


class ObservationBatch(InputModel):
    event_id: UUID
    schema_version: Literal[1] = 1
    reader_version: Literal['semantic-sample-1']
    context_binding: UUID
    stream_id: UUID
    sequence: int = Field(ge=1, le=2_000_000_000)
    document_ref: UUID
    view: Literal['inventory','detail','squad','result']
    scope: Coverage
    observed_at: datetime
    source_kind: Literal['synthetic_dom', 'user_export_dom']
    edition: Literal['FC27']
    records: list[DomCard] = Field(max_length=30)
    unknown_fields: list[Annotated[str, Field(max_length=80)]] = Field(default_factory=list, max_length=40)
    completeness_evidence: Literal['visible_subset'] = 'visible_subset'
    payload_hash: str = Field(pattern=r'^[a-f0-9]{64}$')

    @field_validator('observed_at')
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None:
            raise ValueError('La observación requiere zona horaria')
        return value

    @model_validator(mode='after')
    def consistent(self):
        if self.scope.visible_count != len(self.records) or len({c.ordinal for c in self.records}) != len(self.records):
            raise ValueError('Conteo o candidatas repetidas')
        return self


class EventReview(InputModel):
    confirmation: Literal['REVISAR LOTE DOM']
