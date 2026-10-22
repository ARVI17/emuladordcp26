import {useState} from 'react'
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query'
import {api} from '../api/client'
import {invalidateClub} from '../lib/query'
import {observedDate} from '../lib/i18n'
import {ErrorBox} from './ui'
type Event={event_id:string;status:string;count:number;observed_at:string;source_kind:string;reading_id:number|null}
type Status={grants:{id:string;extension_id:string;status:string}[];events:Event[]}
type Detail={payload:{observed_at:string;view:string;records:{name:string;rating:number;position:string;is_loan:boolean|null;is_evolution:boolean|null;first_owner:boolean|null}[];scope:unknown};receipt:Event}
export function StructuredReader(){
 const qc=useQueryClient(),[extension,setExtension]=useState(''),[selected,setSelected]=useState<string|null>(null)
 const status=useQuery({queryKey:['structured-reader'],queryFn:()=>api<Status>('/reader/status')})
 const detail=useQuery({queryKey:['structured-event',selected],enabled:!!selected,queryFn:()=>api<Detail>(`/reader/events/${selected}`)})
 const pair=useMutation({mutationFn:()=>api<{pairing_id:string;code:string;expires_at:string}>('/reader/pairings',{method:'POST',body:JSON.stringify({extension_id:extension,confirmation:'EMPAREJAR LECTOR'})})})
 const review=useMutation({mutationFn:()=>api(`/reader/events/${selected}/review`,{method:'POST',body:JSON.stringify({confirmation:'REVISAR LOTE DOM'})}),onSuccess:()=>{void invalidateClub(qc);void status.refetch();void detail.refetch()}})
 const revoke=useMutation({mutationFn:(id:string)=>api(`/reader/grants/${id}/revoke`,{method:'POST',body:'{}'}),onSuccess:()=>status.refetch()})
 return <section className="panel"><h3>Lector estructurado local</h3><p>La extensión lee muestras del formato Club Lab. El extractor de FC27 está pendiente de contrastar una muestra real. Cada lote conserva campos desconocidos y cobertura parcial.</p>
 <label>ID mostrado por la extensión<input value={extension} onChange={e=>setExtension(e.target.value)} maxLength={32}/></label><button disabled={!/^[a-p]{32}$/.test(extension)||pair.isPending} onClick={()=>pair.mutate()}>Aprobar emparejamiento del lector</button>
 {pair.data&&<div role="status"><p>Emparejamiento: <code>{pair.data.pairing_id}</code></p><p>Código temporal: <strong>{pair.data.code}</strong> · caduca en tres minutos.</p></div>}
 <button onClick={()=>void status.refetch()}>Actualizar lotes recibidos</button>
 {status.data?.grants.filter(g=>g.status==='active').map(g=><p key={g.id}>Extensión {g.extension_id} <button onClick={()=>revoke.mutate(g.id)}>Revocar</button></p>)}
 {status.data?.events.map(e=><p key={e.event_id}><button onClick={()=>setSelected(e.event_id)}>Revisar lote de {e.count} cartas</button> · {e.source_kind==='synthetic_dom'?'SINTÉTICO':'Exportación declarada'} · {({review_required:'Pendiente de revisión',historical:'Histórico',reviewed:'Revisado'} as Record<string,string>)[e.status]||e.status}</p>)}
 {detail.data&&<><p>Observado: {observedDate(detail.data.payload.observed_at)}. Revisa el lote completo antes de admitirlo al cálculo. No verifica propiedad oficial ni identifica copias EA.</p><ul>{detail.data.payload.records.map((c,i)=><li key={i}>{c.name} · {c.rating} · {c.position} · cesión {c.is_loan==null?'desconocida':c.is_loan?'sí':'no'} · primer propietario {c.first_owner==null?'desconocido':c.first_owner?'sí':'no'}</li>)}</ul><details><summary>Ver todos los campos y la evidencia del lote</summary><p>Comprueba los valores extraídos, los desconocidos y la página de origen antes de admitirlos.</p><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere',maxHeight:400,overflow:'auto'}}>{JSON.stringify(detail.data.payload,null,2)}</pre></details><button disabled={review.isPending||detail.data.receipt.status!=='review_required'} onClick={()=>review.mutate()}>Revisé el lote DOM: admitir observaciones</button><p>Después abre Análisis o pulsa Analizar lo leído en la extensión. Las alternativas conservan la principal.</p></>}
 <ErrorBox error={status.error||detail.error||pair.error||review.error||revoke.error}/></section>
}
