import io
from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload
from app.core.config import settings
from app.db.session import get_db
from app.models.entities import AppSetting, AuditLog, Challenge, ChatMessage, Objective, Player, Profile, Segment, Squad, SquadPlayer, Submission
from app.optimizers.sbc import solve, validate_solution
from app.schemas.api import ChatRequest, ChallengeCreate, ConfirmRequest, ObjectiveCreate, ObjectiveUpdate, OptimizeRequest, PlayerCreate, PlayerUpdate, ProfileUpdate, SegmentCreate, SquadCreate
from app.services.audit import record
from app.services.import_export import export_players, ocr_image, parse_import
from app.services.ollama import chat, status
from app.services.rating import calculate_rating

router = APIRouter()
DB = Annotated[Session, Depends(get_db)]

def player_data(p: Player) -> dict:
    return {key: getattr(p, key) for key in ("id", "name", "rating", "position", "league", "club", "nationality", "card_type", "rare", "special", "tradable", "price", "chemistry", "protected", "starter", "squad_role", "usefulness", "duplicate_untradeable", "deleted", "created_at")}

def objective_data(o: Objective) -> dict:
    return {key: getattr(o, key) for key in ("id", "name", "description", "category", "progress", "target", "completed", "expires_at")}

def segment_data(s: Segment) -> dict:
    return {"id": s.id, "name": s.name, "requirements": s.requirements, "completed": s.completed}

def challenge_data(c: Challenge) -> dict:
    return {"id": c.id, "name": c.name, "description": c.description, "reward": c.reward, "completed": c.completed, "expires_at": c.expires_at, "segments": [segment_data(s) for s in c.segments]}

def squad_data(s: Squad) -> dict:
    entries = [{"slot": entry.slot, "player": player_data(entry.player)} for entry in s.players]
    return {"id": s.id, "name": s.name, "formation": s.formation, "primary": s.primary, "protected": s.protected, "players": entries, "rating": calculate_rating([e.player.rating for e in s.players]), "chemistry": sum(e.player.chemistry for e in s.players)}

def get_or_404(db: Session, model, entity_id: int):
    entity = db.get(model, entity_id)
    if not entity: raise HTTPException(404, "Registro no encontrado")
    return entity

@router.get("/health")
def health(db: DB):
    db.execute(select(1))
    return {"status": "healthy", "database": "ok", "time": datetime.now(timezone.utc)}

@router.get("/dashboard")
def dashboard(db: DB):
    profile = db.scalar(select(Profile).limit(1))
    available = Player.deleted.is_(False)
    count = db.scalar(select(func.count(Player.id)).where(available)) or 0
    protected = db.scalar(select(func.count(Player.id)).where(available, Player.protected.is_(True))) or 0
    duplicates = db.scalar(select(func.count(Player.id)).where(available, Player.duplicate_untradeable.is_(True))) or 0
    pending = db.scalar(select(func.count(Challenge.id)).where(Challenge.completed.is_(False))) or 0
    goals = db.scalars(select(Objective).where(Objective.completed.is_(False)).order_by(Objective.expires_at).limit(5)).all()
    alerts = []
    if duplicates: alerts.append({"level": "warning", "message": f"Tienes {duplicates} duplicados intransferibles para priorizar."})
    if protected: alerts.append({"level": "info", "message": f"{protected} cartas están protegidas contra entregas."})
    return {"profile": {"id": profile.id, "name": profile.name, "coins": profile.coins, "platform": profile.platform, "max_budget": profile.max_budget, "risk_level": profile.risk_level, "preferences": profile.preferences}, "counts": {"players": count, "protected": protected, "duplicates": duplicates, "pending_challenges": pending}, "objectives": [objective_data(o) for o in goals], "alerts": alerts}

