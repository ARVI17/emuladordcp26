import {useState} from 'react'
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query'
import {api} from '../api/client'
import {invalidateClub} from '../lib/query'
import type {Squad} from '../types'
import {ErrorBox,Notice} from './ui'

export type MainSquadStatus={identified:boolean;complete:boolean;squad_id:number|null;state_hash:string;revision:number;reason:string|null;protected_copy_ids:number[];retained_copy_ids:number[];snapshot:{name:string;formation:string;members:{player_id:number;slot:string}[]}|null}
export function MainSquadProtection({squads}:{squads:Squad[]}){
 const qc=useQueryClient(),[selected,setSelected]=useState(''),[complete,setComplete]=useState(false),[phrase,setPhrase]=useState('')
 const main=useQuery({queryKey:['main-squad'],queryFn:()=>api<MainSquadStatus>('/squads/main')})
 const save=useMutation({mutationFn:()=>api(`/squads/${selected}/main`,{method:'POST',body:JSON.stringify({phrase,complete,expected_state_hash:main.data!.state_hash})}),onSuccess:()=>{setPhrase('');setComplete(false);void invalidateClub(qc)}})
 const chosen=squads.find(s=>s.id===Number(selected)),expected=`PROTEGER PRINCIPAL ${selected}`
 return <section className="panel" aria-label="Protección de la principal"><h3>Mi plantilla principal</h3>
  <p>{main.data?.snapshot?`${main.data.snapshot.name} · ${main.data.snapshot.formation} · ${main.data.protected_copy_ids.length} copias protegidas`:'Principal sin identificar'}</p>
  {main.data?.reason&&<Notice>{main.data.reason}</Notice>}
  <p>Once, banquillo y reservas quedan fuera de DCP, ventas y archivo. Puedes usarlos para proponer otros equipos para jugar. Esta elección no activa una plantilla en EA.</p>
  <details><summary>{main.data?.identified?'Revisar cambio de principal':'Identificar y proteger la principal'}</summary>
   <label>Plantilla principal elegida<select value={selected} onChange={e=>{setSelected(e.target.value);setComplete(false);setPhrase('')}}><option value="">Selecciona una plantilla guardada</option>{squads.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></label>
   {chosen&&<><p>{chosen.formation} · {chosen.players.length} copias: {chosen.players.map(m=>`${m.slot.startsWith('BENCH-')?'Suplente':m.slot.startsWith('RESERVE-')?'Reserva':m.player.position} ${m.player.name}`).join(' · ')}</p><label className="check-label"><input type="checkbox" checked={complete} onChange={e=>setComplete(e.target.checked)}/>He revisado el once y he incluido todo su banquillo y reservas.</label>
    <p>Al cambiar de principal se conservan las protecciones anteriores y las individuales.</p><label>Escribe {expected}<input value={phrase} onChange={e=>setPhrase(e.target.value)} autoComplete="off"/></label>
    <button className="primary" disabled={!main.data||!complete||phrase!==expected||save.isPending} onClick={()=>save.mutate()}>Proteger esta principal</button></>}
  </details><ErrorBox error={main.error||save.error}/>
 </section>
}
