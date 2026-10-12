"""Versioned local objective proposals, separate from observed match progress."""
import base64
import binascii
import hashlib
import hmac
import json
import time
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from app.models.entities import Objective, Player, now
from app.models.planner import Reservation
from app.schemas.objective_planning import ObjectiveRules
from app.services.contexts import require_module, utc
from app.services.main_squad import fingerprint, main_status
from app.services.planner import inventory_fingerprint
from app.services.protection import reserved_ids
from app.services.squad_analysis import effective_protected_ids, compare_main
from app.services.objective_squads import solve_objective_squad, validate_composition, context_compatibility


def get_goal(db, identifier):
    row = db.scalar(select(Objective).where(Objective.id == identifier).execution_options(include_pending_definitions=True))
    if row is None:
        raise HTTPException(404, 'Objetivo no disponible en este club FC27')
    return row


def goal_data(row):
    from app.services.definition_validation import is_documented
    progress = row.progress_evidence or {}
    value = progress.get('value') if progress.get('origin') in {'manual', 'observed'} else None
    expired = row.expires_at is not None and utc(row.expires_at) <= now()
    return dict(id=row.id, name=row.name, description=row.description, category=row.category, game_version='FC27',
        target=row.target, expires_at=row.expires_at, expired=expired, rules=row.planning_rules or None,
        revision=row.planning_revision, rule_origin='manual',
        definition_verified=is_documented(row) and not expired,
        progress=dict(value=value, origin=progress.get('origin','unknown'), observed_at=progress.get('observed_at'), note=progress.get('note')),
        completed=value is not None and value >= row.target,
        message='Transcripción auxiliar revisada; no acredita un objetivo oficial activo ni progreso de EA.')


def load_goals(db, identifiers):
    goals = []
    for identifier in identifiers:
        row = get_goal(db, identifier)
        if row.expires_at and utc(row.expires_at) <= now():
            raise HTTPException(409, f'El objetivo #{identifier} está vencido; revisa su versión antes de recalcular.')
        try:
            rules = ObjectiveRules.model_validate(row.planning_rules or {})
        except ValidationError:
            raise HTTPException(409, f'El objetivo #{identifier} aún no tiene reglas auxiliares normalizadas y revisadas.') from None
        if not rules.reviewed:
            raise HTTPException(409, f'Revisa explícitamente las reglas del objetivo #{identifier}.')
        goals.append(dict(id=row.id, row=row, rules=rules))
    return goals


def proposal_state(db, goals):
    context, session = db.info['context'], db.info['local_session']
    dependencies = set(identifier for goal in goals for identifier in goal['rules'].dependencies)
    related = list(db.scalars(select(Objective).where(Objective.id.in_(dependencies)).execution_options(include_pending_definitions=True))) if dependencies else []
    return fingerprint(dict(context=context.id, entry=session.entry_id, snapshot=context.snapshot_id, revision=context.revision,
        inventory=inventory_fingerprint(db), goals=[dict(id=g['id'], rules=g['row'].planning_rules, revision=g['row'].planning_revision,
            name=g['row'].name, target=g['row'].target, progress=g['row'].progress_evidence, expires=g['row'].expires_at) for g in goals],
        dependencies=[dict(id=g.id, progress=g.progress_evidence, target=g.target, expires=g.expires_at) for g in related],
        reservations=[(r.player_id, r.plan_id, str(r.expires_at)) for r in db.scalars(select(Reservation).where(Reservation.expires_at > now()).order_by(Reservation.player_id))]))


def sign_proposal(db, goals, squad, avoid_main):
    from app.api.routes import _import_secret
    deadlines = [utc(g['row'].expires_at).timestamp() for g in goals if g['row'].expires_at]
    payload = dict(purpose='objective_squad_v1', state=proposal_state(db, goals), objective_ids=[g['id'] for g in goals],
        formation=squad['formation'], lineup=[dict(slot=r['slot'], player_id=r['player']['id']) for r in squad['lineup']],
        bench_ids=[p['id'] for p in squad['bench']], avoid_main=avoid_main,
        expires=int(min([time.time()+300, *deadlines])))
    encoded = base64.urlsafe_b64encode(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).decode().rstrip('=')
    return encoded+'.'+hmac.new(_import_secret(db), encoded.encode(), hashlib.sha256).hexdigest()


