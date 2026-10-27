"""Extension credentials can ingest candidates and read proposals, never mutate resources."""
import hashlib
import hmac
import json
import secrets
from datetime import timedelta
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.db.session import get_db, raw_db
from app.models.reader import ReaderGrant, ReaderEvent, ReaderObservation
from app.models.planner import ClubContext, LocalSession
from app.models.assisted import CaptureSession, VisualReading
from app.models.entities import now
from app.schemas.reader import PairingInput, PairingClaim, ObservationBatch, EventReview
from app.schemas.observations import ObservationFragment, ObservationReview
from app.schemas.assisted import ReviewedCard, ReadingReview
from app.services.contexts import digest, utc
from app.services.assisted import require_assisted, save_reading, safe_text
from app.services.audit import record
from app.services.locks import resource_locks
from app.services.observations import summary as observation_summary

router = APIRouter(prefix='/reader', tags=['Lector DOM local'])


def transport(request):
    from app.core.config import settings
    from urllib.parse import urlsplit
    allowed = {'localhost', '127.0.0.1', '[::1]'} | {urlsplit(o).hostname for o in settings.allowed_origins}
    if request.url.hostname not in allowed:
        raise HTTPException(403, 'Host del lector no permitido')
    extension = request.headers.get('X-Reader-Extension', '')
    origin = request.headers.get('Origin')
    if origin and origin != 'chrome-extension://'+extension:
        raise HTTPException(403, 'Origen del lector no permitido')
    return extension


def binding(db, grant):
    session = db.get(LocalSession, grant.session_id)
    context = db.get(ClubContext, grant.club_context_id)
    if (not session or not context or utc(session.expires_at) <= now()
        or session.context_id != context.id or session.mode != 'assisted'
        or context.generation != grant.generation or context.provider != 'visual_assisted'):
        raise HTTPException(401, 'El contexto cambió o caducó. Empareja de nuevo el lector.')
    db.info.update(local_session=session, context=context, club_context_id=context.id, assisted_context=True)


def authenticated(request: Request, db: Session = Depends(raw_db)):
    extension = transport(request)
    header = request.headers.get('Authorization','')
    if not header.startswith('Bearer ') or len(header) > 150:
        raise HTTPException(401, 'Lector no emparejado')
    grant = db.scalar(select(ReaderGrant).where(ReaderGrant.token_hash == digest(header[7:])))
    if not grant or grant.status != 'active' or grant.extension_id != extension or utc(grant.expires_at) <= now():
        raise HTTPException(401, 'Credencial del lector inválida o revocada')
    binding(db, grant)
    return db, grant


@router.get('/capabilities')
def capabilities(request: Request):
    transport(request)
    return dict(protocol=1, schema_versions=[1,2], reader_versions=['semantic-sample-1','bounded-region-2'], max_batch_records=30,
                source_kinds=['synthetic_dom', 'user_export_dom', 'observed_page_dom'],
                observed_page_extraction='requires_private_profile_and_review', remote_navigation=False,
                provider_verified=False, required_schema_revision='0019',
                limits=dict(fragment_bytes=128000, fragments=10, records_per_observation=300, review_minutes=30),
                capabilities=dict(discovery='guided', extract_loaded_view='conditional_profile',
                    refresh_observation='manual', traverse_read_only=False, provider_sync=False, remote_write=False),
                conditions='Perfil privado contrastado, permiso de pestaña y confirmación del contexto. No equivale a autorización EA.',
                evidence_url='https://help.ea.com/es/articles/ea-sports-fc/fc-rules/', checked_on='2026-10-27')


@router.post('/pairings', status_code=201)
def create_pairing(payload: PairingInput, request: Request, db: Session = Depends(get_db)):
    require_assisted(db)
    # Local cookie + CSRF + current entry were checked by get_db.
    with resource_locks(db, 'reader-pair:'+str(db.info['context'].id)):
        code = f'{secrets.randbelow(1_000_000):06d}'
        row = ReaderGrant(id=str(uuid4()), session_id=db.info['local_session'].id,
            generation=db.info['context'].generation, extension_id=payload.extension_id,
            code_hash=digest(code), expires_at=now()+timedelta(minutes=3))
        for old in db.scalars(select(ReaderGrant).where(ReaderGrant.status == 'pending')):
            old.status = 'revoked'
        db.add(row)
        record(db, 'approve_reader_pairing', 'reader', 0, {'extension_id':payload.extension_id})
        db.commit()
        return dict(pairing_id=row.id, code=code, expires_at=row.expires_at, scopes=['candidates','analysis'])


