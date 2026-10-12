"""Manual review records a draft; only documented evidence admits game rules."""
from sqlalchemy import and_, event, func, inspect, or_
from sqlalchemy.orm import Session
from app.models.entities import Challenge, DefinitionEvidence, EvolutionDefinition, GallerySet, Objective, Segment, now
from app.models.planner import PublicDefinition

MODELS = {'dcp': Challenge, 'objective': Objective, 'gallery': GallerySet, 'evolution': EvolutionDefinition, 'public': PublicDefinition}
ACCEPTED = ('documented', 'provider_verified')


def active_definition_clause(model):
    evidence = model.validation_evidence
    stamp = now().isoformat()
    clauses = [model.game_version == 'FC27', model.validation_status.in_(ACCEPTED),
               evidence['game_version'].as_string() == 'FC27',
               evidence['observed_at'].as_string() <= stamp,
               evidence['valid_until'].as_string() > stamp,
               evidence['source_url'].as_string().like('https://%')]
    if hasattr(model, 'expires_at'):
        clauses.append(or_(model.expires_at.is_(None), model.expires_at > now()))
    return func.coalesce(and_(*clauses), False)


def pending_result(row):
    return {'id': row.id, 'game_version': 'FC27', 'validation_status': 'pending_verification',
            'available': False, 'message': 'Borrador conservado. Falta evidencia vigente de las reglas FC27; no participa en cálculos.'}


def is_documented(row):
    evidence = row.validation_evidence or {}
    stamp = now().isoformat()
    return (row.game_version == 'FC27' and row.validation_status in ACCEPTED
            and evidence.get('game_version') == 'FC27'
            and evidence.get('observed_at', 'z') <= stamp < evidence.get('valid_until', '')
            and evidence.get('source_url', '').startswith('https://'))


@event.listens_for(Session, 'before_flush')
def invalidate_changed_rules(db, *_):
    if 'club_context_id' not in db.info:
        return  # Reviewed imports/migrations are internal, never an HTTP bypass.
    for row in list(db.dirty | db.new):
        changed = {a.key for a in inspect(row).attrs if a.history.has_changes()}
        if isinstance(row, DefinitionEvidence) and changed - {'completed', 'progress', 'validation_status', 'validation_evidence'}:
            row.validation_status = 'pending_verification'
            row.validation_evidence = {'reason': 'Las reglas cambiaron; requieren nuevo contraste documental'}
        if isinstance(row, Segment) and changed & {'name', 'requirements'}:
            parent = row.challenge or db.get(Challenge, row.challenge_id, execution_options={'include_pending_definitions': True})
            if parent:
                parent.validation_status = 'pending_verification'
                parent.validation_evidence = {'reason': 'Cambió un segmento; evidencia anterior invalidada'}
