from datetime import datetime
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.entities import Challenge, Segment, GallerySet, EvolutionDefinition, now
from app.models.planner import PublicDefinition, ClubProgress
from app.schemas.api import InputModel, ChallengeCreate
from app.schemas.fc27 import GallerySetInput, EvolutionInput
from app.services.audit import record
from app.services.editions import current_version
from app.services.locks import resource_locks

router = APIRouter(tags=["Definiciones públicas y progreso privado"])


@router.get('/catalog/pending')
def pending_definitions(db: Session = Depends(get_db)):
    from sqlalchemy import func
    from app.services.definition_validation import MODELS, active_definition_clause
    return {'game_version': 'FC27', 'counts': {kind: db.scalar(select(func.count(model.id)).where(
        ~active_definition_clause(model)).execution_options(include_pending_definitions=True)) or 0 for kind, model in MODELS.items()},
        'validation_status': 'pending_verification',
        'message': 'Definiciones conservadas fuera de las funciones activas. Marcar revisión o adjuntar una URL no verifica su edición, reglas ni vigencia.'}


class DefinitionInput(InputModel):
    kind: Literal["dcp", "gallery", "evolution"]
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    revision: int = Field(ge=1)
    body: dict
    source_url: str = Field(pattern="^https://", max_length=500)
    observed_at: datetime
    confirmation: str


@router.post("/catalog/definitions", status_code=201)
def add_definition(payload: DefinitionInput, db: Session = Depends(get_db)):
    if payload.confirmation != "REGISTRAR DEFINICION PUBLICA":
        raise HTTPException(422, "Confirma que registras una definición pública, sin datos personales")
    if payload.observed_at.tzinfo is None or payload.observed_at > now():
        raise HTTPException(422, "Fecha de observación inválida")
    schema = {"dcp": ChallengeCreate, "gallery": GallerySetInput, "evolution": EvolutionInput}[payload.kind]
    try:
        body = schema.model_validate(payload.body)
    except ValueError:
        raise HTTPException(422, "La definición contiene campos desconocidos o reglas inválidas")
    if payload.kind == "dcp" and any(s.requirements.get("required_player_ids") or s.requirements.get("excluded_player_ids") for s in body.segments):
        raise HTTPException(422, "Una definición pública no puede contener identificadores de copias privadas")
    with resource_locks(db, "catalog"):
        existing = db.scalar(select(PublicDefinition).where(PublicDefinition.kind==payload.kind, PublicDefinition.slug==payload.slug, PublicDefinition.game_version==body.game_version, PublicDefinition.revision==payload.revision).execution_options(include_pending_definitions=True))
        if existing:
            if existing.body != body.model_dump(mode="json"):
                raise HTTPException(409, "La revisión existe con otras reglas; registra una nueva revisión")
            return {"id": existing.id, "already_recorded": True}
        row = PublicDefinition(kind=payload.kind, slug=payload.slug, revision=payload.revision, game_version=body.game_version, body=body.model_dump(mode="json"), source_url=payload.source_url, observed_at=payload.observed_at)
        db.add(row)
        db.flush()
        record(db, "public_definition", "catalog", row.id)
        db.commit()
        from app.services.definition_validation import is_documented, pending_result
        return {'id': row.id} if is_documented(row) else pending_result(row)


@router.get("/catalog/definitions")
def definitions(db: Session = Depends(get_db)):
    return [{key: getattr(row,key) for key in ("id","kind","game_version","slug","revision","body","source_url","observed_at")} for row in db.scalars(select(PublicDefinition).order_by(PublicDefinition.id.desc()).limit(200))]


@router.get("/catalog/private-definitions")
def private_definitions(db: Session = Depends(get_db)):
    """Explicitly reviewable rule exports, excluding completion and ownership."""
    rows = []
    for kind, model, schema in [("dcp", Challenge, ChallengeCreate), ("gallery", GallerySet, GallerySetInput), ("evolution", EvolutionDefinition, EvolutionInput)]:
        for row in db.scalars(select(model).where(model.game_version == current_version(db))):
            values = {key: getattr(row, key) for key in schema.model_fields if key != "segments"}
            if kind == "dcp":
                values["segments"] = [{"name": s.name, "requirements": s.requirements} for s in row.segments]
            rows.append({"key": f"{kind}:{row.id}", "kind": kind, "name": row.name, "body": schema.model_validate(values).model_dump(mode="json")})
    return rows


@router.post("/catalog/definitions/{definition_id}/use")
def use_definition(definition_id: int, db: Session = Depends(get_db)):
    with resource_locks(db, "inventory"):
        definition = db.get(PublicDefinition, definition_id)
        if not definition or definition.game_version != current_version(db):
            raise HTTPException(404, "Definición no disponible en esta edición")
        key = f"public:{definition.id}"
        previous = db.scalar(select(ClubProgress).where(ClubProgress.kind=="definition",ClubProgress.definition_key==key))
        if previous:
            return previous.state
        if definition.kind == "dcp":
            body = ChallengeCreate.model_validate(definition.body)
            row = Challenge(**body.model_dump(exclude={"segments"}))
            db.add(row)
            db.flush()
            for segment in body.segments:
                db.add(Segment(challenge_id=row.id, **segment.model_dump()))
        else:
            schema, model = (GallerySetInput, GallerySet) if definition.kind == "gallery" else (EvolutionInput, EvolutionDefinition)
            values = schema.model_validate(definition.body).model_dump()
            values["slug"] = f"public-{definition.id}"
            row = model(**values)
            db.add(row)
            db.flush()
        db.flush()  # Changes to copied segments invalidate old evidence before the new attestation.
        row.validation_status = definition.validation_status
        row.validation_evidence = dict(definition.validation_evidence)
        state = {"kind":definition.kind,"local_id":row.id,"public_definition_id":definition.id,"revision":definition.revision}
        db.add(ClubProgress(kind="definition",definition_key=key,state=state))
        record(db, "use_definition", "catalog", definition.id, state)
        db.commit()
        return state
