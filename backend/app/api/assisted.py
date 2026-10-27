"""Explicit browser capture workflow; every mutation stays local and auditable."""
from datetime import timedelta
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.assisted import CaptureSession, VisualReading, VisualCopy
from app.models.entities import Squad, SquadPlayer, now
from app.models.planner import ClubContext
from app.schemas.api import OptimizeRequest
from app.schemas.assisted import AssistedContextInput, CaptureInput, ReadingReview, CopyResolution, MainObservationInput
from app.services.assisted import (require_assisted, capture_row, read_frame, reading_row, reading_data,
    save_reading, resolve_copies, safe_text, coverage, erase_draft)
from app.services.audit import record
from app.services.locks import resource_locks

router = APIRouter(prefix='/assisted', tags=['Lectura visual asistida'])
DB = Annotated[Session, Depends(get_db)]


@router.post('/contexts', status_code=201)
def create_context(payload: AssistedContextInput, db: DB):
    with resource_locks(db, 'sessions'):
        context = ClubContext(owner_id=db.info['local_session'].owner_id, name=safe_text(payload.name),
            provider='visual_assisted', verified=False, game_version='FC27')
        db.add(context)
        db.flush()
        record(db, 'create_visual_context', 'club_context', context.id, {'identity_verified': False})
        db.commit()
        return dict(id=context.id, name=context.name, mode='assisted', identity_verified=False)


@router.get('/readings')
def readings(db: DB, limit: int = 50):
    require_assisted(db)
    return dict(items=[reading_data(r, detail=False) for r in db.scalars(select(VisualReading).order_by(VisualReading.id.desc()).limit(max(1,min(limit,100))))],
        coverage=coverage(db), image_retention_seconds=0, direct_application_available=False)


@router.get('/readings/{identifier}')
def reading(identifier: int, db: DB):
    require_assisted(db)
    return reading_data(reading_row(db, identifier))


@router.post('/sessions', status_code=201)
def start_capture(payload: CaptureInput, db: DB):
    require_assisted(db)
    with resource_locks(db, 'visual:'+str(db.info['context'].id)):
        db.expire_all()
        from app.core.config import settings
        threshold = now()-timedelta(minutes=settings.assisted_draft_retention_minutes)
        for draft in db.scalars(select(VisualReading).where(VisualReading.status == 'pending', VisualReading.observed_at < threshold)):
            erase_draft(draft)
        for old in db.scalars(select(CaptureSession).where(CaptureSession.entry_id == db.info['local_session'].entry_id, CaptureSession.status == 'active')):
            old.status = 'stopped'
        row = CaptureSession(entry_id=db.info['local_session'].entry_id, source=payload.source, expires_at=now()+timedelta(minutes=30))
        db.add(row)
        db.flush()
        record(db, 'start_visual_capture', 'capture_session', row.id, {'source': row.source, 'audio': False, 'image_retention_seconds': 0})
        db.commit()
        return dict(id=row.id, expires_at=row.expires_at, image_retention_seconds=0)


@router.post('/sessions/{identifier}/stop')
def stop_capture(identifier: int, db: DB):
    require_assisted(db)
    with resource_locks(db, 'visual:'+str(db.info['context'].id)):
        db.expire_all()
        row = capture_row(db, identifier, active=False)
        row.status = 'stopped'
        record(db, 'stop_visual_capture', 'capture_session', row.id, {})
        db.commit()
        return dict(stopped=True)


@router.delete('/sessions/{identifier}/drafts')
def erase_drafts(identifier: int, db: DB):
    require_assisted(db)
    with resource_locks(db, 'visual:'+str(db.info['context'].id)):
        db.expire_all()
        capture_row(db, identifier, active=False)
        for row in db.scalars(select(VisualReading).where(VisualReading.session_id == identifier, VisualReading.status == 'pending')):
            erase_draft(row)
        record(db, 'erase_visual_drafts', 'capture_session', identifier, {})
        db.commit()
        return dict(erased=True, reviewed_observations_preserved=True, images_retained=False)


@router.post('/sessions/{identifier}/read')
def read(identifier: int, db: DB, file: UploadFile = File(...),
         scope: Literal['inventory','squad','objective','dcp','account','result'] = Form(...),
         page: str = Form(..., min_length=1, max_length=80), filters: str = Form('', max_length=240), region: str | None = Form(None, max_length=100)):
    require_assisted(db)
    # A synchronous endpoint executes OCR in FastAPI's worker pool, never on the event loop.
    with resource_locks(db, 'visual:'+str(db.info['context'].id), blocking=False):
        db.expire_all()
        session = capture_row(db, identifier)
        content = file.file.read(10*1024*1024+1)
        try:
            result = read_frame(db, session, content, scope, page, filters, region)
        except ValueError:
            raise HTTPException(422, 'No se pudo leer esta imagen: revisa tamaño, claridad o espera al OCR en curso.') from None
        finally:
            file.file.close()
        if result.get('id') and not result.get('repeated'):
            record(db, 'read_visual_frame', 'visual_reading', result['id'], {'scope': scope, 'image_retained': False})
        db.commit()
        return result


@router.post('/readings/{identifier}/review')
def review(identifier: int, payload: ReadingReview, db: DB):
    require_assisted(db)
    with resource_locks(db, 'inventory', 'visual:'+str(db.info['context'].id)):
        db.expire_all()
        row = reading_row(db, identifier)
        result = save_reading(db, row, payload)
        record(db, 'review_visual_observation', 'visual_reading', row.id, {'provider_verified': False})
        db.commit()
        return result


