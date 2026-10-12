import {useState} from 'react'
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query'
import {api} from '../api/client'
import type {PracticeCatalog,PracticeSession} from '../types'
import {ErrorBox,Notice} from './ui'

function PracticeCard({session}:{session:PracticeSession}){
 const qc=useQueryClient(),[attempts,setAttempts]=useState(10),[successes,setSuccesses]=useState(0),[minutes,setMinutes]=useState(session.agenda.minutes),[change,setChange]=useState('')
 const save=useMutation({mutationFn:(status:string)=>api(`/practice/sessions/${session.id}/result`,{method:'POST',body:JSON.stringify({status,attempts,successes,minutes,next_change:change})}),onSuccess:()=>qc.invalidateQueries({queryKey:['practice-sessions']})})
 return <article className="profile-result"><h4>{session.agenda.title} · {session.agenda.minutes} min · {session.agenda.platform}</h4>
  <p>{session.agenda.control?`Control documentado: ${session.agenda.control}. Confirma tu configuración.`:'Control pendiente de revisar en el juego para esta técnica y plataforma.'}</p>
  <ol>{session.agenda.steps.map((s,i)=><li key={i}>{s.minutes} min: {s.task}</li>)}</ol><p>Métrica: {session.agenda.metric}</p>
  {session.agenda.reference_ids.map(id=><p key={id}><a href={session.agenda.sources[id].url} target="_blank" rel="noreferrer">{id} · {session.agenda.sources[id].title}</a> · publicada {session.agenda.sources[id].published_on}</p>)}
  {session.status==='planned'?<fieldset disabled={save.isPending} className="form-grid"><label>Intentos<input type="number" min={1} max={1000} value={attempts} onChange={e=>setAttempts(Number(e.target.value))}/></label><label>Aciertos<input type="number" min={0} max={attempts} value={successes} onChange={e=>setSuccesses(Number(e.target.value))}/></label><label>Minutos practicados<input type="number" min={1} max={240} value={minutes} onChange={e=>setMinutes(Number(e.target.value))}/></label><label>Único ajuste siguiente<input maxLength={300} value={change} onChange={e=>setChange(e.target.value)}/></label><button disabled={!change.trim()||successes>attempts||attempts<1||minutes<1} onClick={()=>save.mutate('completed')}>Registrar práctica completada</button><button onClick={()=>save.mutate('cancelled')}>Cancelar práctica</button></fieldset>:<Notice>{session.status==='completed'?`Práctica completada: ${session.result.successes}/${session.result.attempts} aciertos en ${session.result.minutes} min. Próximo ajuste: ${session.result.next_change}`:'Práctica cancelada.'}</Notice>}
  <ErrorBox error={save.error}/>
 </article>
}

export function PracticeAgenda(){
 const qc=useQueryClient(),[focus,setFocus]=useState('defending'),[minutes,setMinutes]=useState(15),[platform,setPlatform]=useState('PlayStation')
 const catalog=useQuery({queryKey:['practice-catalog'],queryFn:()=>api<PracticeCatalog>('/practice/catalog')})
 const sessions=useQuery({queryKey:['practice-sessions'],queryFn:()=>api<PracticeSession[]>('/practice/sessions')})
 const create=useMutation({mutationFn:()=>api('/practice/sessions',{method:'POST',body:JSON.stringify({focus,minutes,platform})}),onSuccess:()=>qc.invalidateQueries({queryKey:['practice-sessions']})})
 const drill=catalog.data?.drills[focus]
 return <details className="panel"><summary>Rutina de práctica FC27</summary><p>{catalog.data?.notice}</p>{catalog.data?.review_due&&<Notice>Revisión documental vencida; contrasta la fuente con tu parche antes de practicar.</Notice>}
  <fieldset disabled={create.isPending||!drill} className="form-grid"><label>Técnica<select value={focus} onChange={e=>setFocus(e.target.value)}>{Object.entries(catalog.data?.drills||{}).map(([id,d])=><option key={id} value={id}>{d.title}</option>)}</select></label><label>Tiempo disponible (min)<input type="number" min={5} max={90} value={minutes} onChange={e=>setMinutes(Number(e.target.value))}/></label><label>Plataforma de práctica<select value={platform} onChange={e=>setPlatform(e.target.value)}>{['PlayStation','Xbox','PC','Switch'].map(p=><option key={p}>{p}</option>)}</select></label><button disabled={minutes<5||minutes>90} onClick={()=>create.mutate()}>Guardar rutina local</button></fieldset>
  {drill&&<p>{drill.principle} Error que observar: {drill.error}</p>}<ErrorBox error={catalog.error||sessions.error||create.error}/>
  {sessions.data?.map(s=><PracticeCard key={s.id} session={s}/>)}
 </details>
}