@router.post('/claim')
def claim(payload: PairingClaim, request: Request, db: Session = Depends(raw_db)):
    extension = transport(request)
    with resource_locks(db, 'reader-pair:'+str(payload.pairing_id)):
        row = db.get(ReaderGrant, str(payload.pairing_id))
        if not row or row.status != 'pending' or utc(row.expires_at) <= now():
            raise HTTPException(401, 'Emparejamiento no disponible')
        binding(db, row)
        row.attempts += 1
        valid = row.extension_id == extension and hmac.compare_digest(row.code_hash, digest(payload.code))
        if not valid:
            if row.attempts >= 5: row.status = 'revoked'
            db.commit()
            raise HTTPException(401, 'Emparejamiento no disponible')
        token = secrets.token_urlsafe(32)
        row.token_hash, row.code_hash, row.status = digest(token), '', 'active'
        row.expires_at = min(utc(db.info['local_session'].expires_at), now()+timedelta(hours=12))
        record(db, 'claim_reader', 'reader', 0, {'scopes':['candidates','analysis']})
        db.commit()
        return dict(credential=token, context_binding=row.id, expires_at=row.expires_at)


@router.get('/status')
def status(db: Session = Depends(get_db)):
    rows = list(db.scalars(select(ReaderGrant).order_by(ReaderGrant.created_at.desc()).limit(20)))
    events = list(db.scalars(select(ReaderEvent).order_by(ReaderEvent.received_at.desc()).limit(30)))
    return dict(grants=[dict(id=r.id, extension_id=r.extension_id, status=r.status,
        expires_at=r.expires_at, generation=r.generation) for r in rows],
        events=[{'observed_at':e.observed_at, **e.receipt, **e.review_data} for e in events],
        observations=[observation_summary(r) for r in db.scalars(
            select(ReaderObservation).order_by(ReaderObservation.received_at.desc()).limit(50))],
        ea_extractor='pending_real_sample', remote_write=False, global_complete=False)


@router.post('/grants/{identifier}/revoke')
def revoke(identifier: str, db: Session = Depends(get_db)):
    row = db.scalar(select(ReaderGrant).where(ReaderGrant.id == identifier))
    if not row: raise HTTPException(404, 'Lector no disponible')
    with resource_locks(db, 'reader:'+identifier):
        row.status = 'revoked'
        record(db, 'revoke_reader', 'reader', 0, {})
        db.commit()
    return dict(revoked=True)


@router.post('/disconnect')
def disconnect(auth=Depends(authenticated)):
    db, grant = auth
    with resource_locks(db, 'reader:'+grant.id):
        grant.status = 'revoked'
        record(db, 'disconnect_reader', 'reader', 0, {})
        db.commit()
    return dict(revoked=True)


def canonical_hash(raw):
    # Wire JSON canonicalization: sorted keys, UTF-8, integer-only numeric fields.
    return hashlib.sha256(json.dumps({k:v for k,v in raw.items() if k != 'payload_hash'},
        sort_keys=True, separators=(',',':'), ensure_ascii=False).encode()).hexdigest()


