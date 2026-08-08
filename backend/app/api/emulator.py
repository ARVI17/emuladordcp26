import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import SessionLocal, get_db
from app.models.entities import AppSetting, AutomationPlan, InventoryScan, Player, Segment
from app.optimizers.sbc import validate_solution
from app.schemas.api import AutomationExecuteRequest, AutomationPlanCreate, EmulatorCalibration, EmulatorConnectRequest, EmulatorPairRequest, EmulatorSelectRequest, EmulatorSwipeRequest, EmulatorTapRequest, InventoryScanImportRequest
from app.services.adb import AdbBridge, AdbError, build_dcp_steps, run_step
from app.services.audit import record
from app.services.import_export import extract_accessibility_inventory_candidates, find_accessibility_inventory_action, ocr_image, ocr_inventory, parse_dcp_requirements
from app.db.seed import demo_player_names

router = APIRouter(prefix="/emulator", tags=["Emulador asistido"])
DB = Annotated[Session, Depends(get_db)]

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
    return {key: getattr(scan, key) for key in ("id", "status", "device_serial", "screen_size", "captured_pages", "candidates", "imported_player_ids", "imported_count", "last_error", "created_at", "imported_at")} | {
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
    try: output = AdbBridge().connect(payload.address)
    except AdbError as exc: raise HTTPException(503, str(exc)) from exc
    config = emulator_config(db); config.update({"address": payload.address, "serial": payload.address}); save_emulator_config(db, config)
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
    rows = db.scalars(select(InventoryScan).order_by(InventoryScan.id.desc()).limit(limit)).all()
    return [scan_data(row) for row in rows]

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
    if previous.status != "review" or (previous.captured_pages < 50 and len(previous.candidates) < 1000):
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
    if scan.captured_pages >= 50 or len(scan.candidates) >= 1000: raise HTTPException(409, "La lectura alcanzó su límite; revisa e importa antes de continuar")
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
    current = list(scan.candidates); next_id = max((int(item.get("candidate_id", 0)) for item in current), default=0) + 1
    detected = []
    for offset, candidate in enumerate(result["candidates"][:1000-len(current)]): detected.append({**candidate, "candidate_id": next_id + offset})
    scan.candidates = [*current, *detected]; scan.capture_hashes = [*scan.capture_hashes, digest]; scan.captured_pages = page; scan.status = "review"; scan.last_error = None if detected else "No se detectaron cartas fiables en esta pantalla"
    record(db, "capture", "inventory_scan", scan.id, {"page": page, "detected": len(detected), "image_saved": False, "source": result.get("extraction_source", "ocr")}); db.commit()
    return {"scan": scan_data(scan), "raw_text": result["raw_text"], "duplicate_capture": False, "detected": len(detected)}

@router.post("/scans/{scan_id}/advance")
def advance_inventory_page(scan_id: int, db: DB):
    scan = db.get(InventoryScan, scan_id)
    if not scan: raise HTTPException(404, "Lectura de inventario no encontrada")
    if scan.status in {"imported", "cancelled"}: raise HTTPException(409, "La lectura ya está cerrada")
    is_continuation = scan.captured_pages == 0 and any(value.startswith("continuation") for value in scan.capture_hashes)
    if scan.captured_pages < 1 and not is_continuation: raise HTTPException(409, "Lee primero la página actual")
    if scan.captured_pages >= 50 or len(scan.candidates) >= 1000: raise HTTPException(409, "La lectura alcanzó su límite; revisa e importa antes de continuar")
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
    current = list(scan.candidates); next_id = max((int(item.get("candidate_id", 0)) for item in current), default=0) + 1
    additions = [{**candidate, "candidate_id": next_id + offset} for offset, candidate in enumerate(detected[:1000-len(current)])]
    scan.candidates = [*current, *additions]; scan.capture_hashes = [*scan.capture_hashes, digest]; scan.captured_pages = page; scan.status = "review"; scan.last_error = None
    record(db, "advance_capture", "inventory_scan", scan.id, {"page": page, "detected": len(additions), "image_saved": False, "source": "accessibility", "navigation_validated": True}); db.commit()
    return {"scan": scan_data(scan), "duplicate_capture": False, "detected": len(additions)}

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
    imported: list[Player] = []
    for item in payload.players:
        player = Player(**item.model_dump()); db.add(player); imported.append(player)
    db.flush()
    selected_ids = set(payload.candidate_ids)
    scan.candidates = [item for item in scan.candidates if int(item.get("candidate_id", 0)) not in selected_ids]
    scan.imported_player_ids = [*scan.imported_player_ids, *[player.id for player in imported]]
    scan.imported_count += len(imported)
    scan.status = "imported" if not scan.candidates else "review"
    scan.imported_at = datetime.now(timezone.utc) if scan.status == "imported" else None
    record(db, "import", "inventory_scan", scan.id, {"imported": len(imported), "remaining": len(scan.candidates), "demo_archived": archived, "reviewed": True}); db.commit()
    return {"imported": len(imported), "demo_archived": archived, "player_ids": scan.imported_player_ids, "scan": scan_data(scan)}

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
