"""Local reusable selections and correctable declared match tasks; no EA effects."""
from datetime import datetime
from typing import Annotated,Literal
from uuid import UUID,uuid4
from fastapi import APIRouter,Depends,HTTPException
from pydantic import Field,model_validator,ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.entities import now
from app.models.planner import ClubProgress
from app.models.assisted import VisualReading
from app.schemas.api import InputModel,DcpFilters,OptimizeRequest
from app.schemas.objective_planning import Difficulty,ObjectiveRules
from app.services.locks import resource_locks
from app.services.audit import record
from app.services.main_squad import fingerprint

router=APIRouter(tags=['Utilidades locales del club'])
Id=Annotated[int,Field(strict=True,ge=1)]


class SelectionTemplate(InputModel):
    name:str=Field(min_length=1,max_length=80)
    reading_id:Id
    filters:DcpFilters=Field(default_factory=DcpFilters)
    max_solutions:int=Field(default=3,ge=1,le=5)


def observed_rules(db,identifier):
    row=db.scalar(select(VisualReading).where(VisualReading.id==identifier,VisualReading.status=='reviewed',VisualReading.scope=='dcp'))
    if not row or not row.reviewed.get('dcp'):raise HTTPException(409,'Selecciona un DCP observado y revisado del club actual')
    return row.reviewed['dcp']['requirements']


@router.get('/dcp/templates')
def templates(db:Session=Depends(get_db)):
    return [dict(id=r.definition_key,**r.state) for r in db.scalars(select(ClubProgress).where(ClubProgress.kind=='dcp_template').order_by(ClubProgress.id.desc()).limit(50))]


@router.post('/dcp/templates',status_code=201)
def save_template(payload:SelectionTemplate,db:Session=Depends(get_db)):
    with resource_locks(db,'selection-templates:'+str(db.info['context'].id)):
        rules=observed_rules(db,payload.reading_id)
        count=len(list(db.scalars(select(ClubProgress.id).where(ClubProgress.kind=='dcp_template'))))
        if count>=50:raise HTTPException(409,'La biblioteca alcanzó 50 configuraciones; revisa las existentes')
        row=ClubProgress(kind='dcp_template',definition_key=str(uuid4()),state={**payload.model_dump(),
            'schema_version':1,'requirements_hash':fingerprint(rules),'requirements':rules,
            'strategy':'preserve_resources','game_version':'FC27','authorizes_consumption':False})
        db.add(row);record(db,'save_selection_template','dcp_template',0,{})
        db.commit();return dict(id=row.definition_key,**row.state)


class TemplateReuse(InputModel):
    reading_id:Id
    locked_ids:list[Id]=Field(default_factory=list,max_length=23)
    exclude_ids:list[Id]=Field(default_factory=list,max_length=1000)

    @model_validator(mode='after')
    def consistent(self):
        OptimizeRequest(locked_ids=self.locked_ids,exclude_ids=self.exclude_ids)
        return self


@router.post('/dcp/templates/{identifier}/simulate')
def reuse(identifier:UUID,payload:TemplateReuse,db:Session=Depends(get_db)):
    row=db.scalar(select(ClubProgress).where(ClubProgress.kind=='dcp_template',ClubProgress.definition_key==str(identifier)))
    if not row:raise HTTPException(404,'Configuración no disponible')
    rules=observed_rules(db,payload.reading_id)
    if fingerprint(rules)!=row.state['requirements_hash']:
        raise HTTPException(409,'La versión de requisitos cambió. Revisa el DCP y guarda una configuración nueva.')
    from app.api.assisted import simulate_dcp
    return simulate_dcp(payload.reading_id,OptimizeRequest(filters=DcpFilters.model_validate(row.state['filters']),
        max_solutions=row.state['max_solutions'],locked_ids=payload.locked_ids,exclude_ids=payload.exclude_ids),db)


class TaskCount(InputModel):
    objective_id:Id
    action_id:str=Field(min_length=1,max_length=80)
    count:int=Field(ge=0,le=100)


