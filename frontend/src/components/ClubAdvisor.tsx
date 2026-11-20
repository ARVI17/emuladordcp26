import {useState} from 'react'
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query'
import {api, money} from '../api/client'
import {observedDate} from '../lib/i18n'
import {navigate} from '../lib/navigation'
import type {EntryState} from '../lib/entry'
import {ErrorBox} from './ui'

export type AdvisorStyle = 'balanced' | 'defensive' | 'wide'
type Card = {id:number; name:string; position:string; rating:number}
type Starter = Card & {slot:string; fit:number; reason:string}
type Gap = {slot:string; position:string}
type Squad = {formation:string; solver_status:string; lineup:Starter[]; gaps:Gap[]; bench:Card[]}
type Plan = {binding:{revision:number}; style:AdvisorStyle; reviewed:number; latest_card_observation:string|null;
  protection:{ready:boolean; starters:number; bench:number; reserves:number}; squad:Squad|null}
type Dcp = {name:string; expires_at:string; status:'covered'|'partial'|'no_solution'|'protection_pending'; players:string[]; card_value:number|null}
type Opportunities = {dcp:Dcp[]; dcp_source:string; dcp_reason:string|null;
  sales:{reason:string|null; items:{id:number;name:string;amount:number;observed_at:string;source_url:string}[]};
  gallery:{name:string;filled:number;required:number}[]}

const styles:Record<AdvisorStyle,string> = {balanced:'Equilibrio',defensive:'Defensa',wide:'Por bandas'}
const lines = [['EI','SD','DC','ED'],['MCO'],['MI','MC','MD'],['MCD'],['CAI','LI','DFC','LD','CAD'],['POR']]
const dcpLabels:Record<Dcp['status'],string> = {covered:'Cubierto con tus cartas',partial:'Aporta puntos al segmento',
  no_solution:'Sin combinación acreditada',protection_pending:'Pendiente de proteger la principal'}

function TacticalBoard({squad}:{squad:Squad}){
  const [selected,setSelected] = useState<string>()
  const active = squad.lineup.find(p=>p.slot===selected)
  const slots:(Starter|Gap)[] = [...squad.lineup,...squad.gaps]
  return <div>
    <div className="advisor-field" role="group" aria-label="Once propuesto por puestos">
      {lines.map(positions=>{
        const row = positions.flatMap(position=>slots.filter(s=>s.position===position)).sort((a,b)=>
          positions.indexOf(a.position)-positions.indexOf(b.position) || a.slot.localeCompare(b.slot))
        return row.length>0 && <div className="advisor-line" key={positions[0]}>{row.map(p=>
          'id' in p ? <button key={p.slot} className="advisor-player" aria-pressed={p.slot===selected}
            aria-label={p.name+' · '+p.slot+' · '+p.rating} onClick={()=>setSelected(p.slot===selected?undefined:p.slot)}>
            <span>{p.position} <b>{p.rating}</b></span><strong>{p.name}</strong></button>
          : <div key={p.slot} className="advisor-vacancy"><span>{p.position}</span><small>Vacante</small></div>)}</div>
      })}
    </div>
    {active ? <p className="advisor-evidence" role="status"><strong>{active.name}</strong> · {active.fit} de encaje local. {active.reason.replaceAll('; ', ' · ')}.</p>
      : <p className="meta">Selecciona un titular para ver qué atributos explican su puesto.</p>}
  </div>
}

function Coach({style}:{style:AdvisorStyle}){
  const qc = useQueryClient()
  const ask = useMutation({mutationFn:()=>api<{available:boolean;answer:string}>('/ai/chat',{
    method:'POST',body:JSON.stringify({message:'Explícame este equipo',squad_style:style})}),
    onSuccess:()=>{void qc.invalidateQueries({queryKey:['ai-history']})}})
  return <div className="advisor-coach">
    <button onClick={()=>ask.mutate()} disabled={ask.isPending}>{ask.isPending?'Preparando la explicación…':'Explicar este equipo con IA local'}</button>
    {ask.data && <div role="status"><strong>{ask.data.available?'Análisis con Ollama':'Explicación del optimizador local'}</strong><p>{ask.data.answer}</p></div>}
    <ErrorBox error={ask.error}/>
  </div>
}

