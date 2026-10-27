import {useState} from 'react'
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query'
import {api} from '../api/client'
import {invalidateClub} from '../lib/query'
import {observedDate} from '../lib/i18n'
import {navigate} from '../lib/navigation'
import type {ReaderObservation,ReaderObservationDetail} from '../types/reader'
import type {VisualReading} from '../types/assisted'
import {VisualReview} from './VisualReview'
import {ErrorBox} from './ui'

const domains:Record<string,string>={account:'Cabecera',inventory:'Inventario',detail:'Ficha',squad:'Plantilla',dcp:'DCP',objective:'Objetivo',gallery:'Galería'}
const states:Record<string,string>={partial:'Fragmentos pendientes',review_required:'Revisión pendiente',reviewed:'Revisada',historical:'Histórica'}
export function DomainObservations({items,onRefresh}:{items:ReaderObservation[];onRefresh:()=>void}){
 const qc=useQueryClient(),[selected,setSelected]=useState<string|null>(null),[page,setPage]=useState(0),[confirmed,setConfirmed]=useState(false),[reading,setReading]=useState<VisualReading|null>(null)
 const detail=useQuery({queryKey:['domain-observation',selected],enabled:!!selected,queryFn:()=>api<ReaderObservationDetail>(`/reader/observations/${selected}`)})
 const review=useMutation({mutationFn:()=>api(`/reader/observations/${selected}/review`,{method:'POST',body:JSON.stringify({confirmation:'REVISAR OBSERVACION DOM',context_confirmed:true})}),onSuccess:()=>{setConfirmed(false);void invalidateClub(qc);void detail.refetch();onRefresh()}})
 const openRules=useMutation({mutationFn:(id:number)=>api<VisualReading>(`/assisted/readings/${id}`),onSuccess:setReading})
 const d=detail.data,records=d?Object.values(d.fragments).flatMap(f=>f.payload.records||[]):[]
 return <section><h4>Observaciones por dominio</h4><p>La recepción completa se refiere a esta región. Inventario, historial, Galería y objetivos mantienen coberturas independientes. Confirma el contexto antes de admitir datos; un nombre visible no verifica una cuenta EA.</p>
 {items.map(o=><p key={o.observation_id}><button onClick={()=>{setSelected(o.observation_id);setPage(0);setConfirmed(false);setReading(null)}}>{domains[o.domain]} · {o.count} registros</button> · {states[o.status]} · {o.fragments_received}/{o.fragments_expected} fragmentos · {o.source_kind==='observed_page_dom'?'Página observada, sin verificación EA':o.source_kind==='synthetic_dom'?'SINTÉTICO':'Exportación declarada'}</p>)}
 {d&&<><p>Observado: {observedDate(d.observed_at)} · recibido: {observedDate(d.received_at)}. Perfil r{d.profile.revision} · {d.profile.language}. Fecha de actualización del proveedor desconocida.</p>
 {d.missing_fragments.length>0&&<p>Faltan fragmentos: {d.missing_fragments.map(i=>i+1).join(', ')}. Reintenta el envío desde la extensión; esta lectura aún no se admite.</p>}
 {Object.values(d.fragments).filter(f=>f.payload.domain==='account').map(f=><p key={f.event_id}>Club observado: {f.payload.club_name??'desconocido'} · monedas: {f.payload.balance??'desconocidas'}</p>)}
 <ul>{records.slice(page*20,(page+1)*20).map((r,i)=><li key={page*20+i}>{r.name?`${r.name} · ${r.rating} · ${r.position}${r.slot?' · '+r.slot:''}`:r.title}{r.requirement_text&&<p>{r.requirement_text}</p>}{r.progress_current!=null&&<p>Progreso observado: {r.progress_current} / {r.progress_target??'desconocido'} (sin aplicación automática).</p>}</li>)}</ul>
 {records.length>20&&<p><button disabled={page===0} onClick={()=>setPage(page-1)}>Anteriores</button> {page+1} / {Math.ceil(records.length/20)} <button disabled={(page+1)*20>=records.length} onClick={()=>setPage(page+1)}>Siguientes</button></p>}
 <details><summary>Campos y procedencia de cada fragmento</summary>{Object.entries(d.fragments).map(([key,f])=><details key={key}><summary>Fragmento {Number(key)+1}</summary><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere',maxHeight:400,overflow:'auto'}}>{JSON.stringify(f.payload,null,2)}</pre></details>)}</details>
 {d.status==='review_required'&&<><label className="check"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>Revisé esta región y corresponde al club de este contexto</label><button disabled={!confirmed||review.isPending} onClick={()=>review.mutate()}>Admitir observación revisada</button></>}
 {!!d.pending_records?.length&&<p>{d.pending_records.length} registros requieren resolver identidad o cambios. No se crearon copias adicionales ni se reactivaron retiradas.</p>}
 {d.reading_ids&&<p>Lecturas guardadas: {d.reading_ids.join(', ')}. La principal se registra explícitamente desde Lectura asistida; no se activa ni se sustituye al leer.</p>}
 {d.rule_review_required&&d.pending_rule_reading_ids.map(id=><button key={id} onClick={()=>openRules.mutate(id)}>Revisar todos los requisitos de la lectura {id}</button>)}
 {d.domain==='dcp'&&d.status==='reviewed'&&!d.pending_rule_reading_ids.length&&<button onClick={()=>navigate('dcp')}>Calcular una propuesta con este DCP revisado</button>}
 {d.domain==='gallery'&&d.status==='reviewed'&&<p>La evidencia se conserva. No acredita historial elegible, conjunto completado ni recompensa recibida.</p>}
 </>}
 {reading&&<VisualReview reading={reading} onClose={()=>setReading(null)} onSaved={()=>{setReading(null);void invalidateClub(qc);onRefresh()}}/>}
 <ErrorBox error={detail.error||review.error||openRules.error}/></section>
}
