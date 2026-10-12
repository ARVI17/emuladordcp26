import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session, load_only
from app.core.config import settings
from app.db.session import SessionLocal, get_db
from app.models.entities import AppSetting, AutomationPlan, Challenge, InventoryScan, Objective, Player, Segment
from app.optimizers.sbc import validate_solution
from app.schemas.api import AutomationExecuteRequest, AutomationPlanCreate, DcpSyncRequest, EmulatorCalibration, EmulatorConnectRequest, EmulatorPairRequest, EmulatorSelectRequest, EmulatorSwipeRequest, EmulatorTapRequest, InventoryBulkImportRequest, InventoryScanImportRequest, ObjectiveSyncRequest
from app.services.adb import AdbBridge, AdbError, build_dcp_steps, run_step
from app.services.audit import record
from app.services.import_export import extract_accessibility_inventory_candidates, extract_accessibility_objectives, find_accessibility_inventory_action, ocr_image, ocr_inventory, parse_dcp_requirements
from app.services.inventory import all_player_identities, bulk_inventory_preview, candidate_identity, complete_candidate, normalized_text, open_inventory_scans, remove_pending_identities, unique_new_candidates
from app.db.seed import demo_player_names

router = APIRouter(prefix="/emulator", tags=["Emulador asistido"])
DB = Annotated[Session, Depends(get_db)]
DCP_REQUIREMENT_KEYS = {
    "squad_size", "min_rating", "min_chemistry", "min_rare", "min_special", "min_leagues",
    "max_leagues", "min_clubs", "max_clubs", "min_nations", "max_nations", "required_league",
    "min_from_league", "required_club", "min_from_club", "required_nation", "min_from_nation",
    "required_card_type", "min_card_type", "required_positions", "max_total_value",
}

def emulator_config(db: Session) -> dict:
    row = db.get(AppSetting, "emulator")
    return dict(row.value) if row else {"address": settings.adb_default_address, "calibration": None}

def save_emulator_config(db: Session, value: dict):
    row = db.get(AppSetting, "emulator")
    if row: row.value = dict(value)
    else: db.add(AppSetting(key="emulator", value=dict(value)))

def connected_serial(db: Session) -> str:
    config = emulator_config(db)
    serial = config.get("serial") or config.get("address")
    if not serial: raise HTTPException(409, "Configura y conecta un dispositivo ADB")
    return serial

def plan_data(plan: AutomationPlan) -> dict:
    return {key: getattr(plan, key) for key in ("id", "name", "plan_type", "status", "device_serial", "segment_id", "player_ids", "solution_snapshot", "steps", "progress_step", "last_error", "approved_at", "executed_at", "created_at")} | {"confirmation_phrase": f"PREPARAR {plan.id}" if plan.status == "prepared" else None, "final_submission_automated": False}

def scan_data(scan: InventoryScan) -> dict:
    return {key: getattr(scan, key) for key in ("id", "status", "device_serial", "screen_size", "captured_pages", "candidate_count", "imported_count", "last_error", "created_at", "imported_at")} | {
        "confirmation_phrase": f"IMPORTAR {scan.id}",
        "archive_demo_phrase": f"REEMPLAZAR DEMO {scan.id}",
        "images_saved": False,
        "requires_review": True,
    }

def ready_device(db: Session) -> tuple[AdbBridge, str, tuple[int, int] | None]:
    serial = connected_serial(db); bridge = AdbBridge()
    try:
        devices = bridge.devices()
        if not any(item["serial"] == serial and item["state"] == "device" for item in devices):
            raise AdbError("El dispositivo configurado no está conectado")
        return bridge, serial, bridge.screen_size(serial)
    except AdbError as exc: raise HTTPException(409, str(exc)) from exc

def validate_current_plan_solution(db: Session, plan: AutomationPlan):
    if len(set(plan.player_ids)) != len(plan.player_ids): raise HTTPException(422, "La combinación contiene jugadores repetidos")
    segment = db.get(Segment, plan.segment_id)
    if not segment: raise HTTPException(404, "Segmento no encontrado")
    players = db.scalars(select(Player).where(Player.id.in_(plan.player_ids), Player.deleted.is_(False))).all()
    if len(players) != len(plan.player_ids): raise HTTPException(422, "Uno o más jugadores ya no están disponibles")
    if any(player.protected for player in players): raise HTTPException(422, "La combinación contiene cartas protegidas")
    violations = validate_solution(players, segment.requirements)
    if violations: raise HTTPException(422, {"message": "La combinación dejó de ser válida", "violations": violations})
    return players, segment

