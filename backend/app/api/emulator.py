import hashlib
import json
import logging
import time
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal, get_db
from app.models.entities import AppSetting, AutomationPlan, Challenge, InventoryScan, Player, Segment
from app.optimizers.sbc import validate_solution
from app.schemas.api import AutomationExecuteRequest, AutomationPlanCreate, EmulatorCalibration, EmulatorConnectRequest, EmulatorPairRequest, EmulatorSelectRequest, EmulatorSwipeRequest, EmulatorTapRequest, InventoryScanImportRequest
from app.services.adb import AdbBridge, AdbError, build_dcp_steps, run_step
from app.services.audit import record
from app.services.editions import current_version
from app.services.import_export import extract_accessibility_inventory_candidates, find_accessibility_inventory_action, ocr_image, ocr_inventory, review_dcp_requirements
from app.services.locks import ResourceBusy, resource_locks
from app.services.squad_analysis import effective_protected_ids

router = APIRouter(prefix="/emulator", tags=["Emulador asistido"])
DB = Annotated[Session, Depends(get_db)]
logger = logging.getLogger(__name__)
ACTIVE_PLAN_STATES = {"queued", "running"}
OPEN_SCAN_STATES = {"scanning", "review"}
PLAYER_SNAPSHOT_FIELDS = ("id", "name", "rating", "position", "league", "club", "nationality", "card_type", "rare", "special", "game_version", "card_id", "is_loan", "is_evolution", "is_holographic")
PLACEHOLDER_VALUES = {"por revisar", "revisar", "pendiente", "sin revisar", "desconocido", "n/a"}


@contextmanager
def operation(db: Session, *keys: str, blocking: bool = True):
    try:
        with resource_locks(db, *keys, blocking=blocking):
            db.expire_all()
            yield
    except ResourceBusy as exc:
        raise HTTPException(409, str(exc)) from exc


def emulator_config(db: Session) -> dict:
    row = db.get(AppSetting, "emulator")
    return dict(row.value) if row else {"address": settings.adb_default_address, "calibration": None}


def save_emulator_config(db: Session, value: dict):
    row = db.get(AppSetting, "emulator")
    if row:
        row.value = dict(value)
    else:
        db.add(AppSetting(key="emulator", value=dict(value)))


def connected_serial(db: Session) -> str:
    config = emulator_config(db)
    serial = config.get("serial") or config.get("address")
    if not serial:
        raise HTTPException(409, "Configura y conecta un dispositivo ADB")
    return serial


def plan_data(plan: AutomationPlan) -> dict:
    return {key: getattr(plan, key) for key in ("id", "name", "plan_type", "status", "device_serial", "segment_id", "player_ids", "solution_snapshot", "steps", "progress_step", "last_error", "approved_at", "executed_at", "created_at", "execution_generation", "worker_active")} | {
        "confirmation_phrase": f"PREPARAR {plan.id}" if plan.status == "prepared" else None,
        "final_submission_automated": False,
        "can_prepare": not plan.worker_active and plan.status in {"draft", "prepared", "failed", "cancelled"},
    }


def scan_data(scan: InventoryScan) -> dict:
    return {key: getattr(scan, key) for key in ("id", "status", "game_version", "device_serial", "screen_size", "captured_pages", "candidates", "imported_player_ids", "imported_count", "last_error", "created_at", "imported_at", "source_scan_id", "next_candidate_id")} | {
        "confirmation_phrase": f"IMPORTAR {scan.id}",
        "archive_demo_phrase": f"REEMPLAZAR DEMO {scan.id}",
        "images_saved": False,
        "requires_review": True,
        "is_active": scan.status in OPEN_SCAN_STATES,
        "can_capture": scan.status in OPEN_SCAN_STATES and not scan_at_capacity(scan),
        "can_continue": scan.status in {"review", "imported"} and scan_at_capacity(scan),
    }


def scan_at_capacity(scan: InventoryScan) -> bool:
    return scan.captured_pages >= 50 or scan.next_candidate_id > 1000


def ready_serial(serial: str) -> tuple[AdbBridge, tuple[int, int]]:
    bridge = AdbBridge()
    try:
        devices = bridge.devices()
        if not any(item["serial"] == serial and item["state"] == "device" for item in devices):
            raise AdbError("El dispositivo configurado no está conectado")
        size = bridge.screen_size(serial)
        if not size or min(size) <= 0:
            raise AdbError("No se pudo comprobar la resolución del dispositivo")
        return bridge, size
    except AdbError as exc:
        raise HTTPException(409, str(exc)) from exc