function ClubOpportunities({entry}:{entry:EntryState}){
  const query = useQuery({queryKey:['club-opportunities',entry.club_context_id,entry.entry_id],
    queryFn:({signal})=>api<Opportunities>('/club/opportunities',{signal}),staleTime:0})
  const data = query.data
  return <section aria-label="Opciones con mis cartas" className="advisor-opportunities">
    <h3>Qué puedo hacer con mis cartas</h3>
    {query.isLoading && <p role="status">Comprobando requisitos y observaciones…</p>}
    <ErrorBox error={query.error}/>
    {data && <div className="advisor-domains">
      <article><h4>DCP con mi club</h4>
        {data.dcp.length ? <><p>Hasta tres segmentos próximos a vencer. Cada simulación usa el club por separado.</p>
          {data.dcp.map((d,i)=><div key={i} className="advisor-option"><strong>{d.name}</strong><p>{dcpLabels[d.status]} · vence el {observedDate(d.expires_at)}.</p>
            {!!d.players.length && <><p>{d.players.join(' · ')}</p><small>Compras adicionales 0 · Valor de las cartas {money(d.card_value)}</small></>}</div>)}</>
          : <p>{data.dcp_reason || 'Aún faltan requisitos revisados con vencimiento vigente para calcular qué DCP puedes cubrir.'}</p>}
        <button onClick={()=>navigate('dcp')}>Ver DCP</button></article>
      <article><h4>Cartas para vender</h4><p>{data.sales.reason || 'Anuncios de consola observados para la misma variante, ordenados por importe.'}</p>
        {data.sales.items.map(q=><div key={q.id} className="advisor-option"><strong>{q.name} · {money(q.amount)} monedas</strong><p>Anuncio registrado el {observedDate(q.observed_at)}. <a href={q.source_url} target="_blank" rel="noreferrer">Fuente</a></p></div>)}
        <button onClick={()=>navigate('mercado')}>Ver mercado</button></article>
      <article><h4>Galería</h4>
        {data.gallery.length ? data.gallery.map(g=><p key={g.name}><strong>{g.name}</strong> · Estimación local de {g.filled}/{g.required} puestos con tu historial.</p>)
          : <p>Faltan conjuntos con reglas vigentes para calcular qué cubre tu colección.</p>}
        <button onClick={()=>navigate('galeria')}>Ver conjuntos</button></article>
    </div>}
  </section>
}

export function ClubAdvisor({entry,onBuild}:{entry:EntryState;onBuild:(formation:string,style:AdvisorStyle)=>void}){
  const [style,setStyle] = useState<AdvisorStyle>('balanced')
  const allowed = entry.mode!=='live' || !!entry.modules.squads?.ready
  const query = useQuery({queryKey:['club-match-plan',entry.club_context_id,entry.entry_id,style],
    enabled:allowed,queryFn:({signal})=>api<Plan>('/club/match-plan?style='+style,{signal}),staleTime:60000})
  const plan=query.data, squad=plan?.squad
  return <section aria-label="Mi plan de partido" className="club-advisor">
    <div className="advisor-heading"><h3>Mi plan de partido</h3>{allowed && <div className="advisor-styles" role="group" aria-label="Enfoque táctico">
      {(Object.keys(styles) as AdvisorStyle[]).map(s=><button key={s} aria-pressed={style===s} onClick={()=>setStyle(s)}>{styles[s]}</button>)}</div>}</div>
    {!allowed ? <div className="panel"><p>Abre el club guardado en Mi cuenta para calcular tu equipo con sus cartas.</p><button onClick={()=>navigate('conexiones')}>Elegir mi club</button></div> :
      <>{query.isLoading && <p role="status">Comparando formaciones con tus cartas revisadas…</p>}<ErrorBox error={query.error}/>
        {plan && <><p className="advisor-source">{plan.reviewed} cartas revisadas · {plan.latest_card_observation ? 'Última observación de cartas el '+observedDate(plan.latest_card_observation) : 'Registro local sin fecha de observación en EA'}</p>
          {squad ? <div className="advisor-match"><div><div className="advisor-scoreline"><h4>{squad.formation}</h4><span>{squad.lineup.length}/11 puestos cubiertos</span></div>
            <TacticalBoard key={style+':'+plan.binding.revision} squad={squad}/></div>
            <aside className="advisor-team-notes"><h4>Banquillo propuesto <span>{squad.bench.length}/7</span></h4>
              <ul className="advisor-bench">{squad.bench.map(p=><li key={p.id}><b>{p.position}</b><span>{p.name}</span><strong>{p.rating}</strong></li>)}</ul>
              <h4>Protección de la principal</h4><p>{plan.protection.ready
                ? `${plan.protection.starters} titulares y ${plan.protection.bench} suplentes protegidos. Reservas protegidas: ${plan.protection.reserves}.`
                : 'El once y los siete suplentes de EA siguen pendientes de confirmación.'}</p>
              <p>{squad.solver_status==='timeout'?'Se agotó el tiempo para verificar este once.':squad.gaps.length?'Puestos por cubrir con las cartas revisadas: '+squad.gaps.map(p=>p.position).join(', ')+'.':'Los once puestos tienen una carta elegible.'} Gasto en fichajes de esta propuesta: 0 monedas.</p>
              <button className="primary" onClick={()=>onBuild(squad.formation,style)}>Ajustar en el creador de plantillas</button>
              <Coach key={style+':'+plan.binding.revision} style={style}/></aside></div>
            : <p>{plan.reviewed?'Se necesita una formación con documentación vigente.':'El club seleccionado todavía no tiene cartas admitidas para proponer un equipo.'}</p>}</>}
        {(entry.mode!=='live'||entry.modules.analysis?.ready) && <ClubOpportunities entry={entry}/>}
      </>}
  </section>
}