class DeclaredMatch(InputModel):
    game_version:Literal['FC27']='FC27'
    expected_revision:int=Field(ge=0)
    played_at:datetime
    mode:Literal['squad_battles','rivals','champions','friendlies','rush']
    difficulty:Difficulty='not_required'
    tasks:list[TaskCount]=Field(min_length=1,max_length=50)
    note:str=Field(min_length=5,max_length=500)
    source:Literal['user_declared']='user_declared'

    @model_validator(mode='after')
    def valid(self):
        if self.played_at.tzinfo is None or self.played_at>now():raise ValueError('Indica una fecha pasada con zona horaria')
        if len({(t.objective_id,t.action_id) for t in self.tasks})!=len(self.tasks):raise ValueError('No repitas tareas del mismo objetivo')
        return self


@router.put('/objective-journal/{match_ref}')
def declare_match(match_ref:UUID,payload:DeclaredMatch,db:Session=Depends(get_db)):
    from app.services.objective_planning import get_goal
    from app.services.contexts import utc
    with resource_locks(db,'objective-journal:'+str(db.info['context'].id)):
        row=db.scalar(select(ClubProgress).where(ClubProgress.kind=='objective_match',ClubProgress.definition_key==str(match_ref)))
        digest=fingerprint(payload.model_dump(mode='json',exclude={'expected_revision'}))
        if row and row.state.get('request_hash')==digest:return dict(match_ref=str(match_ref),**row.state)
        revision=row.state['revision'] if row else 0
        if revision!=payload.expected_revision:raise HTTPException(409,'El diario cambió; recarga antes de corregirlo')
        tasks=[]
        levels=['beginner','amateur','semi_pro','professional','world_class','legendary','ultimate']
        for task in payload.tasks:
            goal=get_goal(db,task.objective_id)
            try:rules=ObjectiveRules.model_validate(goal.planning_rules)
            except ValidationError:raise HTTPException(409,'Revisa las reglas de este objetivo antes de registrar tareas') from None
            action=next((a for a in rules.actions if a.id==task.action_id),None)
            if not rules.reviewed or not action or rules.mode not in {'any',payload.mode}:
                raise HTTPException(422,'La tarea no está revisada o sus modalidades son incompatibles')
            if goal.expires_at and utc(goal.expires_at)<payload.played_at:raise HTTPException(422,'El partido es posterior al vencimiento del objetivo')
            if rules.min_difficulty=='unknown' or rules.min_difficulty in levels and (payload.difficulty not in levels or levels.index(payload.difficulty)<levels.index(rules.min_difficulty)):
                raise HTTPException(422,'La dificultad no cumple el requisito revisado')
            if action.kind in {'wins','matches','participate'} and task.count>1:raise HTTPException(422,'Una partida no puede contar como varias victorias o partidos')
            tasks.append({**task.model_dump(),'kind':action.kind,'objective_name':goal.name,'action_text':action.source_text,
                'rules_revision':goal.planning_revision,'conditions_verified':False})
        previous=row.state if row else {}
        if not row:
            row=ClubProgress(kind='objective_match',definition_key=str(match_ref));db.add(row)
        row.state={**payload.model_dump(mode='json',exclude={'expected_revision'}),'tasks':tasks,'request_hash':digest,
            'revision':revision+1,'history':[*previous.get('history',[])[-19:],{k:v for k,v in previous.items() if k!='history'}] if previous else [],
            'ea_progress_updated':False,'updated_at':now().isoformat()}
        record(db,'declare_objective_match','objective_journal',0,{'match_ref':str(match_ref),'revision':revision+1})
        db.commit();return dict(match_ref=str(match_ref),**row.state)


@router.get('/objective-journal')
def journal(db:Session=Depends(get_db)):
    rows=list(db.scalars(select(ClubProgress).where(ClubProgress.kind=='objective_match').order_by(ClubProgress.id.desc()).limit(101)))
    return dict(items=[dict(match_ref=r.definition_key,**r.state) for r in rows[:100]],truncated=len(rows)>100,
        source='user_declared',ea_progress_updated=False,message='Diario declarado por partido. Corregir sustituye esa partida; no certifica condiciones ni progreso de EA.')
