from datetime import datetime
from typing import Annotated, Literal
from pydantic import Field, model_validator
from app.schemas.api import InputModel

Id=Annotated[int,Field(strict=True,ge=1)]

class GalleryProgressInput(InputModel):
    attained_grade: str | None = Field(default=None,max_length=30)
    claimed_grade: str | None = Field(default=None,max_length=30)
    source: Literal['user_declared'] = 'user_declared'
    note: str = Field(min_length=5,max_length=300)
    confirmation: Literal['REGISTRAR GRADO DECLARADO']

class AcquisitionCandidate(InputModel):
    variant_id: str = Field(min_length=1,max_length=80)
    purchase_quote_id: Id
    resale_quote_id: Id | None = None
    keep: bool = True

class GalleryRouteInput(InputModel):
    set_ids: list[Id] = Field(min_length=1,max_length=8)
    mode: Literal['known_only','token_target','capital'] = 'known_only'
    target_tokens: int | None = Field(default=None,ge=1,le=1000000)
    market: Literal['Console','PC','Switch','Switch2'] = 'Console'
    candidates: list[AcquisitionCandidate] = Field(default_factory=list,max_length=10)
    available_coins: int = Field(default=0,ge=0,le=100000000)
    reserve_coins: int = Field(default=0,ge=0,le=100000000)
    maximum_capital: int = Field(default=0,ge=0,le=100000000)
    maximum_loss: int = Field(default=0,ge=0,le=100000000)
    fee_basis_points: int | None = Field(default=None,ge=0,le=10000)
    fee_source: str | None = Field(default=None,min_length=5,max_length=300)
    allow_scenarios: bool = False

    @model_validator(mode='after')
    def consistent(self):
        if len(set(self.set_ids))!=len(self.set_ids) or len({c.variant_id for c in self.candidates})!=len(self.candidates):
            raise ValueError('No repitas conjuntos ni adquisiciones')
        if self.mode=='known_only' and self.candidates:
            raise ValueError('Sin compras no admite una cesta de adquisiciones')
        if self.mode=='token_target' and self.target_tokens is None:
            raise ValueError('Indica las fichas adicionales buscadas')
        if any(not c.keep for c in self.candidates) and (self.fee_basis_points is None or not self.fee_source):
            raise ValueError('La reventa exige una comisión explícita y su procedencia')
        return self
