import {useState} from 'react'
import {useMutation,useQuery} from '@tanstack/react-query'
import {api} from '../api/client'
import {ErrorBox} from './ui'
// getRandomValues also works on the internal HTTP origin used by Docker tests.
function newMatchId(){
 const bytes=crypto.getRandomValues(new Uint8Array(16));bytes[6]=(bytes[6]&15)|64;bytes[8]=(bytes[8]&63)|128
 const hex=Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('')
 return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`
}
const labels:Record<string,string>={squad_battles:'Squad Battles',rivals:'Rivals',champions:'Champions',friendlies:'Amistosos',rush:'Rush',not_required:'Sin requisito',beginner:'Principiante',amateur:'Aficionado',semi_pro:'Semiprofesional',professional:'Profesional',world_class:'Clase mundial',legendary:'Leyenda',ultimate:'Ultimate'}
type Task={objective_id:number;action_id:string;count:number}
type Match={match_ref:string;revision:number;played_at:string;mode:string;difficulty:string;tasks:Task[];note:string}
type Goal={id:number;name:string;rules?:{actions:{id:string;kind:string;source_text:string}[]}}
export function ObjectiveJournal(){
 const [ref,setRef]=useState<string>(newMatchId),[revision,setRevision]=useState(0),[when,setWhen]=useState(()=>new Date().toISOString()),[mode,setMode]=useState('squad_battles'),[difficulty,setDifficulty]=useState('professional'),[note,setNote]=useState(''),[tasks,setTasks]=useState<Task[]>([])
 const goals=useQuery({queryKey:['journal-goals'],queryFn:()=>api<{items:Goal[]}>('/objective-planning')})
 const journal=useQuery({queryKey:['objective-journal'],queryFn:()=>api<{items:Match[]}>('/objective-journal')})
 const save=useMutation({mutationFn:()=>api<Match>(`/objective-journal/${ref}`,{method:'PUT',body:JSON.stringify({game_version:'FC27',expected_revision:revision,played_at:when,mode,difficulty,tasks,note,source:'user_declared'})}),onSuccess:r=>{setRevision(r.revision);void journal.refetch()}})
 const select=(match?:Match)=>{setRef(match?.match_ref||newMatchId());setRevision(match?.revision||0);setWhen(match?.played_at||new Date().toISOString());setTasks(match?.tasks.map(({objective_id,action_id,count})=>({objective_id,action_id,count}))||[]);setNote(match?.note||'');if(match){setMode(match.mode);setDifficulty(match.difficulty)}save.reset()}
 return <details className="panel"><summary>Tareas de objetivos por partido</summary><p>Diario declarado: guardar o corregir una partida no certifica ni aumenta el progreso de EA.</p><button onClick={()=>select()}>Nueva partida</button><label>Partida para corregir<select value={revision?ref:''} onChange={e=>select(journal.data?.items.find(m=>m.match_ref===e.target.value))}><option value="">Partida nueva</option>{journal.data?.items.map(m=><option key={m.match_ref} value={m.match_ref}>{new Date(m.played_at).toLocaleString('es-CO')} · {m.note}</option>)}</select></label>
 <label>Modalidad del partido<select value={mode} onChange={e=>setMode(e.target.value)}>{['squad_battles','rivals','champions','friendlies','rush'].map(v=><option key={v} value={v}>{labels[v]}</option>)}</select></label><label>Dificultad del partido<select value={difficulty} onChange={e=>setDifficulty(e.target.value)}>{['not_required','beginner','amateur','semi_pro','professional','world_class','legendary','ultimate'].map(v=><option key={v} value={v}>{labels[v]}</option>)}</select></label>
 {goals.data?.items.flatMap(g=>(g.rules?.actions||[]).map(a=>{const current=tasks.find(t=>t.objective_id===g.id&&t.action_id===a.id);return <label key={`${g.id}-${a.id}`}>{g.name}: {a.source_text}<input type="number" min={0} max={100} value={current?.count??''} placeholder="No registrado" onChange={e=>setTasks([...tasks.filter(t=>t!==current),...(e.target.value===''?[]:[{objective_id:g.id,action_id:a.id,count:Number(e.target.value)}])])}/></label>}))}
 <label>Nota y condiciones revisadas<textarea value={note} onChange={e=>setNote(e.target.value)} maxLength={500}/></label><button disabled={!tasks.length||note.length<5||save.isPending} onClick={()=>save.mutate()}>{revision?'Guardar corrección de esta partida':'Guardar partida declarada'}</button>{save.isSuccess&&<p role="status">Declaración guardada. El progreso de EA no cambió.</p>}<ErrorBox error={goals.error||journal.error||save.error}/></details>
}