@router.get("/status")
def status(db: DB):
    config = emulator_config(db)
    if not settings.adb_enabled: return {"enabled": False, "available": False, "devices": [], "config": config, "message": "ADB está desactivado"}
    try:
        devices = AdbBridge().devices()
        ready = [item for item in devices if item["state"] == "device"]
        return {"enabled": True, "available": bool(ready), "devices": devices, "config": config, "message": None if ready else "No hay un emulador o teléfono ADB conectado."}
    except AdbError as exc:
        return {"enabled": True, "available": False, "devices": [], "config": config, "message": str(exc)}

@router.post("/connect")
def connect(payload: EmulatorConnectRequest, db: DB):
    bridge = AdbBridge(); config = emulator_config(db)
    try:
        devices = bridge.devices()
        configured_serial = config.get("serial")
        if configured_serial and any(item["serial"] == configured_serial and item["state"] == "device" for item in devices):
            return {"connected": True, "already_connected": True, "address": payload.address, "serial": configured_serial, "output": "El AVD ya estaba conectado"}
        output = bridge.connect(payload.address)
    except AdbError as exc: raise HTTPException(503, str(exc)) from exc
    config.update({"address": payload.address, "serial": payload.address}); save_emulator_config(db, config)
    record(db, "connect", "emulator", details={"address": payload.address}); db.commit()
    return {"connected": True, "address": payload.address, "output": output}

@router.post("/pair")
def pair(payload: EmulatorPairRequest, db: DB):
    try: output = AdbBridge().pair(payload.address, payload.pairing_code)
    except AdbError as exc: raise HTTPException(503, str(exc)) from exc
    record(db, "pair", "emulator", details={"address": payload.address, "pairing_code_stored": False}); db.commit()
    return {"paired": True, "address": payload.address, "output": output, "pairing_code_stored": False}

@router.post("/select")
def select_device(payload: EmulatorSelectRequest, db: DB):
    try: devices = AdbBridge().devices()
    except AdbError as exc: raise HTTPException(503, str(exc)) from exc
    if not any(item["serial"] == payload.serial and item["state"] == "device" for item in devices):
        raise HTTPException(409, "El dispositivo ADB seleccionado no está disponible")
    config = emulator_config(db); config["serial"] = payload.serial; save_emulator_config(db, config)
    record(db, "select", "emulator", details={"serial": payload.serial}); db.commit()
    return {"selected": True, "serial": payload.serial}

@router.get("/screenshot")
def screenshot(db: DB):
    serial = connected_serial(db)
    try: content = AdbBridge().screenshot(serial)
    except AdbError as exc: raise HTTPException(503, str(exc)) from exc
    return Response(content, media_type="image/png", headers={"Cache-Control": "no-store"})

@router.post("/inspect")
def inspect_screen(db: DB):
    serial = connected_serial(db)
    try:
        bridge = AdbBridge(); content = bridge.screenshot(serial); result = ocr_image(content); size = bridge.screen_size(serial)
    except (AdbError, ValueError) as exc: raise HTTPException(503, str(exc)) from exc
    return result | {"screen_size": size, "source": "ADB", "saved": False}

@router.post("/dcp/inspect")
def inspect_dcp_screen(db: DB):
    bridge, serial, size = ready_device(db)
    try:
        content = bridge.screenshot(serial); result = ocr_image(content)
    except (AdbError, ValueError) as exc: raise HTTPException(503, str(exc)) from exc
    requirements = parse_dcp_requirements(result["raw_text"])
    record(db, "inspect_dcp", "emulator", details={"detected_fields": sorted(requirements)}); db.commit()
    return result | {"screen_size": size, "source": "ADB", "saved": False, "detected_requirements": requirements, "requires_confirmation": True}

@router.post("/dcp/sync")
def sync_reviewed_dcp(payload: DcpSyncRequest, db: DB):
    if payload.confirmation.strip().upper() != "ACTUALIZAR DCP":
        raise HTTPException(422, "Escribe ACTUALIZAR DCP para guardar el borrador revisado")
    requirements = {key: value for key, value in payload.requirements.items() if key in DCP_REQUIREMENT_KEYS}
    if not requirements:
        raise HTTPException(422, "No hay requisitos DCP compatibles para actualizar")
    if "squad_size" not in requirements:
        requirements["squad_size"] = 11
    challenge = next((row for row in db.scalars(select(Challenge)).all() if normalized_text(row.name) == normalized_text(payload.name)), None)
    action = "updated"
    if challenge is None:
        challenge = Challenge(name=payload.name.strip(), description="DCP leído desde Companion y revisado por el usuario", reward="")
        db.add(challenge); db.flush()
        segment = Segment(challenge_id=challenge.id, name="Segmento leído", requirements=requirements)
        db.add(segment); db.flush()
        action = "created"
    else:
        segment = next((row for row in challenge.segments if not row.completed), None)
        if segment is None:
            segment = Segment(challenge_id=challenge.id, name="Segmento leído", requirements=requirements)
            db.add(segment); db.flush()
        else:
            segment.requirements = dict(requirements)
        challenge.description = "DCP leído desde Companion y revisado por el usuario"
    record(db, "sync_dcp", "challenge", challenge.id, {"action": action, "segment_id": segment.id, "fields": sorted(requirements), "reviewed": True})
    db.commit()
    return {"challenge_id": challenge.id, "segment_id": segment.id, "action": action, "requirements": requirements, "requires_final_submission": True}

