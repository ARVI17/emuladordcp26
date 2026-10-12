import {useState} from 'react'
import {useMutation,useQuery} from '@tanstack/react-query'
import {api,money} from '../api/client'
import type {VisualReading} from '../types/assisted'
import type {Solution} from '../types'
import {navigate} from '../lib/navigation'
import {DcpFilters,defaultDcpFilters} from './DcpFilters'
import {SectionTitle,ErrorBox} from './ui'

export function AssistedDcp(){
 const [selected,setSelected]=useState<number>(),[filters,setFilters]=useState(defaultDcpFilters)
 const readings=useQuery({queryKey:['assisted-readings'],queryFn:()=>api<{items:VisualReading[]}>('/assisted/readings')})
 const simulate=useMutation({mutationFn:()=>api<{name:string;solutions:Solution[];exclusions:{id:number;name:string;reason:string}[];message:string}>(`/assisted/readings/${selected}/simulate-dcp`,{method:'POST',body:JSON.stringify({filters,max_solutions:3})})})
 return <><SectionTitle title="DCP observados" subtitle="Simulaciones sobre reglas y cartas revisadas; sin entregas"/><section className="panel"><p>Lee el DCP en Mi cuenta y revisa los comparadores, tipo y caducidad. Se mantienen todas las protecciones y reservas del club.</p><button onClick={()=>navigate('conexiones')}>Leer un DCP desde una pantalla</button><label>DCP leído y revisado<select value={selected||''} onChange={e=>{setSelected(Number(e.target.value));simulate.reset()}}><option value="">Seleccionar lectura</option>{readings.data?.items.filter(r=>r.scope==='dcp'&&r.status==='reviewed').map(r=><option key={r.id} value={r.id}>#{r.id} · {r.page}</option>)}</select></label></section><DcpFilters value={filters} onChange={value=>{setFilters(value);simulate.reset()}}/><button disabled={!selected||simulate.isPending} onClick={()=>simulate.mutate()}>Simular DCP con mis cartas aptas</button><ErrorBox error={readings.error||simulate.error}/>{simulate.data&&<><p>{simulate.data.message}</p>{simulate.data.solutions.map((s,i)=><section className="panel" key={i}><h3>{simulate.data!.name} · Propuesta {i+1}</h3><p>Media local {s.rating} · Valor conocido {money(s.total_cost)} · {s.player_ids.length} copias locales</p><ul>{s.players.map(p=><li key={p.id}>{p.name} · {p.rating} · {p.position} · {p.card_type||'Variante desconocida'} · Copia local #{p.id}</li>)}</ul><p>Revisa identidad y requisitos antes de preparar manualmente una combinación. Esta simulación no autoriza ni confirma una entrega.</p></section>)}<details><summary>Exclusiones de esta simulación ({simulate.data.exclusions.length})</summary><ul>{simulate.data.exclusions.map(e=><li key={e.id}>{e.name}: {e.reason}</li>)}</ul></details></>}</>
}
