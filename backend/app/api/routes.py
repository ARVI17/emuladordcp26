import base64
import hashlib
import hmac
import json
import re
import secrets
import time
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload
from starlette.concurrency import run_in_threadpool

from app.api.analysis import SquadRecommendationRequest
from app.core.config import settings
from app.db.session import get_db
from app.models.entities import AppSetting, AuditLog, Challenge, ChatMessage, Objective, Player, Profile, Segment, Squad, SquadPlayer, Submission
from app.optimizers.sbc import solve, validate_solution
from app.schemas.api import ChatRequest, ChallengeCreate, ConfirmRequest, ObjectiveCreate, ObjectiveUpdate, OptimizeRequest, PlayerCreate, PlayerUpdate, ProfileUpdate, SegmentCreate, SquadCreate
from app.schemas.requirements import normalize_requirements
from app.schemas.api import TacticNotes
from app.services.audit import record
from app.services.editions import current_version, ensure_profile
from app.services.gallery import record_player
from app.services.import_export import export_players, ocr_image, parse_import
from app.services.locks import resource_locks
from app.services.ollama import chat, status
from app.services.rating import calculate_rating
from app.services.squad_analysis import verified_formations, athlete_keys, effective_protected_ids, formation_slots, player_positions, recommend_owned_squad, serialize_player

router = APIRouter()
DB = Annotated[Session, Depends(get_db)]


def version_for(db: Session, version: str | None = None) -> str:
    if version not in (None, "FC27"):
        raise HTTPException(422, "El producto solo admite FC27; el histórico no está disponible en estas rutas")
    return version or current_version(db)


def payload_version(payload, db: Session) -> str:
    version = current_version(db)
    if "game_version" in payload.model_fields_set and payload.game_version != version:
        raise HTTPException(422, "Selecciona esa edición en tu perfil antes de modificar su inventario")
    return version


def player_data(player: Player, protected_ids: set[int] | None = None) -> dict:
    return serialize_player(player, protected_ids)


def objective_data(objective: Objective) -> dict:
    from app.services.definition_validation import is_documented, pending_result
    if not is_documented(objective):
        return pending_result(objective)
    return {key: getattr(objective, key) for key in ("id", "game_version", "name", "description", "category", "progress", "target", "completed", "expires_at")}


def score_progress(db: Session, segment: Segment) -> int:
    return int(db.scalar(select(func.coalesce(func.sum(Submission.score_contribution), 0)).where(Submission.segment_id == segment.id, Submission.status == "confirmed")) or 0)


def requirements_for_batch(db: Session, segment: Segment) -> dict:
    """Apply a score segment's player and value rules to its remaining work."""
    requirements = validated_requirements(segment.requirements)
    if requirements["kind"] != "score":
        return requirements
    active = db.scalars(select(Submission).where(Submission.segment_id == segment.id, Submission.status == "confirmed")).all()
    delivered = {player_id for row in active for player_id in row.snapshot.get("player_ids", [])}
    if "required_player_ids" in requirements:
        requirements["required_player_ids"] = [player_id for player_id in requirements["required_player_ids"] if player_id not in delivered]
    if "max_total_value" in requirements:
        requirements["max_total_value"] -= sum(row.total_cost or 0 for row in active)
        if requirements["max_total_value"] < 0:
            raise HTTPException(409, "Las entregas activas ya exceden el valor máximo de este segmento")
    return requirements


def segment_data(segment: Segment, db: Session | None = None) -> dict:
    score = score_progress(db, segment) if db is not None and segment.requirements.get("kind") == "score" else 0
    target = segment.requirements.get("target_score", 0)
    return {"id": segment.id, "name": segment.name, "requirements": segment.requirements, "completed": segment.completed, "current_score": score, "target_score": target, "remaining_score": max(0, target - score)}


def challenge_data(challenge: Challenge, db: Session | None = None) -> dict:
    from app.services.definition_validation import is_documented, pending_result
    if not is_documented(challenge):
        return pending_result(challenge)
    return {"id": challenge.id, "game_version": challenge.game_version, "name": challenge.name, "description": challenge.description, "reward": challenge.reward, "completed": challenge.completed, "expires_at": challenge.expires_at, "segments": [segment_data(segment, db) for segment in challenge.segments]}


def squad_data(squad: Squad, protected_ids: set[int] | None = None) -> dict:
    active = [entry for entry in squad.players if entry.player and not entry.player.deleted and entry.player.game_version == squad.game_version]
    entries = [{"slot": entry.slot, "player": player_data(entry.player, protected_ids), "available": entry.player.availability == "available",
                "position_valid": entry.slot.startswith(("BENCH-", "RESERVE-")) or entry.slot.rsplit("-", 1)[0] in player_positions(entry.player)} for entry in active]
    starters = [entry for entry in active if not entry.slot.startswith(("BENCH-", "RESERVE-")) and entry.player.availability == "available"]
    expected = formation_slots(squad.formation) if squad.formation in verified_formations() else []
    # Older saved squads numbered all slots globally (DFC-3, MC-7...). Count
    # positions rather than treating a legacy suffix as a missing footballer.
    present = Counter(entry.slot.rsplit("-", 1)[0] for entry in starters
                      if entry.slot.rsplit("-", 1)[0] in player_positions(entry.player))
    missing = []
    for slot in expected:
        if present[slot["position"]]:
            present[slot["position"]] -= 1
        else:
            missing.append(slot)
    return {
        "id": squad.id, "game_version": squad.game_version, "name": squad.name, "formation": squad.formation,
        "primary": squad.primary, "protected": squad.protected, "players": entries, "tactic": squad.tactic,
        "tactic_status": "local_hypothesis",
        "rating": calculate_rating([entry.player.rating for entry in starters]),
        "chemistry": sum(entry.player.chemistry for entry in starters), "chemistry_approximate": True,
        "complete": len(starters) == 11 and len(expected) == 11 and not missing, "unavailable_players": len(squad.players) - sum(entry.player.availability == "available" for entry in active),
        "missing_slots": missing,
    }