@router.post("/objectives/inspect")
def inspect_visible_objectives(db: DB):
    bridge, serial, size = ready_device(db)
    try:
        hierarchy = bridge.ui_hierarchy(serial)
    except AdbError as exc:
        raise HTTPException(503, str(exc)) from exc
    objectives = extract_accessibility_objectives(hierarchy)
    record(db, "inspect_objectives", "emulator", details={"detected": len(objectives), "image_saved": False}); db.commit()
    return {
        "objectives": objectives,
        "screen_size": size,
        "source": "accessibility",
        "saved": False,
        "requires_confirmation": True,
        "message": f"Se detectaron {len(objectives)} objetivos visibles" if objectives else "Abre la pantalla Objetivos de Companion y vuelve a leer",
    }

@router.post("/objectives/sync")
def sync_reviewed_objectives(payload: ObjectiveSyncRequest, db: DB):
    if payload.confirmation.strip().upper() != "ACTUALIZAR OBJETIVOS":
        raise HTTPException(422, "Escribe ACTUALIZAR OBJETIVOS para guardar los objetivos revisados")
    existing = {normalized_text(row.name): row for row in db.scalars(select(Objective)).all()}
    created = updated = 0
    synced: list[dict] = []
    seen: set[str] = set()
    for item in payload.objectives:
        identity = normalized_text(item.name)
        if identity in seen:
            continue
        seen.add(identity)
        objective = existing.get(identity)
        if objective is None:
            objective = Objective(name=item.name.strip(), description="Objetivo visible en Companion y revisado por el usuario")
            db.add(objective); created += 1
        else:
            updated += 1
        objective.progress = item.progress
        objective.target = item.target
        objective.category = item.category.strip()
        objective.completed = item.progress >= item.target
        synced.append({"name": objective.name, "progress": objective.progress, "target": objective.target, "category": objective.category})
    record(db, "sync_objectives", "objective", details={"created": created, "updated": updated, "reviewed": True}); db.commit()
    return {"created": created, "updated": updated, "objectives": synced, "missing_objectives_preserved": True}

@router.post("/tap")
def tap(payload: EmulatorTapRequest, db: DB):
    serial = connected_serial(db)
    try: AdbBridge().tap(serial, payload.x, payload.y)
    except AdbError as exc: raise HTTPException(503, str(exc)) from exc
    record(db, "tap", "emulator", details=payload.model_dump()); db.commit(); return {"ok": True}

@router.post("/swipe")
def swipe(payload: EmulatorSwipeRequest, db: DB):
    serial = connected_serial(db)
    try: AdbBridge().swipe(serial, **payload.model_dump())
    except AdbError as exc: raise HTTPException(503, str(exc)) from exc
    record(db, "swipe", "emulator", details=payload.model_dump()); db.commit(); return {"ok": True}

@router.get("/calibration")
def get_calibration(db: DB): return emulator_config(db).get("calibration")

@router.put("/calibration")
def set_calibration(payload: EmulatorCalibration, db: DB):
    config = emulator_config(db); config["calibration"] = payload.model_dump(); save_emulator_config(db, config)
    record(db, "calibrate", "emulator", details={"screen": [payload.screen_width, payload.screen_height]}); db.commit()
    return config["calibration"]

@router.get("/scans")
def list_inventory_scans(db: DB, limit: int = Query(20, ge=1, le=100)):
    summary_columns = (
        InventoryScan.id, InventoryScan.status, InventoryScan.device_serial, InventoryScan.screen_size,
        InventoryScan.captured_pages, InventoryScan.candidate_count, InventoryScan.imported_count,
        InventoryScan.last_error, InventoryScan.created_at, InventoryScan.imported_at,
    )
    rows = db.scalars(select(InventoryScan).options(load_only(*summary_columns)).order_by(InventoryScan.id.desc()).limit(limit)).all()
    return [scan_data(row) for row in rows]

@router.get("/scans/bulk-preview")
def inventory_bulk_preview(db: DB):
    preview, _ = bulk_inventory_preview(db)
    return preview

