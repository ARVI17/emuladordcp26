"""Bounded, read-only ordering of reviewed proposals, never an execution approval."""
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import select
from app.models.entities import Objective, now
from app.models.planner import ClubPlan, Reservation
from app.services.contexts import require_module, utc
from app.services.editions import current_version
from app.services.planner import revalidate, coin_commitments


def summarize(plan):
    actions = plan.inputs['actions']
    copies = {p['id']: p for a in actions for p in a['copies']}
    consumed = sorted({p for a in actions if a['kind'] in {'sell', 'dcp'} for p in a['player_ids']})
    deadlines = [utc(plan.expires_at)]
    deadlines += [datetime.fromisoformat(a[k]) for a in actions for k in ('start_before', 'complete_before') if a.get(k)]
    return {'id': plan.id, 'name': plan.name, 'status': plan.status, 'deadline': min(deadlines),
            'copy_ids': sorted(copies), 'consumed_copy_ids': consumed,
            'max_cost': sum(a['max_cost'] for a in actions), 'reserve_coins': plan.inputs['reserve_coins'],
            'known_card_value': sum(p['price'] for p in copies.values() if p['price'] is not None),
            'unknown_price_count': sum(p['price'] is None for p in copies.values()),
            'kinds': sorted({a['kind'] for a in actions}), 'plan_hash': plan.plan_hash}


def checked(db, identifier):
    plan = db.get(ClubPlan, identifier)
    if not plan or plan.inputs['binding'].get('game_version', 'FC27') != current_version(db):
        raise HTTPException(404, 'Plan no disponible en este club y edición')
    if plan.status not in {'draft', 'reviewed'}:
        raise HTTPException(409, 'Compara borradores sin ejecución ni reservas activas')
    revalidate(db, plan)
    held = set(db.scalars(select(Reservation.player_id).where(Reservation.expires_at > now())))
    if held & {pid for a in plan.inputs['actions'] for pid in a['player_ids']}:
        raise HTTPException(409, 'Hay copias reservadas por otra ruta')
    return plan


def compare(db, a_id, b_id):
    a, b = summarize(checked(db, a_id)), summarize(checked(db, b_id))
    return {'a': a, 'b': b, 'shared_copy_ids': sorted(set(a['copy_ids']) & set(b['copy_ids'])),
            'cost_delta_b_minus_a': b['max_cost']-a['max_cost'], 'alternatives_only': True,
            'message': 'Rutas alternativas, no acumulables automáticamente. El valor local de cartas no es una cotización vigente. Revisa pérdidas y precios desconocidos; ninguna ruta está aprobada.'}


def agenda(db, budget, reserve_coins, priority_ids):
    binding = require_module(db, 'analysis')
    context = db.info['context']
    if context.verified:
        require_module(db, 'market', allow_local=False)
    committed, floor = coin_commitments(db)
    balance = min(budget, context.coins or 0) if context.verified else budget
    floor = max(floor, reserve_coins)
    available = balance-committed
    candidates = list(db.scalars(select(ClubPlan).where(ClubPlan.status.in_(['draft', 'reviewed'])).order_by(ClubPlan.id.desc()).limit(101)))
    truncated = len(candidates) > 100
    candidates = [p for p in candidates[:100] if p.inputs['binding'].get('game_version', 'FC27') == current_version(db)]
    if any(identifier not in {p.id for p in candidates} for identifier in priority_ids):
        raise HTTPException(422, 'Prioriza solo borradores visibles de esta edición')
    rank = {identifier: i for i, identifier in enumerate(priority_ids)}
    candidates.sort(key=lambda p: (rank.get(p.id, len(rank)), summarize(p)['deadline'], p.id))
    used = set(db.scalars(select(Reservation.player_id).where(Reservation.expires_at > now())))
    selected, pending = [], []
    for p in candidates:
        item = summarize(p)
        try:
            revalidate(db, p)
            conflict = used & set(item['copy_ids'])
            if conflict:
                raise HTTPException(409, 'Copias comprometidas por otra ruta: '+', '.join(map(str, sorted(conflict))))
            if available-item['max_cost'] < max(floor, item['reserve_coins']):
                raise HTTPException(409, 'Presupuesto o reserva de monedas insuficiente')
        except HTTPException as exc:
            pending.append({**item, 'reason': exc.detail if isinstance(exc.detail, str) else 'Datos del club pendientes de verificar; vuelve a sincronizar'})
            continue
        available -= item['max_cost']
        floor = max(floor, item['reserve_coins'])
        used.update(item['copy_ids'])
        selected.append({**item, 'balance_after': available})
    objectives = [{'id': o.id, 'name': o.name, 'expires_at': o.expires_at, 'expired': bool(o.expires_at and utc(o.expires_at) <= now()), 'progress': o.progress, 'target': o.target} for o in db.scalars(select(Objective).where(Objective.game_version == current_version(db), Objective.completed.is_(False)).order_by(Objective.expires_at.asc().nulls_last(), Objective.id).limit(50))]
    return {'binding': binding, 'selected': selected, 'pending': pending, 'objectives': objectives,
            'committed_coins': committed, 'remaining_coins': available, 'reserve_coins': floor,
            'truncated': truncated, 'simulation': True, 'resources_reserved': False,
            'message': 'Agenda orientativa: prioridad indicada, luego caducidad; selección secuencial, no óptimo global. Objetivos locales solo como recordatorios, sin estimar esfuerzo ni recompensas. Cada plan exige su propia revisión y reserva; recalcula tras cualquier cambio.'}
