import json
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.entities import AppSetting, now
from app.models.planner import KnowledgeRevision, MatchRecord
from app.schemas.api import InputModel
from app.services.audit import record
from app.services.contexts import utc
from app.services.locks import resource_locks

router = APIRouter(tags=["Conocimiento público"])


def references():
    return json.loads((Path(__file__).parents[1]/"data"/"fc27_references.json").read_text(encoding="utf-8"))


@router.get("/knowledge")
def knowledge(db: Session = Depends(get_db)):
    revisions = list(db.scalars(select(KnowledgeRevision).order_by(KnowledgeRevision.id)))
    active = {r.reference_id: r for r in revisions if r.status == "approved"}
    schedule = db.get(AppSetting, "knowledge_review_schedule")
    days = schedule.value.get("days", 7) if schedule else 7
    rows = []
    for row in references():
        reviewed = active.get(row["id"])
        rows.append({**row, "review": reviewed.evidence if reviewed else None,
                     "revision_id": reviewed.id if reviewed else None,
                     "due": not reviewed or utc(reviewed.observed_at) < now()-timedelta(days=days) or datetime.fromisoformat(reviewed.evidence["valid_until"]) <= now()})
    return {"items": rows, "count": len(rows), "schedule": schedule.value if schedule else {"days": 7, "enabled": False}, "automatic_downloads": False}


class EvidenceInput(InputModel):
    summary: str = Field(min_length=10, max_length=2000)
    scope: str = Field(min_length=3, max_length=200)
    observed_at: datetime
    valid_until: datetime
    confidence: str = Field(pattern="^(low|medium|high)$")
    conflict: str = Field(default="", max_length=500)


@router.post("/knowledge/{reference_id}/revisions", status_code=201)
def evidence(reference_id: str, payload: EvidenceInput, db: Session = Depends(get_db)):
    reference = next((r for r in references() if r["id"] == reference_id), None)
    if not reference:
        raise HTTPException(404, "Referencia no disponible")
    if payload.observed_at.tzinfo is None or payload.valid_until.tzinfo is None or payload.observed_at > now() or payload.valid_until <= payload.observed_at:
        raise HTTPException(422, "Fechas de revisión inválidas")
    if reference["media_scope"] == "metadata_only" and payload.scope != "metadata_only":
        raise HTTPException(422, "Esta referencia audiovisual solo acredita metadatos")
    previous = db.scalar(select(KnowledgeRevision).where(KnowledgeRevision.reference_id == reference_id, KnowledgeRevision.status == "approved").order_by(KnowledgeRevision.id.desc()).limit(1))
    proposed = payload.model_dump(mode="json")
    changes = {key: {"before": previous.evidence.get(key) if previous else None, "after": value} for key, value in proposed.items() if not previous or previous.evidence.get(key) != value}
    row = KnowledgeRevision(reference_id=reference_id, evidence=proposed, observed_at=payload.observed_at)
    db.add(row)
    db.flush()
    record(db, "draft_evidence", "knowledge_revision", row.id)
    db.commit()
    return {"id": row.id, "status": row.status, "previous_revision_id": previous.id if previous else None, "changes": changes, "previous_preserved": True, "rules_changed": False}


@router.get("/knowledge/{reference_id}/revisions")
def evidence_history(reference_id: str, db: Session = Depends(get_db)):
    return [{"id": r.id, "status": r.status, "evidence": r.evidence} for r in db.scalars(select(KnowledgeRevision).where(KnowledgeRevision.reference_id == reference_id).order_by(KnowledgeRevision.id.desc()).limit(100))]


class AcceptEvidence(InputModel):
    confirmation: str


@router.post("/knowledge/revisions/{revision_id}/approve")
def approve_evidence(revision_id: int, payload: AcceptEvidence, db: Session = Depends(get_db)):
    with resource_locks(db, "knowledge"):
        row = db.get(KnowledgeRevision, revision_id)
        if not row:
            raise HTTPException(404, "Revisión no disponible")
        if payload.confirmation != f"REVISAR FUENTE {revision_id}":
            raise HTTPException(422, "Confirma la evidencia concreta")
        row.status = "approved"
        record(db, "approve_evidence", "knowledge_revision", row.id, {"rules_changed": False})
        db.commit()
        return {"id": row.id, "status": row.status, "rules_changed": False}


class ReviewSchedule(InputModel):
    days: int = Field(ge=1, le=90)
    enabled: bool


@router.put("/knowledge/schedule")
def schedule(payload: ReviewSchedule, db: Session = Depends(get_db)):
    row = db.get(AppSetting, "knowledge_review_schedule")
    values = {**payload.model_dump(), "next_review": (now()+timedelta(days=payload.days)).isoformat(), "mode": "review_reminder", "automatic_fetch": False}
    if row:
        row.value = values
    else:
        db.add(AppSetting(key="knowledge_review_schedule", value=values))
    record(db, "schedule_review", "knowledge")
    db.commit()
    return values


class MatchInput(InputModel):
    played_at: datetime
    tactic: str = Field(min_length=1, max_length=120)
    minutes: int = Field(ge=1, le=240)
    chances: int = Field(ge=0, le=100)
    dangerous_losses: int = Field(ge=0, le=100)
    conceded: int = Field(ge=0, le=100)
    change_tested: str = Field(min_length=1, max_length=300)


@router.post("/matches", status_code=201)
def add_match(payload: MatchInput, db: Session = Depends(get_db)):
    if payload.played_at.tzinfo is None or payload.played_at > now():
        raise HTTPException(422, "Revisa la fecha del partido")
    row = MatchRecord(**payload.model_dump())
    db.add(row)
    db.flush()
    record(db, "record_match", "match_record", row.id)
    db.commit()
    return {"id": row.id}


@router.get("/matches")
def matches(db: Session = Depends(get_db)):
    rows = list(db.scalars(select(MatchRecord).order_by(MatchRecord.id.desc()).limit(100)))
    return {"items": [{key: getattr(r, key) for key in MatchInput.model_fields}|{"id": r.id} for r in rows], "sample_size": len(rows), "message": "Compara un cambio por vez; esta muestra no demuestra causalidad ni superioridad táctica."}