@router.post("/scans/reconcile")
def reconcile_pending_inventory(db: DB):
    blocked = all_player_identities(db)
    seen: set[tuple[str, int | None, str]] = set()
    removed_duplicates = removed_existing = 0
    for scan in open_inventory_scans(db):
        kept: list[dict] = []
        for candidate in list(scan.candidates or []):
            identity = candidate_identity(candidate)
            if not complete_candidate(candidate):
                kept.append(candidate)
            elif identity in blocked:
                removed_existing += 1
            elif identity in seen:
                removed_duplicates += 1
            else:
                seen.add(identity); kept.append(candidate)
        scan.candidates = kept
        scan.candidate_count = len(kept)
    record(db, "reconcile", "inventory_scan", details={"duplicates_removed": removed_duplicates, "registered_or_used_removed": removed_existing})
    db.commit()
    preview, _ = bulk_inventory_preview(db)
    return preview | {"duplicates_removed": removed_duplicates, "registered_or_used_removed": removed_existing}

@router.post("/scans/bulk-import")
def bulk_import_reviewed_inventory(payload: InventoryBulkImportRequest, db: DB):
    if payload.confirmation.strip().upper() != "IMPORTAR TODO EL CLUB":
        raise HTTPException(422, "Escribe IMPORTAR TODO EL CLUB para confirmar la carga completa revisada")
    preview, importable = bulk_inventory_preview(db)
    if not preview["sessions"]:
        raise HTTPException(409, "No hay lecturas pendientes para importar")
    if preview["detected"] > 5000:
        raise HTTPException(409, "Hay más de 5000 candidatos pendientes; cancela lecturas antiguas antes de continuar")
    imported_by_scan: dict[int, list[Player]] = {scan_id: [] for scan_id in preview["scan_ids"]}
    for scan, candidate, _ in importable:
        player = Player(
            name=str(candidate["name"]).strip()[:100], rating=int(candidate["rating"]),
            position=str(candidate["position"]).strip().upper()[:8], league="No disponible",
            club="No disponible", nationality="No disponible", card_type="Lectura Companion",
            rare=False, special=False, tradable=False, price=0, chemistry=0, protected=False,
            starter=False, squad_role="club", usefulness=0, duplicate_untradeable=False,
        )
        db.add(player); imported_by_scan[scan.id].append(player)
    db.flush()
    imported_ids: list[int] = []
    for scan in open_inventory_scans(db):
        players = imported_by_scan.get(scan.id, [])
        ids = [player.id for player in players]
        imported_ids.extend(ids)
        remaining = [candidate for candidate in list(scan.candidates or []) if not complete_candidate(candidate)]
        scan.candidates = remaining
        scan.candidate_count = len(remaining)
        scan.imported_player_ids = [*list(scan.imported_player_ids or []), *ids]
        scan.imported_count += len(ids)
        scan.status = "review" if remaining else "imported"
        scan.imported_at = datetime.now(timezone.utc) if not remaining else None
        record(db, "bulk_import", "inventory_scan", scan.id, {"imported": len(ids), "remaining": len(remaining), "reviewed": True})
    record(db, "bulk_import_all", "inventory", details={
        "imported": len(imported_ids), "duplicates_skipped": preview["duplicates"],
        "registered_or_used_skipped": preview["already_registered_or_used"], "incomplete_remaining": preview["incomplete"],
    })
    db.commit()
    return {
        "imported": len(imported_ids), "player_ids": imported_ids,
        "duplicates_skipped": preview["duplicates"],
        "registered_or_used_skipped": preview["already_registered_or_used"],
        "remaining_review": preview["incomplete"], "sessions_processed": preview["sessions"],
    }

@router.get("/scans/{scan_id}/candidates")
def list_inventory_scan_candidates(scan_id: int, db: DB, offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=50)):
    scan = db.scalar(
        select(InventoryScan)
        .options(load_only(InventoryScan.id, InventoryScan.candidate_count, InventoryScan.candidates))
        .where(InventoryScan.id == scan_id)
    )
    if not scan: raise HTTPException(404, "Lectura de inventario no encontrada")
    items = scan.candidates[offset:offset + limit]
    return {"scan_id": scan.id, "items": items, "total": scan.candidate_count, "offset": offset, "limit": limit}

@router.post("/scans", status_code=201)
def create_inventory_scan(db: DB):
    _, serial, size = ready_device(db)
    scan = InventoryScan(device_serial=serial, screen_size=list(size) if size else [], status="scanning")
    db.add(scan); db.flush(); record(db, "create", "inventory_scan", scan.id, {"device_serial": serial, "screen_size": scan.screen_size}); db.commit(); db.refresh(scan)
    return scan_data(scan)

@router.post("/scans/{scan_id}/continue", status_code=201)
def continue_inventory_scan(scan_id: int, db: DB):
    previous = db.get(InventoryScan, scan_id)
    if not previous: raise HTTPException(404, "Lectura de inventario no encontrada")
    if previous.status != "review" or (previous.captured_pages < 50 and previous.candidate_count < 1000):
        raise HTTPException(409, "La lectura actual todavía no alcanzó su límite")
    _, serial, size = ready_device(db)
    if serial != previous.device_serial or not size or list(size) != previous.screen_size:
        raise HTTPException(409, "Conecta el mismo dispositivo con la misma resolución")
    marker = f"continuation:{previous.capture_hashes[-1]}" if previous.capture_hashes else "continuation"
    scan = InventoryScan(device_serial=serial, screen_size=list(size), status="scanning", capture_hashes=[marker])
    db.add(scan); db.flush(); record(db, "continue", "inventory_scan", scan.id, {"previous_scan_id": previous.id, "starts_after_page": previous.captured_pages}); db.commit(); db.refresh(scan)
    return scan_data(scan)

