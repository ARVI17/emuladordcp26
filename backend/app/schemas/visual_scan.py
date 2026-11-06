from typing import Literal
from pydantic import Field, model_validator
from app.schemas.api import InputModel
from app.schemas.assisted import ReviewedCard

Section = Literal['club', 'squad', 'duplicates', 'tradable', 'untradeable']


class ScanStart(InputModel):
    consent: Literal[True]
    source: Literal['shared_tab', 'screenshot'] = 'shared_tab'
    section: Section = 'club'
    region: tuple[float, float, float, float] | None = None

    @model_validator(mode='after')
    def valid_region(self):
        if self.region:
            x, y, w, h = self.region
            if not (0 <= x < 100 and 0 <= y < 100 and 1 <= w <= 100-x and 1 <= h <= 100-y):
                raise ValueError('La región debe quedar dentro de la pantalla, en porcentajes')
        return self


class ScanTransition(InputModel):
    action: Literal['pause', 'resume', 'stop', 'cancel']


class ScanCard(ReviewedCard):
    candidate_key: str = Field(pattern=r'^[a-f0-9]{64}$')


class ScanCommit(InputModel):
    phrase: Literal['GUARDAR SINCRONIZACION']
    edition: Literal['FC27']
    cards: list[ScanCard] = Field(min_length=1, max_length=1000)

    @model_validator(mode='after')
    def unique(self):
        if len({c.candidate_key for c in self.cards}) != len(self.cards):
            raise ValueError('No repitas candidatas')
        ids = [c.existing_player_id for c in self.cards if c.existing_player_id]
        if len(ids) != len(set(ids)):
            raise ValueError('Una copia existente solo puede seleccionarse una vez')
        return self