def get_or_404(db: Session, model, entity_id: int):
    entity = db.get(model, entity_id)
    if not entity:
        raise HTTPException(404, "Registro no encontrado")
    version = current_version(db)
    if hasattr(entity, "game_version") and entity.game_version != version:
        raise HTTPException(404, "Registro no disponible en la edición activa")
    if isinstance(entity, Segment) and (not entity.challenge or entity.challenge.game_version != version):
        raise HTTPException(404, "Segmento no disponible en la edición activa")
    return entity


def available_player(db: Session, player_id: int) -> Player:
    player = get_or_404(db, Player, player_id)
    if player.deleted:
        raise HTTPException(404, "Jugador no disponible")
    return player


def validated_requirements(requirements: dict) -> dict:
    try:
        return normalize_requirements(requirements)
    except ValueError as exc:
        raise HTTPException(422, f"Revisa los requisitos: {exc}") from exc


@router.get("/health")
def health(db: DB):
    db.execute(select(1))
    return {"status": "healthy", "database": "ok", "time": datetime.now(timezone.utc)}


@router.get("/dashboard")
def dashboard(db: DB):
    profile = ensure_profile(db)
    db.commit()
    version = profile.game_version
    available = (Player.deleted.is_(False), Player.game_version == version)
    count = db.scalar(select(func.count(Player.id)).where(*available)) or 0
    protected = db.scalar(select(func.count(Player.id)).where(*available, Player.id.in_(effective_protected_ids(db, version)))) or 0
    duplicates = db.scalar(select(func.count(Player.id)).where(*available, Player.duplicate_untradeable.is_(True))) or 0
    pending = db.scalar(select(func.count(Challenge.id)).where(Challenge.game_version == version, Challenge.completed.is_(False))) or 0
    goals = db.scalars(select(Objective).where(Objective.game_version == version, Objective.completed.is_(False)).order_by(Objective.expires_at).limit(5)).all()
    alerts = []
    if duplicates:
        alerts.append({"level": "warning", "message": f"Tienes {duplicates} duplicados intransferibles para priorizar."})
    if protected:
        alerts.append({"level": "info", "message": f"{protected} cartas están protegidas contra entregas."})
    from app.services.account import account_summary
    return {"account": account_summary(db), "mode": db.info['local_session'].mode,
            "profile": {key: getattr(profile, key) for key in ("id", "game_version", "name", "coins", "platform", "max_budget", "risk_level", "preferences")}, "counts": {"players": count, "protected": protected, "duplicates": duplicates, "pending_challenges": pending}, "objectives": [objective_data(goal) for goal in goals], "alerts": alerts}


@router.get("/players")
def list_players(db: DB, search: str = "", position: str | None = None, league: str | None = None, protected: bool | None = None, duplicate: bool | None = None, sort: str = "rating", order: str = "desc", limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), game_version: str | None = None):
    version = version_for(db, game_version)
    conditions = [Player.deleted.is_(False), Player.game_version == version]
    if search:
        conditions.append(or_(Player.name.ilike(f"%{search}%"), Player.club.ilike(f"%{search}%"), Player.nationality.ilike(f"%{search}%")))
    if position:
        conditions.append(Player.position == position)
    if league:
        conditions.append(Player.league == league)
    protected_ids = effective_protected_ids(db, version)
    if protected is not None:
        conditions.append(Player.id.in_(protected_ids) if protected else Player.id.not_in(protected_ids))
    if duplicate is not None:
        conditions.append(Player.duplicate_untradeable == duplicate)
    sort_column = {"rating": Player.rating, "name": Player.name, "price": Player.price, "position": Player.position}.get(sort, Player.rating)
    ordering = sort_column.asc() if order == "asc" else sort_column.desc()
    total = db.scalar(select(func.count(Player.id)).where(*conditions)) or 0
    players = db.scalars(select(Player).where(*conditions).order_by(ordering, Player.id).offset(offset).limit(limit)).all()
    return {"items": [player_data(player, protected_ids) for player in players], "total": total, "limit": limit, "offset": offset, "game_version": version}


@router.post("/players", status_code=201)
def create_player(payload: PlayerCreate, db: DB):
    with resource_locks(db, "inventory"):
        db.expire_all()
        values = payload.model_dump()
        values["game_version"] = payload_version(payload, db)
        player = Player(**values)
        from app.services.catalog_validation import validate_copy, copy_result
        accepted = validate_copy(db, player, explicit_edition='game_version' in payload.model_fields_set)
        db.add(player)
        db.flush()
        record_player(db, player)
        record(db, "create", "player", player.id)
        db.commit()
        if not accepted:
            return JSONResponse(status_code=202, content=copy_result(player))
        return player_data(player, effective_protected_ids(db))