@router.post("/scans/{scan_id}/capture")
def capture_inventory_page(scan_id: int, db: DB):
    scan = db.get(InventoryScan, scan_id)
    if not scan: raise HTTPException(404, "Lectura de inventario no encontrada")
    if scan.status in {"imported", "cancelled"}: raise HTTPException(409, "La lectura ya está cerrada")
    if scan.captured_pages >= 50 or scan.candidate_count >= 1000: raise HTTPException(409, "La lectura alcanzó su límite; revisa e importa antes de continuar")
    bridge, serial, size = ready_device(db)
    if serial != scan.device_serial: raise HTTPException(409, "Conecta el mismo dispositivo con el que comenzaste la lectura")
    if size and scan.screen_size and list(size) != scan.screen_size: raise HTTPException(409, "La resolución cambió durante la lectura")
    try: content = bridge.screenshot(serial)
    except AdbError as exc: raise HTTPException(503, str(exc)) from exc
    hierarchy = b""
    try: hierarchy = bridge.ui_hierarchy(serial)
    except (AdbError, AttributeError): pass
    page = scan.captured_pages + 1
    try: result = ocr_inventory(content, page, hierarchy) if hierarchy else ocr_inventory(content, page)
    except ValueError as exc: raise HTTPException(422, "No se pudo leer la captura") from exc
    if result.get("extraction_source") == "accessibility":
        signature = [[item.get("name"), item.get("rating"), item.get("position")] for item in result["candidates"]]
        digest = hashlib.sha256(json.dumps(signature, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    else:
        digest = hashlib.sha256(content).hexdigest()
    if digest in scan.capture_hashes:
        return {"scan": scan_data(scan), "raw_text": "", "duplicate_capture": True, "detected": 0}
    accepted, skipped = unique_new_candidates(db, list(result["candidates"]), scan.id)
    current = list(scan.candidates); next_id = max((int(item.get("candidate_id", 0)) for item in current), default=0) + 1
    detected = []
    for offset, candidate in enumerate(accepted[:1000-len(current)]): detected.append({**candidate, "candidate_id": next_id + offset})
    scan.candidates = [*current, *detected]; scan.candidate_count = len(scan.candidates); scan.capture_hashes = [*scan.capture_hashes, digest]; scan.captured_pages = page; scan.status = "review"; scan.last_error = None if detected else ("Las cartas detectadas ya estaban registradas o pendientes" if skipped else "No se detectaron cartas fiables en esta pantalla")
    record(db, "capture", "inventory_scan", scan.id, {"page": page, "detected": len(detected), "duplicates_skipped": skipped, "image_saved": False, "source": result.get("extraction_source", "ocr")}); db.commit()
    return {"scan": scan_data(scan), "raw_text": result["raw_text"], "duplicate_capture": False, "detected": len(detected), "duplicates_skipped": skipped}

@router.post("/scans/{scan_id}/observe")
def observe_visible_inventory_page(scan_id: int, db: DB):
    scan = db.get(InventoryScan, scan_id)
    if not scan: raise HTTPException(404, "Lectura de inventario no encontrada")
    if scan.status in {"imported", "cancelled"}: raise HTTPException(409, "La lectura ya está cerrada")
    if scan.captured_pages >= 50 or scan.candidate_count >= 1000:
        raise HTTPException(409, "La lectura alcanzó su límite; revisa e importa antes de continuar")
    bridge, serial, size = ready_device(db)
    if serial != scan.device_serial: raise HTTPException(409, "Conecta el mismo dispositivo con el que comenzaste la lectura")
    if not size or list(size) != scan.screen_size: raise HTTPException(409, "La resolución cambió durante la lectura")
    try: hierarchy = bridge.ui_hierarchy(serial)
    except AdbError as exc: raise HTTPException(503, str(exc)) from exc
    page = scan.captured_pages + 1
    visible = extract_accessibility_inventory_candidates(hierarchy, page)
    if not visible:
        return {"scan": scan_data(scan), "detected": 0, "duplicate_capture": False, "visible_inventory": False, "source": "accessibility", "message": "Abre Mi club → Futbolistas y vuelve a pulsar Actualizar desde Companion"}
    signature = [[item["name"], item["rating"], item["position"]] for item in visible]
    digest = hashlib.sha256(json.dumps(signature, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    if digest in scan.capture_hashes:
        return {"scan": scan_data(scan), "detected": 0, "duplicate_capture": True, "visible_inventory": True, "source": "accessibility", "message": "Pantalla visible sin cambios"}
    accepted, skipped = unique_new_candidates(db, visible, scan.id)
    current = list(scan.candidates)
    next_id = max((int(item.get("candidate_id", 0)) for item in current), default=0) + 1
    additions = [{**candidate, "candidate_id": next_id + offset} for offset, candidate in enumerate(accepted[:1000-len(current)])]
    scan.candidates = [*current, *additions]
    scan.candidate_count = len(scan.candidates)
    scan.capture_hashes = [*scan.capture_hashes, digest]
    scan.captured_pages = page
    scan.status = "review"
    scan.last_error = None
    record(db, "observe_capture", "inventory_scan", scan.id, {"page": page, "detected": len(additions), "duplicates_skipped": skipped, "image_saved": False, "source": "accessibility", "manual": True})
    db.commit()
    message = f"Se detectaron {len(additions)} cartas nuevas para revisar"
    if skipped:
        message += f"; {skipped} ya estaban registradas o pendientes"
    return {"scan": scan_data(scan), "detected": len(additions), "duplicates_skipped": skipped, "duplicate_capture": False, "visible_inventory": True, "source": "accessibility", "message": message}

@router.post("/scans/{scan_id}/advance")
def advance_inventory_page(scan_id: int, db: DB):
    scan = db.get(InventoryScan, scan_id)
    if not scan: raise HTTPException(404, "Lectura de inventario no encontrada")
    if scan.status in {"imported", "cancelled"}: raise HTTPException(409, "La lectura ya está cerrada")
    is_continuation = scan.captured_pages == 0 and any(value.startswith("continuation") for value in scan.capture_hashes)
    if scan.captured_pages < 1 and not is_continuation: raise HTTPException(409, "Lee primero la página actual")
    if scan.captured_pages >= 50 or scan.candidate_count >= 1000: raise HTTPException(409, "La lectura alcanzó su límite; revisa e importa antes de continuar")
    bridge, serial, size = ready_device(db)
    if serial != scan.device_serial: raise HTTPException(409, "Conecta el mismo dispositivo con el que comenzaste la lectura")
    if not size or list(size) != scan.screen_size: raise HTTPException(409, "La resolución cambió durante la lectura")
    page = scan.captured_pages + 1
    try:
        before = extract_accessibility_inventory_candidates(bridge.ui_hierarchy(serial), max(1, scan.captured_pages))
        if not before: raise AdbError("Abre Mi club → Futbolistas antes de avanzar")
        bridge.scroll_inventory_list_to_end(serial, *size)
        bottom = bridge.ui_hierarchy(serial)
        bounds = find_accessibility_inventory_action(bottom, "Siguiente")
        if not bounds: raise AdbError("No se encontró un botón Siguiente seguro y habilitado")
        x1, y1, x2, y2 = bounds
        if x1 < int(size[0] * 0.6) or x2 > size[0] or y1 < int(size[1] * 0.75) or y2 > size[1]:
            raise AdbError("El botón Siguiente no está en la zona segura esperada")
        bridge.tap(serial, (x1 + x2) // 2, (y1 + y2) // 2)
        detected = []
        for _ in range(3):
            time.sleep(0.6)
            detected = extract_accessibility_inventory_candidates(bridge.ui_hierarchy(serial), page)
            if detected and [(item["name"], item["rating"], item["position"]) for item in detected] != [(item["name"], item["rating"], item["position"]) for item in before]: break
        else: raise AdbError("La página no cambió después de pulsar Siguiente")
    except AdbError as exc: raise HTTPException(409, str(exc)) from exc
    signature = [[item["name"], item["rating"], item["position"]] for item in detected]
    digest = hashlib.sha256(json.dumps(signature, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    if digest in scan.capture_hashes: raise HTTPException(409, "La página detectada ya forma parte de esta lectura")
    accepted, skipped = unique_new_candidates(db, detected, scan.id)
    current = list(scan.candidates); next_id = max((int(item.get("candidate_id", 0)) for item in current), default=0) + 1
    additions = [{**candidate, "candidate_id": next_id + offset} for offset, candidate in enumerate(accepted[:1000-len(current)])]
    scan.candidates = [*current, *additions]; scan.candidate_count = len(scan.candidates); scan.capture_hashes = [*scan.capture_hashes, digest]; scan.captured_pages = page; scan.status = "review"; scan.last_error = None
    record(db, "advance_capture", "inventory_scan", scan.id, {"page": page, "detected": len(additions), "duplicates_skipped": skipped, "image_saved": False, "source": "accessibility", "navigation_validated": True}); db.commit()
    return {"scan": scan_data(scan), "duplicate_capture": False, "detected": len(additions), "duplicates_skipped": skipped}

@router.post("/scans/{scan_id}/import")
def import_inventory_scan(scan_id: int, payload: InventoryScanImportRequest, db: DB):
    scan = db.get(InventoryScan, scan_id)
    if not scan: raise HTTPException(404, "Lectura de inventario no encontrada")
    if scan.status in {"imported", "cancelled"}: raise HTTPException(409, "La lectura ya está cerrada")
    expected = f"REEMPLAZAR DEMO {scan.id}" if payload.archive_demo else f"IMPORTAR {scan.id}"
    if payload.confirmation.strip().upper() != expected: raise HTTPException(422, "La frase de confirmación no coincide")
    available_ids = {int(item.get("candidate_id", 0)) for item in scan.candidates}
    if any(candidate_id not in available_ids for candidate_id in payload.candidate_ids):
        raise HTTPException(422, "Uno o más candidatos ya no están disponibles en esta lectura")
    archived = 0
    if payload.archive_demo:
        demo_rows = db.scalars(select(Player).where(Player.name.in_(demo_player_names()), Player.deleted.is_(False))).all()
        for player in demo_rows: player.deleted = True; player.duplicate_untradeable = False
        archived = len(demo_rows)
    existing_identities = all_player_identities(db)
    seen_payload: set[tuple[str, int | None, str]] = set()
    imported: list[Player] = []
    for item in payload.players:
        identity = candidate_identity(item.model_dump())
        if identity in existing_identities or identity in seen_payload:
            continue
        seen_payload.add(identity)
        player = Player(**item.model_dump()); db.add(player); imported.append(player)
    db.flush()
    selected_ids = set(payload.candidate_ids)
    selected_identities = {candidate_identity(item) for item in scan.candidates if int(item.get("candidate_id", 0)) in selected_ids}
    scan.candidates = [item for item in scan.candidates if int(item.get("candidate_id", 0)) not in selected_ids]
    scan.candidate_count = len(scan.candidates)
    scan.imported_player_ids = [*scan.imported_player_ids, *[player.id for player in imported]]
    scan.imported_count += len(imported)
    scan.status = "imported" if not scan.candidates else "review"
    scan.imported_at = datetime.now(timezone.utc) if scan.status == "imported" else None
    removed_elsewhere = remove_pending_identities(db, selected_identities, exclude_scan_id=scan.id)
    skipped = len(payload.players) - len(imported)
    record(db, "import", "inventory_scan", scan.id, {"imported": len(imported), "duplicates_skipped": skipped, "removed_elsewhere": removed_elsewhere, "remaining": scan.candidate_count, "demo_archived": archived, "reviewed": True}); db.commit()
    return {"imported": len(imported), "duplicates_skipped": skipped, "removed_elsewhere": removed_elsewhere, "demo_archived": archived, "player_ids": scan.imported_player_ids, "scan": scan_data(scan)}

@router.post("/scans/{scan_id}/cancel")
def cancel_inventory_scan(scan_id: int, db: DB):
    scan = db.get(InventoryScan, scan_id)
    if not scan: raise HTTPException(404, "Lectura de inventario no encontrada")
    if scan.status == "imported": raise HTTPException(409, "La lectura ya fue importada")
    scan.status = "cancelled"; record(db, "cancel", "inventory_scan", scan.id); db.commit()
    return scan_data(scan)

@router.get("/plans")
def list_plans(db: DB, limit: int = Query(30, ge=1, le=100)):
    return [plan_data(row) for row in db.scalars(select(AutomationPlan).order_by(AutomationPlan.id.desc()).limit(limit)).all()]

@router.post("/plans", status_code=201)
def create_plan(payload: AutomationPlanCreate, db: DB):
    if len(set(payload.player_ids)) != len(payload.player_ids): raise HTTPException(422, "La combinación contiene jugadores repetidos")
    segment = db.get(Segment, payload.segment_id)
    if not segment: raise HTTPException(404, "Segmento no encontrado")
    players = db.scalars(select(Player).where(Player.id.in_(payload.player_ids), Player.deleted.is_(False))).all()
    if len(players) != len(payload.player_ids): raise HTTPException(422, "Uno o más jugadores no están disponibles")
    if any(player.protected for player in players): raise HTTPException(422, "La combinación contiene cartas protegidas")
    violations = validate_solution(players, segment.requirements)
    if violations: raise HTTPException(422, {"message": "La combinación dejó de ser válida", "violations": violations})
    ordered = sorted(players, key=lambda p: payload.player_ids.index(p.id))
    snapshot = {"players": [{"id": p.id, "name": p.name, "rating": p.rating, "position": p.position, "protected": p.protected, "duplicate": p.duplicate_untradeable} for p in ordered], "requirements": segment.requirements, "validated": True, "delivery_requires_manual_confirmation": True}
    plan = AutomationPlan(name=f"Preparar {segment.name}", segment_id=segment.id, player_ids=payload.player_ids, solution_snapshot=snapshot, status="draft")
    db.add(plan); db.flush(); record(db, "create", "automation_plan", plan.id, {"segment_id": segment.id}); db.commit(); db.refresh(plan)
    return plan_data(plan)

@router.post("/plans/{plan_id}/prepare")
def prepare_plan(plan_id: int, db: DB):
    plan = db.get(AutomationPlan, plan_id)
    if not plan: raise HTTPException(404, "Plan no encontrado")
    if plan.status in {"running", "completed"}: raise HTTPException(409, "El plan ya no se puede preparar")
    config = emulator_config(db); calibration = config.get("calibration")
    if not calibration: raise HTTPException(409, "Calibra primero las coordenadas del emulador")
    validate_current_plan_solution(db, plan)
    plan.solution_snapshot = {**plan.solution_snapshot, "calibration": calibration}
    plan.steps = build_dcp_steps(calibration, plan.solution_snapshot["players"]); plan.device_serial = connected_serial(db); plan.status = "prepared"; plan.progress_step = 0; plan.last_error = None
    record(db, "prepare", "automation_plan", plan.id, {"steps": len(plan.steps)}); db.commit(); return plan_data(plan)

def execute_automation_plan(plan_id: int):
    db = SessionLocal()
    try:
        plan = db.get(AutomationPlan, plan_id)
        if not plan or plan.status != "queued": return
        plan.status = "running"; db.commit()
        bridge = AdbBridge()
        calibration = plan.solution_snapshot.get("calibration", {})
        expected_size = (calibration.get("screen_width"), calibration.get("screen_height"))
        actual_size = bridge.screen_size(plan.device_serial or "")
        if actual_size != expected_size:
            raise AdbError(f"La resolución cambió: esperada {expected_size[0]}x{expected_size[1]}, actual {actual_size}")
        for index, step in enumerate(plan.steps, 1):
            db.refresh(plan)
            if plan.status == "cancelled": return
            run_step(bridge, plan.device_serial or "", step)
            plan.progress_step = index
            record(db, "execute_step", "automation_plan", plan.id, {"step": index, "action": step.get("action"), "label": step.get("label")})
            db.commit()
        plan.status = "completed"; plan.executed_at = datetime.now(timezone.utc); db.commit()
    except Exception as exc:
        plan = db.get(AutomationPlan, plan_id)
        if plan:
            plan.status = "failed"; plan.last_error = str(exc)[:500]
            record(db, "execute_failed", "automation_plan", plan.id, {"error": plan.last_error})
            db.commit()
    finally: db.close()

@router.post("/plans/{plan_id}/execute")
def execute_plan(plan_id: int, payload: AutomationExecuteRequest, background: BackgroundTasks, db: DB):
    plan = db.get(AutomationPlan, plan_id)
    if not plan: raise HTTPException(404, "Plan no encontrado")
    if plan.status != "prepared": raise HTTPException(409, "El plan debe estar preparado")
    if payload.confirmation.strip().upper() != f"PREPARAR {plan.id}": raise HTTPException(422, "La frase de confirmación no coincide")
    validate_current_plan_solution(db, plan)
    serial = plan.device_serial or ""
    active = db.scalar(select(AutomationPlan.id).where(AutomationPlan.id != plan.id, AutomationPlan.device_serial == serial, AutomationPlan.status.in_(["queued", "running"])).limit(1))
    if active: raise HTTPException(409, f"El dispositivo ya está ejecutando el plan {active}")
    try:
        bridge = AdbBridge(); devices = bridge.devices()
        if not any(item["serial"] == serial and item["state"] == "device" for item in devices):
            raise AdbError("El dispositivo configurado no está conectado")
        calibration = plan.solution_snapshot.get("calibration", {})
        expected_size = (calibration.get("screen_width"), calibration.get("screen_height"))
        actual_size = bridge.screen_size(serial)
        if actual_size != expected_size:
            raise AdbError(f"La resolución no coincide con la calibración: esperada {expected_size[0]}x{expected_size[1]}, actual {actual_size}")
    except AdbError as exc: raise HTTPException(409, str(exc)) from exc
    plan.status = "queued"; plan.approved_at = datetime.now(timezone.utc); record(db, "approve", "automation_plan", plan.id); db.commit()
    background.add_task(execute_automation_plan, plan.id)
    return {"queued": True, "plan_id": plan.id, "final_submission_automated": False}

@router.post("/plans/{plan_id}/cancel")
def cancel_plan(plan_id: int, db: DB):
    plan = db.get(AutomationPlan, plan_id)
    if not plan: raise HTTPException(404, "Plan no encontrado")
    if plan.status == "completed": raise HTTPException(409, "El plan ya terminó")
    plan.status = "cancelled"; record(db, "cancel", "automation_plan", plan.id); db.commit(); return plan_data(plan)
