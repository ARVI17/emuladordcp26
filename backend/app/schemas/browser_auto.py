from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import Field, field_validator, model_validator
from app.schemas.api import InputModel
from app.schemas.assisted import ReviewedCard


class AutoEnable(InputModel):
    extension_id: str = Field(pattern=r'^[a-p]{32}$')
    enabled: bool
    protect_main: Literal[True] = True
    confirmation: Literal['ACTIVAR LECTURA LOCAL AUTOMATICA']


class AutoCard(ReviewedCard):
    ordinal: int = Field(ge=0, le=999)
    existing_player_id: None = None


class AutoSnapshot(InputModel):
    request_id: UUID
    reader_version: Literal['ea-visible-1', 'ea-visible-2']
    edition: Literal['FC27']
    # Selected by the owner; never advertised as verified provider identity.
    edition_basis: Literal['owner_selected']
    club_fingerprint: str = Field(pattern=r'^[a-f0-9]{64}$')
    club_name: str = Field(min_length=1, max_length=100)
    observed_at: datetime
    inventory: list[AutoCard] = Field(max_length=1000)
    squad: list[AutoCard] = Field(max_length=30)
    formation: str | None = Field(default=None, max_length=20)
    active_squad_observed: bool
    inventory_complete: Literal[False] = False
    pages_read: int = Field(default=1, ge=1, le=50)
    traversal_end: Literal['legacy', 'end', 'limit', 'unknown'] = 'legacy'

    @field_validator('observed_at')
    @classmethod
    def zoned(cls, value):
        if value.tzinfo is None:
            raise ValueError('La observación requiere zona horaria')
        return value

    @model_validator(mode='after')
    def coherent(self):
        if self.reader_version == 'ea-visible-1' and (len(self.inventory) > 20 or self.pages_read != 1 or self.traversal_end != 'legacy'):
            raise ValueError('El lector anterior solo admite veinte filas')
        if self.reader_version == 'ea-visible-2' and (self.traversal_end == 'legacy' or len(self.inventory) > self.pages_read * 30):
            raise ValueError('Cobertura incoherente')
        for rows in (self.inventory, self.squad):
            if len({c.ordinal for c in rows}) != len(rows):
                raise ValueError('Filas repetidas')
        if any(c.location != 'club' or c.slot is not None for c in self.inventory):
            raise ValueError('Ubicación de inventario incorrecta')
        if self.squad and (not self.active_squad_observed or not self.formation or
                           any(c.location != 'squad' or not c.slot for c in self.squad)):
            raise ValueError('Faltan puestos de la plantilla activa')
        if len({c.slot for c in self.squad}) != len(self.squad):
            raise ValueError('Puestos repetidos')
        return self


class AutoFailure(InputModel):
    request_id: UUID
    reason: Literal['login_required', 'permission_required', 'page_changed', 'cancelled', 'reader_unavailable', 'timeout']


class AutoProgress(InputModel):
    request_id: UUID
    pages_read: int = Field(ge=0, le=50)
    cards_read: int = Field(ge=0, le=1000)
    phase: Literal['squad', 'inventory', 'publishing']
