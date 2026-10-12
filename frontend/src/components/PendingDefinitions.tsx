import {useQuery} from '@tanstack/react-query'
import {api} from '../api/client'
import type {PendingDefinitionsResponse} from '../types'
import {ErrorBox,Notice} from './ui'

export function PendingDefinitions(){
 const query=useQuery({queryKey:['pending-definitions'],queryFn:()=>api<PendingDefinitionsResponse>('/catalog/pending')})
 const labels:Record<string,string>={dcp:'DCP',objective:'objetivos',gallery:'conjuntos',evolution:'evoluciones',public:'referencias de reglas'}
 return <><ErrorBox error={query.error}/><Notice>Solo se utilizan reglas con evidencia vigente de FC27. Guardar una definición manual crea un borrador pendiente.</Notice>{query.data?.counts&&Object.values(query.data.counts).some(Boolean)&&<details className="panel"><summary>Definiciones pendientes de verificación</summary><p>{query.data.message}</p><p>{Object.entries(query.data.counts).filter(([,n])=>n>0).map(([key,n])=>`${n} ${labels[key]}`).join(' · ')}</p></details>}</>
}