def ready_device(db: Session) -> tuple[AdbBridge, str, tuple[int, int]]:
    serial = connected_serial(db)
    bridge, size = ready_serial(serial)
    return bridge, serial, size


def assert_device_idle(db: Session, serial: str, excluding_plan: int | None = None):
    query = select(AutomationPlan.id).where(
        AutomationPlan.device_serial == serial,
        or_(AutomationPlan.status.in_(ACTIVE_PLAN_STATES), AutomationPlan.worker_active.is_(True)),
    )
    if excluding_plan is not None:
        query = query.where(AutomationPlan.id != excluding_plan)
    active = db.scalar(query.limit(1))
    if active:
        raise HTTPException(409, f"El dispositivo está reservado por el plan {active}")


def _snapshot(players, segment: Segment) -> dict:
    return {
        "players": [{field: getattr(player, field) for field in PLAYER_SNAPSHOT_FIELDS} | {"protected": player.protected, "duplicate": player.duplicate_untradeable} for player in players],
        "requirements": deepcopy(segment.requirements),
        "game_version": segment.challenge.game_version,
        "validated": True,
        "delivery_requires_manual_confirmation": True,
    }


def validate_current_plan_solution(db: Session, plan: AutomationPlan, *, compare_snapshot: bool = False):
    if len(set(plan.player_ids)) != len(plan.player_ids):
        raise HTTPException(422, "La combinación contiene jugadores repetidos")
    segment = db.get(Segment, plan.segment_id)
    if not segment:
        raise HTTPException(404, "Segmento no encontrado")
    edition = current_version(db)
    if segment.challenge.game_version != edition:
        raise HTTPException(409, "El plan pertenece a otra edición del juego")
    if segment.completed:
        raise HTTPException(409, "El segmento ya fue completado")
    if segment.requirements.get("kind") == "score":
        raise HTTPException(409, "La preparación ADB admite únicamente DCP tradicionales; la entrega por puntuación requiere preparación manual")
    players = db.scalars(select(Player).where(Player.id.in_(plan.player_ids), Player.deleted.is_(False), Player.game_version == edition)).all()
    if len(players) != len(plan.player_ids):
        raise HTTPException(422, "Uno o más jugadores ya no están disponibles en esta edición")
    protected = effective_protected_ids(db, edition)
    if any(player.id in protected for player in players):
        raise HTTPException(422, "La combinación contiene cartas protegidas")
    if any(player.is_loan for player in players):
        raise HTTPException(422, "La combinación contiene cartas cedidas")
    violations = validate_solution(players, segment.requirements)
    if violations:
        raise HTTPException(422, {"message": "La combinación dejó de ser válida", "violations": violations})
    by_id = {player.id: player for player in players}
    ordered = [by_id[player_id] for player_id in plan.player_ids]
    if compare_snapshot:
        snapshot = plan.solution_snapshot
        current = _snapshot(ordered, segment)
        comparable = lambda rows: [{field: row.get(field) for field in PLAYER_SNAPSHOT_FIELDS} for row in rows]
        if snapshot.get("requirements") != current["requirements"] or comparable(snapshot.get("players", [])) != comparable(current["players"]):
            raise HTTPException(409, "Las cartas o requisitos cambiaron; vuelve a preparar y revisar el plan")
    return ordered, segment


def _scan(db: Session, scan_id: int, *, closed: bool = False) -> InventoryScan:
    scan = db.get(InventoryScan, scan_id, populate_existing=True)
    if not scan:
        raise HTTPException(404, "Lectura de inventario no encontrada")
    if scan.game_version != current_version(db):
        raise HTTPException(409, "La lectura pertenece a otra edición del juego")
    if not closed and scan.status not in OPEN_SCAN_STATES:
        raise HTTPException(409, "La lectura ya está cerrada; inicia o continúa otro lote")
    return scan


def _scan_serial(db: Session, scan_id: int) -> str:
    scan = _scan(db, scan_id, closed=True)
    serial = scan.device_serial
    # Do not retain a read transaction while waiting for an I/O reservation.
    db.rollback()
    return serial


def _same_scan_device(db: Session, scan: InventoryScan) -> tuple[AdbBridge, tuple[int, int]]:
    if connected_serial(db) != scan.device_serial:
        raise HTTPException(409, "Conecta el mismo dispositivo con el que comenzaste la lectura")
    assert_device_idle(db, scan.device_serial)
    bridge, size = ready_serial(scan.device_serial)
    if list(size) != scan.screen_size:
        raise HTTPException(409, "La resolución cambió durante la lectura")
    return bridge, size


