import {observedDate} from '../lib/i18n'
import {useState} from 'react'
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query'
import {api} from '../api/client'
import type {MatchHistory,PracticeSession} from '../types'
import {ErrorBox} from './ui'

export function MatchDiary(){
 const qc=useQueryClient(),[tactic,setTactic]=useState(''),[change,setChange]=useState(''),[minutes,setMinutes]=useState(90),[chances,setChances]=useState(0),[losses,setLosses]=useState(0),[conceded,setConceded]=useState(0),[practice,setPractice]=useState(''),[groupA,setGroupA]=useState(''),[groupB,setGroupB]=useState('')
 const query=useQuery({queryKey:['matches'],queryFn:()=>api<MatchHistory>('/matches')})
 const sessions=useQuery({queryKey:['practice-sessions'],queryFn:()=>api<PracticeSession[]>('/practice/sessions')})
 const save=useMutation({mutationFn:()=>api('/matches',{method:'POST',body:JSON.stringify({played_at:new Date().toISOString(),tactic,minutes,chances,dangerous_losses:losses,conceded,change_tested:change,practice_id:practice?Number(practice):null})}),onSuccess:()=>{void qc.invalidateQueries({queryKey:['matches']});setChange('')}})
 const groups=query.data?.groups||[]
 const groupKey=(g:MatchHistory['groups'][number])=>JSON.stringify([g.tactic,g.change_tested])
 const selected=[groupA,groupB].map(id=>groups.find(g=>groupKey(g)===id))
 return <details className="panel"><summary>Diario de partidos y práctica</summary><p>{query.data?.message}</p>
  <fieldset disabled={save.isPending} className="form-grid"><label>Táctica utilizada<input maxLength={120} value={tactic} onChange={e=>setTactic(e.target.value)}/></label><label>Cambio probado<input maxLength={300} value={change} onChange={e=>setChange(e.target.value)}/></label><label>Práctica relacionada<select value={practice} onChange={e=>setPractice(e.target.value)}><option value="">Sin vínculo</option>{sessions.data?.filter(s=>s.status==='completed').map(s=><option key={s.id} value={s.id}>#{s.id} · {s.agenda.title}</option>)}</select></label>
  {([{label:'Minutos jugados',value:minutes,set:setMinutes,min:1,max:240},{label:'Ocasiones creadas',value:chances,set:setChances,min:0,max:100},{label:'Pérdidas peligrosas',value:losses,set:setLosses,min:0,max:100},{label:'Goles concedidos',value:conceded,set:setConceded,min:0,max:100}]).map(f=><label key={f.label}>{f.label}<input type="number" min={f.min} max={f.max} value={f.value} onChange={e=>f.set(Number(e.target.value))}/></label>)}
  <button disabled={!tactic.trim()||!change.trim()} onClick={()=>save.mutate()}>Guardar partido observado</button></fieldset><ErrorBox error={save.error||query.error||sessions.error}/>
  <p>Muestra {query.data?.game_version}: {query.data?.sample_size||0} partidos{query.data?.truncated?' (limitada a los últimos 100)':''}.</p>
  <div className="form-grid">{[{label:'Muestra A',value:groupA,set:setGroupA},{label:'Muestra B',value:groupB,set:setGroupB}].map(f=><label key={f.label}>{f.label}<select value={f.value} onChange={e=>f.set(e.target.value)}><option value="">Seleccionar</option>{groups.map(g=><option key={groupKey(g)} value={groupKey(g)}>{g.tactic} · {g.change_tested}</option>)}</select></label>)}</div>
  {selected.map((g,i)=>g&&<p key={i}>{i?'B':'A'}: {g.sample_size} partidos, {g.minutes} minutos. Por 90 min: {g.per_90.chances} ocasiones; {g.per_90.dangerous_losses} pérdidas; {g.per_90.conceded} goles concedidos.</p>)}
  {query.data?.items.map(m=><p key={m.id}>{observedDate(m.played_at)} · {m.tactic} · {m.minutes} min · {m.chances} ocasiones · {m.dangerous_losses} pérdidas · {m.conceded} goles concedidos. Cambio: {m.change_tested}{m.practice_id?' · práctica #'+m.practice_id:''}</p>)}
 </details>
}
