"""Personal recommendations from the current club's admitted, dated evidence."""
from dataclasses import asdict
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select

from app.models.assisted import VisualReading
from app.models.entities import Challenge, GalleryEntry, GallerySet, Player, Segment, now
from app.models.planner import MarketQuote
from app.optimizers.sbc import solve, validate_solution
from app.schemas.api import OptimizeRequest
from app.schemas.assisted import VisualDcp
from app.services.contexts import require_module, utc
from app.services.dcp_review import eligible
from app.services.gallery_v2 import evaluate_v2
from app.services.main_squad import fingerprint, main_status
from app.services.remote_evidence import field_known
from app.services.squad_analysis import best_owned_squad, effective_protected_ids


def protection(db):
    main = main_status(db)
    members = (main['snapshot'] or {}).get('members', [])
    locks = set(main['protected_copy_ids'])
    slots = [row['slot'] for row in members if row['player_id'] in locks]
    bench = sum(s.startswith('BENCH-') for s in slots)
    reserves = sum(s.startswith('RESERVE-') for s in slots)
    starters = len(slots) - bench - reserves
    return dict(ready=main['complete'] and starters == 11 and bench >= 7,
                starters=starters, bench=bench, reserves=reserves)


def match_plan(db, style='balanced'):
    binding = require_module(db, 'squads')
    players = list(db.scalars(select(Player).where(Player.game_version == 'FC27',
        Player.deleted.is_(False), Player.availability == 'available').order_by(Player.id)))
    reviewed = [p for p in players if p.data_reviewed or (p.validation_evidence or {}).get('kind') == 'observed_copy']
    dates = [(p.validation_evidence or {}).get('observed_at') for p in reviewed]
    best = best_owned_squad(reviewed, 'FC27', effective_protected_ids(db), style=style, bench_size=7) if reviewed else None
    proposal = None
    if best:
        proposal = dict(formation=best['formation'], solver_status=best['solver_status'],
            lineup=[dict(slot=r['slot'], position=r['position'], id=r['player']['id'], name=r['player']['name'],
                         rating=r['player']['rating'], fit=r['fit_score'], reason=r['explanation']) for r in best['lineup']],
            bench=[{k: p[k] for k in ('id', 'name', 'position', 'rating')} for p in best['bench']],
            gaps=[{k: g[k] for k in ('slot', 'position')} for g in best['gaps']])
    latest = max((utc(datetime.fromisoformat(d)) for d in dates if d), default=None)
    return dict(binding=binding, style=style, reviewed=len(reviewed), latest_card_observation=latest,
                protection=protection(db), squad=proposal, additional_spend=0, official_chemistry=None)


def documented_segments(db, ready):
    from app.api.routes import requirements_for_batch, score_progress
    require_module(db, 'dcp')
    rows = list(db.scalars(select(Segment).join(Challenge).where(Challenge.game_version == 'FC27',
        Challenge.completed.is_(False), Challenge.expires_at > now(), Segment.completed.is_(False))
        .order_by(Challenge.expires_at, Segment.id).limit(3)))
    if not rows:
        return []
    protected = effective_protected_ids(db)
    players = list(db.scalars(select(Player).where(Player.game_version == 'FC27', Player.deleted.is_(False))))
    candidates = eligible(db, players, OptimizeRequest().filters, protected)
    by_id = {p.id: p for p in candidates}
    result = []
    for row in rows:
        rules = requirements_for_batch(db, row)
        current = score_progress(db, row) if rules['kind'] == 'score' else 0
        options = solve(candidates, rules, max_solutions=1, effective_protected_ids=protected, current_score=current) if ready else []
        option = next((s for s in options if not validate_solution([by_id[i] for i in s.player_ids], rules, current_score=current)), None)
        result.append(dcp_item(f'{row.challenge.name} · {row.name}', row.challenge.expires_at, ready, asdict(option) if option else None,
                               [by_id[i].name for i in option.player_ids] if option else []))
    return result


def dcp_item(name, expires_at, ready, option, names):
    state = 'protection_pending' if not ready else 'no_solution'
    if option:
        state = 'covered' if option['will_complete'] else 'partial'
    return dict(name=name, expires_at=expires_at, status=state, players=names,
                card_value=option['total_cost'] if option else None)


def observed_segments(db, ready):
    from app.api.assisted import simulate_dcp
    readings = db.scalars(select(VisualReading).where(VisualReading.scope == 'dcp', VisualReading.status == 'reviewed')
        .order_by(VisualReading.observed_at.desc(), VisualReading.id.desc()).limit(50))
    seen, active = set(), []
    for row in readings:
        data = row.reviewed.get('dcp')
        if not data or not data.get('reviewed'):
            continue
        draft = VisualDcp.model_validate(data)
        if not draft.expires_at or utc(draft.expires_at) <= now():
            continue
        key = fingerprint([draft.name, utc(draft.expires_at).isoformat(), draft.requirements])
        if key not in seen:
            seen.add(key)
            active.append((draft.expires_at, row.id, draft.name))
    results = []
    for expiry, identifier, name in sorted(active)[:3]:
        options = simulate_dcp(identifier, OptimizeRequest(max_solutions=1), db)['solutions'] if ready else []
        option = next(iter(options), None)
        results.append(dcp_item(name, expiry, ready, option, [p['name'] for p in option['players']] if option else []))
    return results


