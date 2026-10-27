"""Only local review admits observed facts; text/progress never become certified rules."""
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy import select
from app.models.reader import ReaderObservation
from app.models.assisted import CaptureSession, VisualReading
from app.models.entities import Player, now
from app.schemas.assisted import ReviewedCard, ReadingReview
from app.services.assisted import ambiguity_key, save_reading
from app.services.contexts import utc

EXTRA_FACTS = ('first_owner', 'holographic_level', 'acquisition_origin', 'variant_label')


def digest_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def metadata(raw):
    return {k: v for k, v in raw.items() if k not in {'event_id', 'sequence', 'fragment_index', 'payload', 'payload_hash'}}


def accept_fragment(db, grant, payload, raw):
    if digest_json(raw['payload']) != payload.manifest[payload.fragment_index]:
        raise HTTPException(409, 'El fragmento no coincide con el manifiesto')
    row = db.get(ReaderObservation, str(payload.observation_id))
    meta = metadata(raw)
    if row and (row.grant_id != grant.id or row.metadata_json != meta or row.domain != payload.payload.domain):
        raise HTTPException(409, 'La observación cambió de contenido, contexto o dominio')
    if not row:
        row = ReaderObservation(id=str(payload.observation_id), grant_id=grant.id, domain=payload.payload.domain,
            metadata_json=meta, observed_at=payload.observed_at, fragments={})
        db.add(row)
    index = str(payload.fragment_index)
    if index in row.fragments:
        raise HTTPException(409, 'Fragmento ya recibido; reintenta con su event_id original')
    row.fragments = {**row.fragments, index: dict(event_id=str(payload.event_id), payload=raw['payload'])}
    complete = len(row.fragments) == payload.fragment_count
    if complete:
        count = sum(1 if f['payload']['domain'] == 'account' else len(f['payload']['records']) for f in row.fragments.values())
        if count != payload.scope.visible_count:
            raise HTTPException(409, 'El total de registros no coincide con el manifiesto')
    row.status = 'review_required' if complete else 'partial'
    if now()-payload.observed_at > timedelta(minutes=30):
        row.status = 'historical'
    return dict(observation_id=row.id, status=row.status, fragments_received=len(row.fragments),
        fragments_expected=payload.fragment_count, domain=row.domain)


def summary(row):
    count = row.metadata_json['fragment_count']
    return dict(observation_id=row.id, domain=row.domain, status=row.status,
        observed_at=row.observed_at, received_at=row.received_at,
        source_kind=row.metadata_json['source_kind'], count=row.metadata_json['scope']['visible_count'],
        fragments_received=len(row.fragments), fragments_expected=count,
        missing_fragments=[i for i in range(count) if str(i) not in row.fragments],
        profile=row.metadata_json['profile'], scope=row.metadata_json['scope'],
        global_complete=False, provider_verified=False, **row.review_data)


