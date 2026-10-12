"""Reviewed auxiliary rules never certify an active EA objective."""
from datetime import datetime
from typing import Annotated, Literal
from pydantic import Field, StrictBool, StrictInt, StrictStr, model_validator
from app.schemas.api import InputModel
from app.models.entities import now

Identifier = Annotated[str, Field(min_length=1, max_length=80)]
Difficulty = Literal['unknown', 'not_required', 'beginner', 'amateur', 'semi_pro', 'professional', 'world_class', 'legendary', 'ultimate']


class CompositionCondition(InputModel):
    id: Identifier
    source_text: str = Field(min_length=1, max_length=1000)
    field: Literal['league', 'club', 'nationality', 'card_type', 'rating', 'position', 'rare', 'special', 'is_loan', 'is_evolution'] | None = None
    comparison: Literal['eq', 'ge', 'le'] = 'eq'
    value: StrictStr | StrictInt | StrictBool | None = None
    quantity: Literal['min', 'max', 'exact'] = 'min'
    count: int = Field(default=1, ge=0, le=23)
    scope: Literal['starters', 'bench', 'roster', 'participants', 'unknown'] = 'starters'
    reviewed: bool = False

    @model_validator(mode='after')
    def typed_predicate(self):
        if self.field is None or self.value is None:
            return self  # Preserve uninterpreted text as pending.
        if self.field == 'rating':
            if type(self.value) is not int or not 1 <= self.value <= 99:
                raise ValueError('La condición de media requiere un entero entre 1 y 99')
        elif self.comparison != 'eq':
            raise ValueError('Solo la media admite comparación numérica')
        elif self.field in {'rare', 'special', 'is_loan', 'is_evolution'}:
            if type(self.value) is not bool:
                raise ValueError('La condición requiere Sí o No explícitos')
        elif not isinstance(self.value, str) or not self.value.strip() or len(self.value) > 80:
            raise ValueError('La condición requiere un texto de hasta 80 caracteres')
        return self


class MatchAction(InputModel):
    id: Identifier
    kind: Literal['goals', 'assists', 'wins', 'matches', 'participate', 'other']
    count: int = Field(ge=1, le=1_000_000)
    actor: str = Field(default='', max_length=500)
    source_text: str = Field(min_length=1, max_length=1000)


class ObjectiveRules(InputModel):
    source_reference: str = Field(min_length=1, max_length=1000)
    source_text: str = Field(min_length=1, max_length=5000)
    observed_at: datetime
    reviewed: bool = False
    mode: Literal['unknown', 'any', 'squad_battles', 'rivals', 'champions', 'friendlies', 'rush'] = 'unknown'
    min_difficulty: Difficulty = 'unknown'
    repeatable: bool | None = None
    dependencies: list[Annotated[int, Field(strict=True, ge=1)]] = Field(default_factory=list, max_length=20)
    loans_allowed: bool | None = None
    minimum_loan_matches: int | None = Field(default=None, ge=1, le=1000)
    conditions: list[CompositionCondition] = Field(default_factory=list, max_length=40)
    actions: list[MatchAction] = Field(default_factory=list, max_length=30)

    @model_validator(mode='after')
    def evidence(self):
        if self.observed_at.tzinfo is None or self.observed_at > now():
            raise ValueError('La fuente requiere una fecha pasada o actual con zona horaria')
        for rows in (self.conditions, self.actions):
            if len({row.id for row in rows}) != len(rows):
                raise ValueError('Cada condición o acción requiere un ID diferente')
        if len(set(self.dependencies)) != len(self.dependencies):
            raise ValueError('No repitas dependencias')
        return self


class ObjectivePlanningInput(InputModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default='', max_length=5000)
    category: Literal['Objetivo', 'Temporada', 'Galería'] = 'Objetivo'
    target: int = Field(default=1, ge=1, le=1_000_000)
    expires_at: datetime | None = None
    rules: ObjectiveRules
    phrase: Literal['REVISAR OBJETIVO']

    @model_validator(mode='after')
    def dates(self):
        if self.expires_at and self.expires_at.tzinfo is None:
            raise ValueError('El vencimiento requiere zona horaria')
        return self


class ManualObjectiveProgress(InputModel):
    value: int | None = Field(ge=0, le=1_000_000)
    note: str = Field(min_length=1, max_length=1000)
    phrase: Literal['REGISTRAR PROGRESO MANUAL']


class ObjectiveProposalRequest(InputModel):
    objective_ids: list[Annotated[int, Field(strict=True, ge=1)]] = Field(min_length=1, max_length=6)
    formation: str = '4-3-3'
    bench_size: int = Field(default=7, ge=0, le=12)
    avoid_main: bool = False

    @model_validator(mode='after')
    def valid_selection(self):
        from app.services.squad_analysis import verified_formations
        if self.formation not in verified_formations():
            raise ValueError('Formación pendiente de revisión FC27')
        if len(set(self.objective_ids)) != len(self.objective_ids):
            raise ValueError('No repitas objetivos')
        return self


class ObjectiveProposalSave(InputModel):
    token: str = Field(min_length=20, max_length=20000)
    name: str = Field(min_length=1, max_length=100)
    protect: bool = False


class ObjectiveProposalExport(InputModel):
    token: str = Field(min_length=20, max_length=20000)
