import {useState} from 'react'
import {useMutation,useQuery} from '@tanstack/react-query'
import {api,money} from '../api/client'
import type {VisualReading} from '../types/assisted'
import type {Solution} from '../types'
import {navigate} from '../lib/navigation'
import {DcpFilters,defaultDcpFilters} from './DcpFilters'
import {DcpTemplates} from './DcpTemplates'
import {SectionTitle,ErrorBox} from './ui'

type Result={name:string;solutions:Solution[];exclusions:{id:number;name:string;reason:string}[];message:string}
export function AssistedDcp(){
 const [selected,setSelected]=useState<number>(),[filters,setFilters]=useState(defaultDcpFilters)
 const [locked,setLocked]=useState<number[]>([]),[result,setResult]=useState<Result>()
 const readings=useQuery({queryKey:['assisted-readings'],queryFn:()=>api<{items:VisualReading[]}>('/assisted/readings')})
 const simulate=useMutation({mutationFn:({keep=locked,exclude=[]}:{keep?:number[];exclude?:number[]})=>api<Result>(`/assisted/readings/${selected}/simulate-dcp`,{method:'POST',body:JSON.stringify({filters,max_solutions:3,locked_ids:keep,exclude_ids:exclude})}),onSuccess:data=>setResult(data)})
 const reset=()=>{setResult(undefined);setLocked([]);simulate.reset()}
 return <><SectionTitle title="DCP observados" subtitle="Simulaciones sobre reglas y cartas revisadas; sin entregas"/>
 <section className="panel"><p>Lee el DCP en Mi cuenta y revisa los comparadores, tipo y caducidad. Se mantienen todas las protecciones y reservas del club.</p>
 <button onClick={()=>navigate('conexiones')}>Leer un DCP desde una pantalla</button>
 <label>DCP leído y revisado<select value={selected||''} onChange={e=>{setSelected(Number(e.target.value));reset()}}><option value="">Seleccionar lectura</option>{readings.data?.items.filter(r=>r.scope==='dcp'&&r.status==='reviewed').map(r=><option key={r.id} value={r.id}>#{r.id} · {r.page}</option>)}</select></label></section>
 <DcpFilters value={filters} onChange={value=>{setFilters(value);reset()}}/>
 <DcpTemplates readingId={selected} filters={filters} onApply={value=>{setFilters({...defaultDcpFilters,...value});reset()}}/>
 <button disabled={!selected||simulate.isPending} onClick={()=>simulate.mutate({})}>Simular DCP con mis cartas aptas</button>
 <ErrorBox error={readings.error||simulate.error}/>
 {result&&<><p>{result.message}</p>{!result.solutions.length&&<p>No hay una combinación validada con estos filtros y cartas fijas. No se ha quitado ningún bloqueo.</p>}
 {result.solutions.map((s,i)=><section className="panel" key={i}><h3>{result.name} · Propuesta {i+1}</h3>
 <p>Media local {s.rating} · Valor conocido {money(s.total_cost)} · {s.player_ids.length} copias locales</p>
 <ul>{s.players.map(p=><li key={p.id}>{p.name} · {p.rating} · {p.position} · {p.card_type||'Variante desconocida'} · Copia local #{p.id}
 <label className="check"><input type="checkbox" checked={locked.includes(p.id)} onChange={e=>setLocked(e.target.checked?[...locked,p.id]:locked.filter(id=>id!==p.id))}/>Fijar en el próximo cálculo</label>
 <button disabled={simulate.isPending||locked.includes(p.id)} onClick={()=>simulate.mutate({keep:[...new Set([...locked,...s.player_ids.filter(id=>id!==p.id)])],exclude:[p.id]})}>Sustituir solo esta carta</button></li>)}</ul>
 <p>Revisa identidad y requisitos antes de preparar manualmente la combinación. Sustituir conserva las demás cartas y vuelve a validar disponibilidad y protecciones.</p></section>)}
 <details><summary>Exclusiones de esta simulación ({result.exclusions.length})</summary><ul>{result.exclusions.map(e=><li key={e.id}>{e.name}: {e.reason}</li>)}</ul></details></>}
 </>
}
