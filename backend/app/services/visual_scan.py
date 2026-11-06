"""Lotes visuales parciales: conciliación explícita y snapshots append-only."""
from collections import Counter, defaultdict
from fastapi import HTTPException
from sqlalchemy import select
from app.models.assisted import CaptureSession, VisualReading, VisualSnapshot
from app.models.entities import Player, now
from app.schemas.assisted import ReadingReview
from app.services.assisted import require_assisted, ambiguity_key, identity_key, save_reading
from app.services.contexts import utc
from app.services.main_squad import fingerprint


def scan_row(db, identifier):
    require_assisted(db)
    row = db.scalar(select(CaptureSession).where(CaptureSession.id == identifier))
    if not row or not row.scan_data or row.entry_id != db.info['local_session'].entry_id:
        raise HTTPException(404, 'Escaneo no disponible en esta entrada del club')
    return row


def scan_readings(db, session):
    return list(db.scalars(select(VisualReading).where(VisualReading.session_id == session.id).order_by(VisualReading.id)))


def candidates(db, session):
    grouped = {}
    for row in scan_readings(db, session):
        if row.status == 'erased':
            continue
        seen = Counter()
        for card in row.original.get('cards', []):
            identity = identity_key(card)
            occurrence = seen[identity]
            seen[identity] += 1
            key = fingerprint([identity, occurrence])
            if key not in grouped:
                grouped[key] = {**card, 'candidate_key': key, 'sightings': [], 'existing': [],
                    'copy_index': occurrence + 1, 'identity_uncertain': True}
            grouped[key]['sightings'].append({'reading_id': row.id, 'ordinal': card['ordinal']})
    existing = defaultdict(list)
    for p in db.scalars(select(Player).execution_options(include_quarantine=True)):
        key = ambiguity_key(dict(name=p.name, rating=p.rating, position=p.position))
        existing[key].append(dict(id=p.id, name=p.name, card_type=p.card_type, deleted=p.deleted,
            visual=p.validation_evidence.get('kind') == 'visual_copy'))
    for item in grouped.values():
        item['existing'] = existing.get(ambiguity_key(item), [])
    return list(grouped.values())


def scan_data(db, row):
    readings = scan_readings(db, row)
    grouped = candidates(db, row)
    return dict(id=row.id, status=row.status, source=row.source, created_at=row.created_at,
        expires_at=row.expires_at, section=row.scan_data['section'], pages=len(readings),
        unique_candidates=len(grouped), pending=sum(r.status == 'pending' for r in readings),
        possible_duplicates=sum(c['copy_index'] > 1 or bool(c['existing']) for c in grouped),
        discarded=row.scan_data.get('discarded', 0), last_frame_at=row.scan_data.get('last_frame_at'),
        coverage='unknown', complete=False, images_saved=False, provider_verified=False,
        snapshot_id=row.scan_data.get('snapshot_id'), reason=row.scan_data.get('reason'),
        sequence=row.scan_data.get('sequence', 0),
        consent_at=row.scan_data['consent_at'], ocr_seconds=row.scan_data.get('ocr_seconds'))


def inventory_snapshot(db):
    fields = ('id', 'name', 'rating', 'position', 'card_type', 'league', 'club', 'nationality',
              'deleted', 'protected', 'starter', 'availability', 'unknown_fields', 'validation_evidence')
    return [{key: getattr(p, key) for key in fields} for p in db.scalars(
        select(Player).order_by(Player.id).execution_options(include_quarantine=True))]


def commit_scan(db, session, payload):
    request_hash = fingerprint(payload.model_dump(mode='json'))
    previous_commit = db.scalar(select(VisualSnapshot).where(VisualSnapshot.session_id == session.id))
    if previous_commit:
        if session.scan_data.get('commit_hash') != request_hash:
            raise HTTPException(409, 'El lote ya se guardó con otra revisión; inicia un escaneo nuevo.')
        return snapshot_data(previous_commit)
    if session.status not in {'needs_review', 'paused_user', 'paused_sensitive'}:
        raise HTTPException(409, 'Detén o pausa el escaneo antes de guardar la revisión.')
    if utc(session.expires_at) <= now():
        raise HTTPException(409, 'El lote caducó. Comparte otra vez las pantallas para revisarlas.')
    known = {c['candidate_key']: c for c in candidates(db, session)}
    by_reading = defaultdict(list)
    existing = list(db.scalars(select(Player).execution_options(include_quarantine=True)))
    for card in payload.cards:
        candidate = known.get(card.candidate_key)
        if not candidate:
            raise HTTPException(409, 'La candidata no pertenece a este escaneo.')
        # Old observations can never resurrect consumed copies under a new internal ID.
        if any(p.deleted and ambiguity_key(dict(name=p.name, rating=p.rating, position=p.position)) == ambiguity_key(card.model_dump()) for p in existing):
            raise HTTPException(409, 'Una carta coincidente fue retirada o consumida. No se reactivó desde el escaneo.')
        link = candidate['sightings'][0]
        values = card.model_dump(exclude={'candidate_key'})
        values['ordinal'] = link['ordinal']
        by_reading[link['reading_id']].append(values)
    before = inventory_snapshot(db)
    session.status = 'committing'
    for row in scan_readings(db, session):
        if row.id in by_reading:
            review = ReadingReview(phrase='GUARDAR OBSERVACION', edition='FC27', cards=by_reading[row.id])
            save_reading(db, row, review, capture_required=False)
    db.flush()
    after = inventory_snapshot(db)
    old, new = {p['id']: p for p in before}, {p['id']: p for p in after}
    changes = dict(added=[i for i in new if i not in old],
        updated=[i for i in new if i in old and new[i] != old[i]], removed=[],
        preserved_unseen=[i for i in old if old[i] == new.get(i)],
        source='user_reviewed_visual', coverage='partial', ea_mutated=False)
    previous = db.scalar(select(VisualSnapshot.id).order_by(VisualSnapshot.id.desc()).limit(1))
    snapshot = VisualSnapshot(session_id=session.id, previous_id=previous, before=before, after=after, changes=changes)
    db.add(snapshot)
    db.flush()
    session.status = 'completed_partial'
    session.scan_data = {**session.scan_data, 'snapshot_id': snapshot.id, 'commit_hash': request_hash}
    return snapshot_data(snapshot)


def snapshot_data(row, detail=True):
    result = dict(id=row.id, session_id=row.session_id, previous_id=row.previous_id, changes=row.changes,
        created_at=row.created_at, before_count=len(row.before), after_count=len(row.after))
    if detail:
        result.update(before=row.before, after=row.after)
    return result
