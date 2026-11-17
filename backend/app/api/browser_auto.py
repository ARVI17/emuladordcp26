"""Local cookie consent/start and separately authenticated extension publication."""
import secrets
from datetime import timedelta
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.entities import now
from app.models.reader import BrowserAutoLink, ReaderGrant
from app.schemas.browser_auto import AutoEnable, AutoSnapshot, AutoFailure, AutoProgress
from app.api.reader import authenticated, binding
from app.services.assisted import require_assisted
from app.services.audit import record
from app.services.contexts import digest
from app.services.locks import resource_locks
from app.services import browser_auto as service

router = APIRouter(prefix='/browser-auto', tags=['Actualización local de Chrome'])


@router.get('/status')
def status(db: Session = Depends(get_db)):
    require_assisted(db)
    return service.status(service.link_row(db))


@router.post('/settings')
def settings(payload: AutoEnable, db: Session = Depends(get_db)):
    require_assisted(db)
    with resource_locks(db, 'browser-auto'):
        db.expire_all()
        row = service.link_row(db)
        if row and row.extension_id != payload.extension_id:
            raise HTTPException(409, 'El contexto ya está vinculado a otra extensión; conserva el destino existente.')
        if not row:
            row = BrowserAutoLink(extension_id=payload.extension_id)
            db.add(row)
        if row.grant_id:
            grant = db.get(ReaderGrant, row.grant_id)
            if grant: grant.status = 'revoked'
        row.enabled, row.protect_main = payload.enabled, payload.protect_main
        row.status = 'ready' if row.enabled else 'disabled'
        row.request_id, row.grant_id, row.updated_at = None, None, now()
        record(db, 'configure_browser_auto', 'reader', 0, {'enabled':row.enabled, 'protect_main':True})
        db.commit()
        return service.status(row)


@router.post('/start')
def start(db: Session = Depends(get_db)):
    require_assisted(db)
    with resource_locks(db, 'browser-auto'):
        db.expire_all()
        row = service.link_row(db)
        if not row or not row.enabled:
            raise HTTPException(409, 'Activa una vez el lector local antes de actualizar automáticamente.')
        if row.grant_id:
            old = db.get(ReaderGrant, row.grant_id)
            if old: old.status = 'revoked'
        code = f'{secrets.randbelow(1_000_000):06d}'
        grant = ReaderGrant(id=str(uuid4()), session_id=db.info['local_session'].id,
            generation=db.info['context'].generation, extension_id=row.extension_id,
            code_hash=digest(code), expires_at=now()+timedelta(minutes=3))
        db.add(grant)
        db.flush()
        row.request_id, row.grant_id = str(uuid4()), grant.id
        row.requested_at, row.updated_at, row.status = now(), now(), 'reading'
        row.result = {**row.result, 'progress':dict(pages_read=0, cards_read=0, phase='squad')}
        record(db, 'start_browser_auto', 'reader', 0, {'request_id':row.request_id})
        db.commit()
        return dict(request_id=row.request_id, pairing_id=grant.id, code=code,
            extension_id=row.extension_id, context_id=row.club_context_id)


@router.post('/cancel')
def cancel(db: Session = Depends(get_db)):
    require_assisted(db)
    with resource_locks(db, 'browser-auto'):
        row = service.link_row(db)
        if row:
            if row.grant_id:
                grant = db.get(ReaderGrant, row.grant_id)
                if grant: grant.status = 'revoked'
            row.status, row.request_id = 'cancelled', None
            record(db, 'cancel_browser_auto', 'reader', 0, {})
            db.commit()
        return service.status(row)


@router.post('/publish')
def publish(payload: AutoSnapshot, auth=Depends(authenticated)):
    db, grant = auth
    with resource_locks(db, 'browser-auto', 'inventory'):
        db.expire_all()
        # Revalidate revocation/context after waiting for the transaction lock.
        if grant.status != 'active': raise HTTPException(401, 'Lector revocado.')
        binding(db, grant)
        link = service.require_run(db, grant, payload.request_id)
        result = service.publish(db, link, payload)
        record(db, 'publish_browser_auto', 'reader', 0, {'request_id':str(payload.request_id), 'status':link.status})
        db.commit()
        return result


@router.post('/failure')
def failure(payload: AutoFailure, auth=Depends(authenticated)):
    db, grant = auth
    with resource_locks(db, 'browser-auto'):
        db.expire_all()
        if grant.status != 'active': raise HTTPException(401, 'Lector revocado.')
        binding(db, grant)
        row = service.require_run(db, grant, payload.request_id)
        if row.status == 'reading':
            row.status, row.updated_at = payload.reason, now()
            record(db, 'fail_browser_auto', 'reader', 0, {'reason':payload.reason})
            db.commit()
        return service.status(row)


@router.post('/progress')
def progress(payload: AutoProgress, auth=Depends(authenticated)):
    db, grant = auth
    with resource_locks(db, 'browser-auto'):
        db.expire_all()
        if grant.status != 'active': raise HTTPException(401, 'Lector revocado.')
        binding(db, grant)
        row = service.require_run(db, grant, payload.request_id)
        if row.status != 'reading': raise HTTPException(409, 'La lectura ya termino.')
        old = row.result.get('progress', {})
        if payload.pages_read < old.get('pages_read', 0) or payload.cards_read < old.get('cards_read', 0):
            raise HTTPException(409, 'El progreso no puede retroceder.')
        row.result = {**row.result, 'progress':payload.model_dump(mode='json', exclude={'request_id'})}
        row.updated_at = now()
        record(db, 'progress_browser_auto', 'reader', 0, {'pages':payload.pages_read, 'cards':payload.cards_read})
        db.commit()
        return service.status(row)
