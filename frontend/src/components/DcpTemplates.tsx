import {useState} from 'react'
import {useMutation,useQuery} from '@tanstack/react-query'
import {api} from '../api/client'
import type {DcpFilterValue} from './DcpFilters'
import {ErrorBox} from './ui'
export function DcpTemplates({readingId,filters,onApply}:{readingId?:number;filters:DcpFilterValue;onApply:(filters:DcpFilterValue)=>void}){
 const [name,setName]=useState('')
 const query=useQuery({queryKey:['dcp-templates'],queryFn:()=>api<{id:string;name:string;filters:DcpFilterValue;requirements_hash:string}[]>('/dcp/templates')})
 const save=useMutation({mutationFn:()=>api('/dcp/templates',{method:'POST',body:JSON.stringify({name,reading_id:readingId,filters,max_solutions:3})}),onSuccess:()=>{setName('');void query.refetch()}})
 return <details className="panel"><summary>Biblioteca de configuraciones DCP</summary><p>Guarda filtros y la versión de requisitos revisada. Aplicar una configuración solo cambia la selección local; vuelve a calcular contra las cartas disponibles.</p><label>Nombre de la configuración<input value={name} onChange={e=>setName(e.target.value)} maxLength={80}/></label><button disabled={!readingId||!name.trim()||save.isPending} onClick={()=>save.mutate()}>Guardar configuración de selección</button>{query.data?.map(t=><p key={t.id}>{t.name} <button onClick={()=>onApply(t.filters)}>Aplicar filtros de esta configuración</button></p>)}<ErrorBox error={query.error||save.error}/></details>
}