@router.patch("/players/{player_id}")
def update_player(player_id: int, payload: PlayerUpdate, db: DB):
    with resource_locks(db, "inventory"):
        db.expire_all()
        player = available_player(db, player_id)
        changes = payload.model_dump(exclude_unset=True)
        if "game_version" in changes and changes["game_version"] != player.game_version:
            raise HTTPException(422, "No se puede trasladar una carta entre ediciones")
        merged = {key: getattr(player, key) for key in PlayerCreate.model_fields}
        merged.update(changes)
        try:
            normalized = PlayerCreate.model_validate(merged).model_dump()
        except ValidationError as exc:
            raise HTTPException(422, exc.errors(include_url=False, include_context=False, include_input=False)) from exc
        from app.services.catalog_validation import check_fields
        if check_fields(db, normalized)[0] is None:
            raise HTTPException(409, 'La modificación no coincide con una variante FC27 documentada')
        for key, value in normalized.items():
            setattr(player, key, value)
        from app.services.catalog_validation import validate_copy
        if set(changes) & {'game_version', 'card_id', 'name', 'rating', 'position', 'card_type', 'data_source'}:
            validate_copy(db, player)
        if player.unknown_fields and changes.get("data_reviewed") is True:
            player.unknown_fields = [field for field in player.unknown_fields if field not in changes]
            if player.unknown_fields:
                player.data_reviewed = False
        record_player(db, player, score_changed="gallery_score" in payload.model_fields_set)
        record(db, "update", "player", player.id, {"fields": list(changes)})
        db.commit()
        return player_data(player, effective_protected_ids(db))


@router.delete("/players/{player_id}")
def delete_player(player_id: int, db: DB):
    with resource_locks(db, "inventory"):
        db.expire_all()
        player = available_player(db, player_id)
        player.deleted = True
        record(db, "soft_delete", "player", player.id)
        db.commit()
    return {"ok": True}


@router.post("/players/{player_id}/protect")
def protect_player(player_id: int, db: DB):
    with resource_locks(db, "inventory"):
        db.expire_all()
        player = available_player(db, player_id)
        player.protected = not player.protected
        record(db, "protect" if player.protected else "unprotect", "player", player.id, {"scope": "manual"})
        db.commit()
        return player_data(player, effective_protected_ids(db))


@router.get("/players/export")
def download_players(db: DB, format: str = Query("csv", pattern="^(csv|xlsx)$")):
    content, media = export_players(db, excel=format == "xlsx")
    return Response(content, media_type=media, headers={"Content-Disposition": f'attachment; filename="inventario_{current_version(db).lower()}.{format}"'})


def _import_secret(db: Session) -> bytes:
    setting = db.get(AppSetting, "_import_signing_key")
    if not setting or not setting.value.get("secret"):
        raise HTTPException(503, "La configuración de importación requiere inicializar el perfil")
    return setting.value["secret"].encode()


