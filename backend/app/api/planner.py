from datetime import timedelta
from decimal import Decimal, ROUND_CEILING
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.entities import Player, Segment, Submission, now
from app.models.planner import ClubPlan, PlanAction, Reservation, MarketQuote, TradeRecord, ClubProgress, MatchRecord
from app.schemas.planner import PlanInput, PlanReview, ActionConfirmation, QuoteInput, TradeInput, MarketSimulation
from app.schemas.api import InputModel
from app.services.planner import preview, plan_data, revalidate, inventory_fingerprint, hash_json
from app.services.contexts import require_module, utc
from app.services.audit import record
from app.services.locks import resource_locks

router = APIRouter(tags=["Planificación y mercado"])


def owned(db, model, identifier):
    row = db.get(model, identifier)
    if row is None:
        raise HTTPException(404, "Registro no disponible")
    return row


@router.post("/plans/preview")
def preview_plan(payload: PlanInput, db: Session = Depends(get_db)):
    return preview(db, payload)


@router.post("/plans", status_code=201)
def save_plan(payload: PlanInput, db: Session = Depends(get_db)):
    with resource_locks(db, "inventory"):
        db.expire_all()
        result = preview(db, payload)
        # Datetimes become JSON only at the persistence boundary.
        import json
        result = json.loads(json.dumps(result, default=str))
        plan = ClubPlan(name=payload.name, entry_id=db.info["local_session"].entry_id,
                        snapshot_id=db.info["context"].snapshot_id, revision=db.info["context"].revision,
                        plan_hash=result["plan_hash"], inputs=result, expires_at=now()+timedelta(minutes=payload.expires_minutes))
        db.add(plan)
        db.flush()
        for row in result["actions"]:
            db.add(PlanAction(plan_id=plan.id, ordinal=row["ordinal"], kind=row["kind"], player_ids=row["player_ids"], details=row))
        record(db, "draft", "club_plan", plan.id)
        db.commit()
        return plan_data(db, plan)


@router.get("/plans")
def list_plans(db: Session = Depends(get_db)):
    from app.services.editions import current_version
    from app.services.planner import documented_plan
    return [plan_data(db, row) for row in db.scalars(select(ClubPlan).order_by(ClubPlan.id.desc()).limit(100)) if documented_plan(db, row)]


@router.post("/plans/{plan_id}/review")
def review_plan(plan_id: int, payload: PlanReview, db: Session = Depends(get_db)):
    with resource_locks(db, "inventory"):
        db.expire_all()
        plan = owned(db, ClubPlan, plan_id)
        revalidate(db, plan)
        if payload.plan_hash != plan.plan_hash or payload.confirmation != f"REVISAR {plan_id}":
            raise HTTPException(422, "Revisa la versión exacta del plan y su frase")
        if plan.status not in {"draft", "reviewed"}:
            raise HTTPException(409, "El plan no está en borrador")
        plan.status = "reviewed"
        record(db, "review", "club_plan", plan.id)
        db.commit()
        return plan_data(db, plan)


@router.post("/plans/{plan_id}/reserve")
def reserve_plan(plan_id: int, db: Session = Depends(get_db)):
    with resource_locks(db, "inventory"):
        db.expire_all()
        plan = owned(db, ClubPlan, plan_id)
        revalidate(db, plan)
        if plan.status not in {"reviewed", "reserved"}:
            raise HTTPException(409, "Revisa el plan antes de reservar")
        ids = {pid for action in plan.inputs["actions"] for pid in action["player_ids"]}
        for player_id in sorted(ids):
            old = db.get(Reservation, player_id)
            if old and old.plan_id != plan.id and utc(old.expires_at) > now():
                raise HTTPException(409, "Otra propuesta ya reservó una de las copias")
            if old:
                old.plan_id, old.expires_at = plan.id, plan.expires_at
            else:
                db.add(Reservation(player_id=player_id, plan_id=plan.id, expires_at=plan.expires_at))
        plan.status = "reserved"
        record(db, "reserve", "club_plan", plan.id, {"players": sorted(ids)})
        db.commit()
        return plan_data(db, plan)