@router.post('/copies/resolve')
def resolve(payload: CopyResolution, db: DB):
    require_assisted(db)
    with resource_locks(db, 'inventory'):
        db.expire_all()
        result = resolve_copies(db, payload)
        record(db, 'resolve_visual_copies', 'visual_copy', 0, {'decision': payload.decision, 'player_ids': payload.player_ids})
        db.commit()
        return result


@router.post('/main', status_code=201)
def register_main(payload: MainObservationInput, db: DB):
    require_assisted(db)
    from app.services.main_squad import select_main
    with resource_locks(db, 'inventory'):
        db.expire_all()
        rows = [reading_row(db, i) for i in payload.reading_ids]
        if any(r.status != 'reviewed' or r.scope not in {'squad','result'} for r in rows):
            raise HTTPException(409, 'Revisa primero las pantallas de tu principal, incluido banquillo y reservas.')
        members = []
        for row in rows:
            for card, identifier in zip(row.reviewed.get('cards',[]), row.reviewed.get('copy_ids',[])):
                if card.get('slot'):
                    members.append(dict(player_id=identifier, slot=card['slot']))
        if len({m['slot'] for m in members}) != len(members):
            raise HTTPException(422, 'Hay posiciones repetidas. Selecciona las lecturas correspondientes al mismo equipo.')
        squad = Squad(name=safe_text(payload.name), formation=payload.formation, game_version='FC27', origin='manual')
        db.add(squad)
        db.flush()
        for member in members:
            db.add(SquadPlayer(squad_id=squad.id, **member))
        db.flush()
        result = select_main(db, squad, expected_hash=payload.expected_hash, complete=payload.complete)
        from app.services.main_squad import state_row
        state = state_row(db)
        state.snapshot = {**state.snapshot, 'source': 'user_reviewed_visual', 'reading_ids': payload.reading_ids,
            'ea_active_squad': None, 'local_lock_only': True}
        record(db, 'register_visual_main', 'squad', squad.id, {'reading_ids': payload.reading_ids})
        db.commit()
        from app.services.main_squad import main_status
        return main_status(db)


@router.post('/readings/{identifier}/simulate-dcp')
def simulate_dcp(identifier: int, payload: OptimizeRequest, db: DB):
    require_assisted(db)
    from app.services.contexts import utc
    from app.services.squad_analysis import effective_protected_ids, serialize_player
    from app.services.remote_evidence import missing_for_dcp
    from app.services.dcp_review import matches
    from app.optimizers.sbc import solve, validate_solution
    from app.models.entities import Player
    from dataclasses import asdict
    with resource_locks(db, 'inventory'):
        db.expire_all()
        row = reading_row(db, identifier)
        draft = row.reviewed.get('dcp') if row.status == 'reviewed' and row.scope == 'dcp' else None
        if not draft or not draft.get('reviewed'):
            raise HTTPException(409, 'Revisa el texto y todos los requisitos del DCP antes de simularlo.')
        from app.schemas.assisted import VisualDcp
        from app.services.main_squad import main_status
        main = main_status(db)
        draft = VisualDcp.model_validate(draft)
        draft.requirements = {**draft.requirements, 'required_player_ids': sorted(set(draft.requirements.get('required_player_ids',[])) | set(payload.locked_ids))}
        from app.schemas.requirements import normalize_requirements
        try: draft.requirements = normalize_requirements(draft.requirements)
        except ValueError: raise HTTPException(422, 'Las cartas fijadas no caben o contradicen los requisitos revisados') from None
        if draft.expires_at and utc(draft.expires_at) <= now():
            raise HTTPException(409, 'El DCP observado está vencido.')
        protected = effective_protected_ids(db)
        players = list(db.scalars(select(Player).where(Player.deleted.is_(False))))
        candidates, excluded = [], []
        for p in players:
            missing = missing_for_dcp(p, draft.requirements)
            reason = ('Copia protegida o reservada' if p.id in protected else 'Copia ambigua o no disponible' if p.availability != 'available'
                else 'Metadatos necesarios desconocidos: '+', '.join(missing) if missing else None)
            if not reason and not matches(p, payload.filters, (p.validation_evidence or {}).get('location','unknown')):
                reason = 'Fuera de los filtros revisados'
            if reason:
                excluded.append(dict(id=p.id,name=p.name,reason=reason))
            else:
                candidates.append(p)
        solutions = solve(candidates, draft.requirements, exclude_ids=set(payload.exclude_ids),
            effective_protected_ids=protected, max_solutions=payload.max_solutions)
        by_id = {p.id:p for p in candidates}
        valid = []
        for solution in solutions:
            selected = [by_id[i] for i in solution.player_ids]
            if set(solution.player_ids)&protected or validate_solution(selected,draft.requirements):
                continue
            valid.append({**asdict(solution),'players':[serialize_player(p,protected) for p in selected],
                'checklist':[dict(player_id=p.id,name=p.name,search=f'{p.name} · {p.rating} · {p.position}',action='Revisar esta copia antes de cualquier preparación manual; no entregar desde el asistente.') for p in selected]})
        return dict(reading_id=row.id, name=draft.name, source='user_reviewed_visual', provider_verified=False,
            main_protection_complete=main['complete'], main_warning=main['reason'],
            simulation=True, solutions=valid, exclusions=excluded, progress_observed=None,
            message='Propuesta local sin consumo. La lectura no demuestra progreso anterior ni autoriza una entrega. Una lista vacía no certifica imposibilidad del club completo.')
