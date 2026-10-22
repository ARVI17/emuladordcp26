from types import SimpleNamespace
from datetime import timedelta
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.entities import GallerySet,GalleryEntry,now
from app.models.planner import ClubProgress,MarketQuote
from app.schemas.fc27 import GalleryRules
from app.schemas.gallery_planning import GalleryProgressInput,GalleryRouteInput
from app.services.gallery import item_key
from app.services.gallery_v2 import evaluate_v2,reward_accounting
from app.services.gallery_route import plan_route
from app.services.contexts import require_module,utc
from app.services.locks import resource_locks
from app.services.audit import record
from app.services.definition_validation import is_documented

router=APIRouter(prefix='/gallery',tags=['Galería por grados y capital'])


def definition(db,identifier):
    row=db.scalar(select(GallerySet).where(GallerySet.id==identifier).execution_options(include_pending_definitions=True))
    if not row or not row.rules_reviewed or row.rules.get('schema_version')!=2:
        raise HTTPException(409,'Se necesita un conjunto revisado con reglas versión 2')
    return row


@router.get('/local-scenarios')
def scenarios(db:Session=Depends(get_db)):
    rows=db.scalars(select(GallerySet).execution_options(include_pending_definitions=True))
    history=list(db.scalars(select(GalleryEntry)))
    states={p.definition_key:p.state for p in db.scalars(select(ClubProgress).where(ClubProgress.kind=='gallery_declared'))}
    return [dict(id=r.id,name=r.name,rules=r.rules,tags=r.tags,grade_thresholds=r.grade_thresholds,
        source='documented' if is_documented(r) else 'local_scenario',progress=states.get(str(r.id),{}),
        evaluation=evaluate_v2(r,history)) for r in rows if r.rules.get('schema_version')==2 and r.rules_reviewed]


@router.put('/sets/{identifier}/declared-progress')
def declared_progress(identifier:int,payload:GalleryProgressInput,db:Session=Depends(get_db)):
    require_module(db,'gallery')
    with resource_locks(db,'gallery-progress:'+str(db.info['context'].id)):
        row=definition(db,identifier)
        rules=GalleryRules.model_validate(row.rules)
        try:reward_accounting(row.grade_thresholds,rules.rewards,rules.reward_mode,0,attained=payload.attained_grade,claimed=payload.claimed_grade)
        except ValueError as error:raise HTTPException(422,str(error)) from None
        progress=db.scalar(select(ClubProgress).where(ClubProgress.kind=='gallery_declared',ClubProgress.definition_key==str(identifier)))
        if not progress:
            progress=ClubProgress(kind='gallery_declared',definition_key=str(identifier));db.add(progress)
        previous=progress.state or {}
        current=payload.model_dump(exclude={'confirmation'})
        if {k:previous.get(k) for k in current}==current:return previous
        progress.state={**current,'observed_at':now().isoformat(),'history':[*previous.get('history',[])[-19:],{k:v for k,v in previous.items() if k!='history'}] if previous else []}
        record(db,'declare_gallery_grade','gallery',identifier,{'source':'user_declared'})
        db.commit();return progress.state


@router.post('/route-preview')
def route_preview(payload:GalleryRouteInput,db:Session=Depends(get_db)):
    require_module(db,'gallery')
    with resource_locks(db,'inventory'):
        sets=[definition(db,i) for i in payload.set_ids]
        if not payload.allow_scenarios and any(not is_documented(r) for r in sets):
            raise HTTPException(409,'Estas reglas son escenarios locales. Revisa y habilita escenarios explícitamente.')
        history=list(db.scalars(select(GalleryEntry)))
        states={int(p.definition_key):p.state for p in db.scalars(select(ClubProgress).where(ClubProgress.kind=='gallery_declared')) if p.definition_key.isdigit()}
        if any(s.id not in states for s in sets):
            raise HTTPException(409,'Declara primero el grado obtenido/reclamado de cada conjunto; desconocido no equivale a cero.')
        for s in sets:
            p=states[s.id]
            try:reward_accounting(s.grade_thresholds,s.rules.get('rewards',{}),s.rules.get('reward_mode','cumulative'),None,attained=p.get('attained_grade'),claimed=p.get('claimed_grade'))
            except ValueError:raise HTTPException(409,'El progreso declarado no coincide con las reglas actuales; revísalo antes de calcular') from None
        acquisitions=[]
        from app.services.catalog_validation import require_variant
        for candidate in payload.candidates:
            variant=require_variant(db,candidate.variant_id)
            quotes=[]
            for identifier in [candidate.purchase_quote_id,candidate.resale_quote_id]:
                if identifier is None:quotes.append(None);continue
                quote=db.scalar(select(MarketQuote).where(MarketQuote.id==identifier))
                if (not quote or quote.variant_id!=variant.variant_id or quote.market!=payload.market or quote.currency!='coins'
                    or quote.amount<=0 or utc(quote.expires_at)<=now() or utc(quote.observed_at)>now()
                    or now()-utc(quote.observed_at)>timedelta(hours=24)):
                    raise HTTPException(409,'Cotización ausente, vencida, desconocida o de otro mercado')
                quotes.append(quote)
            if quotes[0].kind!='listing' or (quotes[1] and quotes[1].kind not in {'listing','observed_sale'}):
                raise HTTPException(409,'Usa un anuncio de adquisición y una salida conservadora revisada')
            facts={k:v for k,v in variant.evidence.get('fields',{}).items() if k in {'athlete_id','league','club','nationality','is_loan','is_evolution','is_holographic','holographic_level','gallery_score','skill_moves','weak_foot'}}
            if facts.get('is_loan') is not False or facts.get('is_evolution') is not False or type(facts.get('gallery_score')) is not int:
                raise HTTPException(409,'La variante de compra necesita puntuación, cesión y base documentadas; no se inventaron puntos')
            card=dict(**facts,card_id=variant.variant_id,name=variant.name,rating=variant.rating,position=variant.position,
                card_type=variant.card_type,score_reviewed=True,first_owner=False,game_version='FC27',hypothetical_acquisition=True)
            key=item_key(card)
            entry=SimpleNamespace(id=-len(acquisitions)-1,item_key=key,player_id=None,game_version='FC27',snapshot=card,recorded_at=None)
            acquisitions.append(dict(key=key,variant_id=variant.variant_id,buy=quotes[0].amount,resale=quotes[1].amount if quotes[1] else None,
                keep=candidate.keep,entry=entry,quote_observed_at=quotes[0].observed_at.isoformat(),source=quotes[0].source_url,
                resale_evidence='estimate_not_observed_sale' if not quotes[1] or quotes[1].kind!='observed_sale' else 'historical_sale_not_your_sale'))
        return plan_route(sets,history,acquisitions,states,payload)
