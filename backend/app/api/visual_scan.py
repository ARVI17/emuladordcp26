"""Captura de pantallas estables enviada por el navegador; ninguna navegación EA."""
import hashlib
import asyncio
import threading
import io
from collections import Counter
from datetime import datetime, timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from starlette.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.assisted import CaptureSession, VisualReading, VisualSnapshot
from app.models.entities import now
from app.schemas.visual_scan import ScanStart, ScanTransition, ScanCommit
from app.services.assisted import require_assisted, parse_screen, identity_key
from app.services.audit import record
from app.services.contexts import utc
from app.services.locks import resource_locks
from app.services.main_squad import fingerprint
from app.services.scan_ocr import recognize, ScanCancelled, SENSITIVE, field_confidence
from app.services.import_export import validate_image
from app.services.visual_scan import scan_row, scan_data, scan_readings, candidates, commit_scan, snapshot_data

router = APIRouter(prefix='/visual-scans', tags=['Escanear mi club'])
DB = Annotated[Session, Depends(get_db)]


@router.post('', status_code=201)
def start(payload: ScanStart, db: DB):
    context = require_assisted(db)
    with resource_locks(db, 'visual:'+str(context.id)):
        db.expire_all()
        for old in db.scalars(select(CaptureSession).where(CaptureSession.entry_id == db.info['local_session'].entry_id, CaptureSession.status == 'scanning')):
            old.status = 'needs_review'
        row = CaptureSession(entry_id=db.info['local_session'].entry_id, source=payload.source,
            status='scanning', expires_at=now()+timedelta(minutes=30),
            scan_data=dict(consent_at=now().isoformat(), section=payload.section, region=payload.region,
                discarded=0, generation=0))
        db.add(row)
        db.flush()
        record(db, 'start_visual_scan', 'capture_session', row.id, {'consent': True, 'source': row.source})
        db.commit()
        return scan_data(db, row)


@router.get('')
def list_scans(db: DB):
    require_assisted(db)
    rows = db.scalars(select(CaptureSession).where(CaptureSession.entry_id == db.info['local_session'].entry_id).order_by(CaptureSession.id.desc()).limit(30))
    return [scan_data(db, r) for r in rows if r.scan_data]


@router.get('/snapshots')
def snapshots(db: DB):
    require_assisted(db)
    return [snapshot_data(r, False) for r in db.scalars(select(VisualSnapshot).order_by(VisualSnapshot.id.desc()).limit(30))]


@router.get('/snapshots/{identifier}')
def snapshot(identifier: int, db: DB):
    require_assisted(db)
    row = db.scalar(select(VisualSnapshot).where(VisualSnapshot.id == identifier))
    if not row:
        raise HTTPException(404, 'Snapshot no disponible en este club.')
    return snapshot_data(row)


@router.get('/{identifier}')
def status(identifier: int, db: DB):
    return scan_data(db, scan_row(db, identifier))


@router.get('/{identifier}/candidates')
def get_candidates(identifier: int, db: DB, offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=20)):
    rows = candidates(db, scan_row(db, identifier))
    return dict(items=rows[offset:offset+limit], total=len(rows), offset=offset, limit=limit)


@router.post('/{identifier}/transition')
def transition(identifier: int, payload: ScanTransition, db: DB):
    context = require_assisted(db)
    with resource_locks(db, 'visual:'+str(context.id)):
        db.expire_all()
        row = scan_row(db, identifier)
        target = {'pause': 'paused_user', 'resume': 'scanning', 'stop': 'needs_review', 'cancel': 'cancelled'}[payload.action]
        if row.status in {'cancelled', 'completed_partial', 'failed'}:
            if payload.action in {'pause', 'stop', 'cancel'}:
                return scan_data(db, row)
            raise HTTPException(409, 'El escaneo terminó. Inicia otro desde el botón de compartir.')
        if payload.action == 'resume' and (row.status != 'paused_user' or utc(row.expires_at) <= now()):
            raise HTTPException(409, 'Comparte otra vez la pestaña después de detenerla, de una pantalla sensible o del vencimiento.')
        row.status = target
        row.scan_data = {**row.scan_data, 'generation': row.scan_data.get('generation', 0)+1, 'inflight': None}
        record(db, 'transition_visual_scan', 'capture_session', row.id, {'state': target})
        db.commit()
        return scan_data(db, row)


