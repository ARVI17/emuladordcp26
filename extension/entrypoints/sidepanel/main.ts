import {endpoint,canonical} from '../../lib/contracts'
import {fields,normalizationFor,isRequired} from '../../lib/profile-extraction'
import './style.css'
const el=(id:string)=>document.getElementById(id)!
const input=(id:string)=>(el(id) as HTMLInputElement).value
let hydrated=false
let profiles:any[]=[]
let maps:any[]=[]
const statusLabels:Record<string,string>={draft:'Borrador',sample_tested:'Definición probada',observed_contrasted:'Contrastado manualmente en vista real',active:'Activo para lectura manual',disabled:'Desactivado'}
const viewLabels:Record<string,string>={header:'Cabecera',account:'Cuenta',inventory:'Inventario',detail:'Ficha',squad:'Plantilla',dcp:'DCP',objective:'Objetivo',gallery:'Galería',unknown:'Desconocida'}
function choices(id:string,values:{id:string;label:string}[],empty:string){
 const select=el(id) as HTMLSelectElement,current=select.value
 select.replaceChildren(new Option(empty,''),...values.map(v=>new Option(v.label,v.id)))
 if(values.some(v=>v.id===current))select.value=current
}
function profileState(){
 const p=profiles.find(p=>p.id===input('profile-choice'))
 el('profile-state').textContent=p?`${statusLabels[p.status]} · revisión ${p.revision}. El envío requiere contexto confirmado y revisión en Club Lab.`:'Selecciona un mapa para definir los campos.'
}
async function refresh(){
 const r=await chrome.runtime.sendMessage({kind:'status'})
 const workflow=r.workflow,report=workflow?.report
 el('workflow-next').textContent=workflow?.status==='paused'||workflow?.status==='cancelled'?'Recorrido detenido; historial y cola conservados.':report?.next_action||r.message||'Autoriza la pestaña desde el icono y empareja el lector una vez.'
 const stages=el('workflow-stages');stages.replaceChildren()
 for(const stage of report?.stages||[]){const li=document.createElement('li');li.textContent=stage.label+' · '+({complete:'comprobado',partial:'parcial',pending:'pendiente',blocked:'requiere una acción'} as Record<string,string>)[stage.status]+' — '+stage.evidence;stages.append(li)}
 el('workflow-coverage').textContent=report?`${report.inventory_count} cartas admitidas; ${report.pending_observations} observaciones pendientes. Cobertura parcial. Siguiente sección: ${report.next_section}. ${report.main.unchanged?'Principal local sin cambios.':'La principal local cambió.'}`:''
 const groups=report?.modules?.squads?.resultú.groups||[]
 el('workflow-results').textContent=report?[(report.source_counts?.synthetic_dom?'Incluye MUESTRAS SINTÉTICAS; no acredita EA.':'Datos locales con procedencia; sin identidad EA verificada.'),...groups.map((g:any)=>g.profiles.join(' / ')+': '+g.squad.lineup.map((p:any)=>p.slot+' '+p.player.name).join(', ')),...Object.entries(report.modules).filter(([,v]:any)=>v.status==='pending').map(([k,v]:any)=>k+': '+v.reason)].join('\n\n'):''
 el('reader-metrics').textContent=r.readerMetrics?`${r.readerMetrics.reads} vistas nuevas; ${r.readerMetrics.repeated} repeticiones evitadas; última lectura ${r.readerMetrics.last_ms} ms. OCR/IA por carta: 0.`:''
 el('extension-id').textContent=r.extensionId||''
 el('extension-version').textContent=r.version||'desconocida'
 if(!hydrated){(el('base') as HTMLInputElement).value=r.base;hydrated=true}
 el('destination').textContent=`Destino guardado: ${r.base}. Origen canónico recomendado: http://localhost:8090. 127.0.0.1 mantiene una sesión local distinta.`
 el('compatibility').textContent=r.compatibility?`${r.compatibility.origin} · ${r.compatibility.revision}\n${r.compatibility.reason}`:'Comprueba versiones antes de emparejar. El reconocimiento de estructura funciona sin backend.'
 el('diagnostic').textContent=r.maps.length?JSON.stringify(r.maps,null,2):'Todavía no hay mapas. Selecciona una región visible y pulsa Reconocer estructura.'
 const partial=r.maps.filter((m:any)=>m.map.coverage.partial||m.map.coverage.truncated).length
 el('coverage').textContent=`${r.maps.length}/8 regiones privadas; ${partial} con omisiones. ${r.maps.filter((m:any)=>m.profile.evidence_origin==='observed_page_map').length} observadas en página oficial. Un mapa no acredita un extractor. Consulta coverage.omitted en la vista previa para ver textos largos, medios y subárboles excluidos.`
 profiles=r.profiles||[]
 maps=r.maps||[]
 choices('profile-map',r.maps.map((m:any)=>({id:m.map_id,label:`${viewLabels[m.profile.view]||'Desconocida'} · ${m.observed_at}`})),'Selecciona una región')
 choices('profile-choice',profiles.map(p=>({id:p.id,label:`${viewLabels[p.definition.view]} · r${p.revision} · ${statusLabels[p.status]}`})),'Nuevo perfil')
 profileState()
 el('status').textContent=`${r.paired?'Emparejado':'Sin emparejar'} · ${r.pending||0} pendientes. ${r.message||''}`
 el('checkpoint').textContent=r.checkpoint?`Recorrido: ${r.checkpoint.reason} · observado ${r.checkpoint.observed_at||'sin lectura'}`:'Sin recorrido iniciado. Límite: 300 registros por región, 30 por fragmento, 100 fragmentos / 2 MB en cola.'
 if(r.proposal){
   const value=r.proposal
   el('proposal').textContent=[
    value.data_sources?.includes('synthetic_dom')?'Incluye muestras SINTÉTICAS; no acredita datos de EA.':'Datos declarados y revisados; sin verificación del proveedor.',
    'Propuestas sobre el subconjunto revisado; la cobertura del club es parcial.',
    ...value.proposal.groups.map((g:any)=>`${g.profiles.join(' / ')} · ${g.squad.formation}\n${g.squad.lineup.map((r:any)=>`${r.slot}: ${r.player.name} (${r.player.rating})`).join('\n')}\n${g.squad.warnings.join('\n')}`),
    ...value.manual_guide,
   ].join('\n\n')
 }else el('proposal').textContent=''
}
for(const kind of ['pair','activate','analyze','pause','retry','disconnect','check','official','select-tab','recognize','delete-maps']){
 el(kind).addEventListener('click',async()=>{
  try{
   const payload:Record<string,unknown>={kind}
   if(kind==='pair'||kind==='check'){
    const base=endpoint(input('base'))
    const permission=new URL(base).hostname==='localhost'?'http://localhost/*':'http://127.0.0.1/*'
    if(!await chrome.permissions.request({origins:[permission]}))throw Error('Permiso local no concedido')
    Object.assign(payload,{base,pairing_id:input('pairing'),code:input('code'),confirm_destination:(el('confirm-destination') as HTMLInputElement).checked})
   }
   if(kind==='recognize')payload.view=input('view')
   if(kind==='disconnect')payload.discard=(el('discard') as HTMLInputElement).checked
   const result=await chrome.runtime.sendMessage(payload)
   if(!result.ok)throw Error(result.error)
   if(kind==='pair')(el('code') as HTMLInputElement).value=''
   if(result.diagnostic)el('diagnostic').textContent=JSON.stringify(result.diagnostic,null,2)
   await refresh()
  }catch(error){el('status').textContent=error instanceof Error?error.message:'Error local'}
 })
}
chrome.storage.onChanged.addListener(()=>void refresh())
const clearPreview=()=>{el('profile-preview-result').textContent='';(el('profile-reviewed') as HTMLInputElement).checked=false}
const fieldLabels:Record<string,string>={name:'Nombre',rating:'Media',position:'Posición',slot:'Puesto (incluye banquillo/reservas)',card_type:'Variante',club_name:'Nombre del club',balance:'Monedas',title:'Título',requirement_text:'Requisito completo',is_loan:'Cesión',is_evolution:'Evolución',tradable:'Transferible',first_owner:'Primer propietario',league:'Liga',club:'Club de carta',nationality:'Nacionalidad',rare:'Rara',special:'Especial',gallery_score:'Puntuación de Galería',progress_current:'Progreso observado',progress_target:'Meta'}
function renderMapping(definition:any){
 const entry=maps.find(m=>m.map_id===definition?.map_id)
 const root=el('visual-mapping');root.replaceChildren()
 if(!entry)return
 const selectors=[...new Set<string>(entry.map.nodes.map((n:any)=>n.selector))]
 const label=document.createElement('label');label.textContent='Contenedor de cada registro'
 const scope=document.createElement('select');scope.id='mapping-record';scope.append(new Option('Toda la región (cabecera/ficha)',''),...selectors.map(s=>new Option(s,s)));scope.value=definition.record_selector||'';label.append(scope);root.append(label)
 const choices=new Map<string,string>()
 for(const n of entry.map.nodes)for(const source of ['text','label'])if(n[source]){
  const key=n.selector+'|'+source
  if(!choices.has(key))choices.set(key,`${n[source].slice(0,80)} · ${n.selector} · ${source==='text'?'texto':'etiqueta'}`)
 }
 for(const field of fields[definition.view as keyof typeof fields]||[]){
  const label=document.createElement('label');label.textContent=(fieldLabels[field]||field)+(isRequired(definition.view,field)?' *':'')
  const select=document.createElement('select');select.dataset.field=field
  select.append(new Option('No observado',''),...Array.from(choices,([key,text])=>new Option(text,key)))
  const existing=definition.fields.find((f:any)=>f.field===field)
  if(existing)select.value=existing.selector+'|'+existing.source
  label.append(select);root.append(label)
 }
}
el('mapping-apply').addEventListener('click',()=>{
 try{
  const definition=JSON.parse(input('profile-definition'))
  definition.record_selector=input('mapping-record')||null
  definition.fields=Array.from(el('visual-mapping').querySelectorAll<HTMLSelectElement>('select[data-field]')).filter(s=>s.value).map(s=>{
   const [selector,source]=s.value.split('|'),field=s.dataset.field!
   return {field,selector,source,normalization:normalizationFor(field),required:isRequired(definition.view,field)}
  })
  ;(el('profile-definition') as HTMLTextAreaElement).value=JSON.stringify(definition,null,2)
  clearPreview();el('profile-save').click()
 }catch{el('status').textContent='Crea primero una definición desde el mapa seleccionado.'}
})
el('profile-choice').addEventListener('change',()=>{
 const p=profiles.find(p=>p.id===input('profile-choice'))
 ;(el('profile-definition') as HTMLTextAreaElement).value=p?JSON.stringify(p.definition,null,2):''
 renderMapping(p?.definition)
 clearPreview();profileState()
})
el('profile-definition').addEventListener('input',clearPreview)
el('profile-file').addEventListener('change',async()=>{
 const file=(el('profile-file') as HTMLInputElement).files?.[0]
 if(!file)return
 if(file.size>32000){el('status').textContent='Definición demasiado grande (máximo 32 KB).';return}
 ;(el('profile-definition') as HTMLTextAreaElement).value=await file.text()
 ;(el('profile-choice') as HTMLSelectElement).value=''
 clearPreview();profileState()
})
for(const kind of ['profile-draft','profile-save','profile-test-map','profile-test','profile-preview','profile-contrast','profile-enable','profile-disable','profile-read','profile-send']){
 el(kind).addEventListener('click',async()=>{
  try{
   const payload:Record<string,unknown>={kind,profile_id:input('profile-choice'),map_id:input('profile-map'),reviewed:(el('profile-reviewed') as HTMLInputElement).checked}
   if(kind==='profile-send')payload.context_confirmed=(el('context-confirmed') as HTMLInputElement).checked
   if(kind==='profile-save'){
    try{payload.definition=JSON.parse(input('profile-definition'))}catch{throw Error('JSON inválido; revisa la definición.')}
   }
   if(!['profile-draft','profile-save','profile-disable'].includes(kind)){
    const p=profiles.find(p=>p.id===payload.profile_id)
    let edited:unknown
    try{edited=JSON.parse(input('profile-definition'))}catch{throw Error('Selecciona y guarda la definición antes de probarla.')}
    if(!p||canonical(p.definition)!==canonical(edited))throw Error('Guarda los cambios de la definición antes de probar o activar el perfil.')
   }
   const result=await chrome.runtime.sendMessage(payload)
   if(!result.ok)throw Error(result.error)
   if(result.definition){(el('profile-definition') as HTMLTextAreaElement).value=JSON.stringify(result.definition,null,2);(el('profile-choice') as HTMLSelectElement).value='';renderMapping(result.definition)}
   if(kind==='profile-send')(el('context-confirmed') as HTMLInputElement).checked=false
   clearPreview()
   if(result.preview)el('profile-preview-result').textContent=JSON.stringify(result.preview,null,2)
   await refresh()
   if(result.profile){(el('profile-choice') as HTMLSelectElement).value=result.profile.id;profileState()}
  }catch(error){clearPreview();el('status').textContent=error instanceof Error?error.message:'Error local'}
 })
}
el('export-maps').addEventListener('click',async()=>{
 if(!(el('review-export') as HTMLInputElement).checked){el('status').textContent='Revisa el mapa y confirma que eliminaste cualquier dato que no quieras compartir.';return}
 const r=await chrome.runtime.sendMessage({kind:'status'})
 if(!r.maps?.length)return
 const url=URL.createObjectURL(new Blob([JSON.stringify({format:'club-lab-view-map-1',maps:r.maps},null,2)],{type:'application/json'}))
 const a=document.createElement('a');a.href=url;a.download='club-lab-mapa-revisado.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
})
void refresh()