def sale_listings(db, ready):
    if not ready:
        return dict(items=[], reason='Primero se deben identificar y proteger los once titulares y los siete suplentes.')
    context = db.info['context']
    if not context.verified or context.platform != 'Console':
        return dict(items=[], reason='Falta acreditar el mercado de consola de este club con una lectura del juego.')
    try:
        require_module(db, 'market', allow_local=False)
    except HTTPException as error:
        if error.status_code != 409:
            raise
        return dict(items=[], reason='Falta una lectura vigente del club y su mercado de consola.')
    at = now()
    protected = effective_protected_ids(db)
    pairs = db.execute(select(Player, MarketQuote).join(MarketQuote, MarketQuote.variant_id == Player.card_id)
        .where(Player.game_version == 'FC27', Player.deleted.is_(False), Player.availability == 'available',
               Player.tradable.is_(True), Player.is_loan.is_(False), Player.id.not_in(protected),
               MarketQuote.game_version == 'FC27', MarketQuote.market == 'Console', MarketQuote.kind == 'listing',
               MarketQuote.currency == 'coins', MarketQuote.amount > 0, MarketQuote.expires_at > at,
               MarketQuote.observed_at.between(at-timedelta(hours=24), at))
        .order_by(MarketQuote.observed_at.desc(), MarketQuote.id.desc(), Player.id))
    latest = {}
    for p, quote in pairs:
        if p.id not in latest and all(field_known(p, k) for k in ('tradable', 'card_id', 'is_loan', 'is_evolution')):
            latest[p.id] = dict(id=p.id, name=p.name, amount=quote.amount, observed_at=quote.observed_at,
                                source_url=quote.source_url)
    return dict(items=sorted(latest.values(), key=lambda q: (-q['amount'], q['id']))[:3],
                reason=None if latest else 'Faltan anuncios vigentes para una variante transferible y disponible fuera del equipo protegido.')


def opportunities(db):
    require_module(db, 'analysis')
    ready = protection(db)['ready']
    assisted = db.info['local_session'].mode == 'assisted'
    dcp_reason = None
    try:
        dcps = observed_segments(db, ready) if assisted else documented_segments(db, ready)
    except HTTPException as error:
        if error.status_code != 409:
            raise
        dcps = []
        dcp_reason = error.detail if isinstance(error.detail, str) else 'Falta cobertura vigente de los requisitos de DCP en este club.'
    gallery = []
    try:
        require_module(db, 'gallery')
    except HTTPException as error:
        if error.status_code != 409:
            raise
    else:
        sets = db.scalars(select(GallerySet).where(GallerySet.rules_reviewed.is_(True),
            GallerySet.rules['schema_version'].as_integer() == 2).order_by(GallerySet.id).limit(3)).all()
        history = list(db.scalars(select(GalleryEntry))) if sets else []
        for item in sets:
            evaluation = evaluate_v2(item, history)
            gallery.append(dict(name=item.name, filled=evaluation['filled_slots'], required=evaluation['required_slots']))
    return dict(dcp=dcps, dcp_source='observed' if assisted else 'documented', dcp_reason=dcp_reason,
                sales=sale_listings(db, ready), gallery=gallery)


def explain_opportunity(db, focus):
    from app.services.locks import resource_locks
    with resource_locks(db, 'inventory'):
        db.expire_all()
        evidence = opportunities(db)
    if focus == 'market':
        sales = evidence['sales']
        return sales['reason'] or 'Anuncios registrados de consola para copias disponibles: ' + ', '.join(
            f"{item['name']} ({item['amount']} monedas, {utc(item['observed_at']):%Y-%m-%d %H:%M} UTC)" for item in sales['items']) + '.'
    if focus == 'gallery':
        return ('Tu historial cubre ' + ', '.join(f"{g['filled']} de {g['required']} puestos en {g['name']}" for g in evidence['gallery']) + '.'
                if evidence['gallery'] else 'Faltan conjuntos con reglas vigentes y datos de colección para calcular una ruta de Galería.')
    if not evidence['dcp']:
        return evidence['dcp_reason'] or 'Faltan requisitos revisados con vencimiento vigente para proponerte un DCP con tus cartas.'
    messages = []
    for d in evidence['dcp']:
        if d['players']:
            outcome = 'puedes cubrir este segmento' if d['status'] == 'covered' else 'puedes aportar parte de los puntos'
            value = 'valor de las cartas pendiente' if d['card_value'] is None else f"valor registrado de {d['card_value']} monedas"
            messages.append(f"{d['name']}: {outcome} con {', '.join(d['players'])}, cero compras y {value}.")
        else:
            reason = 'faltan las protecciones del once y el banquillo' if d['status'] == 'protection_pending' else 'no se encontró una combinación con las cartas disponibles'
            messages.append(f"{d['name']}: {reason}.")
    return ' '.join(messages)
