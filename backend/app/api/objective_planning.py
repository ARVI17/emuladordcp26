"""Local objective transcription, simulation, export and new alternative squads."""
import hashlib
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.entities import Objective, Squad, SquadPlayer, AuditLog, now
from app.schemas.objective_planning import (
    ObjectivePlanningInput, ManualObjectiveProgress, ObjectiveProposalRequest,
    ObjectiveProposalSave, ObjectiveProposalExport,
)
from app.services.objective_planning import get_goal, goal_data, objective_preview, check_proposal
from app.services.audit import record
from app.services.locks import resource_locks

router = APIRouter(prefix='/objective-planning', tags=['Plantillas para objetivos'])
DB = Annotated[Session, Depends(get_db)]


@router.get('')
def goals(db: DB, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    query = select(Objective).order_by(Objective.id.desc()).execution_options(include_pending_definitions=True)
    total = db.scalar(select(func.count(Objective.id)).execution_options(include_pending_definitions=True))
    return dict(items=[goal_data(row) for row in db.scalars(query.limit(limit).offset(offset))], total=total,
                limit=limit, offset=offset, game_version='FC27', remote_progress_available=False)


def apply_rules(db, row, payload):
    for identifier in payload.rules.dependencies:
        dependency = get_goal(db, identifier)
        if row.id is not None and dependency.id == row.id:
            raise HTTPException(422, 'Un objetivo no puede depender de sí mismo')
    if row.id is not None and row.planning_rules:
        row.planning_history = [*(row.planning_history or [])[-19:], dict(revision=row.planning_revision,
            name=row.name, target=row.target, expires_at=row.expires_at.isoformat() if row.expires_at else None,
            rules=row.planning_rules, replaced_at=now().isoformat())]
    for key in ('name', 'description', 'category', 'target', 'expires_at'):
        setattr(row, key, getattr(payload, key))
    row.planning_rules = payload.rules.model_dump(mode='json')
    row.planning_revision = (row.planning_revision or 0)+1
    row.completed = (row.progress_evidence or {}).get('value') is not None and row.progress_evidence['value'] >= row.target


@router.post('', status_code=201)
def create_goal(payload: ObjectivePlanningInput, db: DB):
    with resource_locks(db, 'inventory'):
        db.expire_all()
        row = Objective(game_version='FC27', progress=0, progress_evidence={})
        apply_rules(db, row, payload)
        db.add(row)
        db.flush()
        record(db, 'create_auxiliary_rules', 'objective', row.id, {'revision': row.planning_revision, 'origin': 'manual'})
        db.commit()
        return goal_data(row)


@router.put('/{identifier}')
def update_goal(identifier: int, payload: ObjectivePlanningInput, db: DB):
    with resource_locks(db, 'inventory'):
        db.expire_all()
        row = get_goal(db, identifier)
        apply_rules(db, row, payload)
        record(db, 'revise_auxiliary_rules', 'objective', row.id, {'revision': row.planning_revision, 'origin': 'manual'})
        db.commit()
        return goal_data(row)


@router.patch('/{identifier}/progress')
def manual_progress(identifier: int, payload: ManualObjectiveProgress, db: DB):
    with resource_locks(db, 'inventory'):
        db.expire_all()
        row = get_goal(db, identifier)
        row.progress_evidence = dict(value=payload.value, origin='manual' if payload.value is not None else 'unknown',
            observed_at=now().isoformat(), note=payload.note)
        if payload.value is not None:
            row.progress = payload.value
        row.completed = payload.value is not None and payload.value >= row.target
        record(db, 'manual_progress', 'objective', row.id, {'origin': row.progress_evidence['origin']})
        db.commit()
        return goal_data(row)


@router.post('/preview')
def preview(payload: ObjectiveProposalRequest, db: DB):
    with resource_locks(db, 'inventory'):
        db.expire_all()
        return objective_preview(db, payload)


@router.post('/save', status_code=201)
def save(payload: ObjectiveProposalSave, db: DB):
    with resource_locks(db, 'inventory'):
        db.expire_all()
        digest = hashlib.sha256(payload.token.encode()).hexdigest()
        previous = db.scalar(select(AuditLog).where(AuditLog.action == 'save_objective_squad', AuditLog.details['proposal_digest'].as_string() == digest))
        if previous:
            raise HTTPException(409, f'Esta propuesta ya se guardó como plantilla #{previous.entity_id}. No se creó otra copia.')
        claim, goals, checked, players = check_proposal(db, payload.token)
        if db.scalar(select(Squad.id).where(func.lower(Squad.name) == payload.name.strip().lower())):
            raise HTTPException(409, 'Ya existe una plantilla con ese nombre. Elige otro nombre para distinguir esta alternativa.')
        row = Squad(name=payload.name, game_version='FC27', formation=claim['formation'], primary=False, protected=payload.protect,
            objective_context=dict(objective_ids=[g['id'] for g in goals], rule_revisions={str(g['id']):g['row'].planning_revision for g in goals},
                composition_ready=checked['composition_ready'], saved_at=now().isoformat(), snapshot_id=db.info['context'].snapshot_id,
                status='saved_observation', progress_changed=False),
            tactic=dict(style='balanced', opponent='', instructions='Alternativa local para objetivos; revisar acciones y contexto antes de jugar.',
                        practice_focus='', reference_ids=[]))
        db.add(row)
        db.flush()
        for member in claim['lineup']:
            db.add(SquadPlayer(squad_id=row.id, **member))
        for number, identifier in enumerate(claim['bench_ids'], 1):
            db.add(SquadPlayer(squad_id=row.id, player_id=identifier, slot=f'BENCH-{number}'))
        record(db, 'save_objective_squad', 'squad', row.id, dict(proposal_digest=digest,
            objective_ids=[g['id'] for g in goals], composition_ready=checked['composition_ready'], progress_changed=False))
        db.commit()
        return dict(id=row.id, name=row.name, protected=row.protected, primary=False,
            composition_ready=checked['composition_ready'], progress_changed=False, applied_in_ea=False)


@router.post('/export')
def export(payload: ObjectiveProposalExport, db: DB):
    with resource_locks(db, 'inventory'):
        db.expire_all()
        claim, goals, checked, players = check_proposal(db, payload.token)
        by_id = {p.id:p for p in players}
        members = [*claim['lineup'], *[dict(player_id=identifier, slot=f'BENCH-{n}') for n,identifier in enumerate(claim['bench_ids'],1)]]
        return dict(game_version='FC27', formation=claim['formation'], simulation=True,
            objectives=[goal_data(g['row']) for g in goals], checklist=checked['checklist'],
            players=[dict(**m, name=by_id[m['player_id']].name) for m in members],
            composition_ready=checked['composition_ready'], progress_changed=False, applied_in_ea=False,
            message='Lista local: no acredita acciones de partido, progreso ni premios.')
