import {useState} from 'react'
import {useMutation,useQueryClient} from '@tanstack/react-query'
import {api} from '../api/client'
import {invalidateClub} from '../lib/query'
import type {Squad,TacticNotes} from '../types'
import {ErrorBox,Notice} from './ui'

export function TacticEditor({squad}:{squad:Squad}){
  const qc=useQueryClient()
  const [notes,setNotes]=useState<TacticNotes>({style:'balanced',opponent:'',instructions:'',practice_focus:'',reference_ids:[],...squad.tactic})
  const [references,setReferences]=useState(notes.reference_ids.join(', '))
  const save=useMutation({mutationFn:()=>api(`/squads/${squad.id}/tactics`,{method:'PATCH',body:JSON.stringify({...notes,reference_ids:references.split(',').map(r=>r.trim().toUpperCase()).filter(Boolean)})}),onSuccess:()=>invalidateClub(qc)})
  return <details><summary>Táctica y alternativa por rival</summary><p>Hipótesis local para ensayar. Las referencias no certifican una táctica oficial.</p>
    <fieldset disabled={save.isPending} className="form-grid">
      <label>Enfoque de la táctica<select value={notes.style} onChange={e=>setNotes({...notes,style:e.target.value})}><option value="balanced">Equilibrado</option><option value="defensive">Defensivo</option><option value="wide">Bandas</option><option value="possession">Combinación interior</option><option value="attacking">Ataque</option></select></label>
      <label>Rival o situación<input maxLength={120} value={notes.opponent} onChange={e=>setNotes({...notes,opponent:e.target.value})}/></label>
      <label>Ajuste que voy a probar<textarea maxLength={2000} value={notes.instructions} onChange={e=>setNotes({...notes,instructions:e.target.value})}/></label>
      <label>Ejercicio y métrica<textarea maxLength={500} value={notes.practice_focus} onChange={e=>setNotes({...notes,practice_focus:e.target.value})}/></label>
      <label>Referencias revisadas (R01–R50)<input value={references} onChange={e=>setReferences(e.target.value)} placeholder="R15, R24"/></label>
      <button onClick={()=>save.mutate()}>Guardar táctica local</button>
    </fieldset><ErrorBox error={save.error}/>{save.isSuccess&&<Notice>Táctica guardada.</Notice>}
  </details>
}