def review_observation(db, row):
    if row.review_data:
        return summary(row)
    if row.status != 'review_required' or now()-utc(row.observed_at) > timedelta(minutes=30):
        raise HTTPException(409, 'Completa los fragmentos o realiza una lectura nueva; no se admite una observación incompleta o antigua')
    meta = row.metadata_json
    session = CaptureSession(entry_id=db.info['local_session'].entry_id, source='structured_dom', expires_at=now()+timedelta(minutes=30))
    db.add(session)
    db.flush()
    pieces = [row.fragments[str(i)]['payload'] for i in range(meta['fragment_count'])]
    records = [c for p in pieces for c in p.get('records', [])]
    by_key = defaultdict(list)
    for p in db.scalars(select(Player).execution_options(include_quarantine=True)):
        by_key[ambiguity_key(dict(name=p.name, rating=p.rating, position=p.position))].append(p)
    multiplicity = Counter(ambiguity_key(c) for c in records) if row.domain in {'inventory', 'detail', 'squad'} else Counter()
    blocked, readings, reused = [], [], 0
    for index, piece in enumerate(pieces):
        cards = []
        prior_evidence = {}
        for ordinal, c in enumerate(piece.get('records', []) if row.domain in {'inventory', 'detail', 'squad'} else []):
            key = ambiguity_key(c)
            existing = by_key[key]
            # A visual identity is not an EA copy ID. Reuse only a unique reviewed
            # match; never create another copy from an old/ambiguous observation.
            if existing:
                p = existing[0]
                if len(existing) != 1 or multiplicity[key] != 1 or p.deleted or p.availability != 'available' or p.validation_evidence.get('kind') != 'visual_copy':
                    blocked.append(dict(fragment=index, ordinal=ordinal, reason='Identidad ambigua o retirada; no se multiplicó ni reactivó la copia'))
                    continue
                facts = p.validation_evidence
                if utc(row.observed_at) < utc(datetime.fromisoformat(facts['observed_at'])):
                    blocked.append(dict(fragment=index, ordinal=ordinal, reason='Existe una observación más reciente'))
                    continue
                from app.services.assisted import FACTS
                conflicts = [k for k in FACTS if c.get(k) is not None and k in facts.get('observed_fields', []) and getattr(p, k) != c[k]]
                conflicts += [k for k in EXTRA_FACTS if c.get(k) is not None and facts.get('additional_facts', {}).get(k) is not None
                    and facts['additional_facts'][k] != c[k]]
                if conflicts:
                    blocked.append(dict(fragment=index, ordinal=ordinal, reason='Cambios en campos conocidos requieren revisión de la copia', fields=conflicts))
                    continue
                c = {**c, 'existing_player_id': p.id}
                prior_evidence[p.id] = dict(facts)
                reused += 1
            cards.append(ReviewedCard.model_validate({**{k:v for k,v in c.items() if k in ReviewedCard.model_fields}, 'ordinal':ordinal}))
        original = dict(cards=[c.model_dump() for c in cards], source_kind=meta['source_kind'],
            reader_version=meta['reader_version'], observation_id=row.id, profile=meta['profile'],
            domain_payload=piece, objective_text=None)
        if row.domain in {'dcp', 'objective'}:
            original['objective_text'] = '\n'.join(c['title']+'\n'+c['requirement_text'] for c in piece['records'])
            if len(original['objective_text']) > 5000:
                raise HTTPException(422, 'Requisitos demasiado largos para una revisión conjunta; selecciona cada desafío por separado')
        reading = VisualReading(session_id=session.id, frame_hash=digest_json([row.id,index]),
            scope='inventory' if row.domain == 'detail' else row.domain,
            page=meta['scope']['page'], filters=meta['scope']['filters'], original=original, observed_at=row.observed_at)
        db.add(reading)
        db.flush()
        readings.append(reading.id)
        if row.domain in {'dcp', 'objective', 'gallery'}:
            # Typed private evidence only. Existing rule editor performs the next
            # explicit review; no objective/definition/progress is fabricated here.
            continue
        review = ReadingReview(phrase='GUARDAR OBSERVACION', edition='FC27', cards=cards,
            club_name=piece.get('club_name'), coins=piece.get('balance'))
        save_reading(db, reading, review)
        for identifier, card in zip(reading.reviewed['copy_ids'], cards):
            p = db.get(Player, identifier)
            source_card = piece['records'][card.ordinal]
            prior = prior_evidence.get(identifier, {})
            current = dict(p.validation_evidence)
            previous_fields = prior.get('observed_fields', [])
            current_fields = current['observed_fields']
            # Missing fields retain their earlier observation date, not a newly
            # fabricated date. The complete current payload remains on the row.
            dates = {k: prior.get('field_observed_at', {}).get(k, prior.get('observed_at')) for k in previous_fields}
            dates.update({k: current['observed_at'] for k in current_fields})
            extra = dict(prior.get('additional_facts', {}))
            for key in EXTRA_FACTS:
                if source_card.get(key) is not None:
                    extra[key] = source_card[key]
                    dates[key] = current['observed_at']
                elif extra.get(key) is not None:
                    dates[key] = prior.get('field_observed_at', {}).get(key, prior.get('observed_at'))
            p.unknown_fields = sorted(set(p.unknown_fields) - set(previous_fields))
            p.validation_evidence = {**p.validation_evidence, 'source_kind':meta['source_kind'],
                'reader_version':meta['reader_version'], 'observation_id':row.id, 'profile':meta['profile'],
                'observed_fields':sorted(set(previous_fields) | set(current_fields)), 'field_observed_at':dates,
                'additional_facts':extra,
                'field_evidence':{**prior.get('field_evidence', {}), **source_card.get('evidence',{})}}
        # New repeated rows within ONE loaded view demonstrate minimum
        # multiplicity. Across observations we refuse to multiply ambiguous rows.
    row.status = 'reviewed'
    row.review_data = dict(reading_ids=readings, pending_records=blocked, reused_copies=reused,
        context_confirmed=True, rule_review_required=row.domain in {'dcp','objective'},
        progress_applied=False, main_automatically_changed=False)
    return summary(row)
