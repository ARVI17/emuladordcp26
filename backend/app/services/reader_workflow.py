"""Local orchestration. Reading permission, observation and provider identity stay distinct."""
from collections import Counter
from time import perf_counter
from uuid import uuid4
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from app.models.entities import Player, Objective, now
from app.models.reader import ReaderWorkflow, ReaderObservation
from app.models.assisted import VisualReading
from app.services.main_squad import main_status
from app.services.observations import digest_json

SECTIONS = {'account': 'Cabecera del club', 'inventory': 'Jugadores', 'detail': 'Detalle de carta',
    'squad': 'Principal, banquillo y reservas', 'dcp': 'Requisitos DCP', 'objective': 'Objetivos', 'gallery': 'Galería'}
OBSTACLES = {
    'permission_required': 'Pulsa el icono de la extensión en la pestaña que quieres analizar para conceder permiso temporal.',
    'context_required': 'Empareja el panel desde Mi cuenta y confirma el contexto del club una vez.',
    'sensitive_screen': 'Termina el acceso o la verificación directamente en EA. El lector no inspecciona esa pantalla.',
    'profile_required': 'Perfil requiere revisión. El diagnóstico estructural está disponible en el panel; no necesitas seleccionar cada carta.',
    'authorization_required': 'Lectura automática EA pendiente de un mecanismo permitido y perfil contrastado. El diagnóstico no acredita autorización.',
    'ready_sample': 'Muestra o exportación propia reconocida. Navega personalmente; se leen únicamente las regiones cargadas.',
    'loading': 'Espera a que termine de cargar esta región; todavía no hay una lectura estable.',
    'offline': 'Backend temporalmente no disponible. Los fragmentos permanecen en la extensión con sus IDs y fechas.',
    'structure_changed': 'Perfil requiere revisión: cambió la estructura, idioma o cuenta declarada. Se conserva lo leído.',
    'paused': 'Lectura pausada. Reanudar conserva el historial; cancelar detiene la admisión automática.',
}


def current(db):
    row = db.scalar(select(ReaderWorkflow))
    if row:
        # A new entry invalidates permissions, not the persisted local checkpoint.
        row._generation_valid = row.generation == db.info['context'].generation
    return row


def begin(db):
    row = db.scalar(select(ReaderWorkflow))
    main = main_status(db)
    if not row:
        row = ReaderWorkflow(id=str(uuid4()), generation=db.info['context'].generation,
            main_hash=main['state_hash'], trusted_profiles={}, view_state={}, report={})
        db.add(row)
    elif row.generation != db.info['context'].generation:
        row.generation = db.info['context'].generation
        row.trusted_profiles, row.view_state, row.report = {}, {}, {}
    if row.status != 'active':
        row.main_hash = main['state_hash']
    row.status, row.requested_at, row.updated_at = 'active', now(), now()
    row._generation_valid = True
    db.flush()
    return row


def trust_key(observation):
    meta = observation.metadata_json
    p = meta['profile']
    # No trust transfers across grant, source, language, structure or definition edits.
    return digest_json([observation.grant_id, observation.domain, meta['source_kind'],
        {k:p[k] for k in ('profile_id','revision','definition_hash','structure_hash','origin','route','language')}])


def approve_incremental(db, observation):
    if observation.domain != 'inventory' or observation.status != 'reviewed' or observation.review_data.get('pending_records'):
        raise HTTPException(409, 'Revisa una lista de inventario completa y resuelve sus discrepancias antes de permitir actualizaciones.')
    if observation.metadata_json['scope']['location'] != 'club':
        raise HTTPException(409, 'La admisión automática solo cubre inventario en el club; otras ubicaciones requieren revisión.')
    row = current(db)
    if not row or row.generation != db.info['context'].generation:
        row = begin(db)
    if row.status != 'active':
        raise HTTPException(409, 'Reanuda el análisis antes de autorizar actualizaciones.')
    if len(row.trusted_profiles) >= 20 and trust_key(observation) not in row.trusted_profiles:
        raise HTTPException(409, 'Límite de perfiles aprobados; cancela el recorrido para revisar sus permisos.')
    row.trusted_profiles = {**row.trusted_profiles, trust_key(observation): dict(
        observation_id=observation.id, approved_at=now().isoformat(), grant_id=observation.grant_id)}


def auto_review(db, observation):
    row = current(db)
    if not row or row.generation != db.info['context'].generation or row.status != 'active' or observation.status != 'review_required':
        return
    if trust_key(observation) not in row.trusted_profiles or observation.domain != 'inventory':
        return
    if observation.metadata_json['scope']['location'] != 'club':
        return
    from app.services.observations import review_observation
    from app.services.audit import record
    result = review_observation(db, observation, automatic=True)
    row.updated_at = now()
    record(db, 'admit_incremental_observation', 'reader', 0,
        {'observation_id':observation.id, 'pending':len(result['pending_records'])})