@router.post('/{identifier}/frames', openapi_extra={'requestBody': {'required': True,
    'content': {mime: {'schema': {'type': 'string', 'format': 'binary'}} for mime in ('image/png', 'image/jpeg', 'image/webp')}}})
async def frame(identifier: int, request: Request, db: DB, sequence: int = Query(..., ge=1, le=5000)):
    # A raw, bounded body avoids multipart's disk spool for images larger than 1 MB.
    if request.headers.get('content-type', '').split(';')[0] not in {'image/png', 'image/jpeg', 'image/webp'}:
        raise HTTPException(415, 'Usa PNG, JPEG o WebP.')
    content = bytearray()
    async for chunk in request.stream():
        if len(content)+len(chunk) > 4*1024*1024:
            raise HTTPException(413, 'El fotograma supera 4 MB.')
        content.extend(chunk)
    disconnected = threading.Event()
    async def watch():
        while not disconnected.is_set():
            if await request.is_disconnected():
                disconnected.set()
                return
            await asyncio.sleep(.25)
    watcher = asyncio.create_task(watch())
    try:
        return await run_in_threadpool(process_frame, identifier, db, bytes(content), sequence, disconnected)
    finally:
        content.clear()
        disconnected.set()
        watcher.cancel()
        await asyncio.gather(watcher, return_exceptions=True)


