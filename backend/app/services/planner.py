"""Reviewable local plans; no operation is executed on EA."""
import hashlib
import json
from datetime import timedelta
from fastapi import HTTPException
from sqlalchemy import select
from app.models.entities import Player, Segment, EvolutionDefinition, GallerySet, now
from app.models.planner import ClubPlan, MarketQuote, PlanAction, Reservation
from app.schemas.planner import PlanInput
from app.services.contexts import require_module, utc
from app.services.squad_analysis import effective_protected_ids, serialize_player
from app.optimizers.sbc import validate_solution


def hash_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def evolution_rules(definition):
    return {"requirements": definition.requirements, "paths": definition.paths, "rules_reviewed": definition.rules_reviewed,
            "expires_at": utc(definition.expires_at).isoformat() if definition.expires_at else None, "game_version": definition.game_version}


def inventory_fingerprint(db):
    fields = ("id", "club_context_id", "game_version", "name", "rating", "position", "alternate_positions", "card_id", "athlete_id", "price", "gallery_score", "protected", "starter", "favorite", "is_evolution", "is_loan", "tradable", "deleted", "availability", "attributes", "data_reviewed", "updated_at")
    return hash_json([{key: utc(getattr(p, key)).isoformat() if key == "updated_at" else getattr(p, key) for key in fields} for p in db.scalars(select(Player).order_by(Player.id))])


def valid_quote(db, quote_id, *, variant=None):
    quote = db.get(MarketQuote, quote_id)
    context = db.info["context"]
    from app.services.editions import current_version
    if not quote or quote.game_version != current_version(db) or (variant and quote.variant_id != variant):
        raise HTTPException(409, "Cotización de otra edición o variante")
    if context.platform and quote.market != context.platform:
        raise HTTPException(409, "La cotización no corresponde al mercado verificado del club")
    if utc(quote.expires_at) <= now() or utc(quote.observed_at) > now() or now()-utc(quote.observed_at) > timedelta(hours=24):
        raise HTTPException(409, "La cotización está caducada o tiene fecha inválida")
    if quote.kind not in {"listing", "observed_sale"}:
        raise HTTPException(409, "Una puja o rango permitido no demuestra un precio de compra")
    return quote


def coin_commitments(db, excluding=None):
    """Durable claims derive from persisted plans, under the inventory lock.

    A confirmed/uncertain spend remains committed until newer remote coin
    evidence arrives. A listing or proposed sale never supplies funds.
    """
    from app.models.planner import InventorySnapshot
    context = db.info["context"]
    snapshot = db.get(InventorySnapshot, context.snapshot_id) if context.snapshot_id else None
    observed = utc(snapshot.observed_at) if snapshot and snapshot.coverage.get("coins", {}).get("complete") else None
    total, floor = 0, 0
    from app.services.editions import current_version
    for plan in db.scalars(select(ClubPlan)):
        if plan.id == excluding or plan.inputs["binding"].get("game_version", "FC27") != current_version(db):
            continue
        active = plan.status in {"reserved", "pending_manual_execution", "uncertain"} and utc(plan.expires_at) > now()
        if active:
            floor = max(floor, plan.inputs["reserve_coins"])
        for action in db.scalars(select(PlanAction).where(PlanAction.plan_id == plan.id)):
            if action.kind not in {"buy", "evolution"}:
                continue
            if action.status in {"confirmed", "uncertain"}:
                from datetime import datetime
                reconciled = observed and action.receipt.get("at") and observed >= datetime.fromisoformat(action.receipt["at"])
                if not reconciled:
                    total += action.receipt.get("amount") if action.status == "confirmed" and action.receipt.get("amount") is not None else action.details["max_cost"]
            elif active:
                total += action.details["max_cost"]
    return total, floor


def check_coin_budget(db, inputs, excluding=None):
    context = db.info["context"]
    balance = min(inputs["budget"], context.coins or 0) if context.verified else inputs["budget"]
    committed, floor = coin_commitments(db, excluding)
    cost = sum(a["max_cost"] for a in inputs["actions"])
    if balance - committed - cost < max(inputs["reserve_coins"], floor):
        raise HTTPException(409, "Las monedas comprometidas por otros planes o la reserva impiden esta propuesta")
    return committed


