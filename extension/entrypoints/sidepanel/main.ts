import {endpoint,canonical} from '../../lib/contracts'
import './style.css'
const el=(id:string)=>document.getElementById(id)!
const input=(id:string)=>(el(id) as HTMLInputElement).value
let hydrated=false
let profiles:any[]=[]
const statusLabels:Record<string,string>={draft:'Borrador',sample_tested:'Probado con muestra',observed_contrasted:'Contrastado manualmente en vista real',active:'Activo para vista previa manual',disabled:'Desactivado'}
function choices(id:string,values:{id:string;label:string}[],empty:string){
 const select=el(id) as HTMLSelectElement,current=select.value
 select.replaceChildren(new Option(empty,''),...values.map(v=>new Option(v.label,v.id)))
 if(values.some(v=>v.id===current))select.value=current
}
function profileState(){
 const p=profiles.find(p=>p.id===input('profile-choice'))
 el('profile-state').textContent=p?`${statusLabels[p.status]} · revisión ${p.revision}. Pruebas vinculadas a esta definición; sin ingesta real.`:'Selecciona un mapa para definir los campos.'
}
async function refresh(){
 const r=await chrome.runtime.sendMessage({kind:'status'})
 el('extension-id').textContent=r.extensionId||''
 el('extension-version').textContent=r.version||'desconocida'
 if(!hydrated){(el('base') as HTMLInputElement).value=r.base;hydrated=true}
 el('destination').textContent=`Destino guardado: ${r.base}. Origen canónico recomendado: http://localhost:8090. 127.0.0.1 mantiene una sesión local distinta.`
 el('compatibility').textContent=r.compatibility?`${r.compatibility.origin} · ${r.compatibility.revision}\n${r.compatibility.reason}`:'Comprueba versiones antes de emparejar. El reconocimiento de estructura funciona sin backend.'
 el('diagnostic').textContent=r.maps.length?JSON.stringify(r.maps,null,2):'Todavía no hay mapas. Selecciona una región visible y pulsa Reconocer estructura.'
 const partial=r.maps.filter((m:any)=>m.map.coverage.partial||m.map.coverage.truncated).length
 el('coverage').textContent=`${r.maps.length}/8 regiones privadas; ${partial} con omisiones. ${r.maps.filter((m:any)=>m.profile.evidence_origin==='observed_page_map').length} observadas en página oficial. Un mapa no acredita un extractor. Consulta coverage.omitted en la vista previa para ver textos largos, medios y subárboles excluidos.`
 profiles=r.profiles||[]
 choices('profile-map',r.maps.map((m:any)=>({id:m.map_id,label:`${m.profile.view} · ${m.observed_at}`})),'Selecciona una región')
 choices('profile-choice',profiles.map(p=>({id:p.id,label:`${p.definition.view} · r${p.revision} · ${statusLabels[p.status]}`})),'Nuevo perfil')
 profileState()
 el('status').textContent=`${r.paired?'Emparejado':'Sin emparejar'} · ${r.pending||0} pendientes. ${r.message||''}`
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
el('profile-choice').addEventListener('change',()=>{
 const p=profiles.find(p=>p.id===input('profile-choice'))
 ;(el('profile-definition') as HTMLTextAreaElement).value=p?JSON.stringify(p.definition,null,2):''
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
for(const kind of ['profile-draft','profile-save','profile-test','profile-preview','profile-contrast','profile-enable','profile-disable','profile-read']){
 el(kind).addEventListener('click',async()=>{
  try{
   const payload:Record<string,unknown>={kind,profile_id:input('profile-choice'),map_id:input('profile-map'),reviewed:(el('profile-reviewed') as HTMLInputElement).checked}
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
   if(result.definition){(el('profile-definition') as HTMLTextAreaElement).value=JSON.stringify(result.definition,null,2);(el('profile-choice') as HTMLSelectElement).value=''}
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