@router.get("/players")
def list_players(db: DB, search: str = "", position: str | None = None, league: str | None = None, protected: bool | None = None, duplicate: bool | None = None, sort: str = "rating", order: str = "desc", limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    conditions = [Player.deleted.is_(False)]
    if search: conditions.append(or_(Player.name.ilike(f"%{search}%"), Player.club.ilike(f"%{search}%"), Player.nationality.ilike(f"%{search}%")))
    if position: conditions.append(Player.position == position)
    if league: conditions.append(Player.league == league)
    if protected is not None: conditions.append(Player.protected == protected)
    if duplicate is not None: conditions.append(Player.duplicate_untradeable == duplicate)
    columns = {"rating": Player.rating, "name": Player.name, "price": Player.price, "position": Player.position}
    sort_column = columns.get(sort, Player.rating)
    ordering = sort_column.asc() if order == "asc" else sort_column.desc()
    total = db.scalar(select(func.count(Player.id)).where(*conditions)) or 0
    players = db.scalars(select(Player).where(*conditions).order_by(ordering, Player.id).offset(offset).limit(limit)).all()
    return {"items": [player_data(p) for p in players], "total": total, "limit": limit, "offset": offset}

@router.post("/players", status_code=201)
def create_player(payload: PlayerCreate, db: DB):
    player = Player(**payload.model_dump()); db.add(player); db.flush(); record(db, "create", "player", player.id); db.commit(); db.refresh(player)
    return player_data(player)

@router.patch("/players/{player_id}")
def update_player(player_id: int, payload: PlayerUpdate, db: DB):
    player = get_or_404(db, Player, player_id)
    if player.deleted: raise HTTPException(404, "Jugador no disponible")
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items(): setattr(player, key, value.strip() if isinstance(value, str) else value)
    record(db, "update", "player", player.id, {"fields": list(changes)}); db.commit(); db.refresh(player)
    return player_data(player)

@router.delete("/players/{player_id}")
def delete_player(player_id: int, db: DB):
    player = get_or_404(db, Player, player_id); player.deleted = True; record(db, "soft_delete", "player", player.id); db.commit()
    return {"ok": True}

@router.post("/players/{player_id}/protect")
def protect_player(player_id: int, db: DB):
    player = get_or_404(db, Player, player_id); player.protected = not player.protected; record(db, "protect" if player.protected else "unprotect", "player", player.id); db.commit()
    return player_data(player)

@router.get("/players/export")
def download_players(db: DB, format: str = Query("csv", pattern="^(csv|xlsx)$")):
    content, media = export_players(db, excel=format == "xlsx")
    filename = f"inventario_fc26.{format}"
    return Response(content, media_type=media, headers={"Content-Disposition": f'attachment; filename="{filename}"'})

@router.post("/players/import")
async def import_players(db: DB, file: UploadFile = File(...), confirm: bool = Form(False)):
    if not (file.filename or "").lower().endswith((".csv", ".xlsx")): raise HTTPException(415, "Solo se permiten CSV o XLSX")
    content = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(content) > settings.max_upload_mb * 1024 * 1024: raise HTTPException(413, "Archivo demasiado grande")
    try: records = parse_import(content, file.filename or "import.csv")
    except Exception as exc: raise HTTPException(422, str(exc)) from exc
    if not confirm: return {"preview": records[:100], "total": len(records), "requires_confirmation": True}
    for item in records: db.add(Player(**item))
    record(db, "import", "players", details={"count": len(records), "filename": (file.filename or "")[:120]}); db.commit()
    return {"imported": len(records)}

@router.get("/duplicates")
def duplicates(db: DB):
    players = db.scalars(select(Player).where(Player.deleted.is_(False), Player.duplicate_untradeable.is_(True)).order_by(Player.rating.desc())).all()
    return [player_data(p) for p in players]

@router.post("/duplicates/{player_id}/used")
def mark_duplicate_used(player_id: int, db: DB):
    player = get_or_404(db, Player, player_id); player.duplicate_untradeable = False; record(db, "duplicate_used", "player", player.id); db.commit(); return player_data(player)

@router.get("/squads")
def list_squads(db: DB):
    squads = db.scalars(select(Squad).options(selectinload(Squad.players).selectinload(SquadPlayer.player)).order_by(Squad.primary.desc(), Squad.id)).all()
    return [squad_data(s) for s in squads]

@router.post("/squads", status_code=201)
def create_squad(payload: SquadCreate, db: DB):
    if len(set(payload.player_ids)) != len(payload.player_ids): raise HTTPException(422, "No se permiten jugadores repetidos")
    players = db.scalars(select(Player).where(Player.id.in_(payload.player_ids), Player.deleted.is_(False))).all() if payload.player_ids else []
    if len(players) != len(payload.player_ids): raise HTTPException(422, "Uno o más jugadores no están disponibles")
    squad = Squad(name=payload.name, formation=payload.formation); db.add(squad); db.flush()
    for index, player_id in enumerate(payload.player_ids): db.add(SquadPlayer(squad_id=squad.id, player_id=player_id, slot=f"POS-{index + 1}"))
    record(db, "create", "squad", squad.id); db.commit()
    squad = db.scalar(select(Squad).where(Squad.id == squad.id).options(selectinload(Squad.players).selectinload(SquadPlayer.player)))
    return squad_data(squad)

@router.post("/squads/{squad_id}/duplicate")
def duplicate_squad(squad_id: int, db: DB):
    source = db.scalar(select(Squad).where(Squad.id == squad_id).options(selectinload(Squad.players)))
    if not source: raise HTTPException(404, "Plantilla no encontrada")
    copy = Squad(name=f"{source.name} (copia)", formation=source.formation); db.add(copy); db.flush()
    for entry in source.players: db.add(SquadPlayer(squad_id=copy.id, player_id=entry.player_id, slot=entry.slot))
    record(db, "duplicate", "squad", copy.id, {"source": squad_id}); db.commit()
    return {"id": copy.id, "name": copy.name}

@router.post("/squads/{squad_id}/protect")
def protect_squad(squad_id: int, db: DB):
    squad = db.scalar(select(Squad).where(Squad.id == squad_id).options(selectinload(Squad.players).selectinload(SquadPlayer.player)))
    if not squad: raise HTTPException(404, "Plantilla no encontrada")
    squad.protected = not squad.protected
    for entry in squad.players: entry.player.protected = squad.protected
    record(db, "protect" if squad.protected else "unprotect", "squad", squad.id, {"players": len(squad.players)}); db.commit()
    return squad_data(squad)

@router.post("/squads/recommend")
def recommend_squad(db: DB, formation: str = "4-3-3"):
    positions = ["POR", "LD", "DFC", "DFC", "LI", "MCD", "MC", "MCO", "ED", "DC", "EI"]
    available = db.scalars(select(Player).where(Player.deleted.is_(False)).order_by(Player.rating.desc(), Player.chemistry.desc())).all()
    chosen = []
    for position in positions:
        candidate = next((p for p in available if p.position == position and p.id not in {c.id for c in chosen}), None)
        if candidate: chosen.append(candidate)
    return {"formation": formation, "players": [player_data(p) for p in chosen], "rating": calculate_rating([p.rating for p in chosen]), "chemistry": sum(p.chemistry for p in chosen), "recommendation": True}

@router.get("/challenges")
def list_challenges(db: DB):
    challenges = db.scalars(select(Challenge).options(selectinload(Challenge.segments)).order_by(Challenge.completed, Challenge.id)).all()
    return [challenge_data(c) for c in challenges]

@router.post("/challenges", status_code=201)
def create_challenge(payload: ChallengeCreate, db: DB):
    challenge = Challenge(**payload.model_dump()); db.add(challenge); db.flush(); record(db, "create", "challenge", challenge.id); db.commit(); return challenge_data(challenge)

@router.post("/challenges/{challenge_id}/segments", status_code=201)
def create_segment(challenge_id: int, payload: SegmentCreate, db: DB):
    get_or_404(db, Challenge, challenge_id)
    segment = Segment(challenge_id=challenge_id, **payload.model_dump()); db.add(segment); db.flush(); record(db, "create", "segment", segment.id); db.commit(); return segment_data(segment)

def optimization_payload(db: Session, segment: Segment, request: OptimizeRequest):
    players = db.scalars(select(Player).where(Player.deleted.is_(False))).all()
    solutions = solve(players, segment.requirements, set(request.allow_protected_ids), set(request.exclude_ids), request.max_solutions)
    by_id = {p.id: p for p in players}
    return [{"player_ids": item.player_ids, "players": [player_data(by_id[pid]) for pid in item.player_ids], "total_cost": item.total_cost, "rating": item.rating, "chemistry": item.chemistry, "valid": item.valid, "violations": item.violations, "uses_protected": any(by_id[pid].protected for pid in item.player_ids), "duplicate_count": sum(by_id[pid].duplicate_untradeable for pid in item.player_ids)} for item in solutions]

@router.post("/segments/{segment_id}/optimize")
def optimize_segment(segment_id: int, payload: OptimizeRequest, db: DB):
    segment = get_or_404(db, Segment, segment_id)
    solutions = optimization_payload(db, segment, payload)
    return {"segment": segment_data(segment), "solutions": solutions, "message": "No existe una solución válida con el inventario y protecciones actuales." if not solutions else None, "simulation": True}

@router.post("/segments/{segment_id}/confirm")
def confirm_segment(segment_id: int, payload: ConfirmRequest, db: DB):
    segment = get_or_404(db, Segment, segment_id)
    if segment.completed: raise HTTPException(409, "El segmento ya está completado")
    players = db.scalars(select(Player).where(Player.id.in_(payload.player_ids), Player.deleted.is_(False))).all()
    if len(players) != len(set(payload.player_ids)): raise HTTPException(422, "Hay jugadores repetidos o no disponibles")
    if any(p.protected for p in players): raise HTTPException(422, "No se pueden entregar jugadores protegidos sin autorización individual")
    violations = validate_solution(players, segment.requirements)
    if violations: raise HTTPException(422, {"message": "La solución no es válida", "violations": violations})
    snapshot = {str(p.id): {"deleted": p.deleted, "duplicate_untradeable": p.duplicate_untradeable} for p in players}
    for player in players: player.deleted = True; player.duplicate_untradeable = False
    segment.completed = True
    submission = Submission(segment_id=segment.id, total_cost=sum(p.price for p in players), snapshot={"players": snapshot, "player_ids": payload.player_ids})
    db.add(submission); db.flush()
    challenge = get_or_404(db, Challenge, segment.challenge_id)
    db.flush(); challenge.completed = all(s.completed for s in db.scalars(select(Segment).where(Segment.challenge_id == challenge.id)).all())
    record(db, "confirm", "submission", submission.id, {"segment_id": segment.id, "players": payload.player_ids}); db.commit()
    return {"submission_id": submission.id, "confirmed": True, "consumed_players": len(players)}

@router.post("/submissions/{submission_id}/restore")
def restore_submission(submission_id: int, db: DB):
    submission = get_or_404(db, Submission, submission_id)
    if submission.status == "restored": raise HTTPException(409, "La entrega ya fue restaurada")
    for raw_id, state in submission.snapshot.get("players", {}).items():
        player = db.get(Player, int(raw_id))
        if player:
            player.deleted = bool(state.get("deleted", False)); player.duplicate_untradeable = bool(state.get("duplicate_untradeable", False))
    segment = get_or_404(db, Segment, submission.segment_id); segment.completed = False
    challenge = get_or_404(db, Challenge, segment.challenge_id); challenge.completed = False; submission.status = "restored"
    record(db, "restore", "submission", submission.id); db.commit()
    return {"restored": True, "players": len(submission.snapshot.get("players", {}))}

@router.get("/objectives")
def list_objectives(db: DB):
    return [objective_data(o) for o in db.scalars(select(Objective).order_by(Objective.completed, Objective.expires_at)).all()]

@router.post("/objectives", status_code=201)
def create_objective(payload: ObjectiveCreate, db: DB):
    objective = Objective(**payload.model_dump()); objective.completed = objective.progress >= objective.target; db.add(objective); db.flush(); record(db, "create", "objective", objective.id); db.commit(); return objective_data(objective)

@router.patch("/objectives/{objective_id}")
def update_objective(objective_id: int, payload: ObjectiveUpdate, db: DB):
    objective = get_or_404(db, Objective, objective_id)
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(objective, key, value)
    if payload.completed is None: objective.completed = objective.progress >= objective.target
    record(db, "update", "objective", objective.id); db.commit(); return objective_data(objective)

@router.get("/ai/status")
async def ai_status(): return await status()

@router.post("/ai/chat")
async def ai_chat(payload: ChatRequest, db: DB):
    count = db.scalar(select(func.count(Player.id)).where(Player.deleted.is_(False))) or 0
    duplicates_count = db.scalar(select(func.count(Player.id)).where(Player.deleted.is_(False), Player.duplicate_untradeable.is_(True))) or 0
    protected_count = db.scalar(select(func.count(Player.id)).where(Player.deleted.is_(False), Player.protected.is_(True))) or 0
    pending = db.scalars(select(Challenge.name).where(Challenge.completed.is_(False)).limit(10)).all()
    context = f"DATOS REGISTRADOS: {count} jugadores; {duplicates_count} duplicados; {protected_count} protegidos; DCP pendientes: {', '.join(pending)}."
    result = await chat(payload.message, context)
    db.add(ChatMessage(role="user", content=payload.message, metadata_json={"source": "local"}))
    db.add(ChatMessage(role="assistant", content=result["answer"], metadata_json={"available": result["available"], "model": settings.ollama_model}))
    record(db, "chat", "ai", details={"available": result["available"], "message_length": len(payload.message)}); db.commit()
    return result

@router.get("/ai/history")
def ai_history(db: DB, limit: int = Query(50, ge=1, le=200)):
    rows = list(reversed(db.scalars(select(ChatMessage).order_by(ChatMessage.id.desc()).limit(limit)).all()))
    return [{"id": row.id, "role": row.role, "content": row.content, "metadata": row.metadata_json, "created_at": row.created_at} for row in rows]

@router.post("/ocr/preview")
async def ocr_preview(file: UploadFile = File(...)):
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed: raise HTTPException(415, "Formato no permitido. Usa JPEG, PNG o WebP")
    content = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(content) > settings.max_upload_mb * 1024 * 1024: raise HTTPException(413, "Imagen demasiado grande")
    try: return ocr_image(content)
    except Exception as exc: raise HTTPException(422, "No se pudo procesar la imagen") from exc

@router.get("/profile")
def get_profile(db: DB):
    profile = db.scalar(select(Profile).limit(1)); return {key: getattr(profile, key) for key in ("id", "name", "coins", "platform", "max_budget", "risk_level", "preferences")}

@router.patch("/profile")
def update_profile(payload: ProfileUpdate, db: DB):
    profile = db.scalar(select(Profile).limit(1))
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(profile, key, value)
    record(db, "update", "profile", profile.id); db.commit(); return {key: getattr(profile, key) for key in ("id", "name", "coins", "platform", "max_budget", "risk_level", "preferences")}

@router.get("/settings")
def list_settings(db: DB):
    return {row.key: row.value for row in db.scalars(select(AppSetting)).all()}

@router.put("/settings/{key}")
def update_setting(key: str, value: dict, db: DB):
    if not key.replace("_", "").isalnum() or len(key) > 80: raise HTTPException(422, "Clave inválida")
    setting = db.get(AppSetting, key)
    if setting: setting.value = value
    else: db.add(AppSetting(key=key, value=value))
    record(db, "update", "setting", details={"key": key}); db.commit(); return {"key": key, "value": value}

@router.get("/audit")
def audit_logs(db: DB, limit: int = Query(50, ge=1, le=200)):
    logs = db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)).all()
    return [{"id": row.id, "action": row.action, "entity_type": row.entity_type, "entity_id": row.entity_id, "details": row.details, "created_at": row.created_at} for row in logs]