@router.post("/plans/{plan_id}/approve")
def approve_plan(plan_id: int, payload: PlanReview, db: Session = Depends(get_db)):
    with resource_locks(db, "inventory"):
        db.expire_all()
        plan = owned(db, ClubPlan, plan_id)
        revalidate(db, plan)
        if payload.plan_hash != plan.plan_hash or payload.confirmation != f"APROBAR {plan_id}":
            raise HTTPException(422, "La aprobación no coincide con la propuesta revisada")
        if plan.status != "reserved":
            raise HTTPException(409, "Primero revisa y reserva las copias de esta propuesta")
        plan.approval = {"hash": plan.plan_hash, "session": db.info["local_session"].id, "approved_at": now().isoformat(), "context": plan.club_context_id}
        plan.status = "pending_manual_execution"
        record(db, "approve", "club_plan", plan.id, {"execution": "manual"})
        db.commit()
        return plan_data(db, plan)


@router.post("/plans/{plan_id}/cancel")
def cancel_plan(plan_id: int, db: Session = Depends(get_db)):
    with resource_locks(db, "inventory"):
        plan = owned(db, ClubPlan, plan_id)
        if plan.status == "confirmed":
            raise HTTPException(409, "Cancelar no revierte acciones ya confirmadas")
        for row in db.scalars(select(Reservation).where(Reservation.plan_id == plan.id)):
            db.delete(row)
        plan.status = "cancelled"
        record(db, "cancel", "club_plan", plan.id)
        db.commit()
        return plan_data(db, plan)


@router.post("/plans/{plan_id}/actions/{action_id}/confirm")
def confirm_action(plan_id: int, action_id: int, payload: ActionConfirmation, db: Session = Depends(get_db)):
    with resource_locks(db, "inventory"):
        db.expire_all()
        plan, action = owned(db, ClubPlan, plan_id), owned(db, PlanAction, action_id)
        if action.plan_id != plan.id:
            raise HTTPException(404, "Acción no disponible")
        if payload.plan_hash != plan.plan_hash or payload.confirmation != f"CONFIRMAR {plan.id} {action.ordinal}":
            raise HTTPException(422, "Confirma la acción concreta y la versión revisada")
        if plan.approval.get("session") != db.info["local_session"].id or plan.approval.get("hash") != plan.plan_hash:
            raise HTTPException(403, "Falta una autorización válida de esta sesión")
        if action.status == "confirmed":
            if action.receipt.get("request_hash") != hash_json(payload.model_dump()):
                raise HTTPException(409, "La confirmación repetida tiene datos distintos")
            return plan_data(db, plan)
        if plan.status != "pending_manual_execution":
            raise HTTPException(409, "El plan no admite ejecución")
        revalidate(db, plan)
        earlier = list(db.scalars(select(PlanAction).where(PlanAction.plan_id == plan.id, PlanAction.ordinal < action.ordinal)))
        if any(row.status != "confirmed" for row in earlier):
            raise HTTPException(409, "Confirma primero los pasos anteriores")
        if payload.actual_amount is not None and action.kind in {"buy", "evolution"} and payload.actual_amount > action.details["max_cost"]:
            raise HTTPException(409, "El coste supera el máximo aprobado")
        if action.kind in {"buy", "sell", "evolution"} and payload.actual_amount is None:
            raise HTTPException(422, "Registra el importe real de la operación")
        db.info["executing_plan"] = plan.id
        players = [owned(db, Player, pid) for pid in action.player_ids]
        if any(p.deleted or p.availability != "available" for p in players):
            raise HTTPException(409, "Confirma la disponibilidad de las copias antes de registrar otro paso")
        if action.kind == "evolution":
            from app.models.entities import EvolutionDefinition
            from app.services.evolutions import preview_path
            from app.services.squad_analysis import serialize_player
            definition = owned(db, EvolutionDefinition, action.details["definition_id"])
            path = next((p for p in definition.paths if p["id"] == action.details["path_id"]), None)
            if path is None or not preview_path(serialize_player(players[0]), definition, path)["eligible"]:
                raise HTTPException(409, "La elegibilidad de la evolución requiere una nueva revisión")
        if payload.outcome == "uncertain":
            action.status = "uncertain"
            plan.status = "uncertain"
            for player in players:
                player.availability = "uncertain"
        else:
            if action.kind == "unprotect":
                db.info["reviewed_exception_ids"] = set(action.player_ids)
                for player in players:
                    player.protected = False  # Never clears starters, favourites, Evo or squad protection.
            elif action.kind == "dcp":
                from app.api.routes import requirements_for_batch, score_progress, _recompute_completion
                from app.optimizers.sbc import validate_solution
                segment = owned(db, Segment, action.details["segment_id"])
                requirements = requirements_for_batch(db, segment)
                violations = validate_solution(players, requirements, current_score=score_progress(db, segment))
                if violations:
                    raise HTTPException(409, {"message": "El DCP cambió", "violations": violations})
                snapshot = {"ownership_version": 1, "origin": "manual_game_confirmation", "player_ids": action.player_ids, "fc27_checked": True,
                            "players": {str(p.id): {"deleted": p.deleted, "duplicate_untradeable": p.duplicate_untradeable} for p in players}}
                submission = Submission(segment_id=segment.id, game_version=segment.challenge.game_version,
                    score_contribution=sum(p.gallery_score or 0 for p in players) if requirements["kind"] == "score" else 0,
                    total_cost=None if any(p.price is None for p in players) else sum(p.price for p in players), snapshot=snapshot)
                db.add(submission)
                db.flush()
                for player in players:
                    player.deleted = True
                    player.consumed_by_submission_id = submission.id
                _recompute_completion(db, segment)
            elif action.kind == "sell":
                for player in players:
                    player.deleted = True
                    player.availability = "sold"
            elif action.kind in {"buy", "evolution"}:
                # An operation log cannot manufacture verified provider attributes/identity.
                for player in players:
                    player.availability = "review_required"
                db.add(ClubProgress(kind="operation", definition_key=f"plan:{plan.id}:{action.ordinal}", state={"kind": action.kind, "amount": payload.actual_amount, "reconciliation_required": True}))
            elif action.kind == "gallery":
                from app.services.gallery import record_player
                for player in players:
                    record_player(db, player)
            action.status = "confirmed"
            for player_id in action.player_ids:
                claim = db.get(Reservation, player_id)
                later = db.scalars(select(PlanAction).where(PlanAction.plan_id == plan.id, PlanAction.ordinal > action.ordinal))
                still_needed = any(player_id in step.player_ids and step.status != "confirmed" for step in later)
                if claim and claim.plan_id == plan.id and not still_needed:
                    db.delete(claim)
        action.receipt = {"evidence": payload.evidence, "amount": payload.actual_amount, "at": now().isoformat(), "request_hash": hash_json(payload.model_dump())}
        db.flush()
        # Expected effects of this confirmed step do not invalidate the remaining batch.
        expected = dict(plan.approval)
        expected["expected_inventory_hash"] = inventory_fingerprint(db)
        if payload.outcome == "confirmed":
            expected["post_action_entry"] = plan.entry_id
        if action.kind == "dcp" and payload.outcome == "confirmed":
            from app.api.routes import requirements_for_batch
            expected["expected_rules"] = {**expected.get("expected_rules", plan.inputs["rules"]), str(segment.id): requirements_for_batch(db, segment)}
        plan.approval = expected
        if all(row.status == "confirmed" for row in db.scalars(select(PlanAction).where(PlanAction.plan_id == plan.id))):
            plan.status = "confirmed"
        record(db, "confirm_manual_action", "club_plan", plan.id, {"step": action.ordinal, "outcome": payload.outcome})
        db.commit()
        return plan_data(db, plan)


