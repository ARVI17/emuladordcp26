import {endpoint} from '../../lib/contracts'
import './style.css'
const el=(id:string)=>document.getElementById(id)!
const input=(id:string)=>(el(id) as HTMLInputElement).value
async function refresh(){
 const r=await chrome.runtime.sendMessage({kind:'status'})
 el('extension-id').textContent=r.extensionId||''
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
for(const kind of ['pair','activate','analyze','pause','retry','disconnect','diagnose']){
 el(kind).addEventListener('click',async()=>{
  try{
   const payload:Record<string,unknown>={kind}
   if(kind==='pair'){
    const base=endpoint(input('base'))
    const permission=new URL(base).hostname==='localhost'?'http://localhost/*':'http://127.0.0.1/*'
    if(!await chrome.permissions.request({origins:[permission]}))throw Error('Permiso local no concedido')
    Object.assign(payload,{base,pairing_id:input('pairing'),code:input('code')})
   }
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
void refresh()