@router.post('/events')
async def ingest(request: Request, document: ObservationBatch | ObservationFragment, auth=Depends(authenticated)):
    db, grant = auth
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > 128_000: raise HTTPException(413, 'Lote demasiado grande')
    try:
        raw = json.loads(content)
        payload = (ObservationFragment if raw.get('schema_version') == 2 else ObservationBatch).model_validate(raw)
    except (ValueError, TypeError):
        raise HTTPException(422, 'Lote DOM inválido') from None
    if str(payload.context_binding) != grant.id or canonical_hash(raw) != payload.payload_hash:
        raise HTTPException(409, 'El contexto o la huella del lote no coinciden')
    safe_text(json.dumps(raw, ensure_ascii=False))
    if payload.observed_at > now()+timedelta(minutes=2):
        raise HTTPException(422, 'La observación tiene una fecha futura')
    with resource_locks(db, 'reader:'+grant.id):
        db.refresh(grant)
        binding(db, grant)
        if grant.status != 'active': raise HTTPException(401, 'Credencial revocada')
        old = db.get(ReaderEvent, str(payload.event_id))
        if old:
            if old.grant_id != grant.id or old.payload_hash != payload.payload_hash:
                raise HTTPException(409, 'event_id ya usado con otro contenido')
            return old.receipt
        last = db.scalar(select(func.max(ReaderEvent.sequence)).where(
            ReaderEvent.grant_id == grant.id, ReaderEvent.stream_id == str(payload.stream_id))) or 0
        if db.scalar(select(ReaderEvent.event_id).where(ReaderEvent.grant_id == grant.id,
            ReaderEvent.stream_id == str(payload.stream_id), ReaderEvent.sequence == payload.sequence)):
            raise HTTPException(409, 'Secuencia ya utilizada')
        recent = db.scalar(select(func.count()).select_from(ReaderEvent).where(
            ReaderEvent.grant_id == grant.id, ReaderEvent.received_at > now()-timedelta(minutes=1)))
        if recent >= 30: raise HTTPException(429, 'Espera antes de enviar más lotes', headers={'Retry-After':'60'})
        is_v2 = isinstance(payload, ObservationFragment)
        stale = (not is_v2 and payload.sequence < last) or now()-payload.observed_at > timedelta(minutes=30)
        count = (1 if payload.payload.domain == 'account' else len(payload.payload.records)) if is_v2 else len(payload.records)
        receipt = dict(event_id=str(payload.event_id), status='historical' if stale else 'review_required',
            count=count, source_kind=payload.source_kind, reading_id=None,
            global_complete=False, provider_verified=False)
        if is_v2:
            from app.services.observations import accept_fragment
            receipt.update(accept_fragment(db, grant, payload, raw))
        row = ReaderEvent(event_id=str(payload.event_id), grant_id=grant.id, stream_id=str(payload.stream_id),
            sequence=payload.sequence, payload_hash=payload.payload_hash, payload=raw,
            receipt=receipt, observed_at=payload.observed_at)
        db.add(row)
        record(db, 'ingest_dom_candidates', 'reader', 0, {'event_id':row.event_id,'count':count})
        db.commit()  # receipt + candidate effects are one atomic transaction
        return receipt


@router.post('/events/{event_id}/review')
def review_event(event_id: str, payload: EventReview, db: Session = Depends(get_db)):
    require_assisted(db)
    with resource_locks(db, 'inventory', 'reader-review:'+str(db.info['context'].id)):
        row = db.scalar(select(ReaderEvent).where(ReaderEvent.event_id == event_id))
        if not row: raise HTTPException(404, 'Lote no disponible')
        if row.payload.get('schema_version') == 2:
            raise HTTPException(409, 'Revisa la observación completa desde sus fragmentos')
        if row.review_data: return {**row.receipt, **row.review_data}
        grant = db.get(ReaderGrant,row.grant_id)
        if grant.status != 'active' or grant.generation != db.info['context'].generation:
            raise HTTPException(409, 'El contexto del lote caducó')
        if row.receipt['status'] == 'historical' or now()-utc(row.observed_at) > timedelta(minutes=30):
            raise HTTPException(409, 'El lote antiguo se conserva como historial; realiza otra lectura')
        newer = db.scalar(select(ReaderEvent.event_id).where(ReaderEvent.grant_id == row.grant_id,
            ReaderEvent.stream_id == row.stream_id, ReaderEvent.sequence > row.sequence))
        if newer: raise HTTPException(409, 'Hay una observación posterior en este flujo')
        batch = ObservationBatch.model_validate(row.payload)
        session = CaptureSession(entry_id=db.info['local_session'].entry_id, source='structured_dom', expires_at=now()+timedelta(minutes=30))
        db.add(session)
        db.flush()
        cards = [ReviewedCard.model_validate({k:v for k,v in c.model_dump().items() if k in ReviewedCard.model_fields}) for c in batch.records]
        reading = VisualReading(session_id=session.id, frame_hash=row.payload_hash,
            scope='inventory' if batch.view == 'detail' else batch.view, page=batch.scope.page,
            filters=batch.scope.filters, original=dict(cards=[c.model_dump() for c in cards],
                source_kind=batch.source_kind, reader_version=batch.reader_version, dom_event_id=row.event_id,
                field_evidence=[c.evidence for c in batch.records]), observed_at=row.observed_at)
        db.add(reading)
        db.flush()
        save_reading(db, reading, ReadingReview(phrase='GUARDAR OBSERVACION', edition='FC27', cards=cards))
        # Preserve additional evidence without inventing model attributes or EA IDs.
        from app.models.entities import Player
        for identifier, card in zip(reading.reviewed['copy_ids'], batch.records):
            p = db.get(Player,identifier)
            p.validation_evidence = {**p.validation_evidence,'source_kind':batch.source_kind,
                'reader_version':batch.reader_version,'dom_event_id':row.event_id,
                'additional_facts':{k:getattr(card,k) for k in ('first_owner','holographic_level','acquisition_origin','variant_label')},
                'field_evidence':card.evidence}
        row.review_data = dict(status='reviewed', reading_id=reading.id)
        record(db, 'review_dom_batch', 'visual_reading', reading.id, {'event_id':row.event_id})
        db.commit()
        return {**row.receipt, **row.review_data}