@router.get("/market/quotes")
def quotes(db: Session = Depends(get_db)):
    return [{field: getattr(row, field) for field in QuoteInput.model_fields} | {"id": row.id, "imported_at": row.imported_at, "expired": utc(row.expires_at) <= now() or now()-utc(row.observed_at) > timedelta(hours=24)} for row in db.scalars(select(MarketQuote).order_by(MarketQuote.id.desc()).limit(200))]


@router.post("/market/quotes", status_code=201)
def add_quote(payload: QuoteInput, db: Session = Depends(get_db)):
    from app.services.catalog_validation import require_variant
    require_variant(db, payload.variant_id)
    if payload.observed_at.tzinfo is None or payload.expires_at.tzinfo is None or payload.observed_at > now() or payload.expires_at <= payload.observed_at:
        raise HTTPException(422, "Revisa las fechas de observación y caducidad con su zona horaria")
    row = MarketQuote(**payload.model_dump())
    db.add(row)
    db.flush()
    record(db, "record_quote", "market_quote", row.id)
    db.commit()
    return {"id": row.id, "source": "manual_review", "verified_provider": False}


@router.post("/market/simulate")
def market_simulation(payload: MarketSimulation):
    factor = 1 - Decimal(str(payload.tax_percent))/100
    cost = payload.purchase + payload.other_costs
    break_even = Decimal(cost)/factor
    if payload.price_increment:
        break_even = (break_even/Decimal(payload.price_increment)).to_integral_value(rounding=ROUND_CEILING)*payload.price_increment
    return {"estimated_profit": float(Decimal(payload.sale)*factor-cost),
            "adverse_profit": float(Decimal(payload.adverse_sale)*factor-cost), "capital_exposed": cost,
            "break_even": float(break_even), "price_increment_verified": False, "sales_volume": None,
            "decision": "no_operar" if Decimal(payload.sale)*factor <= cost else "revisar",
            "tax_status": "third_party_assumption", "rounding_status": "unverified", "simulation": True,
            "tax_assumption": {"percent": payload.tax_percent, "reference_percent": 5, "reference_date": "2026-09-18", "source_url": "https://www.fut.gg/news/how-to-get-fut-gallery-tokens-fast-in-ea-fc-27-and-unlock-pato-hulk-and-david-luiz/", "official_fc27_confirmation": False},
            "warning": "Tasa y redondeo son hipótesis; comprueba el neto real. No es una cotización ni una garantía de rentabilidad."}


