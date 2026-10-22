import {useState} from 'react'
import {useMutation} from '@tanstack/react-query'
import {api} from '../api/client'
import {ErrorBox} from './ui'
type Tier={minimum:string;percent:string}
type Tag={name:string;field:string;value:string;aggregation:string;tiers:Tier[]}
const fields:Record<string,string>={card_type:'Tipo de carta',first_owner:'Primer propietario',is_holographic:'Holográfica',holographic_level:'Nivel holográfico',nationality:'Nacionalidad',league:'Liga',club:'Club',position:'Posición',weak_foot:'Pie débil',skill_moves:'Filigranas'}
export function GalleryScenarioEditor({onSaved}:{onSaved:()=>void}){
 const [name,setName]=useState(''),[size,setSize]=useState(''),[multiplicity,setMultiplicity]=useState('variant'),[source,setSource]=useState(''),[rewardMode,setRewardMode]=useState('cumulative')
 const [grades,setGrades]=useState<{name:string;score:string;reward:string}[]>([]),[tags,setTags]=useState<Tag[]>([]),[reviewed,setReviewed]=useState(false)
 const tag=(index:number,value:Partial<Tag>)=>setTags(tags.map((t,i)=>i===index?{...t,...value}:t))
 const save=useMutation({mutationFn:()=>{
  if(new Set(grades.map(g=>g.name)).size!==grades.length)throw Error('No repitas nombres de grados.')
  if(!name.trim()||!size||!reviewed||grades.some(g=>!g.name||!g.score||!g.reward)||tags.some(t=>!t.name||(t.aggregation==='matched'&&!t.value)||!t.tiers.length||t.tiers.some(v=>!v.minimum||!v.percent)))throw Error('Completa y revisa los valores de tu fuente. Cero debe escribirse explícitamente; vacío significa desconocido.')
  return api('/gallery/sets',{method:'POST',body:JSON.stringify({name,description:source,rules_reviewed:true,
   rules:{schema_version:2,size:Number(size),multiplicity,evidence_status:'scenario',rewards:Object.fromEntries(grades.map(g=>[g.name,Number(g.reward)])),reward_mode:rewardMode},
   grade_thresholds:Object.fromEntries(grades.map(g=>[g.name,Number(g.score)])),tags:tags.map(t=>({name:t.name,field:t.field,aggregation:t.aggregation,mode:'percentage',minimum:Number(t.tiers[0].minimum),tiers:t.tiers.map(v=>({minimum:Number(v.minimum),percent_basis_points:Math.round(Number(v.percent)*100)})),value:t.aggregation!=='matched'?null:['first_owner','is_holographic'].includes(t.field)?t.value==='true':['holographic_level','weak_foot','skill_moves'].includes(t.field)?Number(t.value):t.value}))})})
 },onSuccess:onSaved})
 return <div className="panel"><label>Nombre del escenario<input value={name} maxLength={120} onChange={e=>setName(e.target.value)}/></label>
 <label>Fuente y observaciones<textarea value={source} maxLength={5000} onChange={e=>setSource(e.target.value)}/></label>
 <label>Cartas exigidas<input type="number" min={1} max={100} value={size} onChange={e=>setSize(e.target.value)}/></label>
 <label>Restricción de repeticiones<select value={multiplicity} onChange={e=>setMultiplicity(e.target.value)}><option value="variant">Una entrada por variante</option><option value="athlete">Una entrada por futbolista identificado</option><option value="entry">Cada entrada histórica por separado</option></select></label>
 <label>Interpretación de premios<select value={rewardMode} onChange={e=>setRewardMode(e.target.value)}><option value="cumulative">Total acumulado hasta cada grado</option><option value="incremental">Premio adicional de cada grado</option></select></label>
 <p>Introduce las cifras de tu fuente. Guardarlas aquí crea un escenario local revisado.</p>
 {grades.map((g,i)=><fieldset key={i}><legend>Grado {i+1}</legend>{(['name','score','reward'] as const).map((key,j)=><label key={key}>{['Nombre del grado','Puntos mínimos del grado','Fichas del grado'][j]}<input type={key==='name'?'text':'number'} min={0} value={g[key]} onChange={e=>setGrades(grades.map((v,n)=>n===i?{...v,[key]:e.target.value}:v))}/></label>)}<button onClick={()=>setGrades(grades.filter((_,n)=>n!==i))}>Quitar grado {i+1}</button></fieldset>)}
 <button disabled={grades.length>=20} onClick={()=>setGrades([...grades,{name:'',score:'',reward:''}])}>Añadir grado y premio</button>
 {tags.map((t,i)=><fieldset key={i}><legend>Bonificación {i+1}</legend>
 <label>Nombre de bonificación<input value={t.name} onChange={e=>tag(i,{name:e.target.value})}/></label>
 <label>Atributo de bonificación<select value={t.field} onChange={e=>tag(i,{field:e.target.value,value:'',aggregation:'matched'})}>{Object.entries(fields).map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></label>
 <label>Cómputo de la bonificación<select value={t.aggregation} onChange={e=>tag(i,{aggregation:e.target.value})}><option value="matched">Cartas con el valor indicado</option>{['nationality','league','club'].includes(t.field)&&<><option value="distinct">Cantidad de valores distintos</option><option value="largest_group">Mayor grupo con el mismo valor</option></>}</select></label>
 {t.aggregation==='matched'&&<label>Valor que deben cumplir{['first_owner','is_holographic'].includes(t.field)?<select value={t.value} onChange={e=>tag(i,{value:e.target.value})}><option value="">Selecciona</option><option value="true">Sí</option><option value="false">No</option></select>:<input value={t.value} onChange={e=>tag(i,{value:e.target.value})}/>}</label>}
 {t.tiers.map((v,n)=><div className="form-grid" key={n}><label>Cantidad mínima del tramo {n+1}<input type="number" min={1} value={v.minimum} onChange={e=>tag(i,{tiers:t.tiers.map((r,j)=>j===n?{...r,minimum:e.target.value}:r)})}/></label><label>Porcentaje del tramo {n+1}<input type="number" min={0} step="0.01" value={v.percent} onChange={e=>tag(i,{tiers:t.tiers.map((r,j)=>j===n?{...r,percent:e.target.value}:r)})}/></label></div>)}
 <button onClick={()=>tag(i,{tiers:[...t.tiers,{minimum:'',percent:''}]})}>Añadir tramo</button><button onClick={()=>setTags(tags.filter((_,n)=>n!==i))}>Quitar bonificación {i+1}</button>
 </fieldset>)}
 <button disabled={tags.length>=30} onClick={()=>setTags([...tags,{name:'',field:'card_type',value:'',aggregation:'matched',tiers:[{minimum:'',percent:''}]}])}>Añadir bonificación porcentual</button>
 <label className="check"><input type="checkbox" checked={reviewed} onChange={e=>setReviewed(e.target.checked)}/>Revisé las reglas, premios y multiplicidad de este escenario</label>
 <button disabled={save.isPending||!reviewed} onClick={()=>save.mutate()}>Guardar escenario revisado</button><ErrorBox error={save.error}/></div>
}