def _new_preview_token(db: Session, content_hash: str, suffix: str, version: str) -> str:
    payload = {"context": db.info.get("club_context_id", 1), "hash": content_hash, "format": suffix, "version": version, "nonce": secrets.token_urlsafe(18), "expires": int(time.time()) + 3600}
    encoded = base64.urlsafe_b64encode(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(_import_secret(db), encoded.encode(), hashlib.sha256).hexdigest()
    return f"{encoded}.{signature}"


def _check_preview_token(db: Session, token: str | None, content_hash: str, suffix: str, version: str) -> dict:
    if not token:
        raise HTTPException(422, "Revisa el archivo antes de confirmar la importación")
    try:
        encoded, signature = token.split(".", 1)
        expected = hmac.new(_import_secret(db), encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("signature")
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        if payload["hash"] != content_hash or payload["format"] != suffix or payload["version"] != version or payload.get("context") != db.info.get("club_context_id", 1):
            raise ValueError("file")
        if not isinstance(payload["expires"], int):
            raise ValueError("expires")
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(422, "El archivo o la edición no coinciden con la vista previa. Revisa el archivo de nuevo") from exc
    return payload


def _parse_player_records(content: bytes, filename: str, version: str) -> list[dict]:
    try:
        records = parse_import(content, filename)
        if not records:
            raise ValueError("El archivo no contiene jugadores")
        if len(records) > 5000:
            raise ValueError("El límite es de 5000 cartas por archivo")
        for item in records:
            if item.get("game_version") and item["game_version"] != version:
                raise ValueError("El archivo incluye otra edición. Cambia la edición activa antes de importarlo")
        return records
    except (ValueError, TypeError, OverflowError) as exc:
        raise HTTPException(422, str(exc)) from exc


def _process_import(db: Session, content: bytes, filename: str, confirm: bool, token: str | None) -> dict:
    content_hash = hashlib.sha256(content).hexdigest()
    suffix = Path(filename).suffix.lower()
    if not confirm:
        version = current_version(db)
        records = _parse_player_records(content, filename, version)
        from app.services.catalog_validation import check_fields
        preview = [dict(item, validation_status='documented' if check_fields(db, item)[0] else 'pending_verification') for item in records[:100]]
        return {"preview": preview, "total": len(records), "requires_confirmation": True, "content_hash": content_hash, "preview_token": _new_preview_token(db, content_hash, suffix, version), "game_version": version}
    with resource_locks(db, "inventory"):
        db.expire_all()
        version = current_version(db)
        payload = _check_preview_token(db, token, content_hash, suffix, version)
        receipt_key = "_import_receipt_" + hashlib.sha256(f"{db.info.get('club_context_id', 1)}:{version}:{content_hash}".encode()).hexdigest()
        receipt = db.get(AppSetting, receipt_key)
        if receipt:
            return {"imported": 0, "quarantined": 0, "already_imported": True, "original_imported": receipt.value["imported"], "original_quarantined": receipt.value.get("quarantined", 0), "content_hash": content_hash}
        if payload["expires"] < int(time.time()):
            raise HTTPException(422, "La vista previa caducó. Revisa el archivo de nuevo")
        records = _parse_player_records(content, filename, version)
        players = [Player(**item) for item in records]
        from app.services.catalog_validation import validate_copy
        accepted = [validate_copy(db, player, explicit_edition='game_version' in item) for player, item in zip(players, records)]
        db.add_all(players)
        db.flush()
        for player in players:
            record_player(db, player)
        imported, quarantined = sum(accepted), len(players)-sum(accepted)
        db.add(AppSetting(key=receipt_key, value={"imported": imported, "quarantined": quarantined, "hash": content_hash, "game_version": version}))
        record(db, "import", "players", details={"count": len(players), "filename": filename[:120], "content_hash": content_hash, "game_version": version})
        db.commit()
        return {"imported": imported, "quarantined": quarantined, "already_imported": False, "content_hash": content_hash}


@router.post("/players/import")
async def import_players(db: DB, file: UploadFile = File(...), confirm: bool = Form(False), preview_token: str | None = Form(default=None, max_length=2048)):
    filename = file.filename or ""
    if not filename.lower().endswith((".csv", ".xlsx")):
        raise HTTPException(415, "Solo se permiten CSV o XLSX")
    content = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "Archivo demasiado grande")
    return await run_in_threadpool(_process_import, db, content, filename, confirm, preview_token)


@router.get("/duplicates")
def duplicates(db: DB):
    version = current_version(db)
    protected = effective_protected_ids(db, version)
    players = db.scalars(select(Player).where(Player.game_version == version, Player.deleted.is_(False), Player.duplicate_untradeable.is_(True)).order_by(Player.rating.desc())).all()
    return [player_data(player, protected) for player in players]


@router.post("/duplicates/{player_id}/used")
def mark_duplicate_used(player_id: int, db: DB):
    with resource_locks(db, "inventory"):
        db.expire_all()
        player = available_player(db, player_id)
        if player.id in effective_protected_ids(db):
            raise HTTPException(409, 'Esta copia está protegida o reservada; no se puede marcar como utilizada.')
        player.duplicate_untradeable = False
        record(db, "duplicate_used", "player", player.id)
        db.commit()
        return player_data(player, effective_protected_ids(db))


@router.get("/squads")
def list_squads(db: DB, game_version: str | None = None):
    version = version_for(db, game_version)
    squads = db.scalars(select(Squad).where(Squad.game_version == version).options(selectinload(Squad.players).selectinload(SquadPlayer.player)).order_by(Squad.primary.desc(), Squad.id)).all()
    protected = effective_protected_ids(db, version)
    return [squad_data(squad, protected) for squad in squads]


@router.post("/squads", status_code=201)
def create_squad(payload: SquadCreate, db: DB):
    with resource_locks(db, "inventory"):
        db.expire_all()
        version = payload_version(payload, db)
        from app.services.contexts import require_module
        binding = require_module(db, "squads")
        if payload.expected_binding and any(binding.get(key) != value for key, value in payload.expected_binding.model_dump().items()):
            raise HTTPException(409, "El inventario o la entrada cambió; vuelve a calcular esta propuesta")
        if payload.formation not in verified_formations():
            raise HTTPException(422, "Formación no disponible")
        players = db.scalars(select(Player).where(Player.id.in_(payload.player_ids), Player.deleted.is_(False), Player.game_version == version, Player.availability == "available")).all() if payload.player_ids else []
        if len(players) != len(payload.player_ids) or len(set(payload.player_ids)) != len(payload.player_ids):
            raise HTTPException(422, "Hay jugadores repetidos o no disponibles")
        identities = set()
        for player in players:
            keys = athlete_keys(player)
            if identities & keys:
                raise HTTPException(422, "No se pueden alinear dos versiones del mismo futbolista")
            identities.update(keys)
        by_id = {player.id: player for player in players}
        assignments = []
        if payload.slots is not None:
            allowed = {slot["slot"]: slot["position"] for slot in formation_slots(payload.formation)}
            allowed.update({f"BENCH-{number}": None for number in range(1, 13)})
            allowed.update({f"RESERVE-{number}": None for number in range(1, 13)})
            if len(payload.slots) != len(players) or len(set(payload.slots)) != len(payload.slots):
                raise HTTPException(422, "Cada jugador requiere una plaza única")
            for player_id, slot in zip(payload.player_ids, payload.slots):
                if slot not in allowed or (allowed[slot] and allowed[slot] not in player_positions(by_id[player_id])):
                    raise HTTPException(422, "Una carta no es elegible para la plaza indicada")
                assignments.append((player_id, slot))
        elif players:
            starters = [by_id[player_id] for player_id in payload.player_ids[:11]]
            try:
                result = recommend_owned_squad(starters, game_version=version, formation=payload.formation, locked_player_ids=[p.id for p in starters], include_unreviewed=True, bench_size=0)
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
            assignments = [(row["player"]["id"], row["slot"]) for row in result["lineup"]]
            assignments += [(player_id, f"BENCH-{number}") for number, player_id in enumerate(payload.player_ids[11:], 1)]
        squad = Squad(name=payload.name, formation=payload.formation, game_version=version, tactic=payload.tactic.model_dump())
        db.add(squad)
        db.flush()
        for player_id, slot in assignments:
            db.add(SquadPlayer(squad_id=squad.id, player_id=player_id, slot=slot))
        record(db, "create", "squad", squad.id)
        db.commit()
        db.refresh(squad)
        return squad_data(squad, effective_protected_ids(db, version))


@router.post("/squads/{squad_id}/duplicate")
def duplicate_squad(squad_id: int, db: DB):
    with resource_locks(db, "inventory"):
        db.expire_all()
        source = get_or_404(db, Squad, squad_id)
        copy = Squad(name=f"{source.name[:92]} (copia)", formation=source.formation, game_version=source.game_version, tactic=dict(source.tactic or {}))
        db.add(copy)
        db.flush()
        copied = 0
        for entry in source.players:
            if not entry.player.deleted and entry.player.game_version == source.game_version and entry.player.availability == "available":
                db.add(SquadPlayer(squad_id=copy.id, player_id=entry.player_id, slot=entry.slot))
                copied += 1
        record(db, "duplicate", "squad", copy.id, {"source": squad_id, "available_players": copied})
        db.commit()
        return {"id": copy.id, "name": copy.name, "copied_players": copied}


@router.patch("/squads/{squad_id}/tactics")
def update_squad_tactics(squad_id: int, payload: TacticNotes, db: DB):
    with resource_locks(db, 'inventory'):
        db.expire_all()
        squad = get_or_404(db, Squad, squad_id)
        squad.tactic = payload.model_dump()
        record(db, "tactic_notes", "squad", squad.id, {"status": "local_hypothesis"})
        db.commit()
        return squad_data(squad, effective_protected_ids(db, squad.game_version))


@router.post("/squads/{squad_id}/protect")
def protect_squad(squad_id: int, db: DB):
    with resource_locks(db, "inventory"):
        db.expire_all()
        squad = get_or_404(db, Squad, squad_id)
        squad.protected = not squad.protected
        record(db, "protect" if squad.protected else "unprotect", "squad", squad.id, {"players": len(squad.players), "scope": "squad"})
        db.commit()
        return squad_data(squad, effective_protected_ids(db))


@router.post("/squads/recommend")
def recommend_squad(db: DB, formation: str | None = None, payload: SquadRecommendationRequest | None = None):
    try:
        options = (payload or SquadRecommendationRequest()).model_dump()
    except ValueError as exc:
        raise HTTPException(422, 'Formaciones pendientes de revisión FC27') from exc
    if formation is not None:
        if formation not in verified_formations():
            raise HTTPException(422, "Formación no disponible")
        options["formation"] = formation
    version = current_version(db)
    players = db.scalars(select(Player).where(Player.game_version == version, Player.deleted.is_(False))).all()
    if options.pop('avoid_main', False):
        from app.services.main_squad import main_ids
        options['excluded_player_ids'] = sorted(set(options['excluded_player_ids']) | main_ids(db))
    try:
        from app.services.contexts import require_module
        return {**recommend_owned_squad(players, game_version=version, protected_ids=effective_protected_ids(db, version), **options), "binding": require_module(db, "squads")}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/challenges")
def list_challenges(db: DB, game_version: str | None = None):
    version = version_for(db, game_version)
    challenges = db.scalars(select(Challenge).where(Challenge.game_version == version).options(selectinload(Challenge.segments)).order_by(Challenge.completed, Challenge.id)).all()
    return [challenge_data(challenge, db) for challenge in challenges]


@router.post("/challenges", status_code=201)
def create_challenge(payload: ChallengeCreate, db: DB):
    with resource_locks(db, "inventory"):
        db.expire_all()
        values = payload.model_dump(exclude={"segments"})
        values["game_version"] = payload_version(payload, db)
        challenge = Challenge(**values)
        db.add(challenge)
        db.flush()
        for segment in payload.segments:
            db.add(Segment(challenge_id=challenge.id, name=segment.name, requirements=validated_requirements(segment.requirements)))
        record(db, "create", "challenge", challenge.id, {"segments": len(payload.segments)})
        db.commit()
        db.refresh(challenge)
        return challenge_data(challenge, db)


@router.post("/challenges/{challenge_id}/segments", status_code=201)
def create_segment(challenge_id: int, payload: SegmentCreate, db: DB):
    with resource_locks(db, "inventory"):
        db.expire_all()
        challenge = get_or_404(db, Challenge, challenge_id)
        segment = Segment(challenge_id=challenge_id, name=payload.name, requirements=validated_requirements(payload.requirements))
        challenge.completed = False
        db.add(segment)
        db.flush()
        record(db, "create", "segment", segment.id)
        db.commit()
        return segment_data(segment, db)


@router.patch("/segments/{segment_id}")
def update_segment(segment_id: int, payload: SegmentCreate, db: DB):
    with resource_locks(db, "inventory"):
        db.expire_all()
        segment = get_or_404(db, Segment, segment_id)
        requirements = validated_requirements(payload.requirements)
        active = db.scalar(select(Submission.id).where(Submission.segment_id == segment.id, Submission.status == "confirmed").limit(1))
        if active is not None and requirements != validated_requirements(segment.requirements):
            raise HTTPException(409, "Restaura las entregas activas antes de cambiar los requisitos")
        segment.name = payload.name
        segment.requirements = requirements
        record(db, "update", "segment", segment.id)
        db.commit()
        return segment_data(segment, db)


def optimization_payload(db: Session, segment: Segment, request: OptimizeRequest):
    if request.allow_protected_ids:
        raise HTTPException(422, 'Las protecciones no se pueden exceptuar desde un DCP.')
    version = current_version(db)
    requirements = requirements_for_batch(db, segment)
    players = db.scalars(select(Player).where(Player.game_version == version, Player.deleted.is_(False))).all()
    protected = effective_protected_ids(db, version)
    from app.services.dcp_review import eligible, issue_review
    players = eligible(db, players, request.filters, protected)
    progress = score_progress(db, segment) if requirements["kind"] == "score" else 0
    solutions = solve(players, requirements, set(request.allow_protected_ids), set(request.exclude_ids), request.max_solutions, effective_protected_ids=protected, current_score=progress)
    by_id = {player.id: player for player in players}
    return [{**asdict(item), "review_token": issue_review(db, segment, item.player_ids, request.filters), "players": [player_data(by_id[player_id], protected) for player_id in item.player_ids], "uses_protected": any(player_id in protected for player_id in item.player_ids), "duplicate_count": sum(by_id[player_id].duplicate_untradeable for player_id in item.player_ids), "chemistry_approximate": True, "chemistry_status": "unavailable", "rating_status": "estimated", "official_validation": False} for item in solutions]


@router.post("/segments/{segment_id}/optimize")
def optimize_segment(segment_id: int, payload: OptimizeRequest, db: DB):
    with resource_locks(db, 'inventory'):
        db.expire_all()
        return optimize_segment_locked(segment_id, payload, db)


def optimize_segment_locked(segment_id: int, payload: OptimizeRequest, db: DB):
    segment = get_or_404(db, Segment, segment_id)
    if segment.completed:
        raise HTTPException(409, "El segmento ya está completado")
    solutions = optimization_payload(db, segment, payload)
    from app.services.contexts import require_module
    binding = require_module(db, "dcp")
    from app.services.main_squad import main_status
    main = main_status(db)
    return {"binding": binding, "main": main, "segment": segment_data(segment, db), "solutions": solutions, "message": "No se encontró una combinación válida dentro del tiempo de cálculo. Revisa inventario, datos pendientes y protecciones." if not solutions else None, "simulation": True, "warnings": [*([main['reason']] if not main['complete'] else []), "La puntuación de selección es local; el valor de las cartas y los puntos de Galería se muestran por separado.", "Las medias y la química tradicional son aproximaciones registradas."]}


def _recompute_completion(db: Session, segment: Segment) -> int:
    db.flush()
    progress = score_progress(db, segment)
    if segment.requirements.get("kind") == "score":
        segment.completed = progress >= segment.requirements["target_score"]
    else:
        segment.completed = db.scalar(select(Submission.id).where(Submission.segment_id == segment.id, Submission.status == "confirmed").limit(1)) is not None
    db.flush()
    challenge = segment.challenge
    challenge.completed = all(row.completed for row in db.scalars(select(Segment).where(Segment.challenge_id == challenge.id)).all())
    return progress


@router.post("/segments/{segment_id}/confirm")
def confirm_segment(segment_id: int, payload: ConfirmRequest, db: DB):
    if db.info["context"].verified:
        raise HTTPException(409, "Revisa y aprueba una propuesta en Planes antes de registrar una entrega real")
    with resource_locks(db, "inventory"):
        db.expire_all()
        from app.services.main_squad import require_main_ready
        require_main_ready(db)
        segment = get_or_404(db, Segment, segment_id)
        requirements = requirements_for_batch(db, segment)
        if segment.completed:
            raise HTTPException(409, "El segmento ya está completado")
        if len(payload.player_ids) != len(set(payload.player_ids)):
            raise HTTPException(422, "No se permiten jugadores repetidos")
        version = current_version(db)
        players = db.scalars(select(Player).where(Player.id.in_(payload.player_ids), Player.deleted.is_(False), Player.game_version == version).order_by(Player.id).with_for_update()).all()
        if len(players) != len(payload.player_ids):
            raise HTTPException(422, "Hay jugadores no disponibles en la edición activa")
        protected = effective_protected_ids(db, version)
        if any(player.id in protected for player in players):
            raise HTTPException(422, "Hay cartas protegidas individualmente o por una plantilla")
        progress = score_progress(db, segment) if requirements["kind"] == "score" else 0
        violations = validate_solution(players, requirements, current_score=progress)
        if violations:
            raise HTTPException(422, {"message": "La solución no es válida", "violations": violations})
        from app.services.dcp_review import check_review, eligible
        filters = check_review(db, segment, payload.player_ids, payload.review_token)
        if len(eligible(db, players, filters, protected)) != len(players):
            raise HTTPException(409, 'La propuesta dejó de cumplir los filtros revisados.')
        contribution = sum(player.gallery_score for player in players) if requirements["kind"] == "score" else 0
        total_value = None if any(player.price is None for player in players) else sum(player.price for player in players)
        if max(contribution, total_value or 0) > 2_147_483_647:
            raise HTTPException(422, "El valor total de esta entrega excede el límite de almacenamiento")
        snapshot = {
            "ownership_version": 1, "origin": "local_simulation", "requirements": requirements, "game_version": version, "fc27_checked": True,
            "players": {str(player.id): {"deleted": player.deleted, "duplicate_untradeable": player.duplicate_untradeable, "consumed_by_submission_id": player.consumed_by_submission_id} for player in players},
            "player_ids": list(payload.player_ids),
            "cards": [{"id": player.id, "name": player.name, "rating": player.rating, "price": player.price, "gallery_score": player.gallery_score, "card_id": player.card_id, "base_card_id": player.base_card_id, "data_reviewed": player.data_reviewed, "data_source": player.data_source} for player in players],
        }
        submission = Submission(segment_id=segment.id, game_version=version, total_cost=total_value, score_contribution=contribution, snapshot=snapshot)
        db.add(submission)
        db.flush()
        for player in players:
            record_player(db, player)
            player.deleted = True
            player.duplicate_untradeable = False
            player.consumed_by_submission_id = submission.id
        progress = _recompute_completion(db, segment)
        record(db, "confirm", "submission", submission.id, {"segment_id": segment.id, "players": payload.player_ids, "score_contribution": contribution, "partial": not segment.completed})
        db.commit()
        return {"submission_id": submission.id, "confirmed": True, "consumed_players": len(players), "completed": segment.completed, "score_contribution": contribution, "current_score": progress, "remaining_score": max(0, requirements.get("target_score", 0) - progress)}


@router.get("/submissions")
def list_submissions(db: DB, limit: int = Query(50, ge=1, le=200)):
    version = current_version(db)
    rows = db.scalars(select(Submission).where(Submission.game_version == version, Submission.snapshot['fc27_checked'].as_boolean().is_(True)).order_by(Submission.id.desc())).all()
    items = []
    for row in rows:
        segment = db.get(Segment, row.segment_id)
        identifiers = set(row.snapshot.get('player_ids', []))
        if not segment or not segment.challenge or not identifiers or set(db.scalars(select(Player.id).where(Player.id.in_(identifiers)))) != identifiers:
            continue
        items.append({"id": row.id, "game_version": row.game_version, "segment_id": row.segment_id, "segment_name": segment.name, "challenge_name": segment.challenge.name, "status": row.status, "total_cost": row.total_cost, "score_contribution": row.score_contribution, "player_ids": row.snapshot.get("player_ids", []), "created_at": row.created_at})
    return {"items": items[:limit], "total": len(items)}


@router.post("/submissions/{submission_id}/restore")
def restore_submission(submission_id: int, db: DB):
    with resource_locks(db, "inventory"):
        db.expire_all()
        submission = get_or_404(db, Submission, submission_id)
        if submission.status != "confirmed":
            raise HTTPException(409, "La entrega ya fue restaurada o no está confirmada")
        if submission.snapshot.get("origin") != "local_simulation" or not submission.snapshot.get("ownership_version"):
            raise HTTPException(409, "Una entrega real o de origen incierto requiere conciliación; restaurar no recupera cartas en EA")
        states = submission.snapshot.get("players", {})
        if not states:
            raise HTTPException(409, "La entrega no contiene un snapshot restaurable")
        players = []
        legacy_rows = None
        for raw_id, state in states.items():
            player = db.get(Player, int(raw_id))
            if not player or player.game_version != submission.game_version or not player.deleted:
                raise HTTPException(409, "El inventario cambió y no permite una restauración segura")
            if player.consumed_by_submission_id != submission.id:
                if player.consumed_by_submission_id is not None or submission.snapshot.get("ownership_version"):
                    raise HTTPException(409, "Una carta pertenece a otra entrega activa")
                if legacy_rows is None:
                    legacy_rows = db.scalars(select(Submission).where(Submission.game_version == submission.game_version, Submission.status == "confirmed")).all()
                owners = [row.id for row in legacy_rows if str(player.id) in row.snapshot.get("players", {})]
                if owners != [submission.id]:
                    raise HTTPException(409, "La entrega antigua tiene propietarios ambiguos y requiere revisión")
            players.append((player, state))
        for player, state in players:
            player.deleted = bool(state.get("deleted", False))
            player.duplicate_untradeable = bool(state.get("duplicate_untradeable", False))
            player.consumed_by_submission_id = state.get("consumed_by_submission_id")
        submission.status = "restored"
        segment = get_or_404(db, Segment, submission.segment_id)
        progress = _recompute_completion(db, segment)
        record(db, "restore", "submission", submission.id, {"players": len(players), "current_score": progress})
        db.commit()
        return {"restored": True, "players": len(players), "current_score": progress, "completed": segment.completed}


@router.get("/objectives")
def list_objectives(db: DB, game_version: str | None = None):
    version = version_for(db, game_version)
    return [objective_data(objective) for objective in db.scalars(select(Objective).where(Objective.game_version == version).order_by(Objective.completed, Objective.expires_at)).all()]


@router.post("/objectives", status_code=201)
def create_objective(payload: ObjectiveCreate, db: DB):
    with resource_locks(db, "inventory"):
        db.expire_all()
        values = payload.model_dump()
        values["game_version"] = payload_version(payload, db)
        objective = Objective(**values)
        objective.completed = objective.progress >= objective.target
        db.add(objective)
        db.flush()
        record(db, "create", "objective", objective.id)
        db.commit()
        return objective_data(objective)


@router.patch("/objectives/{objective_id}")
def update_objective(objective_id: int, payload: ObjectiveUpdate, db: DB):
    with resource_locks(db, "inventory"):
        db.expire_all()
        objective = get_or_404(db, Objective, objective_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(objective, key, value)
        if payload.completed is None:
            objective.completed = objective.progress >= objective.target
        record(db, "update", "objective", objective.id)
        db.commit()
        return objective_data(objective)


@router.get("/ai/status")
async def ai_status():
    return await status()


@router.post("/ai/chat")
async def ai_chat(payload: ChatRequest, db: DB):
    from app.services.ollama import POLICY, FOCUSES, question_focus, grounded_answer
    try:
        focus = question_focus(payload.message)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    version = current_version(db)
    conditions = (Player.game_version == version, Player.deleted.is_(False))
    count = db.scalar(select(func.count(Player.id)).where(*conditions)) or 0
    duplicates_count = db.scalar(select(func.count(Player.id)).where(*conditions, Player.duplicate_untradeable.is_(True))) or 0
    protected_count = db.scalar(select(func.count(Player.id)).where(*conditions, Player.id.in_(effective_protected_ids(db, version)))) or 0
    pending = db.scalar(select(func.count(Challenge.id)).where(Challenge.game_version == version, Challenge.completed.is_(False))) or 0
    counts = {'players': count, 'duplicates': duplicates_count, 'protected': protected_count, 'dcp': pending}
    context = f'DATOS FC27: {json.dumps(counts)}'
    result = grounded_answer(await chat(focus, context), counts, focus)
    # Retain the intent, never arbitrary text that may contain secrets or unverified facts.
    db.add(ChatMessage(role="user", content=FOCUSES[focus], metadata_json={"source": "local", "game_version": version, "policy": POLICY}))
    db.add(ChatMessage(role="assistant", content=result["answer"], metadata_json={"available": result["available"], "model": settings.ollama_model, "game_version": version, "policy": POLICY}))
    record(db, "chat", "ai", details={"available": result["available"], "message_length": len(payload.message), "game_version": version})
    db.commit()
    return result


@router.get("/ai/history")
def ai_history(db: DB, limit: int = Query(50, ge=1, le=200)):
    version = current_version(db)
    edition = ChatMessage.metadata_json["game_version"].as_string()
    from app.services.ollama import POLICY
    condition = (edition == version) & (ChatMessage.metadata_json['policy'].as_string() == POLICY)
    rows = list(reversed(db.scalars(select(ChatMessage).where(condition).order_by(ChatMessage.id.desc()).limit(limit)).all()))
    return [{"id": row.id, "role": row.role, "content": row.content, "metadata": row.metadata_json, "created_at": row.created_at} for row in rows]


@router.post("/ocr/preview")
async def ocr_preview(file: UploadFile = File(...)):
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(415, "Formato no permitido. Usa JPEG, PNG o WebP")
    content = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "Imagen demasiado grande")
    try:
        return await run_in_threadpool(ocr_image, content)
    except Exception as exc:
        raise HTTPException(422, "No se pudo procesar la imagen") from exc


@router.get("/profile")
def get_profile(db: DB):
    profile = ensure_profile(db)
    db.commit()
    return {key: getattr(profile, key) for key in ("id", "game_version", "name", "coins", "platform", "max_budget", "risk_level", "preferences")}


@router.patch("/profile")
def update_profile(payload: ProfileUpdate, db: DB):
    with resource_locks(db, "inventory"):
        db.expire_all()
        profile = ensure_profile(db)
        context = db.info["context"]
        if context.verified and payload.game_version and payload.game_version != context.game_version:
            raise HTTPException(409, "Selecciona el contexto de la otra edicion antes de cambiar de temporada")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(profile, key, value)
        record(db, "update", "profile", profile.id)
        db.commit()
        return {key: getattr(profile, key) for key in ("id", "game_version", "name", "coins", "platform", "max_budget", "risk_level", "preferences")}


@router.get("/settings")
def list_settings(db: DB):
    # Internal caches/manifests contain unreviewed or historical domain data.
    return {'game_version': 'FC27', 'ollama': {'model': settings.ollama_model},
            'optimizer': {'configurable': False, 'message': 'Coeficientes locales fijos en el motor'}}


@router.put("/settings/{key}")
def update_setting(key: str, value: dict, db: DB):
    raise HTTPException(422, 'Configuración interna reservada; usa la función específica del perfil, emulador o revisión')


@router.get("/audit")
def audit_logs(db: DB, limit: int = Query(50, ge=1, le=200)):
    logs = db.scalars(select(AuditLog).where(AuditLog.details['game_version'].as_string() == 'FC27').order_by(AuditLog.id.desc()).limit(limit)).all()
    return [{"id": row.id, "action": row.action, "entity_type": row.entity_type, "entity_id": row.entity_id, "details": row.details, "created_at": row.created_at} for row in logs]
