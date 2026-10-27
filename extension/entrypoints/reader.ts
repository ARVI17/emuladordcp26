import {reading,forbidden,admitted} from '../lib/contracts'
export default defineUnlistedScript(()=>{
  const world=globalThis as typeof globalThis & {clubLabReaderInstalled?:boolean}
  if(world.clubLabReaderInstalled)return
  world.clubLabReaderInstalled=true
  // This selector belongs to our documented sample/export schema, NOT to EA.
  let observer:MutationObserver|null=null, timer:ReturnType<typeof setTimeout>|undefined
  let last='', documentRef='', nonce=''
  const text=(row:Element,field:string)=>{
    const el=row.querySelector(`[data-field="${field}"]`)
    if(!el || el.children.length || el.tagName==='INPUT') return null
    const value=(el.textContent||'').trim()
    return value && value.length<=120 && !forbidden.test(value) ? value : null
  }
  const bool=(v:string|null)=>v==null?null:/^(true|sí|si|yes)$/i.test(v)?true:/^(false|no)$/i.test(v)?false:null
  const number=(v:string|null)=>v && /^\d+(?:[.,]\d{3})*$/.test(v)?Number(v.replace(/[.,]/g,'')):null
  const positions:Record<string,string>={GK:'POR',RB:'LD',CB:'DFC',LB:'LI',RWB:'CAD',LWB:'CAI',CDM:'MCD',CM:'MC',CAM:'MCO',RM:'MD',LM:'MI',RW:'ED',LW:'EI',CF:'SD',ST:'DC'}
  const stop=()=>{observer?.disconnect();observer=null;clearTimeout(timer)}
  const scan=async()=>{
    if(!admitted(location.href)){stop();return}
    const root=document.querySelector('[data-club-lab-sample="1"]')
    if(!root || root.getAttribute('aria-busy')==='true' || root.querySelector('[aria-busy="true"]')) return
    if(root.getAttribute('data-edition')!=='FC27') {stop();return}
    const rows=Array.from(root.querySelectorAll('[data-card]')).filter(el=>el.getClientRects().length>0)
    if(rows.length>30) {await chrome.runtime.sendMessage({kind:'reader-error',nonce,documentRef,message:'Más de 30 filas visibles; lectura pausada.'});stop();return}
    const records=rows.map((row,ordinal)=>{
      const get=(f:string)=>text(row,f),position=get('position')||''
      const facts={ordinal,name:get('name'),rating:number(get('rating')),position:positions[position]||position,
        card_type:get('card_type'),league:get('league'),club:get('club'),nationality:get('nationality'),
        is_loan:bool(get('is_loan')),is_evolution:bool(get('is_evolution')),tradable:bool(get('tradable')),
        rare:bool(get('rare')),special:bool(get('special')),is_holographic:bool(get('is_holographic')),
        first_owner:bool(get('first_owner')),holographic_level:number(get('holographic_level')),gallery_score:number(get('gallery_score'))}
      return {...facts,location:'club',evidence:Object.fromEntries(Object.entries(facts).filter(([k,v])=>k!=='ordinal'&&v!==null).map(([k])=>[k,`sample-v1:data-field=${k}`]))}
    })
    const value=reading.safeParse({view:root.getAttribute('data-view')||'inventory',edition:'FC27',source_kind:root.getAttribute('data-source'),records,
      scope:{page:root.getAttribute('data-page')||'visible',filters:'',location:'club',visible_count:records.length,loading:false,
        virtualized:root.hasAttribute('data-virtualized')?root.getAttribute('data-virtualized')==='true':null,
        terminal_observed:false,global_complete:false},unknown_fields:[...new Set(records.flatMap(r=>Object.entries(r).filter(([,v])=>v===null).map(([k])=>k)))]})
    if(!value.success){await chrome.runtime.sendMessage({kind:'reader-error',nonce,documentRef,message:'La estructura cambió o hay campos esenciales desconocidos. Revisión necesaria.'});return}
    const signature=JSON.stringify(value.data)
    if(signature===last)return
    const answer=await chrome.runtime.sendMessage({kind:'observation',nonce,documentRef,data:value.data,observed_at:new Date().toISOString()})
    if(answer?.ok)last=signature
  }
  chrome.runtime.onMessage.addListener((message,_sender,sendResponse)=>{
    if(message.kind==='pause'){stop();sendResponse({ok:true});return}
    if(message.kind==='start'){
      stop();documentRef=message.documentRef;nonce=message.nonce
      const root=document.querySelector('[data-club-lab-sample="1"]')
      if(!root || !admitted(location.href)){sendResponse({ok:false,error:'Vista sin extractor contrastado. Usa el diagnóstico mínimo.'});return}
      observer=new MutationObserver(()=>{clearTimeout(timer);timer=setTimeout(()=>void scan(),400)})
      observer.observe(root,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['aria-busy','data-page','data-edition','data-view']})
      void scan();sendResponse({ok:true})
    }
  })
  addEventListener('pagehide',stop,{once:true})
})