def check_proposal(db, token):
    from app.api.routes import _import_secret
    try:
        encoded, signature = token.split('.')
        if not hmac.compare_digest(signature, hmac.new(_import_secret(db), encoded.encode(), hashlib.sha256).hexdigest()):
            raise ValueError()
        claim = json.loads(base64.urlsafe_b64decode(encoded+'='*(-len(encoded)%4)))
        if claim['purpose'] != 'objective_squad_v1' or claim['expires'] <= time.time():
            raise ValueError()
        goals = load_goals(db, claim['objective_ids'])
        require_module(db, 'squads')
        if claim['state'] != proposal_state(db, goals):
            raise ValueError()
        main = main_status(db)
        if claim['avoid_main'] and not main['complete']:
            raise ValueError()
        excluded = reserved_ids(db) | (set(main['protected_copy_ids']) if claim['avoid_main'] else set())
        ids = [r['player_id'] for r in claim['lineup']]+claim['bench_ids']
        players = list(db.scalars(select(Player).where(Player.id.in_(ids), Player.deleted.is_(False))))
        checked = validate_composition(players, claim['lineup'], claim['bench_ids'], goals, claim['formation'], len(claim['bench_ids']), excluded)
        if not checked['valid'] or any(c['status'] == 'failed' for c in checked['checklist']):
            raise ValueError()
        return claim, goals, checked, players
    except (ValueError, KeyError, TypeError, binascii.Error):
        raise HTTPException(409, 'La propuesta caducó o cambiaron inventario, objetivo, reglas o protecciones. Vuelve a calcularla.') from None


def objective_preview(db, payload):
    binding = require_module(db, 'squads')
    goals = load_goals(db, payload.objective_ids)
    context = context_compatibility(goals)
    if not context['compatible']:
        return dict(status='conflict', context=context, proposals=[], objectives=[goal_data(g['row']) for g in goals], binding=binding, simulation=True)
    main = main_status(db)
    if payload.avoid_main and not main['complete']:
        raise HTTPException(409, 'Revisa primero la principal completa para verificar una alternativa sin sus copias.')
    players = list(db.scalars(select(Player).where(Player.deleted.is_(False), Player.availability == 'available')))
    reserved, protected = reserved_ids(db), effective_protected_ids(db)
    strategies = [('A', 'Composición con propias', False, payload.avoid_main),
                  ('B', 'Mejor encaje sin compras', True, payload.avoid_main)]
    pending = []
    if main['complete'] and not payload.avoid_main:
        strategies.append(('C', 'Sin reutilizar la principal', True, True))
    elif not main['complete']:
        pending.append(dict(profile='C', reason='Identifica y revisa la principal para acreditar una alternativa sin sus copias.'))
    proposals, signatures = [], {}
    for code, label, competitive, avoid in strategies:
        excluded = reserved | (set(main['protected_copy_ids']) if avoid else set())
        squad = solve_objective_squad(players, goals, formation=payload.formation, bench_size=payload.bench_size,
            excluded=excluded, protected=protected, competitive=competitive)
        if squad['status'] not in {'optimal', 'feasible'}:
            pending.append(dict(profile=code, reason=squad['reason'], status=squad['status']))
            continue
        signature = (squad['formation'], tuple((r['slot'],r['player']['id']) for r in squad['lineup']), tuple(p['id'] for p in squad['bench']))
        if signature in signatures:
            signatures[signature]['profiles'].append(label)
            continue
        squad['main_comparison'] = compare_main(db, squad)
        proposal = dict(key=code, profiles=[label], name=('Objetivos '+code+' - '+' / '.join(g['row'].name for g in goals))[:93]+' - FC27',
            squad=squad, token=sign_proposal(db, goals, squad, avoid), avoid_main=avoid,
            active_objective_verified=all(goal_data(g['row'])['definition_verified'] for g in goals),
            objective_completed=False)
        signatures[signature] = proposal
        proposals.append(proposal)
    warnings = []
    if context['pending']:
        warnings.append('Falta revisar modalidad o dificultad; la composición no acredita el contexto de juego.')
    for goal in goals:
        row, rules = goal['row'], goal['rules']
        if row.expires_at is None:
            warnings.append(f'Objetivo #{row.id}: vencimiento desconocido.')
        if rules.loans_allowed is None:
            warnings.append(f'Objetivo #{row.id}: cesiones sin revisar; solo se proponen copias conocidas sin cesión.')
        if rules.minimum_loan_matches is not None:
            warnings.append(f'Objetivo #{row.id}: los partidos restantes de cesión no están disponibles; las cesiones quedan excluidas.')
        for dependency in rules.dependencies:
            other = get_goal(db, dependency)
            if not goal_data(other)['completed']:
                warnings.append(f'Objetivo #{row.id}: dependencia #{dependency} sin cumplimiento registrado.')
    pending.append(dict(profile='D', reason='Las propuestas propias no requieren compras.' if proposals else 'No se acredita un fichaje necesario: falta un catálogo de candidatas con metadatos y cesión verificados, cobertura completa del club y cotizaciones vigentes.'))
    return dict(status='proposals' if proposals else 'unverified', binding=binding, context=context,
        proposals=proposals, pending=pending, warnings=warnings, simulation=True,
        objectives=[goal_data(g['row']) for g in goals],
        actions_pending=[dict(objective_id=g['id'], **a.model_dump(), status='pending_match') for g in goals for a in g['rules'].actions],
        progress_changed=False, message='Composición lista no significa objetivo completado. No se ejecutan partidos ni se reclaman premios.')
