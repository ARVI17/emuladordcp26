import {z} from 'zod'
import {eaDiagnostic,endpoint} from './contracts'
import {visibleSession} from './visible-session'
const ticketSchema=z.object({request_id:z.uuid(),pairing_id:z.uuid(),code:z.string().regex(/^\d{6}$/),extension_id:z.string().regex(/^[a-p]{32}$/),context_id:z.number().int().positive()}).strict()
const official='https://www.ea.com/ea-sports-fc/ultimate-team/web-app/'
async function selectOfficialTab(tabs: chrome.tabs.Tab[], preferredId?: number) {
 if(tabs.length<=1)return tabs[0]
 const deadline=Date.now()+3500
 while(true){
  const observed=await Promise.all(tabs.map(async tab=>{
   if(!tab.id||tab.discarded)return {tab,state:'unavailable' as const}
   const frames=await chrome.scripting.executeScript({target:{tabId:tab.id},func:visibleSession}).catch(()=>[])
   return {tab,state:frames[0]?.result||'unknown'}
  }))
  const signedIn=observed.filter(item=>item.state==='club')
  const preferred=signedIn.find(item=>item.tab.id===preferredId)
  if(preferred)return preferred.tab
  const unresolved=observed.some(item=>item.state==='unknown')
  if(!unresolved&&signedIn.length===1)return signedIn[0]!.tab
  if(signedIn.length>1)throw Error('page_changed')
  if(Date.now()>=deadline){
   if(observed.every(item=>item.state==='login'))throw Error('login_required')
   throw Error('page_changed')
  }
  await new Promise(resolve=>setTimeout(resolve,300))
 }
}
type Job={base:string;credential:string;requestId:string;tabId:number;ownerDocument?:string;started:number;step:string;phase:string;inventory:any[];squad:any[];pages:number;signatures:string[];identity?:{club_fingerprint:string;club_name:string};formation?:string;publication?:Record<string,unknown>}
export function installBrowserAuto(){
 // Each page returns as a new event. Private session state survives worker suspension.
 let serial=Promise.resolve()
 const enqueue=(fn:()=>Promise<unknown>)=>{const next=serial.then(fn);serial=next.then(()=>{},()=>{});return next}
 const load=async():Promise<Record<string,Job>>=>(await chrome.storage.session.get('autoJobs')).autoJobs||{}
 const alarmName='club-lab-auto-resume'
 const schedule=async(jobs:Record<string,Job>)=>{
  if(Object.keys(jobs).length)await chrome.alarms.create(alarmName,{periodInMinutes:0.5})
  else await chrome.alarms.clear(alarmName)
 }
 const save=async(jobs:Record<string,Job>)=>{await chrome.storage.session.set({autoJobs:jobs});await schedule(jobs)}
 const request=async(job:Job,path:string,body:unknown)=>{
  const r=await fetch(job.base+'/api/'+path,{method:'POST',credentials:'omit',redirect:'error',headers:{'Content-Type':'application/json','X-Reader-Extension':chrome.runtime.id,...(job.credential?{Authorization:'Bearer '+job.credential}:{})},body:JSON.stringify(body),signal:AbortSignal.timeout(25000)})
  if(!r.ok)throw Error('backend');return r.json()
 }
 const stop=async(job:Job,reason='cancelled')=>{
  if(job.tabId)await chrome.tabs.sendMessage(job.tabId,{kind:'ea-auto-stop'}).catch(()=>{})
  if(job.credential)await request(job,'browser-auto/failure',{request_id:job.requestId,reason}).catch(()=>{})
  const jobs=await load();if(jobs[job.base]?.requestId===job.requestId){delete jobs[job.base];await save(jobs)}
 }
 const dispatch=async(job:Job,phase:string,resume=false)=>{
  job.phase=phase;if(!resume)job.step=crypto.randomUUID()
  await save({...await load(),[job.base]:job})
  await request(job,'browser-auto/progress',{request_id:job.requestId,pages_read:job.pages,cards_read:job.inventory.length,phase:phase==='squad'?'squad':'inventory'})
  await chrome.scripting.executeScript({target:{tabId:job.tabId},files:['ea-auto.js']})
  for(let attempt=0;attempt<5;attempt++){
   const ack=await chrome.tabs.sendMessage(job.tabId,{kind:'ea-auto-step',request_id:job.requestId,step:job.step,phase,offset:job.inventory.length})
   if(ack?.ok)return
   if(ack?.reason!=='busy')throw Error(ack?.reason||'page_changed')
   await new Promise(r=>setTimeout(r,300))
  }
  throw Error('page_changed')
 }
 const fail=async(job:Job,error:unknown)=>{
  const code=error instanceof Error?error.message:''
  await stop(job,['login_required','permission_required','page_changed','cancelled','timeout'].includes(code)?code:'page_changed')
 }
 // A worker can stop after saving a step but before delivering its command.
 // The alarm wakes it even when the content script has no result left to send.
 chrome.alarms.onAlarm.addListener(alarm=>{
  if(alarm.name!==alarmName)return
  void enqueue(async()=>{
   const jobs=await load()
   if(!Object.keys(jobs).length){await schedule(jobs);return}
   for(const job of Object.values(jobs))try{
    if(Date.now()-job.started>30*60*1000)throw Error('timeout')
    if(job.publication){
     await request(job,'browser-auto/publish',job.publication)
     const remaining=await load();delete remaining[job.base];await save(remaining)
    }else await dispatch(job,job.phase,true)
   }catch(error){await fail(job,error)}
  }).catch(()=>{})
 })
 // An old alarm after a browser restart finds no session job and is removed.
 void enqueue(async()=>schedule(await load())).catch(()=>{})
 chrome.permissions.onRemoved.addListener(()=>{void enqueue(async()=>{for(const job of Object.values(await load()))await stop(job,'permission_required')})})
 chrome.tabs.onRemoved.addListener(id=>{void enqueue(async()=>{for(const job of Object.values(await load()))if(job.tabId===id)await stop(job)})})
 chrome.runtime.onMessage.addListener((message,sender,reply)=>{
  if(!['browser-auto-start','browser-auto-cancel','browser-auto-step-result'].includes(message?.kind))return
  void enqueue(async()=>{
   if(sender.id!==chrome.runtime.id||!sender.tab?.id||sender.frameId!==0||!sender.url)throw Error('origin')
   const jobs=await load()
   if(message.kind==='browser-auto-step-result'){
    if(!eaDiagnostic(sender.url))throw Error('origin')
    const job=Object.values(jobs).find(j=>j.tabId===sender.tab!.id&&j.requestId===message.request_id)
    if(!job)return {ok:false}
    try{
     if(job.publication){await request(job,'browser-auto/publish',job.publication);delete jobs[job.base];await save(jobs);return {ok:true}}
     if(message.step!==job.step){await dispatch(job,job.phase,true);return {ok:true}}
     if(Date.now()-job.started>30*60*1000)throw Error('timeout')
     if(!message.ok)throw Error(message.reason)
     const data=message.data
     if(!data?.identity||!Array.isArray(data.cards)||data.cards.length>30)throw Error('page_changed')
     if(job.identity&&JSON.stringify(job.identity)!==JSON.stringify(data.identity))throw Error('page_changed')
     job.identity=data.identity
     if(job.phase==='squad'){
      job.squad=data.cards;job.formation=data.formation
      await dispatch(job,'inventory-start');return {ok:true}
     }
     if(typeof data.signature!=='string'||job.signatures.includes(data.signature))throw Error('page_changed')
     job.signatures.push(data.signature);job.pages++;job.inventory.push(...data.cards)
     if(job.inventory.length>1000)throw Error('page_changed')
     const end=job.pages>=50||job.inventory.length+30>1000?'limit':data.end
     if(end==='next'){await dispatch(job,'inventory-next');return {ok:true}}
     if(!['end','unknown','limit'].includes(end))throw Error('page_changed')
     await request(job,'browser-auto/progress',{request_id:job.requestId,pages_read:job.pages,cards_read:job.inventory.length,phase:'publishing'})
     const payload={...job.identity,request_id:job.requestId,reader_version:'ea-visible-2',edition:'FC27',edition_basis:'owner_selected',observed_at:new Date().toISOString(),inventory:job.inventory,squad:job.squad,formation:job.formation,active_squad_observed:true,inventory_complete:false,pages_read:job.pages,traversal_end:end}
     job.publication=payload;await save({...await load(),[job.base]:job})
     try{await request(job,'browser-auto/publish',payload)}catch{await request(job,'browser-auto/publish',payload)}
     delete jobs[job.base];await save(jobs)
     return {ok:true}
    }catch(error){await fail(job,error);return {ok:false}}
   }
   const url=new URL(sender.url),base=endpoint(url.origin)
   if(url.pathname!=='/'||url.search)throw Error('origin')
   if(message.kind==='browser-auto-cancel'){
    if(jobs[base]?.ownerDocument===sender.documentId&&jobs[base])await stop(jobs[base])
    return {ok:true}
   }
   const ticket=ticketSchema.parse(message.ticket)
   if(ticket.extension_id!==chrome.runtime.id)throw Error('extension')
   if(jobs[base]?.requestId===ticket.request_id)return {ok:true}
   const job:Job={base,credential:'',requestId:ticket.request_id,tabId:0,ownerDocument:sender.documentId,started:Date.now(),step:'',phase:'squad',inventory:[],squad:[],pages:0,signatures:[]}
   try{
    const grant=await request(job,'reader/claim',{pairing_id:ticket.pairing_id,code:ticket.code});job.credential=grant.credential
    if(jobs[base])await stop(jobs[base])
    const tabs=(await chrome.tabs.query({url:'https://www.ea.com/*'})).filter(t=>t.url&&eaDiagnostic(t.url))
    const {officialTab}=await chrome.storage.session.get('officialTab')
    let selected=await selectOfficialTab(tabs,officialTab)
    const created=!selected
    // Keep the tab identity before navigating: failures/closure can now be attributed
    // to this job even while the official page is still loading.
    if(!selected)selected=await chrome.tabs.create({url:'about:blank',active:false})
    if(!selected.id)throw Error('reader_unavailable')
    job.tabId=selected.id
    if(Object.values(await load()).some(j=>j.tabId===job.tabId)){job.tabId=0;throw Error('page_changed')}
    if(created)await chrome.tabs.update(job.tabId,{url:official})
    const until=Date.now()+20000
    while(true){
     const tab=await chrome.tabs.get(job.tabId)
     if(tab.status==='complete'&&tab.url&&eaDiagnostic(tab.url))break
     if(Date.now()>until)throw Error('timeout')
     await new Promise(r=>setTimeout(r,300))
    }
    await dispatch(job,'squad')
    return {ok:true}
   }catch(error){await fail(job,error);return {ok:false}}
  }).then(reply).catch(()=>reply({ok:false,reason:'reader_unavailable'}))
  return true
 })
}
