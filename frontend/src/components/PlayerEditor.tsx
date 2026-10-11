import {useState} from 'react'
import type {AttributeKey,PlayerInput} from '../types'
import {attributeLabels,emptyPlayer,playerSchema,positions,splitValues,type PlayerDraft} from '../lib/players'
import {useSeason} from '../lib/season'
import {ErrorBox} from './ui'

export function PlayerEditor({initial,onSave,onCancel,pending=false,error,buttonLabel='Guardar jugador'}:{initial?:Partial<PlayerDraft>;onSave:(player:PlayerInput)=>void;onCancel:()=>void;pending?:boolean;error?:unknown;buttonLabel?:string}){
  const season=useSeason()
  const [draft,setDraft]=useState<PlayerDraft>(()=>({...emptyPlayer(season),...initial,game_version:season}))
  const [alternates,setAlternates]=useState((initial?.alternate_positions||[]).join(', '))
  const [styles,setStyles]=useState((initial?.playstyles||[]).join(', '))
  const [plus,setPlus]=useState((initial?.playstyles_plus||[]).join(', '))
  const [roles,setRoles]=useState(Object.entries(initial?.roles||{}).map(([key,value])=>`${key}: ${value}`).join('\n'))
  const [validation,setValidation]=useState<string[]>([])
  const update=<K extends keyof PlayerDraft>(key:K,value:PlayerDraft[K])=>setDraft(previous=>({...previous,[key]:value}))
  const submit=()=>{
    const rolePairs=roles.split('\n').map(value=>value.trim()).filter(Boolean)
    if(rolePairs.some(value=>!value.includes(':')||!value.split(':')[0].trim()||!value.split(':').slice(1).join(':').trim())){setValidation(['Escribe cada rol como posición: rol, uno por línea.']);return}
    const result=playerSchema.safeParse({...draft,alternate_positions:splitValues(alternates).map(value=>value.toUpperCase()),playstyles:splitValues(styles),playstyles_plus:splitValues(plus),roles:Object.fromEntries(rolePairs.map(value=>{const index=value.indexOf(':');return [value.slice(0,index).trim(),value.slice(index+1).trim()]}))})
    if(!result.success){setValidation(result.error.issues.map(issue=>`${issue.path.join(' · ')}: ${issue.message}`));return}
    if(!result.data.data_reviewed){setValidation(['Confirma que revisaste los datos de esta carta antes de guardarla.']);return}
    setValidation([]);onSave(result.data as PlayerInput)
  }
  return <form className="panel editor" onSubmit={event=>{event.preventDefault();submit()}}>
    <div className="split"><div><span className="eyebrow">FICHA {season}</span><h3>{initial?.name?'Revisar carta':'Añadir jugador'}</h3></div><button type="button" onClick={onCancel} disabled={pending}>Cerrar</button></div>
    <fieldset disabled={pending} className="form-grid">
      <label className="wide">Nombre<input required maxLength={100} value={draft.name} onChange={e=>update('name',e.target.value)}/></label>
      <label>Media<input required type="number" min={1} max={99} value={draft.rating} onChange={e=>update('rating',e.target.value===''?'':Number(e.target.value))}/></label>
      <label>Posición principal<select required value={draft.position} onChange={e=>update('position',e.target.value)}><option value="">Seleccionar</option>{positions.map(value=><option key={value}>{value}</option>)}</select></label>
      {(['league','club','nationality'] as const).map((key,index)=><label key={key}>{['Liga','Club','Nacionalidad'][index]}<input required maxLength={80} value={draft[key]} onChange={e=>update(key,e.target.value)}/></label>)}
      <label>Versión de carta<input required maxLength={40} value={draft.card_type} onChange={e=>update('card_type',e.target.value)} list="card-types"/><datalist id="card-types">{(season==='FC27'?['Bronce','Plata','Oro','Especial','Evolución']:['Oro común','Oro raro','Especial','Evolución']).map(value=><option key={value}>{value}</option>)}</datalist></label>
      <label>Precio registrado (monedas)<input type="number" min={0} max={100000000} value={draft.price??''} onChange={e=>update('price',e.target.value===''?null:Number(e.target.value))}/><small>Vacío significa desconocido; cero solo si el coste fue cero.</small></label>
      <label>Química registrada (0–3)<input type="number" min={0} max={3} value={draft.chemistry} onChange={e=>update('chemistry',Number(e.target.value))}/></label>
      <label>Utilidad personal (0–100)<input type="number" min={0} max={100} value={draft.usefulness} onChange={e=>update('usefulness',Number(e.target.value))}/></label>
      <label>Puntos de Galería observados<input type="number" min={0} max={1000000} step={1} value={draft.gallery_score??''} onChange={e=>update('gallery_score',e.target.value===''?null:Number(e.target.value))}/><small>Déjalo vacío si no lo has verificado en el juego.</small></label>
      {(['tradable','is_loan','is_evolution'] as const).some(key=>draft[key]===null)&&<p className="wide">Hay indicadores desconocidos. Marca o desmarca explícitamente Transferible, Cesión y Evolucionado antes de guardar; un dato omitido no significa que sea falso.</p>}
      <div className="check-row wide">{([['rare','Raro (FC 26)'],['special','Especial'],['tradable','Transferible'],['duplicate_untradeable','Duplicado'],['protected','Proteger'],['starter','Titular'],['favorite','Favorito'],['is_loan','Cesión'],['is_evolution','Evolucionado'],['is_holographic','Holográfico']] as const).filter(([key])=>key!=='rare'||season==='FC26').map(([key,label])=><label key={key}><input type="checkbox" checked={draft[key]===true} onChange={e=>update(key,e.target.checked)}/>{label}</label>)}</div>
    </fieldset>
    <details className="editor-more"><summary>Atributos, posiciones y PlayStyles</summary><fieldset disabled={pending} className="form-grid">
      <label className="wide">Posiciones alternativas<input value={alternates} onChange={e=>setAlternates(e.target.value)} placeholder="MC, MCO"/><small>Solo posiciones que aparecen en esta carta.</small></label>
      {(Object.entries(attributeLabels) as [AttributeKey,string][]).map(([key,label])=><label key={key}>{label}<input type="number" min={1} max={99} value={draft.attributes[key]??''} onChange={e=>{const next={...draft.attributes};if(e.target.value==='')delete next[key];else next[key]=Number(e.target.value);update('attributes',next)}}/></label>)}
      <label className="wide">PlayStyles<input value={styles} onChange={e=>setStyles(e.target.value)} placeholder="Separados por coma"/></label><label className="wide">PlayStyles+<input value={plus} onChange={e=>setPlus(e.target.value)} placeholder="Separados por coma"/></label>
      <label>Filigranas (1–5)<input type="number" min={1} max={5} value={draft.skill_moves??''} onChange={e=>update('skill_moves',e.target.value===''?null:Number(e.target.value))}/></label><label>Pierna mala (1–5)<input type="number" min={1} max={5} value={draft.weak_foot??''} onChange={e=>update('weak_foot',e.target.value===''?null:Number(e.target.value))}/></label>
      <label className="wide">Roles por posición<textarea value={roles} onChange={e=>setRoles(e.target.value)} placeholder={'MC: Organizador\nMCD: Contención'}/></label>
    </fieldset></details>
    <details className="editor-more"><summary>Identificación y procedencia</summary><fieldset disabled={pending} className="form-grid"><label>ID de esta carta<input value={draft.card_id??''} onChange={e=>update('card_id',e.target.value.trim()||null)}/></label><label>ID de carta base<input value={draft.base_card_id??''} onChange={e=>update('base_card_id',e.target.value.trim()||null)}/><small>Permite vincular una evolución a su carta base.</small></label><label className="wide">Fuente de los datos<input required value={draft.data_source} onChange={e=>update('data_source',e.target.value)}/></label></fieldset></details>
    <label className="check review-check"><input type="checkbox" checked={draft.data_reviewed} disabled={pending} onChange={e=>update('data_reviewed',e.target.checked)}/>He contrastado estos datos con mi carta.</label>
    {validation.length>0&&<div className="error-box" role="alert"><ul>{validation.map((value,index)=><li key={index}>{value}</li>)}</ul></div>}<ErrorBox error={error}/>
    <div className="button-row"><button className="primary" disabled={pending}>{pending?'Guardando…':buttonLabel}</button><button type="button" disabled={pending} onClick={onCancel}>Cancelar</button></div>
  </form>
}