def process_frame(identifier, db, content, sequence, disconnected):
    context = require_assisted(db)
    key = 'visual:'+str(context.id)
    try:
        size = list(validate_image(content))
    except ValueError:
        raise HTTPException(422, 'Imagen vacía, corrupta o demasiado grande.') from None
    with resource_locks(db, key, blocking=False):
        db.expire_all()
        row = scan_row(db, identifier)
        stats = dict(row.scan_data)
        if row.status != 'scanning' or utc(row.expires_at) <= now():
            raise HTTPException(409, 'La recepción de fotogramas está detenida.')
        if stats.get('frame_size') and stats['frame_size'] != size:
            row.status = 'needs_review'
            row.scan_data = {**stats, 'generation': stats['generation']+1, 'inflight': None,
                'reason': 'Cambió la resolución. Revisa la región y comparte de nuevo.'}
            db.commit()
            return scan_data(db, row)
        if sequence <= stats.get('sequence', 0):
            raise HTTPException(409, 'El número de fotograma ya se recibió.')
        if stats.get('inflight') or (stats.get('last_frame_at') and (now()-utc(datetime.fromisoformat(stats['last_frame_at']))).total_seconds() < 1):
            raise HTTPException(429, 'Espera a que termine el fotograma anterior.')
        if len(scan_readings(db, row)) >= 50 or len(candidates(db, row)) >= 1000:
            row.status = 'needs_review'
            db.commit()
            raise HTTPException(409, 'Límite de 50 páginas o 1000 candidatas; revisa este lote.')
        stats.update(sequence=sequence, inflight=sequence, frame_size=size, last_frame_at=now().isoformat())
        row.scan_data = stats
        generation = stats['generation']
        db.commit()
    def cancelled():
        db.expire_all()
        current = scan_row(db, identifier)
        local = db.info['local_session']
        db.refresh(local)
        stopped = (disconnected.is_set() or current.status != 'scanning' or current.scan_data['generation'] != generation
            or local.context_id != current.club_context_id or local.entry_id != current.entry_id
            or utc(current.expires_at) <= now())
        db.rollback()
        return stopped
    try:
        digest = hashlib.sha256(content).hexdigest()
        # Repeated exact frames do not invoke OCR or refresh evidence.
        repeated = db.scalar(select(VisualReading.id).where(VisualReading.session_id == identifier, VisualReading.frame_hash == digest))
        result = None if repeated else recognize(content, cancelled)
        # Inspect the full unmasked area first; an ROI cannot conceal a sensitive screen.
        if result and stats.get('region') and not SENSITIVE.search(result['text']) and parse_screen(result['text'], 'inventory') is not None:
            from PIL import Image
            x, y, w, h = stats['region']
            with Image.open(io.BytesIO(content)) as image:
                width, height = image.size
                cropped = image.crop((int(width*x/100), int(height*y/100), int(width*(x+w)/100), int(height*(y+h)/100)))
                buffer = io.BytesIO()
                cropped.save(buffer, format='PNG')
            roi = recognize(buffer.getvalue(), cancelled)
            result = {**roi, 'text': 'FC27 Mi club\n'+roi['text'], 'seconds': result['seconds']+roi['seconds']}
    except ScanCancelled:
        with resource_locks(db, key):
            db.expire_all()
            row = scan_row(db, identifier)
            if row.scan_data['generation'] == generation:
                row.status = 'needs_review'
                row.scan_data = {**row.scan_data, 'inflight': None}
                db.commit()
        return dict(discarded=True, stopped=True)
    except ValueError:
        with resource_locks(db, key):
            db.expire_all()
            row = scan_row(db, identifier)
            if row.scan_data['generation'] == generation:
                row.status = 'failed'
                row.scan_data = {**row.scan_data, 'inflight': None, 'reason': 'No se pudo procesar el fotograma dentro de los límites.'}
                db.commit()
        raise HTTPException(422, 'No se pudo procesar el fotograma. Revisa tamaño y claridad, y vuelve a compartir.') from None
    finally:
        content = b''
    with resource_locks(db, key):
        db.expire_all()
        row = scan_row(db, identifier)
        if cancelled():
            row = scan_row(db, identifier)
            if row.scan_data['generation'] == generation and row.status == 'scanning':
                row.status = 'needs_review'
                row.scan_data = {**row.scan_data, 'inflight': None}
                db.commit()
            return dict(discarded=True, stopped=True)
        row = scan_row(db, identifier)
        stats = {**row.scan_data, 'inflight': None}
        if result is not None:
            parsed = None if SENSITIVE.search(result['text']) else parse_screen(result['text'], 'inventory')
            if parsed is None:
                row.status = 'paused_sensitive'
                stats.update(discarded=stats['discarded']+1, reason='Pantalla sensible, ajena o ilegible: comparte de nuevo una vista del club.')
            elif not parsed['cards']:
                stats['discarded'] += 1
            else:
                for card in parsed['cards']:
                    card['confidence'] = field_confidence(card, result['lines'])
                semantic = fingerprint([[c['name'], c['rating'], c['position'], c.get('card_type')] for c in parsed['cards']])
                if any(r.original.get('scan_semantic') == semantic for r in scan_readings(db, row)):
                    stats['discarded'] += 1
                else:
                    keys = {c['candidate_key'] for c in candidates(db, row)}
                    occurrences = Counter()
                    for card in parsed['cards']:
                        identity = identity_key(card)
                        keys.add(fingerprint([identity, occurrences[identity]]))
                        occurrences[identity] += 1
                    if len(keys) > 1000:
                        row.status = 'needs_review'
                        stats.update(discarded=stats['discarded']+1, reason='Límite de 1000 candidatas; revisa este lote.')
                    else:
                        parsed.update(scan_semantic=semantic, source_kind='screen_scan')
                        reading = VisualReading(session_id=row.id, frame_hash=digest, scope='inventory',
                            page=f'Escaneo {row.id} · {sequence}', filters=stats['section'], original=parsed)
                        db.add(reading)
                        db.flush()
                        record(db, 'scan_frame', 'visual_reading', reading.id, {'section': stats['section']})
                stats['ocr_seconds'] = result['seconds']
        else:
            stats['discarded'] += 1
        row.scan_data = stats
        db.commit()
        return scan_data(db, row)


@router.post('/{identifier}/commit')
def commit(identifier: int, payload: ScanCommit, db: DB):
    context = require_assisted(db)
    if SENSITIVE.search(str(payload.model_dump())):
        raise HTTPException(422, 'Retira contenido sensible de la revisión.')
    with resource_locks(db, 'inventory', 'visual:'+str(context.id)):
        db.expire_all()
        row = scan_row(db, identifier)
        committed = bool(row.scan_data.get('snapshot_id'))
        result = commit_scan(db, row, payload)
        if not committed:
            record(db, 'commit_visual_scan', 'visual_snapshot', result['id'], {'ea_mutated': False})
        db.commit()
        return result
