import {MainComparison} from './MainComparison'
import {statusLabel} from '../lib/i18n'
import {useState} from 'react'
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query'
import {api} from '../api/client'
import {invalidateClub} from '../lib/query'
import {squadRequest} from '../lib/squads'
import type {Challenge,Player,SquadBinding,SquadRecommendation} from '../types'
import {PlayerPicker} from './PlayerPicker'
import {ErrorBox,Notice} from './ui'

type Group={profiles:string[];squad:SquadRecommendation;why:string;practice:string;vulnerability:string;bench_missing:number;data_quality:{cards_with_attributes:number;cards:number}}
type Profiles={binding:SquadBinding;groups:Group[];pending_profiles:{profile:string;reason:string}[]}

function ProfileResult({group:g,binding}:{group:Group;binding:SquadBinding}){
  const qc=useQueryClient(),[name,setName]=useState(g.profiles.join(' / ').slice(0,100))
  const save=useMutation({mutationFn:()=>api('/squads',{method:'POST',body:JSON.stringify(squadRequest(name,g.squad,binding,
    {style:g.squad.style,opponent:'',instructions:'Probar este enfoque como hipótesis local.',practice_focus:g.practice,reference_ids:['R24']}))}),onSuccess:()=>invalidateClub(qc)})
  return <article className="profile-result"><h4>{g.profiles.join(' / ')} · {g.squad.formation}</h4>
    <p>{g.why}</p><p>Once: {g.squad.lineup.map(r=>`${r.position}: ${r.player.name}`).join(' · ')}</p>
    <p>Suplentes ({g.squad.bench.length}/7): {g.squad.bench.map(p=>p.name).join(', ')||'Sin suplentes elegibles'}</p>
    <p>Huecos: {g.squad.gaps.map(r=>r.position).join(', ')||'Ninguno en esta simulación'}. Suplentes pendientes: {g.bench_missing}.</p>
    <p>Compras adicionales: 0 monedas. Química oficial: desconocida. Atributos registrados en {g.data_quality.cards_with_attributes}/{g.data_quality.cards} cartas.</p>
    <MainComparison value={g.squad.main_comparison}/><small>{g.practice} {g.vulnerability}</small>
    <label>Nombre del equipo propuesto<input value={name} maxLength={100} onChange={e=>setName(e.target.value)}/></label>
    <button disabled={save.isPending||save.isSuccess||!g.squad.complete||g.bench_missing>0||!name.trim()} onClick={()=>save.mutate()}>Guardar once y siete suplentes</button>
    <ErrorBox error={save.error}/>{save.isSuccess&&<Notice>Equipo guardado; puedes ajustar su táctica en Plantillas.</Notice>}
  </article>
}

export function PlanningAnalysis(){
  const [avoidMain,setAvoidMain]=useState(false),[disjoint,setDisjoint]=useState(false),[locked,setLocked]=useState<Player[]>([]),[excluded,setExcluded]=useState<Player[]>([]),[loans,setLoans]=useState(true)
  const [players,setPlayers]=useState<Player[]>([]),[segments,setSegments]=useState<number[]>([])
  const profiles=useMutation({mutationFn:()=>api<Profiles>('/club/profiles',{method:'POST',body:JSON.stringify({disjoint,avoid_main:avoidMain,bench_size:7,locked_player_ids:locked.map(p=>p.id),excluded_player_ids:excluded.map(p=>p.id),include_loans:loans})})})
  const challenges=useQuery({queryKey:['challenges','joint'],queryFn:()=>api<Challenge[]>('/challenges')})
  const joint=useMutation({mutationFn:()=>api<{status:string;reason?:string;solutions:{segment_id:number;player_ids:number[]}[]}>('/dcp/joint-preview',{method:'POST',body:JSON.stringify({segment_ids:segments,player_ids:players.map(p=>p.id)})})})
  const invalid=locked.length>11||locked.some(p=>excluded.some(e=>e.id===p.id))||(disjoint&&locked.length>0)
  return <><section className="panel"><h3>Comparar cinco objetivos de plantilla</h3>
    <p>Equilibrio, defensa, ataque por bandas, combinación interior y mejor once sin compras. Los perfiles que coinciden se agrupan.</p>
    <fieldset disabled={profiles.isPending}><label className="check"><input type="checkbox" checked={avoidMain} onChange={e=>{setAvoidMain(e.target.checked);profiles.reset()}}/>No reutilizar mi principal</label>
      <PlayerPicker label="Fijados en los cinco perfiles" selected={locked} onChange={v=>{setLocked(v);profiles.reset()}}/>
      <PlayerPicker label="Excluir de los cinco perfiles" selected={excluded} onChange={v=>{setExcluded(v);profiles.reset()}}/>
      <label className="check"><input type="checkbox" checked={loans} onChange={e=>{setLoans(e.target.checked);profiles.reset()}}/>Incluir cesiones para jugar</label>
      <label className="check"><input type="checkbox" checked={disjoint} onChange={e=>{setDisjoint(e.target.checked);profiles.reset()}}/>Equipos disjuntos (sin compartir cartas ni fijados comunes)</label>
      {invalid&&<Notice>Revisa fijados y excluidos: máximo once, sin coincidencias. Los fijados comunes solo sirven para alternativas.</Notice>}
      <button disabled={invalid} onClick={()=>profiles.mutate()}>Comparar perfiles</button>
    </fieldset><ErrorBox error={profiles.error}/>
    {profiles.data?.pending_profiles.map(p=><p className="alert warning" key={p.profile}>{p.profile}: {p.reason}</p>)}
    {profiles.data?.groups.map((g,i)=><ProfileResult key={`${profiles.submittedAt}-${i}`} group={g} binding={profiles.data!.binding}/>)}
  </section>
  <section className="panel"><h3>Planificar varios DCP juntos</h3>
    <Notice>Búsqueda acotada a 24 copias y 6 segmentos. Solo propone completar todos; no inicia entregas parciales inviables.</Notice>
    <PlayerPicker label="Cartas disponibles para comparar" selected={players} onChange={setPlayers}/>
    {challenges.data?.flatMap(c=>c.segments.filter(s=>!s.completed).map(s=><label className="check" key={s.id}><input type="checkbox" checked={segments.includes(s.id)} onChange={e=>setSegments(e.target.checked?[...segments,s.id]:segments.filter(id=>id!==s.id))}/>{c.name} · {s.name}</label>))}
    <button disabled={joint.isPending||players.length>24||!players.length||!segments.length||segments.length>6} onClick={()=>joint.mutate()}>Simular conjunto sin consumir</button>
    <ErrorBox error={joint.error}/>{joint.data&&<><p>Resultado: {statusLabel(joint.data.status)} {joint.data.reason}</p>{joint.data.solutions.map(s=><p key={s.segment_id}>Segmento {s.segment_id}: {s.player_ids.map(id=>players.find(p=>p.id===id)?.name).join(', ')}</p>)}</>}
  </section></>
}