def _signature(candidates: list[dict]) -> str:
    values = [[item.get("name"), item.get("rating"), item.get("position")] for item in candidates]
    return hashlib.sha256(json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def _append_page(scan: InventoryScan, candidates: list[dict], digest: str, page: int):
    if digest in scan.capture_hashes or digest == scan.last_page_hash:
        return None
    # A migrated scan can already contain higher IDs than its initial counter.
    next_id = max(scan.next_candidate_id, scan.imported_count + len(scan.candidates) + 1, max((int(item.get("candidate_id", 0)) + 1 for item in scan.candidates), default=1))
    additions = []
    for candidate in candidates:
        if next_id > 1000:
            break
        if type(candidate.get("rating")) is not int or not 1 <= candidate["rating"] <= 99:
            continue
        if not str(candidate.get("name", "")).strip() or not str(candidate.get("position", "")).strip():
            continue
        additions.append({**candidate, "candidate_id": next_id, "game_version": scan.game_version, "source_page": page})
        next_id += 1
    scan.next_candidate_id = next_id
    scan.candidates = [*scan.candidates, *additions]
    scan.capture_hashes = [*scan.capture_hashes, digest]
    scan.last_page_hash = digest
    scan.captured_pages = page
    scan.status = "review"
    scan.last_error = None if additions else "No se detectaron cartas fiables; revisa la pantalla antes de avanzar"
    return additions


@router.get("/status")
def status(db: DB):
    config = emulator_config(db)
    if not settings.adb_enabled:
        return {"enabled": False, "available": False, "devices": [], "config": config, "message": "ADB está desactivado"}
    try:
        devices = AdbBridge().devices()
        serial = config.get("serial") or config.get("address")
        ready = any(item["serial"] == serial and item["state"] == "device" for item in devices)
        return {"enabled": True, "available": ready, "devices": devices, "config": config, "message": None if ready else "Selecciona un emulador o teléfono ADB conectado."}
    except AdbError as exc:
        return {"enabled": True, "available": False, "devices": [], "config": config, "message": str(exc)}


@router.post("/connect")
def connect(payload: EmulatorConnectRequest, db: DB):
    with operation(db, "emulator-config"):
        try:
            output = AdbBridge().connect(payload.address)
        except AdbError as exc:
            raise HTTPException(503, str(exc)) from exc
        config = emulator_config(db)
        if config.get("serial") != payload.address:
            config["calibration"] = None
        config.update({"address": payload.address, "serial": payload.address})
        save_emulator_config(db, config)
        record(db, "connect", "emulator", details={"address": payload.address})
        db.commit()
        return {"connected": True, "address": payload.address, "output": output}


@router.post("/pair")
def pair(payload: EmulatorPairRequest, db: DB):
    try:
        output = AdbBridge().pair(payload.address, payload.pairing_code)
    except AdbError as exc:
        raise HTTPException(503, str(exc).replace(payload.pairing_code, "[redactado]")) from None
    record(db, "pair", "emulator", details={"address": payload.address, "pairing_code_stored": False})
    db.commit()
    return {"paired": True, "address": payload.address, "output": output.replace(payload.pairing_code, "[redactado]"), "pairing_code_stored": False}


@router.post("/select")
def select_device(payload: EmulatorSelectRequest, db: DB):
    with operation(db, "emulator-config"):
        try:
            devices = AdbBridge().devices()
        except AdbError as exc:
            raise HTTPException(503, str(exc)) from exc
        if not any(item["serial"] == payload.serial and item["state"] == "device" for item in devices):
            raise HTTPException(409, "El dispositivo ADB seleccionado no está disponible")
        config = emulator_config(db)
        if config.get("serial") != payload.serial:
            config["calibration"] = None
        config["serial"] = payload.serial
        save_emulator_config(db, config)
        record(db, "select", "emulator", details={"serial": payload.serial})
        db.commit()
        return {"selected": True, "serial": payload.serial}


@router.get("/screenshot")
def screenshot(db: DB):
    serial = connected_serial(db)
    try:
        content = AdbBridge().screenshot(serial)
    except AdbError as exc:
        raise HTTPException(503, str(exc)) from exc
    return Response(content, media_type="image/png", headers={"Cache-Control": "no-store"})


@router.post("/inspect")
def inspect_screen(db: DB):
    serial = connected_serial(db)
    with operation(db, f"device:{serial}", blocking=False):
        assert_device_idle(db, serial)
        try:
            bridge, size = ready_serial(serial)
            result = ocr_image(bridge.screenshot(serial))
        except (AdbError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc
        return result | {"screen_size": size, "source": "ADB", "saved": False}


@router.post("/dcp/inspect")
def inspect_dcp_screen(db: DB):
    serial = connected_serial(db)
    with operation(db, f"device:{serial}", blocking=False):
        assert_device_idle(db, serial)
        bridge, size = ready_serial(serial)
        try:
            result = ocr_image(bridge.screenshot(serial))
        except (AdbError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc
        review = review_dcp_requirements(result["raw_text"])
        record(db, "inspect_dcp", "emulator", details={"detected_fields": sorted(review["requirements"]), "requires_human_review": True})
        db.commit()
        return result | {"screen_size": size, "source": "ADB", "saved": False, "detected_requirements": review["requirements"], "review_warnings": review["warnings"], "requires_confirmation": True, "requires_human_review": True}


@router.post("/tap")
def tap(payload: EmulatorTapRequest, db: DB):
    serial = connected_serial(db)
    with operation(db, f"device:{serial}", blocking=False):
        assert_device_idle(db, serial)
        bridge, size = ready_serial(serial)
        if not 0 <= payload.x < size[0] or not 0 <= payload.y < size[1]:
            raise HTTPException(422, "Las coordenadas quedan fuera de la pantalla")
        try:
            bridge.tap(serial, payload.x, payload.y)
        except AdbError as exc:
            raise HTTPException(503, str(exc)) from exc
        record(db, "tap", "emulator", details=payload.model_dump() | {"serial": serial})
        db.commit()
        return {"ok": True}


@router.post("/swipe")
def swipe(payload: EmulatorSwipeRequest, db: DB):
    serial = connected_serial(db)
    with operation(db, f"device:{serial}", blocking=False):
        assert_device_idle(db, serial)
        bridge, size = ready_serial(serial)
        if any(not 0 <= x < size[0] for x in (payload.x1, payload.x2)) or any(not 0 <= y < size[1] for y in (payload.y1, payload.y2)):
            raise HTTPException(422, "Las coordenadas quedan fuera de la pantalla")
        try:
            bridge.swipe(serial, **payload.model_dump())
        except AdbError as exc:
            raise HTTPException(503, str(exc)) from exc
        record(db, "swipe", "emulator", details=payload.model_dump() | {"serial": serial})
        db.commit()
        return {"ok": True}


@router.get("/calibration")
def get_calibration(db: DB):
    return emulator_config(db).get("calibration")


@router.put("/calibration")
def set_calibration(payload: EmulatorCalibration, db: DB):
    with operation(db, "emulator-config"):
        config = emulator_config(db)
        config["calibration"] = payload.model_dump()
        save_emulator_config(db, config)
        record(db, "calibrate", "emulator", details={"screen": [payload.screen_width, payload.screen_height]})
        db.commit()
        return config["calibration"]


@router.get("/scans")
def list_inventory_scans(db: DB, limit: int = Query(20, ge=1, le=100)):
    rows = db.scalars(select(InventoryScan).where(InventoryScan.game_version == current_version(db)).order_by(InventoryScan.id.desc()).limit(limit)).all()
    return [scan_data(row) for row in rows]


@router.post("/scans", status_code=201)
def create_inventory_scan(db: DB):
    serial = connected_serial(db)
    with operation(db, f"device:{serial}", "scan-create", blocking=False):
        edition = current_version(db)
        assert_device_idle(db, serial)
        _, size = ready_serial(serial)
        existing = db.scalar(select(InventoryScan).where(InventoryScan.game_version == edition, InventoryScan.device_serial == serial, InventoryScan.status.in_(OPEN_SCAN_STATES)).order_by(InventoryScan.id.desc()).limit(1))
        if existing:
            return scan_data(existing) | {"reused": True}
        scan = InventoryScan(device_serial=serial, screen_size=list(size), game_version=edition, status="scanning", next_candidate_id=1)
        db.add(scan)
        db.flush()
        record(db, "create", "inventory_scan", scan.id, {"device_serial": serial, "screen_size": scan.screen_size, "game_version": edition})
        db.commit()
        return scan_data(scan)


@router.post("/scans/{scan_id}/continue", status_code=201)
def continue_inventory_scan(scan_id: int, db: DB):
    serial = _scan_serial(db, scan_id)
    with operation(db, f"device:{serial}", f"scan:{scan_id}", blocking=False):
        previous = _scan(db, scan_id, closed=True)
        if previous.status not in {"review", "imported"} or not scan_at_capacity(previous):
            raise HTTPException(409, "La lectura actual todavía no alcanzó su límite")
        bridge, size = _same_scan_device(db, previous)
        existing = db.scalar(select(InventoryScan).where(InventoryScan.source_scan_id == previous.id).limit(1))
        if existing:
            return scan_data(existing) | {"reused": True}
        last_hash = previous.last_page_hash or next((value.removeprefix("continuation:") for value in reversed(previous.capture_hashes) if value != "continuation"), None)
        scan = InventoryScan(device_serial=serial, screen_size=list(size), game_version=previous.game_version, status="scanning", next_candidate_id=1, source_scan_id=previous.id, last_page_hash=last_hash, capture_hashes=[last_hash] if last_hash else [])
        db.add(scan)
        db.flush()
        record(db, "continue", "inventory_scan", scan.id, {"previous_scan_id": previous.id, "starts_after_page": previous.captured_pages})
        db.commit()
        return scan_data(scan)


@router.post("/scans/{scan_id}/capture")
def capture_inventory_page(scan_id: int, db: DB):
    serial = _scan_serial(db, scan_id)
    with operation(db, f"device:{serial}", f"scan:{scan_id}", blocking=False):
        scan = _scan(db, scan_id)
        if scan_at_capacity(scan):
            raise HTTPException(409, "La lectura alcanzó su límite; continúa en otro lote")
        bridge, _ = _same_scan_device(db, scan)
        try:
            content = bridge.screenshot(serial)
            try:
                hierarchy = bridge.ui_hierarchy(serial)
            except (AdbError, AttributeError):
                hierarchy = b""
            page = scan.captured_pages + 1
            result = ocr_inventory(content, page, hierarchy) if hierarchy else ocr_inventory(content, page)
        except (AdbError, ValueError) as exc:
            raise HTTPException(422, "No se pudo leer la captura de forma fiable") from exc
        candidates = result.get("candidates", [])
        digest = _signature(candidates) if candidates else hashlib.sha256(content).hexdigest()
        additions = _append_page(scan, candidates, digest, page)
        if additions is None:
            return {"scan": scan_data(scan), "raw_text": "", "duplicate_capture": True, "detected": 0}
        record(db, "capture", "inventory_scan", scan.id, {"page": page, "detected": len(additions), "image_saved": False, "source": result.get("extraction_source", "ocr")})
        db.commit()
        return {"scan": scan_data(scan), "raw_text": result.get("raw_text", ""), "duplicate_capture": False, "detected": len(additions)}


@router.post("/scans/{scan_id}/advance")
def advance_inventory_page(scan_id: int, db: DB):
    serial = _scan_serial(db, scan_id)
    with operation(db, f"device:{serial}", f"scan:{scan_id}", blocking=False):
        scan = _scan(db, scan_id)
        if scan.captured_pages < 1 and scan.source_scan_id is None:
            raise HTTPException(409, "Lee primero la página actual")
        if scan_at_capacity(scan):
            raise HTTPException(409, "La lectura alcanzó su límite; continúa en otro lote")
        bridge, size = _same_scan_device(db, scan)
        page = scan.captured_pages + 1
        try:
            before = extract_accessibility_inventory_candidates(bridge.ui_hierarchy(serial), max(1, scan.captured_pages))
            if not before:
                raise AdbError("Abre Mi club → Futbolistas antes de avanzar")
            bridge.scroll_inventory_list_to_end(serial, *size)
            bounds = find_accessibility_inventory_action(bridge.ui_hierarchy(serial), "Siguiente")
            if not bounds:
                raise AdbError("No se encontró un botón Siguiente seguro y habilitado")
            x1, y1, x2, y2 = bounds
            if not int(size[0] * 0.6) <= x1 < x2 <= size[0] or not int(size[1] * 0.75) <= y1 < y2 <= size[1]:
                raise AdbError("El botón Siguiente no está en la zona segura esperada")
            bridge.tap(serial, (x1 + x2) // 2, (y1 + y2) // 2)
            for _ in range(3):
                time.sleep(0.6)
                detected = extract_accessibility_inventory_candidates(bridge.ui_hierarchy(serial), page)
                if detected and _signature(detected) != _signature(before):
                    break
            else:
                raise AdbError("La página no cambió después de pulsar Siguiente")
        except AdbError as exc:
            raise HTTPException(409, str(exc)) from exc
        additions = _append_page(scan, detected, _signature(detected), page)
        if additions is None:
            raise HTTPException(409, "La página detectada ya forma parte de esta lectura")
        record(db, "advance_capture", "inventory_scan", scan.id, {"page": page, "detected": len(additions), "image_saved": False, "source": "accessibility", "navigation_validated": True})
        db.commit()
        return {"scan": scan_data(scan), "duplicate_capture": False, "detected": len(additions)}


@router.post("/scans/{scan_id}/import")
def import_inventory_scan(scan_id: int, payload: InventoryScanImportRequest, db: DB):
    with operation(db, "inventory", f"scan:{scan_id}"):
        scan = _scan(db, scan_id)
        expected = f"REEMPLAZAR DEMO {scan.id}" if payload.archive_demo else f"IMPORTAR {scan.id}"
        if payload.confirmation.strip().upper() != expected:
            raise HTTPException(422, "La frase de confirmación no coincide")
        available_ids = {int(item["candidate_id"]) for item in scan.candidates}
        if any(candidate_id not in available_ids for candidate_id in payload.candidate_ids):
            raise HTTPException(409, "Uno o más candidatos ya fueron importados o dejaron de estar disponibles")
        validated = []
        for item in payload.players:
            if not item.data_reviewed:
                raise HTTPException(422, "Revisa cada carta seleccionada antes de importarla")
            value = item.model_dump()
            if "game_version" not in item.model_fields_set:
                value["game_version"] = scan.game_version
            if value["game_version"] != scan.game_version:
                raise HTTPException(422, "Todas las cartas deben pertenecer a la edición de la lectura")
            for field in ("name", "position", "league", "club", "nationality"):
                if not str(value[field]).strip() or str(value[field]).strip().casefold() in PLACEHOLDER_VALUES:
                    raise HTTPException(422, f"Revisa el campo {field}; no se importan marcadores pendientes")
            value.update(data_source="companion_review", data_reviewed=True)
            validated.append(value)
        archived = 0
        if payload.archive_demo:
            demo_rows = db.scalars(select(Player).where(Player.game_version == scan.game_version, Player.data_source == "demo", Player.deleted.is_(False))).all()
            for player in demo_rows:
                player.deleted = True
                player.duplicate_untradeable = False
            archived = len(demo_rows)
        imported = [Player(**value) for value in validated]
        db.add_all(imported)
        db.flush()
        from app.services.gallery import record_player
        for player in imported:
            record_player(db, player)
        selected_ids = set(payload.candidate_ids)
        scan.candidates = [item for item in scan.candidates if int(item["candidate_id"]) not in selected_ids]
        scan.imported_player_ids = [*scan.imported_player_ids, *[player.id for player in imported]]
        scan.imported_count += len(imported)
        scan.status = "imported" if not scan.candidates else "review"
        scan.imported_at = datetime.now(timezone.utc) if scan.status == "imported" else None
        record(db, "import", "inventory_scan", scan.id, {"imported": len(imported), "remaining": len(scan.candidates), "demo_archived": archived, "reviewed": True, "game_version": scan.game_version, "candidate_ids": payload.candidate_ids})
        db.commit()
        return {"imported": len(imported), "demo_archived": archived, "player_ids": scan.imported_player_ids, "scan": scan_data(scan)}


@router.post("/scans/{scan_id}/cancel")
def cancel_inventory_scan(scan_id: int, db: DB):
    with operation(db, f"scan:{scan_id}"):
        scan = _scan(db, scan_id, closed=True)
        if scan.status == "imported":
            raise HTTPException(409, "La lectura ya fue importada")
        scan.status = "cancelled"
        record(db, "cancel", "inventory_scan", scan.id)
        db.commit()
        return scan_data(scan)


@router.get("/plans")
def list_plans(db: DB, limit: int = Query(30, ge=1, le=100)):
    segment_ids = select(Segment.id).join(Challenge).where(Challenge.game_version == current_version(db))
    rows = db.scalars(select(AutomationPlan).where(AutomationPlan.segment_id.in_(segment_ids)).order_by(AutomationPlan.id.desc()).limit(limit)).all()
    return [plan_data(row) for row in rows]


@router.post("/plans", status_code=201)
def create_plan(payload: AutomationPlanCreate, db: DB):
    with operation(db, "inventory"):
        plan = AutomationPlan(player_ids=payload.player_ids, segment_id=payload.segment_id, status="draft")
        players, segment = validate_current_plan_solution(db, plan)
        plan.name = f"Preparar {segment.name}"
        plan.solution_snapshot = _snapshot(players, segment)
        db.add(plan)
        db.flush()
        record(db, "create", "automation_plan", plan.id, {"segment_id": segment.id, "game_version": current_version(db)})
        db.commit()
        return plan_data(plan)


@router.post("/plans/{plan_id}/prepare")
def prepare_plan(plan_id: int, db: DB):
    with operation(db, "inventory", f"plan:{plan_id}"):
        plan = db.get(AutomationPlan, plan_id)
        if not plan:
            raise HTTPException(404, "Plan no encontrado")
        if plan.worker_active or plan.status in {"queued", "running", "completed"}:
            raise HTTPException(409, "Espera a que termine o se detenga la ejecución antes de preparar")
        config = emulator_config(db)
        if not config.get("calibration"):
            raise HTTPException(409, "Calibra primero las coordenadas del emulador")
        try:
            calibration = EmulatorCalibration.model_validate(config["calibration"]).model_dump()
        except ValueError as exc:
            raise HTTPException(422, "La calibración guardada no es válida") from exc
        players, segment = validate_current_plan_solution(db, plan)
        plan.solution_snapshot = _snapshot(players, segment) | {"calibration": calibration}
        plan.steps = build_dcp_steps(calibration, plan.solution_snapshot["players"])
        plan.device_serial = connected_serial(db)
        plan.status = "prepared"
        plan.execution_generation += 1
        plan.progress_step = 0
        plan.last_error = None
        plan.approved_at = None
        plan.executed_at = None
        record(db, "prepare", "automation_plan", plan.id, {"steps": len(plan.steps), "generation": plan.execution_generation})
        db.commit()
        return plan_data(plan)


def _same_execution(plan: AutomationPlan | None, generation: int, status: str) -> bool:
    return bool(plan and plan.execution_generation == generation and plan.status == status)


def execute_automation_plan(plan_id: int, generation: int | None = None):
    db = SessionLocal()
    worker_started = False
    try:
        initial = db.get(AutomationPlan, plan_id)
        if not initial:
            return
        generation = initial.execution_generation if generation is None else generation
        if not _same_execution(initial, generation, "queued"):
            return
        serial = initial.device_serial or ""
        db.rollback()
        with resource_locks(db, f"device:{serial}", blocking=False):
            with resource_locks(db, "inventory", f"plan:{plan_id}"):
                db.expire_all()
                plan = db.get(AutomationPlan, plan_id)
                if not _same_execution(plan, generation, "queued") or plan.worker_active:
                    return
                assert_device_idle(db, serial, excluding_plan=plan_id)
                validate_current_plan_solution(db, plan, compare_snapshot=True)
                steps = deepcopy(plan.steps)
                calibration = deepcopy(plan.solution_snapshot["calibration"])
                plan.status = "running"
                plan.worker_active = True
                worker_started = True
                db.commit()
            bridge = AdbBridge()
            expected_size = (calibration["screen_width"], calibration["screen_height"])
            if bridge.screen_size(serial) != expected_size:
                raise AdbError("La resolución cambió; revisa y vuelve a calibrar")
            for index, step in enumerate(steps, 1):
                with resource_locks(db, "inventory", f"plan:{plan_id}"):
                    db.expire_all()
                    plan = db.get(AutomationPlan, plan_id)
                    if not _same_execution(plan, generation, "running"):
                        return
                    validate_current_plan_solution(db, plan, compare_snapshot=True)
                run_step(bridge, serial, step)
                with resource_locks(db, f"plan:{plan_id}"):
                    db.expire_all()
                    plan = db.get(AutomationPlan, plan_id)
                    record(db, "execute_step", "automation_plan", plan_id, {"step": index, "action": step.get("action"), "label": step.get("label"), "generation": generation, "serial": serial})
                    if not _same_execution(plan, generation, "running"):
                        db.commit()
                        return
                    plan.progress_step = index
                    if index == len(steps):
                        plan.status = "completed"
                        plan.executed_at = datetime.now(timezone.utc)
                    db.commit()
    except Exception as exc:
        db.rollback()
        if not isinstance(exc, (AdbError, HTTPException, ResourceBusy)):
            logger.exception("Preparación ADB interrumpida para plan %s", plan_id)
        try:
            with resource_locks(db, f"plan:{plan_id}"):
                db.expire_all()
                plan = db.get(AutomationPlan, plan_id)
                if plan and plan.execution_generation == generation and plan.status in ACTIVE_PLAN_STATES:
                    plan.status = "failed"
                    plan.last_error = (str(exc.detail) if isinstance(exc, HTTPException) else str(exc))[:500] if isinstance(exc, (AdbError, HTTPException, ResourceBusy)) else "La preparación se interrumpió; revisa el estado del dispositivo antes de preparar otro plan"
                    record(db, "execute_failed", "automation_plan", plan_id, {"error": plan.last_error, "generation": generation})
                    db.commit()
        except Exception:
            db.rollback()
            logger.exception("No se pudo registrar la interrupción del plan %s", plan_id)
    finally:
        if worker_started:
            try:
                with resource_locks(db, f"plan:{plan_id}"):
                    db.expire_all()
                    plan = db.get(AutomationPlan, plan_id)
                    if plan and plan.execution_generation in {generation, generation + 1}:
                        plan.worker_active = False
                        db.commit()
            except Exception:
                db.rollback()
                logger.exception("No se pudo liberar el marcador del plan %s", plan_id)
        db.close()


@router.post("/plans/{plan_id}/execute")
def execute_plan(plan_id: int, payload: AutomationExecuteRequest, background: BackgroundTasks, db: DB):
    initial = db.get(AutomationPlan, plan_id)
    if not initial:
        raise HTTPException(404, "Plan no encontrado")
    serial = initial.device_serial or ""
    db.rollback()
    with operation(db, f"device:{serial}", "inventory", f"plan:{plan_id}", blocking=False):
        plan = db.get(AutomationPlan, plan_id)
        if plan.status != "prepared" or plan.worker_active:
            raise HTTPException(409, "El plan debe estar preparado y sin una ejecución anterior activa")
        if payload.confirmation.strip().upper() != f"PREPARAR {plan.id}":
            raise HTTPException(422, "La frase de confirmación no coincide")
        if plan.device_serial != serial:
            raise HTTPException(409, "El dispositivo del plan cambió; revisa de nuevo la preparación")
        validate_current_plan_solution(db, plan, compare_snapshot=True)
        assert_device_idle(db, serial, excluding_plan=plan.id)
        bridge, size = ready_serial(serial)
        calibration = plan.solution_snapshot.get("calibration", {})
        if size != (calibration.get("screen_width"), calibration.get("screen_height")):
            raise HTTPException(409, "La resolución no coincide con la calibración")
        plan.status = "queued"
        plan.execution_generation += 1
        plan.approved_at = datetime.now(timezone.utc)
        record(db, "approve", "automation_plan", plan.id, {"generation": plan.execution_generation, "serial": serial})
        db.commit()
        background.add_task(execute_automation_plan, plan.id, plan.execution_generation)
        return {"queued": True, "plan_id": plan.id, "final_submission_automated": False}


@router.post("/plans/{plan_id}/cancel")
def cancel_plan(plan_id: int, db: DB):
    with operation(db, f"plan:{plan_id}"):
        plan = db.get(AutomationPlan, plan_id)
        if not plan:
            raise HTTPException(404, "Plan no encontrado")
        segment = db.get(Segment, plan.segment_id)
        if segment and segment.challenge.game_version != current_version(db):
            raise HTTPException(409, "El plan pertenece a otra edición del juego")
        if plan.status == "completed":
            raise HTTPException(409, "El plan ya terminó")
        if plan.status != "cancelled":
            plan.status = "cancelled"
            plan.execution_generation += 1
            record(db, "cancel", "automation_plan", plan.id, {"generation": plan.execution_generation, "worker_stopping": plan.worker_active})
            db.commit()
        return plan_data(plan)


def recover_interrupted_automation():
    """Release abandoned work after startup; never replay device commands."""
    with SessionLocal() as db:
        pending = [(row.id, row.device_serial or "") for row in db.scalars(select(AutomationPlan).where(or_(AutomationPlan.status.in_(ACTIVE_PLAN_STATES), AutomationPlan.worker_active.is_(True)))).all()]
        db.rollback()
        for plan_id, serial in pending:
            try:
                with resource_locks(db, f"device:{serial}", f"plan:{plan_id}", blocking=False):
                    db.expire_all()
                    plan = db.get(AutomationPlan, plan_id)
                    if not plan or (plan.status not in ACTIVE_PLAN_STATES and not plan.worker_active):
                        continue
                    if plan.status != "cancelled":
                        plan.status = "failed"
                    plan.worker_active = False
                    plan.execution_generation += 1
                    plan.last_error = "Ejecución interrumpida. Revisa manualmente el dispositivo y vuelve a preparar; no se reanudaron pulsaciones"
                    record(db, "execution_recovered", "automation_plan", plan.id, {"resumed": False})
                    db.commit()
            except ResourceBusy:
                # A live worker in another process still owns the device.
                db.rollback()
