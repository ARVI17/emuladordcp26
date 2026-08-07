from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import SessionLocal, get_db
from app.models.entities import AppSetting, AutomationPlan, Player, Segment
from app.optimizers.sbc import validate_solution
from app.schemas.api import AutomationExecuteRequest, AutomationPlanCreate, EmulatorCalibration, EmulatorConnectRequest, EmulatorSwipeRequest, EmulatorTapRequest
from app.services.adb import AdbBridge, AdbError, build_dcp_steps, run_step
from app.services.audit import record
from app.services.import_export import ocr_image

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
    plan.steps = build_dcp_steps(calibration, plan.solution_snapshot["players"]); plan.device_serial = config.get("serial") or config.get("address"); plan.status = "prepared"; plan.progress_step = 0; plan.last_error = None
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