def preview(db, payload: PlanInput):
    binding = require_module(db, "analysis")
    context = db.info["context"]
    local = binding.get("scope") == "local_unlinked"
    if not local and any(a.max_cost or a.kind == "buy" for a in payload.actions):
        require_module(db, "market", allow_local=False)
    committed = check_coin_budget(db, payload.model_dump())
    balance = payload.budget if local else min(payload.budget, context.coins or 0)
    balance -= committed
    if balance < payload.reserve_coins:
        raise HTTPException(409, "La reserva supera las monedas disponibles")
    protected = effective_protected_ids(db)
    used, actions, rules, quotes = set(), [], {}, {}
    for index, action in enumerate(payload.actions):
        extra = {}
        if any(deadline and deadline <= now() for deadline in (action.start_before, action.complete_before)):
            raise HTTPException(409, "Uno de los plazos revisados ya venció")
        if action.max_cost and action.kind not in {"buy", "evolution"}:
            raise HTTPException(409, "El coste adicional solo corresponde a una compra o evolución concreta")
        players = list(db.scalars(select(Player).where(Player.id.in_(action.player_ids), Player.deleted.is_(False))))
        from app.services.editions import current_version
        if len(players) != len(action.player_ids) or any(p.game_version != current_version(db) or p.availability != "available" for p in players):
            raise HTTPException(409, "Hay copias no disponibles en este club y edición")
        incompatible = action.kind in {"sell", "dcp", "evolution"}
        if action.kind in {"sell", "dcp", "evolution", "gallery"} and any(p.unknown_fields for p in players):
            raise HTTPException(409, "Hay datos indispensables desconocidos en las copias; revísalos antes de comprometerlas")
        if incompatible and used & set(action.player_ids):
            raise HTTPException(409, "Una copia no puede alimentar acciones incompatibles")
        if incompatible:
            used.update(action.player_ids)
        from app.services.protection import reserved_ids
        if set(action.player_ids) & reserved_ids(db):
            raise HTTPException(409, "Hay copias reservadas por otro plan")
        if action.kind in {"sell", "dcp"} and protected & set(action.player_ids):
            raise HTTPException(409, "Titulares, favoritos, Evos, reservas y cartas protegidas quedan excluidos")
        if action.kind == "sell" and any(not p.tradable or p.is_loan for p in players):
            raise HTTPException(409, "La venta exige copias transferibles sin cesión")
        if action.kind == "dcp":
            require_module(db, "dcp")
            from app.api.routes import requirements_for_batch, score_progress
            segment = db.get(Segment, action.segment_id)
            if not segment or segment.completed or segment.challenge.game_version != current_version(db):
                raise HTTPException(409, "Segmento no disponible")
            requirements = requirements_for_batch(db, segment)
            violations = validate_solution(players, requirements, current_score=score_progress(db, segment))
            if violations:
                raise HTTPException(409, {"message": "Revisa el DCP", "violations": violations})
            partial = requirements["kind"] == "score" and score_progress(db, segment) + sum(p.gallery_score or 0 for p in players) < requirements["target_score"]
            if partial and not action.accept_irreversible_partial:
                raise HTTPException(409, "Esta entrega parcial consume cartas sin completar el DCP. Acepta específicamente esa pérdida o prepara una combinación completa.")
            rules[str(segment.id)] = requirements
        if action.kind == "evolution":
            require_module(db, "evolutions")
            from app.services.evolutions import preview_path
            definition = db.get(EvolutionDefinition, action.definition_id)
            if not definition or not definition.rules_reviewed:
                raise HTTPException(409, "La evolución requiere reglas revisadas")
            # Eligibility is evaluated by the existing engine, not the language model.
            path = next((p for p in definition.paths if p["id"] == action.path_id), None)
            if path is None:
                raise HTTPException(409, "Camino no disponible")
            projection = preview_path(serialize_player(players[0]), definition, path)
            if not projection["eligible"]:
                raise HTTPException(409, "La carta no cumple los requisitos de esta evolución")
            rules[f"evo:{definition.id}"] = evolution_rules(definition)
            extra = {"projection": projection["projected"], "source_url": definition.source_url,
                     "impact": ["Proyección local sin modificar la carta real", "Transferibilidad y química posteriores pendientes de verificación", "Los puntos de Galería de la proyección son desconocidos; el historial de la base se conserva", "Una Evo queda excluida de consumo en DCP"]}
        if action.kind == "gallery":
            require_module(db, "gallery")
            if any(p.is_loan for p in players):
                raise HTTPException(409, "Las cesiones no son adquisiciones de Galería")
        if action.quote_id:
            quote = valid_quote(db, action.quote_id, variant=players[0].card_id if action.kind == "sell" and players else None)
            quotes[str(quote.id)] = {"amount": quote.amount, "variant_id": quote.variant_id, "market": quote.market, "observed_at": quote.observed_at.isoformat(), "expires_at": quote.expires_at.isoformat(), "source_url": quote.source_url}
            if action.kind == "buy" and action.max_cost < quote.amount:
                raise HTTPException(409, "La compra máxima no cubre el precio observado")
        # Pending sales and random rewards never fund a later purchase.
        balance -= action.max_cost
        if balance < payload.reserve_coins:
            raise HTTPException(409, "El saldo cae bajo la reserva en un paso; no se cuentan ventas pendientes")
        actions.append({**action.model_dump(mode="json"), **extra, "ordinal": index+1, "balance_after": balance,
                        "copies": [serialize_player(p, protected) for p in players]})
    result = {"name": payload.name, "binding": binding, "actions": actions, "rules": rules, "quotes": quotes, "other_coin_commitments": committed,
              "budget": payload.budget, "reserve_coins": payload.reserve_coins, "inventory_hash": inventory_fingerprint(db),
              "expires_at": (now()+timedelta(minutes=payload.expires_minutes)).isoformat(),
              "simulation": True, "local_unlinked": local, "final_submission_automated": False,
              "warnings": ["Los registros locales no certifican posesión en EA.", "Química no verificada; media estimada. Comprueba el resultado en el juego.", "Una entrega parcial real consume cartas definitivamente.", "Las ventas pendientes y premios aleatorios no financian este plan."]}
    result["plan_hash"] = hash_json(result)
    return result


