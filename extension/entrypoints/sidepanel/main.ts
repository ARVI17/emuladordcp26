import {endpoint} from '../../lib/contracts'
import './style.css'
const el=(id:string)=>document.getElementById(id)!
const input=(id:string)=>(el(id) as HTMLInputElement).value
let hydrated=false
async function refresh(){
 const r=await chrome.runtime.sendMessage({kind:'status'})
 el('extension-id').textContent=r.extensionId||''
 if(!hydrated){(el('base') as HTMLInputElement).value=r.base;hydrated=true}
 el('destination').textContent=`Destino guardado: ${r.base}. Origen canónico recomendado: http://localhost:8090. 127.0.0.1 mantiene una sesión local distinta.`
 el('compatibility').textContent=r.compatibility?`${r.compatibility.origin} · ${r.compatibility.revision}\n${r.compatibility.reason}`:'Comprueba versiones antes de emparejar. El reconocimiento de estructura funciona sin backend.'
 el('diagnostic').textContent=r.maps.length?JSON.stringify(r.maps,null,2):'Todavía no hay mapas. Selecciona una región visible y pulsa Reconocer estructura.'
 el('coverage').textContent=`${r.maps.length}/8 regiones privadas. ${r.maps.filter((m:any)=>m.profile.evidence_origin==='observed_page_map').length} observadas en página oficial; ninguna contrastada aún como extractor. La vista la declaras tú.`
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
el('export-maps').addEventListener('click',async()=>{
 if(!(el('review-export') as HTMLInputElement).checked){el('status').textContent='Revisa el mapa y confirma que eliminaste cualquier dato que no quieras compartir.';return}
 const r=await chrome.runtime.sendMessage({kind:'status'})
 if(!r.maps?.length)return
 const url=URL.createObjectURL(new Blob([JSON.stringify({format:'club-lab-view-map-1',maps:r.maps},null,2)],{type:'application/json'}))
 const a=document.createElement('a');a.href=url;a.download='club-lab-mapa-revisado.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
})
void refresh()
