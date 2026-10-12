"""A manual checklist is not an EA executor or a receipt of irreversible delivery."""
from datetime import timedelta
from fastapi import HTTPException
from sqlalchemy import or_, select
from app.models.entities import Player, now
from app.models.planner import ClubPlan, PlanAction
from app.services.assisted import require_assisted, reading_row, safe_text, identity_key
from app.services.contexts import utc
from app.services.main_squad import fingerprint
from app.services.objective_planning import check_proposal, load_goals, proposal_state

ACTIVE = {'draft','reviewed','approved','pending_application','checking','paused','failed','uncertain','result_declared','result_observed'}


def own_plan(db, identifier):
    plan = db.scalar(select(ClubPlan).where(ClubPlan.id == identifier))
    if not plan or plan.inputs.get('mode') != 'assisted_guided':
        raise HTTPException(404, 'Guía no disponible')
    return plan


def plan_data(db, plan):
    steps = list(db.scalars(select(PlanAction).where(PlanAction.plan_id == plan.id).order_by(PlanAction.ordinal)))
    result = dict(id=plan.id, name=plan.name, status=plan.status, expires_at=plan.expires_at,
        binding=plan.inputs['binding'], formation=plan.inputs['formation'], rules=plan.inputs['rules'],
        approval=plan.approval, steps=[dict(id=s.id, ordinal=s.ordinal, status=s.status, **s.details, receipt=s.receipt) for s in steps],
        direct_application_available=False, action='prepare_objective_squad', consumption=False, progress_changed=False)
    result['state_hash'] = fingerprint(result)
    return result


def validate_live(db, plan):
    require_assisted(db)
    goals = load_goals(db, plan.inputs['objective_ids'])
    if utc(plan.expires_at) <= now() or plan.entry_id != db.info['local_session'].entry_id or plan.inputs['state'] != proposal_state(db, goals):
        raise HTTPException(409, 'La aprobación caducó o cambiaron cuenta, entrada, cartas, reservas, principal o reglas. Conserva el resultado incierto y prepara una propuesta nueva tras revisarlo.')
    return goals


def create_guide(db, token):
    require_assisted(db)
    claim, goals, checked, players = check_proposal(db, token)
    if not checked['composition_ready']:
        raise HTTPException(409, 'Resuelve las restricciones de composición pendientes antes de preparar la guía.')
    source = fingerprint(claim)
    previous = db.scalar(select(ClubPlan).where(ClubPlan.inputs['source'].as_string() == source))
    if previous:
        return plan_data(db, previous)
    # Recomputing the same operation must not invite a repeat while outcome is unknown.
    operation = fingerprint(dict(objectives=claim['objective_ids'], lineup=claim['lineup'], bench=claim['bench_ids']))
    if db.scalar(select(ClubPlan.id).where(ClubPlan.inputs['operation'].as_string() == operation,
            or_(ClubPlan.status.in_(ACTIVE), ClubPlan.approval['outcome_unknown'].as_boolean().is_(True)))):
        raise HTTPException(409, 'Ya existe una guía de esta propuesta pendiente o incierta. Comprueba su resultado antes de repetirla.')
    binding = dict(game_version='FC27', context_id=db.info['context'].id, entry_id=db.info['local_session'].entry_id,
        snapshot=claim['state'], identity='user_reviewed_visual', economic_limit=0, action='prepare_objective_squad')
    plan = ClubPlan(name=('Preparar equipo · '+goals[0]['row'].name)[:120], status='draft',
        entry_id=binding['entry_id'], snapshot_id=None, revision=db.info['context'].revision, plan_hash=source,
        expires_at=min([now()+timedelta(minutes=15), *[utc(g['row'].expires_at) for g in goals if g['row'].expires_at]]),
        inputs=dict(mode='assisted_guided', binding=binding, source=source, operation=operation, state=claim['state'],
            formation=claim['formation'], objective_ids=claim['objective_ids'],
            rules=[dict(id=g['id'], name=g['row'].name, revision=g['row'].planning_revision, rules=g['row'].planning_rules) for g in goals]), approval={})
    db.add(plan)
    db.flush()
    by_id = {p.id:p for p in players}
    members = [*claim['lineup'], *[dict(player_id=i,slot=f'BENCH-{n}') for n,i in enumerate(claim['bench_ids'],1)]]
    for n, member in enumerate(members):
        p = by_id[member['player_id']]
        db.add(PlanAction(plan_id=plan.id, ordinal=n, kind='prepare_squad', player_ids=[p.id], details=dict(
            player_id=p.id, name=p.name, rating=p.rating, position=p.position, card_type=p.card_type or None, slot=member['slot'],
            identity_key=identity_key({k:getattr(p,k) for k in ('name','rating','position','card_type')}),
            search=f'{p.name} · {p.rating} · {p.position}',
            expected=f'Colocar manualmente esta copia en {member["slot"]} de una plantilla alternativa.',
            check='Comparar nombre, media, variante y posición visibles. No entregar, comprar ni activar la principal.',
            ea_copy_id=None)))
    db.flush()
    return plan_data(db, plan)