def documented_plan(db, plan):
    from app.services.catalog_validation import check_fields, find_variant
    ids = {pid for a in plan.inputs.get('actions', []) for pid in a.get('player_ids', [])}
    found = set(db.scalars(select(Player.id).where(Player.id.in_(ids)))) if ids else set()
    return (plan.inputs.get('binding', {}).get('game_version') == 'FC27'
        and ids == found
        and all(check_fields(db, p)[0] is not None for a in plan.inputs.get('actions', []) for p in a.get('copies', []))
        and all(find_variant(db, q.get('variant_id')) is not None for q in plan.inputs.get('quotes', {}).values()))


def plan_data(db, plan):
    if not documented_plan(db, plan):
        return {'id': plan.id, 'status': plan.status, 'verification_status': 'pending_verification',
                'message': 'Plan conservado fuera de las operaciones activas; revisa sus variantes', 'actions': []}
    actions = list(db.scalars(select(PlanAction).where(PlanAction.plan_id == plan.id).order_by(PlanAction.ordinal)))
    return {"id": plan.id, "name": plan.name, "status": plan.status, "plan_hash": plan.plan_hash,
            "entry_id": plan.entry_id, "expires_at": plan.expires_at, "inputs": plan.inputs,
            "actions": [{"id": a.id, "ordinal": a.ordinal, "kind": a.kind, "player_ids": a.player_ids,
                         "status": a.status, "details": a.details, "receipt": a.receipt} for a in actions],
            "reserved": list(db.scalars(select(Reservation.player_id).where(Reservation.plan_id == plan.id))),
            "approval_phrase": f"APROBAR {plan.id}", "execution": "manual"}


def revalidate(db, plan):
    from app.services.editions import current_version
    if plan.inputs["binding"].get("game_version", "FC27") != current_version(db):
        raise HTTPException(409, "El plan pertenece a otra edición")
    require_module(db, "analysis", expected_plan=plan)
    session = db.info["local_session"]
    if plan.entry_id != session.entry_id or utc(plan.expires_at) <= now():
        raise HTTPException(409, "La aprobación caducó o pertenece a otra entrada; revisa un nuevo plan")
    if hash_json({key: value for key, value in plan.inputs.items() if key != "plan_hash"}) != plan.plan_hash:
        raise HTTPException(409, "La propuesta guardada cambió y requiere revisión")
    check_coin_budget(db, plan.inputs, plan.id)
    if plan.approval.get("expected_inventory_hash", plan.inputs["inventory_hash"]) != inventory_fingerprint(db):
        raise HTTPException(409, "El inventario o sus protecciones cambiaron; revisa el plan")
    from app.api.routes import requirements_for_batch
    for key, expected in plan.approval.get("expected_rules", plan.inputs["rules"]).items():
        if key.startswith("evo:"):
            definition = db.get(EvolutionDefinition, int(key.split(":")[1]))
            current = evolution_rules(definition) if definition else None
            if definition and definition.expires_at and utc(definition.expires_at) <= now():
                raise HTTPException(409, "La evolución ha vencido")
        else:
            segment = db.get(Segment, int(key))
            current = requirements_for_batch(db, segment) if segment else None
        if current != expected:
            raise HTTPException(409, "Los requisitos cambiaron; revisa el plan")
    from datetime import datetime
    for action in plan.inputs["actions"]:
        if any(action.get(field) and datetime.fromisoformat(action[field]) <= now() for field in ("start_before", "complete_before")):
            raise HTTPException(409, "Uno de los plazos del proyecto venció")
    for quote_id, expected in plan.inputs["quotes"].items():
        quote = valid_quote(db, int(quote_id))
        if any(getattr(quote, key) != expected[key] for key in ("amount", "variant_id", "market", "source_url")):
            raise HTTPException(409, "El precio cambió; revisa el plan")