def calculate(db, row):
    started = perf_counter()
    main = main_status(db)
    players = list(db.scalars(select(Player).where(Player.deleted.is_(False)).limit(5001)))
    observations = list(db.scalars(select(ReaderObservation).order_by(ReaderObservation.received_at.desc()).limit(1001)))
    sections = []
    for domain, label in SECTIONS.items():
        rows = [o for o in observations[:1000] if o.domain == domain]
        scopes = {(o.metadata_json['scope']['page'], o.metadata_json['scope']['filters'], o.metadata_json['scope']['location']) for o in rows}
        sections.append(dict(domain=domain, label=label, observations=len(rows), loaded_scopes=len(scopes),
            reviewed=sum(o.status == 'reviewed' for o in rows),
            observed_rows=sum(o.metadata_json['scope']['visible_count'] for o in rows),
            last_observed_at=max((o.observed_at for o in rows), default=None), complete=False))
    sources = Counter((p.validation_evidence or {}).get('source_kind', 'declared_local') for p in players)
    from app.services.squad_analysis import effective_protected_ids
    protected = effective_protected_ids(db)
    missing = Counter(f for p in players for f in (p.unknown_fields or []))
    modules = {}
    def compute(name, fn):
        try:
            result = fn()
            modules[name] = dict(status='calculated', result=result, calculated_at=now().isoformat())
        except (HTTPException, ValueError) as error:
            # Only domain validation errors are expected; unexpected failures remain server errors.
            detail = error.detail if isinstance(error, HTTPException) else str(error)
            modules[name] = dict(status='pending', reason=detail if isinstance(detail, str) else 'Faltan datos vigentes para este cálculo.')
    if len(players) > 5000:
        modules['squads'] = dict(status='pending', reason='Más de 5.000 cartas; reduce el ámbito del cálculo en Plantillas.')
    elif players:
        from app.api.analysis import squad_profiles, ProfilesRequest
        compute('squads', lambda: squad_profiles(ProfilesRequest(bench_size=7), db))
    else:
        modules['squads'] = dict(status='pending', reason='Todavía no hay cartas admitidas en este contexto. Revisa la primera región recibida.')
    # Reviewed visual requirements are separate from inventory; never infer rules from raw DOM text.
    dcps = list(db.scalars(select(VisualReading).where(VisualReading.scope == 'dcp', VisualReading.status == 'reviewed')
        .order_by(VisualReading.id.desc()).limit(3)))
    dcp_results = []
    for reading in dcps:
        from app.api.assisted import simulate_dcp
        from app.schemas.api import OptimizeRequest
        try:
            result = simulate_dcp(reading.id, OptimizeRequest(max_solutions=3), db)
            # Show the actual source mix, including synthetic observations used in tests.
            dcp_results.append(result)
        except (HTTPException, ValueError) as error:
            dcp_results.append(dict(reading_id=reading.id, status='pending', reason=str(error.detail if isinstance(error, HTTPException) else error)))
    modules['dcp'] = dict(status='calculated' if dcp_results else 'pending', proposals=dcp_results,
        reason=None if dcp_results else 'Abre un DCP y revisa sus requisitos completos en Mi cuenta. No se deducen reglas del inventario.',
        limit=3, simulation=True)
    goals = list(db.scalars(select(Objective).where(Objective.completed.is_(False))
        .order_by(Objective.id.desc()).limit(3).execution_options(include_pending_definitions=True)))
    objectives = []
    for goal in goals:
        if not goal.planning_rules:
            continue
        from app.services.objective_planning import objective_preview
        from app.schemas.objective_planning import ObjectiveProposalRequest
        try:
            result = objective_preview(db, ObjectiveProposalRequest(objective_ids=[goal.id], bench_size=7))
            for proposal in result.get('proposals', []):
                proposal.pop('token', None)  # Recalculate a fresh token in the dedicated editor before saving.
            objectives.append(result)
        except (HTTPException, ValueError) as error:
            objectives.append(dict(objective_id=goal.id, status='pending', reason=str(error.detail if isinstance(error, HTTPException) else error)))
    modules['objectives'] = dict(status='calculated' if objectives else 'pending', proposals=objectives, limit=3,
        reason=None if objectives else 'Revisa las restricciones de un objetivo para calcular su equipo. Crear equipos no completa objetivos.')
    from app.api.gallery_planning import scenarios
    gallery = scenarios(db)
    modules['gallery'] = dict(status='calculated' if gallery else 'pending', scenarios=gallery[:20],
        reason='El historial de variantes, grados reclamados y precios requiere evidencia propia; no equivale al inventario actual.',
        birmingham=dict(source='public_reference', source_url='https://www.fut.gg/fut-gallery/premier-league/birmingham-city/',
            checked_on='2026-10-27', team='Birmingham City femenino', required_players=15,
            thresholds={'D':10,'C':300,'B':500,'A':700,'S':1000}, token_rewards={'B':5,'A':8,'S':15},
            owned_count=None, history_known=False, acquisition_cost=None, progress=None,
            missing=['Identidad y variantes elegibles propias', 'Historial y premios reclamados', 'Reglas completas de bonificación y redondeo', 'Cotizaciones vigentes'],
            plan='Contrasta las variantes del conjunto con tus lecturas. El precio público 000,000 es desconocido; no se propone comprar ni se acredita posesión.'))
    modules['evolutions'] = dict(status='pending', reason='Abre Evoluciones y revisa requisitos, caducidad y la base de tu copia antes de evaluar una ruta.')
    modules['market'] = dict(status='pending', reason='Faltan cotizaciones vigentes y presupuesto revisado. Las lecturas del club no acreditan compras, ventas ni ingresos.')
    after = main_status(db)
    code = row.view_state.get('code', 'permission_required')
    pending = sum(o.status in {'review_required','partial'} or bool(o.review_data.get('pending_records')) for o in observations[:1000])
    next_action = OBSTACLES[code]
    if code == 'ready_sample' and pending:
        next_action = ('En Mi cuenta, revisa la primera región recibida. Puedes autorizar allí los siguientes incrementos sin conflictos.'
            if any(o.status=='review_required' for o in observations) else
            'Revisa las discrepancias o completa los fragmentos pendientes en Mi cuenta. Las demás lecturas pueden continuar.')
    stages = [
        dict(key='context', label='Comprobando permiso y contexto', status='complete' if code == 'ready_sample' else 'blocked', evidence=OBSTACLES[code]),
        dict(key='recognition', label='Reconociendo vista', status='complete' if code == 'ready_sample' else 'pending', evidence='Perfil de muestra propia validado' if code == 'ready_sample' else 'Compatibilidad real todavía no acreditada'),
        dict(key='reading', label='Leyendo cartas observables', status='partial' if observations else 'pending', evidence=f'{len(observations[:1000])} observaciones guardadas; alcance parcial'),
        dict(key='review', label='Actualizando datos revisados', status='partial' if pending else 'complete' if players else 'pending', evidence=f'{len(players)} cartas admitidas; {pending} observaciones pendientes'),
        dict(key='main', label='Protegiendo mi principal', status='complete' if after['complete'] else 'blocked', evidence=after['reason'] or 'Principal local identificada y protegida'),
        dict(key='calculate', label='Calculando recomendaciones', status='partial' if any(m['status']=='calculated' for m in modules.values()) else 'pending', evidence='Comprobaciones locales ejecutadas; cada módulo distingue resultados y datos pendientes'),
    ]
    row.report = jsonable_encoder(dict(stages=stages, sections=sections, global_complete=False,
        coverage_window_truncated=len(observations)>1000, inventory_count=len(players), source_counts=dict(sources),
        protected_count=len(protected), ambiguous_count=sum(p.availability != 'available' for p in players),
        unknown_fields=dict(missing), pending_observations=pending,
        main=dict(complete=after['complete'], revision=after['revision'], unchanged=after['state_hash']==row.main_hash,
            reason=after['reason'], protected_copy_ids=after['protected_copy_ids']),
        modules=modules, next_action=next_action,
        next_section=next((s['label'] for s in sections if not s['reviewed']), 'Siguiente página de Jugadores o ubicación pendiente'),
        ea_identity_verified=False, remote_navigation=False, remote_write=False,
        calculated_at=now(), context_revision=db.info['context'].revision,
        metrics=dict(calculation_ms=round((perf_counter()-started)*1000), llm_calls=0, ocr_calls=0)))
    row.updated_at = now()
    return serialize(row)


def serialize(row):
    if not row:
        return dict(status='idle', report=None, remote_write=False)
    valid = getattr(row, '_generation_valid', True)
    return dict(id=row.id, status=row.status if valid or row.status=='cancelled' else 'paused',
        requested_at=row.requested_at, updated_at=row.updated_at, context_current=valid,
        approved_profiles=len(row.trusted_profiles) if valid else 0, view=row.view_state, report=row.report, remote_write=False)
