"""Synthetic evidence for pre-existing solver/workflow tests, never imported by production.

Boundary tests use plain TestClient. No application validator is mocked: these
fixtures write a separate catalog and send explicit edition/variant identifiers.
"""
import hashlib
import threading
from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.engine import make_url
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.catalog import CardVariant
from app.models.entities import Player, now
from app.schemas.api import PlayerCreate
from app.services.catalog_validation import validate_copy
_gate = threading.RLock()


def safe_database():
    name = make_url(settings.database_url).database or ''
    if name not in {'planner_review_test', 'planner_unit_test', 'fc27_test', './test_fc26.db', '/tmp/fc27-e2e.db', '/tmp/exclusive.db'}:
        raise RuntimeError('Synthetic evidence requires a known disposable test database')


def witness(values):
    with _gate:
        return _witness(values)


def _witness(values):
    safe_database()
    if values.get('game_version', 'FC27') != 'FC27':
        return values
    result = dict(values)
    result.setdefault('game_version', 'FC27')
    if not result.get('card_id'):
        result['card_id'] = 'fixture-' + hashlib.sha256(str((result.get('name'), result.get('rating'), result.get('position'), result.get('card_type'))).encode()).hexdigest()[:20]
    try:
        fields = PlayerCreate.model_validate(result).model_dump()
    except ValueError:
        return result
    with SessionLocal() as db:
        row = db.scalar(select(CardVariant).where(CardVariant.variant_id == fields['card_id']))
        if row is None:
            row = CardVariant(game_version='FC27', variant_id=fields['card_id'])
            db.add(row)
        for key in ('name', 'rating', 'position', 'card_type'):
            setattr(row, key, fields[key])
        row.validation_status = 'documented'
        row.source_url = 'https://example.invalid/fc27/synthetic-fixture'
        row.observed_at, row.valid_until = now()-timedelta(seconds=1), now()+timedelta(days=1)
        row.evidence = {'synthetic': True, 'official': False}
        db.commit()
    return result


def prepare_payload(path, method, payload):
    if not isinstance(payload, dict):
        return payload
    path = str(path).removeprefix('/api')
    if path == '/players' and method.upper() == 'POST':
        return witness(payload)
    if path.startswith('/players/') and method.upper() == 'PATCH':
        if not set(payload) & {'game_version', 'card_id', 'name', 'rating', 'position', 'card_type'}:
            return payload
        try:
            identifier = int(path.rsplit('/', 1)[1])
        except ValueError:
            return payload
        with SessionLocal() as db:
            player = db.get(Player, identifier)
            if player:
                fields = {k: getattr(player, k) for k in PlayerCreate.model_fields}
                updated = {**fields, **payload}
                if any(k in payload and payload[k] != fields[k] for k in ('name', 'rating', 'position', 'card_type')) and payload.get('card_id', fields['card_id']) == fields['card_id']:
                    updated['card_id'] = None
                    prepared = witness(updated)
                    return {**payload, 'card_id': prepared['card_id']}
                witness(updated)
    if path.startswith('/emulator/scans/') and path.endswith('/import'):
        return {**payload, 'players': [witness(p) for p in payload.get('players', [])]}
    if path == '/transfers/compare':
        return {**payload, 'candidates': [{**c, 'card': witness(c['card'])} for c in payload.get('candidates', [])]}
    if path in {'/market/quotes', '/market/journal', '/market/alerts'} and payload.get('variant_id'):
        with SessionLocal() as db:
            if db.scalar(select(CardVariant.id).where(CardVariant.variant_id == payload['variant_id'])):
                return payload
        witness(dict(game_version=payload.get('game_version', 'FC27'), card_id=payload['variant_id'], name='Synthetic market fixture', rating=80, position='MC', league='Test', club='Test', nationality='Test'))
    return payload


def activate_seed():
    safe_database()
    with SessionLocal() as db:
        rows = list(db.scalars(select(Player)))
        for player in rows:
            db.add(CardVariant(game_version='FC27', variant_id=player.card_id,
                **{k: getattr(player, k) for k in ('name', 'rating', 'position', 'card_type')},
                source_url='https://example.invalid/fc27/synthetic-fixture',
                observed_at=now()-timedelta(seconds=1), valid_until=now()+timedelta(days=1),
                validation_status='documented', evidence={'synthetic': True, 'official': False}))
        db.flush()
        for player in rows:
            player.data_source = 'synthetic_test_fixture'
            validate_copy(db, player)
        from app.models.entities import Squad
        from app.services.definition_validation import MODELS
        for model in MODELS.values():
            for row in db.scalars(select(model)):
                witness_definition(row)
        for row in db.scalars(select(Squad)):
            row.origin = 'manual'
        # Synthetic evidence includes an explicitly chosen, complete main squad.
        # Production never infers this from old flags. Boundary tests omit this fixture.
        from app.models.squad_safety import MainSquadState
        squad = db.scalar(select(Squad).where(Squad.primary.is_(True)))
        if squad and db.scalar(select(MainSquadState.id)) is None:
            members = [{'player_id': m.player_id, 'slot': m.slot} for m in squad.players]
            db.add(MainSquadState(squad_id=squad.id, snapshot={'name': squad.name, 'formation': squad.formation,
                'tactic': squad.tactic, 'manager': None, 'source': 'synthetic_user_selection', 'complete': True,
                'members': members, 'observed_at': now().isoformat(), 'ea_active_squad': False},
                locked_copy_ids=[m['player_id'] for m in members], history=[]))
        db.commit()


def witness_definition(row):
    row.validation_status = 'documented'
    row.validation_evidence = {'game_version': 'FC27', 'source_url': 'https://example.invalid/fc27/synthetic-definition',
        'observed_at': (now()-timedelta(seconds=1)).isoformat(), 'valid_until': (now()+timedelta(days=1)).isoformat(), 'synthetic': True}


def witness_definitions(db, *_):
    from app.models.entities import DefinitionEvidence
    for row in list(db.new | db.dirty):
        if isinstance(row, DefinitionEvidence) and row.game_version in (None, 'FC27'):
            witness_definition(row)
