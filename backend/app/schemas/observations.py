"""Version 2 keeps observations separate from ownership and provider verification."""
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID
from urllib.parse import urlsplit
from pydantic import Field, field_validator, model_validator
from app.schemas.api import InputModel
from app.schemas.reader import DomCard

Digest = Annotated[str, Field(pattern=r'^[a-f0-9]{64}$')]
Text = Annotated[str, Field(min_length=1, max_length=5000)]


class AccountObservation(InputModel):
    domain: Literal['account']
    club_name: str | None = Field(default=None, min_length=1, max_length=100)
    balance: int | None = Field(default=None, ge=0, le=2_000_000_000)
    evidence: dict[Literal['club_name','balance'], Annotated[str, Field(max_length=120)] | None] = Field(default_factory=dict)


class InventoryObservation(InputModel):
    domain: Literal['inventory', 'detail', 'squad']
    records: list[DomCard] = Field(min_length=1, max_length=30)

    @model_validator(mode='after')
    def ordinals(self):
        if len({r.ordinal for r in self.records}) != len(self.records):
            raise ValueError('Registros repetidos en el fragmento')
        if self.domain == 'detail' and len(self.records) != 1:
            raise ValueError('Una ficha describe una carta')
        if self.domain == 'squad' and any(not r.slot for r in self.records):
            raise ValueError('La plantilla requiere puestos observados')
        return self


class RequirementRecord(InputModel):
    title: str = Field(min_length=1, max_length=120)
    requirement_text: Text
    progress_current: int | None = Field(default=None, ge=0, le=2_000_000_000)
    progress_target: int | None = Field(default=None, ge=0, le=2_000_000_000)


class RequirementObservation(InputModel):
    domain: Literal['dcp', 'objective']
    records: list[RequirementRecord] = Field(min_length=1, max_length=30)
    # Text is retained in full; rule interpretation remains explicit review.
    rules_verified: Literal[False] = False


class GalleryRecord(InputModel):
    title: str = Field(min_length=1, max_length=120)
    progress_current: int | None = Field(default=None, ge=0, le=2_000_000_000)
    progress_target: int | None = Field(default=None, ge=0, le=2_000_000_000)


class GalleryObservation(InputModel):
    domain: Literal['gallery']
    records: list[GalleryRecord] = Field(min_length=1, max_length=30)


Payload = Annotated[AccountObservation | InventoryObservation | RequirementObservation | GalleryObservation,
                    Field(discriminator='domain')]


class ProfileEvidence(InputModel):
    profile_id: UUID
    revision: int = Field(ge=1, le=1_000_000)
    definition_hash: Digest
    structure_hash: Digest
    origin: str = Field(max_length=120)
    route: str = Field(max_length=160)
    language: str = Field(pattern=r'^(es|en)(-[a-zA-Z0-9]{2,8}){0,2}$')
    edition: Literal['FC27']
    omissions: dict[Annotated[str, Field(max_length=40)], Annotated[int, Field(ge=0, le=100000)]] = Field(default_factory=dict, max_length=12)


class ObservationScope(InputModel):
    page: str = Field(min_length=1, max_length=80)
    filters: str = Field(default='', max_length=240)
    location: Literal['club', 'squad', 'unassigned', 'sbc_storage', 'transfer_list', 'unknown']
    visible_count: int = Field(ge=1, le=300)
    virtualized: bool | None = None
    global_complete: Literal[False] = False


class ObservationFragment(InputModel):
    schema_version: Literal[2]
    reader_version: Literal['bounded-region-2']
    event_id: UUID
    observation_id: UUID
    context_binding: UUID
    stream_id: UUID
    sequence: int = Field(ge=1, le=2_000_000_000)
    document_ref: UUID
    observed_at: datetime
    source_updated_at: datetime | None = None
    source_kind: Literal['observed_page_dom', 'synthetic_dom', 'user_export_dom']
    profile: ProfileEvidence
    scope: ObservationScope
    fragment_index: int = Field(ge=0, le=9)
    fragment_count: int = Field(ge=1, le=10)
    manifest: list[Digest] = Field(min_length=1, max_length=10)
    payload: Payload
    payload_hash: Digest

    @field_validator('observed_at', 'source_updated_at')
    @classmethod
    def zoned(cls, value):
        if value and value.tzinfo is None:
            raise ValueError('La fecha requiere zona horaria')
        return value

    @model_validator(mode='after')
    def consistent(self):
        from re import fullmatch
        if len(self.manifest) != self.fragment_count or self.fragment_index >= self.fragment_count:
            raise ValueError('Manifiesto incompleto')
        p = self.profile
        if self.source_kind == 'observed_page_dom':
            if p.origin != 'https://www.ea.com' or not fullmatch(r'/(?:[a-z]{2}-[a-z]{2}/)?ea-sports-fc/ultimate-team/web-app/(?:#[/a-zA-Z0-9_-]{0,79})?', p.route):
                raise ValueError('Procedencia real incompatible')
        else:
            url = urlsplit(p.origin)
            if url.scheme != 'http' or url.hostname not in {'localhost', '127.0.0.1'} or url.username or url.password or url.path or url.query or url.fragment or p.route != '/reader-sample.html':
                raise ValueError('Las muestras y exportaciones conservan su origen local')
        if self.source_updated_at is not None:
            # This reader observes DOM only. It has no provider freshness evidence.
            raise ValueError('Este lector no acredita la fecha de actualización del proveedor')
        if self.payload.domain in {'account', 'detail'} and self.fragment_count != 1:
            raise ValueError('Esta vista requiere un solo fragmento')
        return self


class ObservationReview(InputModel):
    confirmation: Literal['REVISAR OBSERVACION DOM']
    context_confirmed: Literal[True]