@router.get('/events/{event_id}')
def event_detail(event_id: str, db: Session = Depends(get_db)):
    row = db.scalar(select(ReaderEvent).where(ReaderEvent.event_id == event_id))
    if not row: raise HTTPException(404, 'Lote no disponible')
    return dict(payload=row.payload, receipt={**row.receipt, **row.review_data})


@router.get('/observations/{identifier}')
def observation_detail(identifier: str, db: Session = Depends(get_db)):
    from app.services.observations import summary
    row = db.scalar(select(ReaderObservation).where(ReaderObservation.id == identifier))
    if not row: raise HTTPException(404, 'Observación no disponible')
    pending_rules = list(db.scalars(select(VisualReading.id).where(
        VisualReading.id.in_(row.review_data.get('reading_ids', [])),
        VisualReading.scope.in_(['dcp','objective']), VisualReading.status == 'pending')))
    return dict(**summary(row), fragments=row.fragments, pending_rule_reading_ids=pending_rules)


@router.post('/observations/{identifier}/review')
def observation_review(identifier: str, payload: ObservationReview, db: Session = Depends(get_db)):
    require_assisted(db)
    from app.services.observations import review_observation
    with resource_locks(db, 'inventory', 'reader-review:'+str(db.info['context'].id)):
        row = db.scalar(select(ReaderObservation).where(ReaderObservation.id == identifier))
        if not row: raise HTTPException(404, 'Observación no disponible')
        grant = db.get(ReaderGrant, row.grant_id)
        if grant.status != 'active' or grant.generation != db.info['context'].generation or utc(grant.expires_at) <= now():
            raise HTTPException(409, 'El contexto del lector caducó')
        result = review_observation(db, row)
        record(db, 'review_domain_observation', 'reader', 0, {'observation_id':row.id, 'domain':row.domain})
        db.commit()
        return result


@router.get('/proposal')
def proposal(auth=Depends(authenticated)):
    db, grant = auth
    from app.api.analysis import squad_profiles, ProfilesRequest
    result = squad_profiles(ProfilesRequest(bench_size=0), db)
    sources = sorted({item['player'].get('source_kind','visual_assisted')
        for group in result['groups'] for item in group['squad']['lineup']})
    return dict(proposal=result, global_complete=False, writes_performed=False,
        source='reviewed_dom_or_visual_subset', data_sources=sources, manual_guide=[
            'Revisa identidades, posiciones y datos desconocidos de la propuesta.',
            'Crea una plantilla alternativa manualmente en EA; conserva la principal.',
            'Lee el resultado y compáralo en Club Lab. Esta guía no ejecuta acciones en EA.'])
