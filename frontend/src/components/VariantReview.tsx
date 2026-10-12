import {observedDate} from '../lib/i18n'
import {useState} from 'react'
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query'
import {api} from '../api/client'
import type {PlayerInput} from '../types'
import {invalidateClub} from '../lib/query'
import {PlayerEditor} from './PlayerEditor'
import {ErrorBox,Notice,Pagination} from './ui'

type Variant={id:number;variant_id:string;name:string;rating:number;position:string;card_type:string;source_url:string;observed_at:string;valid_until:string;validation_status:string}
type Claim={id:number;claim:PlayerInput;evidence:{reason?:string}}
export function VariantReview({onChoose}:{onChoose:(p:Partial<PlayerInput>)=>void}){
 const qc=useQueryClient(),[search,setSearch]=useState(''),[offset,setOffset]=useState(0),[edit,setEdit]=useState<Claim|null>(null),[source,setSource]=useState(''),[confirmation,setConfirmation]=useState(''),[message,setMessage]=useState('')
 const catalog=useQuery({queryKey:['variant-catalog',search],queryFn:()=>api<{items:Variant[];has_more:boolean}>('/catalog/variants?search='+encodeURIComponent(search))})
 const pending=useQuery({queryKey:['quarantine',offset],queryFn:()=>api<{items:Claim[];total:number;message:string}>('/inventory/quarantine?offset='+offset)})
 const review=useMutation({mutationFn:(player:PlayerInput)=>api<{quarantined?:boolean;message?:string}>(`/inventory/quarantine/${edit!.id}/review`,{method:'POST',body:JSON.stringify({player,source_url:source,confirmation})}),onSuccess:r=>{setMessage(r.quarantined?r.message!:'Copia FC27 documentada activada en el registro manual.');setEdit(null);void invalidateClub(qc)}})
 return <>
  <details className="panel"><summary>Catálogo FC27 documentado · no son mis cartas</summary><p>Fichas contrastadas con su fuente y fecha. No acreditan posesión, atributos completos ni precios. Las variantes pendientes quedan excluidas. El tipo conserva la etiqueta del catálogo de origen; no certifica la clasificación oficial de EA.</p><label>Buscar variante<input value={search} onChange={e=>setSearch(e.target.value)}/></label><ErrorBox error={catalog.error}/>
   {catalog.data?.items.map(v=><div key={v.id} className="list-row"><div><strong>{v.name} · {v.rating} · {v.position}</strong><p>{v.card_type} · ID {v.variant_id} · <a href={v.source_url} target="_blank" rel="noreferrer">Fuente</a> · {observedDate(v.observed_at)}</p></div><button onClick={()=>onChoose({game_version:'FC27',name:v.name,rating:v.rating,position:v.position,card_type:v.card_type,card_id:v.variant_id})}>Revisar copia que poseo</button></div>)}
   {catalog.data?.has_more&&<p>Afina la búsqueda para ver otras variantes.</p>}
  </details>
  <details className="panel"><summary>Cuarentena · {pending.data?.total??0} declaraciones pendientes</summary><p>{pending.data?.message}</p><ErrorBox error={pending.error}/>
   {pending.data?.items.map(p=><div className="list-row" key={p.id}><div>{p.claim.name} · {p.claim.rating}<p>{p.evidence.reason||'Evidencia de variante pendiente'}</p></div><button onClick={()=>{setEdit(p);setConfirmation('');review.reset()}}>Revisar declaración #{p.id}</button></div>)}
   <Pagination page={offset/20+1} total={pending.data?.total??0} pageSize={20} onPage={p=>setOffset((p-1)*20)}/>
   {edit&&<><label>Fuente pública de la variante<input type="url" value={source} onChange={e=>setSource(e.target.value)}/></label><label>Escribe REVISAR FC27 {edit.id}<input value={confirmation} onChange={e=>setConfirmation(e.target.value)}/></label><PlayerEditor key={edit.id} initial={edit.claim} onSave={p=>review.mutate(p)} onCancel={()=>setEdit(null)} pending={review.isPending} error={review.error} buttonLabel="Contrastar variante y guardar revisión"/></>}
  </details>{message&&<Notice>{message}</Notice>}
 </>
}
