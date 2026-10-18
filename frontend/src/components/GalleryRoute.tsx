import {useEffect,useState} from 'react'
import {useMutation,useQuery} from '@tanstack/react-query'
import {api} from '../api/client'
import {ErrorBox} from './ui'
import {GalleryRouteResult,type GalleryRouteResultData} from './GalleryRouteResult'
import {GalleryScenarioEditor} from './GalleryScenarioEditor'
import {GalleryAcquisitions,type Acquisition} from './GalleryAcquisitions'
type Breakdown={name:string;basis_score:number|null;bonus:number|null;percent_basis_points:number|null;count:number;provisional:boolean}
type Scenario={id:number;name:string;source:string;grade_thresholds:Record<string,number>;progress:{attained_grade?:string|null;claimed_grade?:string|null};evaluation:{score:number|null;grade:string|null;tags:Breakdown[];warnings:string[]}}
export function GalleryRoute(){
 const [selected,setSelected]=useState<number[]>([]),[mode,setMode]=useState('known_only'),[target,setTarget]=useState(1),[capital,setCapital]=useState(0),[loss,setLoss]=useState(0),[coins,setCoins]=useState(0),[reserve,setReserve]=useState(0)
 const [editor,setEditor]=useState(false)
 const [candidates,setCandidates]=useState<Acquisition[]>([]),[market,setMarket]=useState('Console'),[fee,setFee]=useState(''),[feeSource,setFeeSource]=useState('')
 const scenarios=useQuery({queryKey:['gallery-scenarios'],queryFn:()=>api<Scenario[]>('/gallery/local-scenarios')})

 const progress=useMutation({mutationFn:({id,attained,claimed}:{id:number;attained:string|null;claimed:string|null})=>api(`/gallery/sets/${id}/declared-progress`,{method:'PUT',body:JSON.stringify({attained_grade:attained,claimed_grade:claimed,note:'Declaración revisada desde Galería local',confirmation:'REGISTRAR GRADO DECLARADO'})}),onSuccess:()=>{route.reset();return scenarios.refetch()}})
 const route=useMutation({mutationFn:()=>api<GalleryRouteResultData>('/gallery/route-preview',{method:'POST',body:JSON.stringify({set_ids:selected,mode,market,target_tokens:mode==='token_target'?target:null,maximum_capital:capital,maximum_loss:loss,available_coins:coins,reserve_coins:reserve,candidates:mode==='known_only'?[]:candidates,fee_basis_points:fee===''?null:Number(fee),fee_source:feeSource||null,allow_scenarios:true})})})

 useEffect(()=>route.reset(),[selected,mode,target,capital,loss,coins,reserve,candidates,fee,feeSource,market,route.reset])
 return <section className="panel"><h3>Avanzar Galería · reglas versión 2</h3><p>Calcula sobre historia elegible conocida. Las reglas declaradas se conservan como escenarios y no se presentan como fórmula oficial. El grado obtenido y el premio reclamado son datos distintos.</p>
 <button onClick={()=>setEditor(!editor)}>Definir escenario revisado</button>
 {editor&&<GalleryScenarioEditor onSaved={()=>{setEditor(false);void scenarios.refetch()}}/>}
 <button onClick={()=>{route.reset();void scenarios.refetch()}}>Actualizar historia y escenarios</button>
 {scenarios.data?.map(s=><article className="panel" key={s.id}><label className="check"><input type="checkbox" checked={selected.includes(s.id)} onChange={e=>setSelected(e.target.checked?[...selected,s.id]:selected.filter(id=>id!==s.id))}/>{s.name} · {s.source==='local_scenario'?'Escenario local':'Reglas documentadas'}</label><p>Puntos: {s.evaluation.score??'Pendientes'} · grado calculado: {s.evaluation.grade??'Pendiente'}</p><ul>{s.evaluation.tags.map(t=><li key={t.name}>{t.name}: base {t.basis_score??'desconocida'} · {t.percent_basis_points==null?'puntos fijos':`${t.percent_basis_points/100}%`} · aporte {t.bonus??'pendiente'}{t.provisional?' (provisional)':''}</li>)}</ul><Progress scenario={s} save={(attained,claimed)=>progress.mutate({id:s.id,attained,claimed})}/></article>)}
 <label>Modo<select value={mode} onChange={e=>setMode(e.target.value)}><option value="known_only">Solo historia conocida, sin compras</option><option value="token_target">Objetivo de fichas adicionales</option><option value="capital">Capital y pérdida máximos</option></select></label>
 {mode==='token_target'&&<label>Fichas adicionales<input type="number" min={1} value={target} onChange={e=>setTarget(Number(e.target.value))}/></label>}
 {mode!=='known_only'&&<><div className="form-grid">{[['Monedas declaradas disponibles',coins,setCoins],['Reserva mínima',reserve,setReserve],['Capital máximo',capital,setCapital],['Pérdida tolerada',loss,setLoss]].map(([label,value,set])=><label key={String(label)}>{String(label)}<input type="number" min={0} value={value as number} onChange={e=>(set as (n:number)=>void)(Number(e.target.value))}/></label>)}</div><details><summary>Candidatas y cotizaciones revisadas</summary><label>Mercado de las candidatas<select value={market} onChange={e=>{setMarket(e.target.value);setCandidates([]);route.reset()}}>{['Console','PC','Switch','Switch2'].map(m=><option key={m}>{m}</option>)}</select></label><GalleryAcquisitions market={market} value={candidates} onChange={setCandidates}/><label>Comisión asumida, puntos básicos (100 = 1 %)<input type="number" value={fee} onChange={e=>setFee(e.target.value)}/></label><label>Fuente o hipótesis de la comisión<input value={feeSource} onChange={e=>setFeeSource(e.target.value)}/></label></details></>}
 <button disabled={!selected.length||route.isPending||progress.isPending} onClick={()=>route.mutate()}>Calcular ruta local revisable</button>
 {route.data&&<GalleryRouteResult value={route.data}/>}
 <ErrorBox error={scenarios.error||progress.error||route.error}/></section>
}
function Progress({scenario,save}:{scenario:Scenario;save:(a:string|null,c:string|null)=>void}){
 const [attained,setAttained]=useState(scenario.progress.attained_grade||''),[claimed,setClaimed]=useState(scenario.progress.claimed_grade||'')
 const grades=Object.keys(scenario.grade_thresholds)
 return <div><label>Grado obtenido declarado<select value={attained} onChange={e=>setAttained(e.target.value)}><option value="">Declaro ningún grado</option>{grades.map(g=><option key={g}>{g}</option>)}</select></label><label>Premio reclamado hasta<select value={claimed} onChange={e=>setClaimed(e.target.value)}><option value="">Declaro ninguno</option>{grades.map(g=><option key={g}>{g}</option>)}</select></label><button onClick={()=>save(attained||null,claimed||null)}>Guardar declaración de progreso</button></div>
}
