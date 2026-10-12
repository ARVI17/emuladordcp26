"""Admission of observed copies, independent of documentary catalog freshness.

Only the internal reconciler creates this evidence. There is no HTTP importer
for it. The SQL proof joins context, mapping, published run and snapshot before
pagination; a client-supplied provider label or validation flag is insufficient.
"""
from fastapi import HTTPException
from sqlalchemy import and_, event, exists, inspect, select
from sqlalchemy.orm import Session
from app.models.entities import Player
from app.models.planner import ClubContext, ExternalItemMapping, InventorySnapshot, SyncRun

IDENTITY_FIELDS = ('name', 'rating', 'position', 'card_type', 'card_id', 'athlete_id')
PREFERENCES = {'notes', 'favorite', 'price', 'protected', 'starter', 'usefulness', 'squad_role'}


def snapshot_proof(evidence, context_id):
    return exists(select(InventorySnapshot.id).join(SyncRun, SyncRun.id == InventorySnapshot.run_id)
        .join(ClubContext, ClubContext.id == InventorySnapshot.club_context_id).where(
            InventorySnapshot.id == evidence['snapshot_id'].as_integer(),
            SyncRun.id == evidence['run_id'].as_integer(),
            SyncRun.club_context_id == context_id, InventorySnapshot.club_context_id == context_id,
            ClubContext.verified.is_(True), ClubContext.game_version == 'FC27',
            ClubContext.provider == evidence['provider'].as_string(),
            SyncRun.status.in_(['ready', 'partial', 'review_required']),
            evidence['kind'].as_string() == 'observed_copy', evidence['game_version'].as_string() == 'FC27'))


def observed_copy_clause():
    evidence = Player.validation_evidence
    identity = evidence['identity']
    return and_(Player.validation_status == 'provider_verified', snapshot_proof(evidence, Player.club_context_id),
        *(getattr(Player, key) == (identity[key].as_integer() if key == 'rating' else identity[key].as_string()) for key in IDENTITY_FIELDS),
        exists(select(ExternalItemMapping.id).where(ExternalItemMapping.player_id == Player.id,
            ExternalItemMapping.club_context_id == Player.club_context_id,
            ExternalItemMapping.provider == evidence['provider'].as_string(),
            ExternalItemMapping.external_copy_id == evidence['copy_id'].as_string(),
            ExternalItemMapping.last_snapshot_id == evidence['snapshot_id'].as_integer())))


def observe_copy(player, item, snapshot, read):
    player.validation_status = 'provider_verified'
    player.catalog_variant_id = None
    player.validation_evidence = dict(kind='observed_copy', game_version='FC27', provider=read.provider,
        copy_id=item.copy_id, snapshot_id=snapshot.id, run_id=snapshot.run_id,
        observed_at=read.observed_at.isoformat(),
        identity={key: getattr(player, key) for key in IDENTITY_FIELDS},
        observed_fields=sorted(set(item.fields) | {'card_id', 'athlete_id', 'game_version'}),
        ownership='observed', source='authorized_read_contract', official_classification=False)


def is_observed(db, player):
    return bool(db.scalar(select(Player.id).where(Player.id == player.id, observed_copy_clause())))


def field_known(player, field):
    evidence = getattr(player, 'validation_evidence', None) or {}
    if field in (getattr(player, 'unknown_fields', None) or []):
        return False
    return evidence.get('kind') not in {'observed_copy', 'visual_copy'} or field in evidence.get('observed_fields', []) or field in PREFERENCES


def missing_for_dcp(player, requirements):
    fields = {'is_loan', 'is_evolution', 'tradable'}
    if requirements.get('kind') == 'score':
        fields.add('gallery_score')
    else:
        for attr, prefix, value in [('league', 'leagues', 'required_league'), ('club', 'clubs', 'required_club'), ('nationality', 'nations', 'required_nation')]:
            if requirements.get(value) or any(requirements.get(key+'_'+prefix) is not None for key in ('min', 'max')):
                fields.add(attr)
        for key, field in [('min_rare', 'rare'), ('min_special', 'special'), ('min_chemistry', 'chemistry'), ('required_card_type', 'card_type')]:
            if requirements.get(key):
                fields.add(field)
    return sorted(field for field in fields if not field_known(player, field))


@event.listens_for(Session, 'before_flush')
def immutable_observation(db, *_):
    if 'club_context_id' not in db.info or db.info.get('remote_reconciliation') or db.info.get('visual_reconciliation'):
        return
    for row in db.dirty:
        if not isinstance(row, Player):
            continue
        state = inspect(row)
        histories = state.attrs.validation_evidence.history.deleted
        evidence = histories[0] if histories else row.validation_evidence or {}
        if evidence.get('kind') not in {'observed_copy', 'visual_copy'}:
            continue
        mutable = PREFERENCES | {'deleted', 'availability', 'consumed_by_submission_id', 'duplicate_untradeable', 'updated_at'}
        if any(a.history.has_changes() and a.key not in mutable for a in state.attrs):
            raise HTTPException(409, 'No se pueden sustituir hechos observados por una edición manual; solicita otra lectura autorizada.')