for(const kind of ['analyze-club','diagnostic-one'])el(kind).addEventListener('click',async()=>{
 const button=el(kind) as HTMLButtonElement;button.disabled=true
 try{
  const result=await chrome.runtime.sendMessage({kind})
  if(!result.ok)throw Error(result.error)
  if(result.diagnostic){
   const url=URL.createObjectURL(new Blob([JSON.stringify(result.diagnostic,null,2)],{type:'application/json'}))
   const link=document.createElement('a');link.href=url;link.download='club-lab-esqueleto-sanitizado.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
  }
  await refresh()
 }catch(e){el('workflow-next').textContent=e instanceof Error?e.message:'No se pudo analizar la vista.'}
 finally{button.disabled=false}
})
for(const action of ['pause','resume','cancel'])el('workflow-'+action).addEventListener('click',async()=>{
 const result=await chrome.runtime.sendMessage({kind:'workflow-control',action})
 if(!result.ok)el('workflow-next').textContent=result.error
 else await refresh()
})
let polling=false,failures=0,nextPoll=0
setInterval(async()=>{
 if(polling||Date.now()<nextPoll)return
 polling=true
 try{const result=await chrome.runtime.sendMessage({kind:'workflow-poll'});if(!result.ok)throw Error(result.error);failures=0}
 catch{failures++;nextPoll=Date.now()+Math.min(60000,5000*2**Math.min(failures,4))}
 finally{polling=false}
},5000)