@router.get("/market/journal")
def journal(db: Session = Depends(get_db)):
    from app.services.editions import current_version
    rows = list(db.scalars(select(TradeRecord).where(TradeRecord.game_version == current_version(db)).order_by(TradeRecord.id.desc()).limit(500)))
    by_id = {row.id: row for row in rows}
    sales = [r for r in rows if r.kind == "sold" and r.purchase_record_id in by_id]
    profit = sum(r.amount-r.fees-by_id[r.purchase_record_id].amount-by_id[r.purchase_record_id].fees for r in sales)
    buys = [r for r in rows if r.kind == "bought"]
    return {"items": [{key: getattr(r, key) for key in ("id", "game_version", "market", "variant_id", "kind", "amount", "fees", "occurred_at", "evidence", "purchase_record_id")} for r in rows],
            "realized_profit": profit, "closed_sample": len(sales), "purchase_sample": len(buys), "pending_purchases": len(buys)-len(sales),
            "sold_percent": round(100*len(sales)/len(buys), 1) if buys else None,
            "average_hours_to_sale": sum((utc(r.occurred_at)-utc(by_id[r.purchase_record_id].occurred_at)).total_seconds()/3600 for r in sales)/len(sales) if sales else None,
            "scope": "Muestra de hasta 500 registros recientes de esta edición; no representa el volumen del mercado ni actualiza monedas verificadas"}


@router.post("/market/journal", status_code=201)
def add_trade(payload: TradeInput, db: Session = Depends(get_db)):
    from app.services.catalog_validation import require_variant
    require_variant(db, payload.variant_id)
    with resource_locks(db, "inventory"):
        from app.services.editions import current_version
        if payload.game_version != current_version(db):
            raise HTTPException(409, "La operación pertenece a otra edición")
        if db.info["context"].verified and payload.market != db.info["context"].platform:
            raise HTTPException(409, "El mercado no corresponde al club verificado")
        if payload.confirmation != "REGISTRAR OPERACION":
            raise HTTPException(422, "Escribe REGISTRAR OPERACION tras contrastar la operación")
        old = db.scalar(select(TradeRecord).where(TradeRecord.receipt_key == payload.receipt_key))
        values = payload.model_dump(exclude={"confirmation"})
        if old:
            if utc(old.occurred_at) != payload.occurred_at or any(getattr(old, key) != value for key, value in values.items() if key != "occurred_at"):
                raise HTTPException(409, "El recibo ya existe con datos distintos")
            return {"id": old.id, "already_recorded": True}
        if payload.occurred_at.tzinfo is None or payload.occurred_at > now() or payload.fees > payload.amount:
            raise HTTPException(422, "Revisa fecha e importes")
        if payload.player_id:
            owned(db, Player, payload.player_id)
        if payload.purchase_record_id:
            purchase = owned(db, TradeRecord, payload.purchase_record_id)
            if purchase.kind != "bought" or payload.kind != "sold" or purchase.variant_id != payload.variant_id or purchase.market != payload.market or purchase.game_version != payload.game_version or utc(purchase.occurred_at) > payload.occurred_at:
                raise HTTPException(409, "La venta no corresponde a esa compra")
            if db.scalar(select(TradeRecord.id).where(TradeRecord.purchase_record_id == purchase.id)):
                raise HTTPException(409, "La compra ya tiene una venta confirmada")
        row = TradeRecord(**values)
        db.add(row)
        db.flush()
        record(db, "confirmed_diary", "trade_record", row.id, {"kind": row.kind})
        db.commit()
        return {"id": row.id, "already_recorded": False}