def transition(db, plan, payload):
    require_assisted(db)
    before = plan_data(db, plan)
    action = payload.action
    evidence_ids = sorted(set(payload.reading_ids))
    # An exact replay is read-only, including after reconciliation or expiration.
    receipt = plan.approval.get('result', {})
    if action == 'check' and evidence_ids and receipt.get('reading_ids') == evidence_ids:
        return before
    if action == 'reconcile' and plan.status == 'reconciled':
        return before
    if payload.expected_hash != before['state_hash']:
        raise HTTPException(409, 'La guía cambió en otra pestaña. Revisa su estado actual.')
    if action not in {'cancel','pause','check','reconcile','declare','fail'}:
        validate_live(db, plan)
    approval = dict(plan.approval)
    steps = list(db.scalars(select(PlanAction).where(PlanAction.plan_id == plan.id).order_by(PlanAction.ordinal)))
    if action == 'review' and plan.status == 'draft':
        plan.status = 'reviewed'
    elif action == 'approve' and plan.status == 'reviewed':
        if payload.phrase != f'APROBAR GUIA {plan.id}':
            raise HTTPException(422, 'Escribe la frase exacta de aprobación de esta guía')
        approval.update(binding=plan.inputs['binding'], plan_hash=plan.plan_hash, approved_at=now().isoformat(),
            expires_at=utc(plan.expires_at).isoformat(), direct_write=False, scope='Preparación manual de plantilla para jugar; sin operaciones irreversibles')
        plan.status = 'approved'
    elif action == 'start' and plan.status in {'approved','paused'} and approval.get('approved_at'):
        plan.status = 'pending_application'
        approval['outcome_unknown'] = True
    elif action == 'next' and plan.status == 'pending_application':
        pending = next((s for s in steps if s.status == 'pending'), None)
        if not pending:
            raise HTTPException(409, 'Los pasos ya están declarados; comprueba la pantalla final.')
        pending.status = 'declared'
        pending.receipt = dict(origin='manual_declaration', at=now().isoformat(), executed_by_server=False)
    elif action == 'pause' and plan.status in {'approved','pending_application'}:
        plan.status = 'paused'
    elif action == 'cancel' and plan.status in ACTIVE:
        plan.status = 'cancelled'
        approval['cancellation'] = dict(at=now().isoformat(), ea_reversed=False, note=safe_text(payload.note))
    elif action == 'declare' and plan.status in {'pending_application','paused','checking','uncertain'}:
        plan.status = 'result_declared'
        approval['declaration'] = dict(at=now().isoformat(), note=safe_text(payload.note), verified=False)
    elif action == 'fail' and plan.status in {'pending_application','paused','checking','uncertain','result_declared'}:
        if len(payload.note.strip()) < 5:
            raise HTTPException(422, 'Describe el fallo que revisaste antes de registrarlo.')
        plan.status = 'failed'
        approval['outcome_unknown'] = True
        approval['failure'] = dict(at=now().isoformat(), note=safe_text(payload.note), origin='manual_declaration', provider_verified=False)
    elif action == 'check' and (plan.status in {'pending_application','paused','checking','uncertain','result_declared','result_observed'} or plan.status in {'cancelled','failed'} and approval.get('outcome_unknown')):
        if not evidence_ids:
            plan.status = 'checking'
        else:
            rows = [reading_row(db,i) for i in evidence_ids]
            if any(r.scope != 'result' or r.status != 'reviewed' or utc(r.observed_at) < utc(plan.created_at) for r in rows):
                raise HTTPException(409, 'Selecciona lecturas de resultado posteriores a la creación de esta guía, revisadas en este contexto.')
            observed = [c for r in rows for c in r.reviewed.get('cards',[])]
            slots = [c.get('slot') for c in observed]
            differences = []
            if len(set(slots)) != len(slots):
                differences.append('Hay posiciones repetidas entre las pantallas seleccionadas')
            for step in steps:
                matches = [c for c in observed if c.get('slot') == step.details['slot'] and identity_key(c) == step.details['identity_key']]
                if len(matches) != 1:
                    differences.append(f'Falta acreditar {step.details["name"]} en {step.details["slot"]}')
            if not all(r.reviewed.get('formation') == plan.inputs['formation'] for r in rows):
                differences.append('La formación no coincide o no fue revisada')
            approval_current = True
            try:
                validate_live(db, plan)
            except HTTPException:
                approval_current = False
            result = dict(id=fingerprint([plan.id,evidence_ids]), reading_ids=evidence_ids,
                origin='user_reviewed_visual', observed_at=max(utc(r.observed_at) for r in rows).isoformat(),
                differences=differences, provider_verified=False, exact_ea_copies_verified=False,
                supported_fact='Composición visible de plantilla alternativa' if not differences else None,
                approval_current=approval_current, approval_warning=None if approval_current else 'La aprobación anterior ya no permite continuar pasos. Este recibo conserva únicamente la composición observada.',
                coins_changed=False, cards_consumed=False, objective_completed=False)
            approval['result'] = result
            approval['checks'] = [*approval.get('checks', [])[-19:], result]
            plan.status = 'uncertain' if differences else 'result_observed'
    elif action == 'reconcile' and plan.status == 'result_observed':
        plan.status = 'reconciled'
        approval['outcome_unknown'] = False
        approval['reconciled_at'] = now().isoformat()
        # Only the supported visual lineup receipt is persisted. No stock, balance,
        # active principal, objectives, rewards or consumption can be inferred here.
    else:
        raise HTTPException(409, 'La acción no corresponde al estado actual. No se repitió ninguna operación.')
    plan.approval = approval
    db.flush()
    return plan_data(db, plan)
