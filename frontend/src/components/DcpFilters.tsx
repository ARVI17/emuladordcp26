import {useEffect,useState} from 'react'
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query'
import {api} from '../api/client'
import {ErrorBox,Notice} from './ui'
import type {MainSquadStatus} from './MainSquadProtection'

export type DcpFilterValue={min_rating:number;max_rating:number;position:string|null;league:string|null;club:string|null;nationality:string|null;card_type:string|null;tradable:boolean|null;duplicate:boolean|null;special:boolean|null;max_price:number|null;location:string|null;availability:'available'|'all';preset:'available'|'duplicates'|'keep_special'|'limit_value'}
export const defaultDcpFilters:DcpFilterValue={min_rating:1,max_rating:99,position:null,league:null,club:null,nationality:null,card_type:null,tradable:null,duplicate:null,special:null,max_price:null,location:null,availability:'available',preset:'available'}
export function DcpFilters({value,onChange}:{value:DcpFilterValue;onChange:(value:DcpFilterValue)=>void}){
 const qc=useQueryClient(),[loaded,setLoaded]=useState(false),[offset,setOffset]=useState(0)
 const saved=useQuery({queryKey:['dcp-preferences'],queryFn:()=>api<DcpFilterValue>('/dcp/preferences')})
 useEffect(()=>{if(saved.data&&!loaded){onChange(saved.data);setLoaded(true)}},[saved.data,loaded,onChange])
 const exclusions=useQuery({queryKey:['dcp-exclusions',offset],queryFn:()=>api<{items:{id:number;name:string;rating:number;reason:string}[];total:number;main:MainSquadStatus}>(`/dcp/exclusions?offset=${offset}&limit=20`)})
 const save=useMutation({mutationFn:()=>api('/dcp/preferences',{method:'PUT',body:JSON.stringify(value)}),onSuccess:()=>qc.invalidateQueries({queryKey:['dcp-preferences']})})
 return <section className="panel"><h3>Cartas que puede usar el DCP</h3>
  {exclusions.data?.main.reason&&<Notice>{exclusions.data.main.reason} La simulación sigue disponible.</Notice>}
  <details><summary>Filtrar cartas y guardar preferencias</summary><div className="form-grid">
   <label>Media mínima<input type="number" min={1} max={99} value={value.min_rating} onChange={e=>onChange({...value,min_rating:Number(e.target.value)})}/></label>
   <label>Media máxima<input type="number" min={1} max={99} value={value.max_rating} onChange={e=>onChange({...value,max_rating:Number(e.target.value)})}/></label>
   {(['position','league','club','nationality','card_type'] as const).map((key,i)=><label key={key}>{['Posición','Liga','Club','Nacionalidad','Tipo de carta'][i]}<input value={value[key]||''} onChange={e=>onChange({...value,[key]:e.target.value||null})}/></label>)}
   {(['tradable','duplicate','special'] as const).map((key,i)=><label key={key}>{['Transferible','Copia duplicada','Carta especial'][i]}<select value={value[key]===null?'':String(value[key])} onChange={e=>onChange({...value,[key]:e.target.value===''?null:e.target.value==='true'})}><option value="">Cualquiera</option><option value="true">Sí</option><option value="false">No</option></select></label>)}
   <label>Precio conocido máximo<input type="number" min={0} value={value.max_price??''} onChange={e=>onChange({...value,max_price:e.target.value===''?null:Number(e.target.value)})}/></label>
   <label>Ubicación<select value={value.location||''} onChange={e=>onChange({...value,location:e.target.value||null})}><option value="">Cualquiera</option><option value="local">Registro local</option><option value="club">Club</option><option value="sbc_storage">Almacén DCP</option><option value="unassigned">Sin asignar</option><option value="transfer_list">Lista de transferibles</option></select></label>
   <label>Preferencia<select value={value.preset} onChange={e=>onChange({...value,preset:e.target.value as DcpFilterValue['preset']})}><option value="available">Propias disponibles</option><option value="duplicates">Priorizar duplicados</option><option value="keep_special">Conservar especiales</option><option value="limit_value">Limitar valor conocido</option></select></label>
  </div><p>Las protecciones siempre se aplican. Un precio desconocido no cumple un límite de precio conocido.</p><button onClick={()=>save.mutate()} disabled={save.isPending}>Guardar filtros DCP</button>{save.isSuccess&&<p role="status">Filtros guardados.</p>}</details>
  <details><summary>Protegidas: no se usarán · {exclusions.data?.total??'Sin consultar'} excluidas</summary><p>También se muestran cartas pendientes o no disponibles; ninguna puede incluirse cambiando un filtro.</p>{exclusions.data?.items.map(p=><p key={p.id}>{p.rating} · {p.name}: {p.reason}</p>)}<div className="button-row"><button disabled={!offset} onClick={()=>setOffset(Math.max(0,offset-20))}>Anteriores</button><button disabled={!exclusions.data||offset+20>=exclusions.data.total} onClick={()=>setOffset(offset+20)}>Siguientes</button></div></details>
  <ErrorBox error={saved.error||save.error||exclusions.error}/>
 </section>
}
