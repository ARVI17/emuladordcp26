import {z} from 'zod'
import {eaDiagnostic,endpoint} from './contracts'

const ticketSchema=z.object({request_id:z.uuid(),pairing_id:z.uuid(),code:z.string().regex(/^\d{6}$/),extension_id:z.string().regex(/^[a-p]{32}$/),context_id:z.number().int().positive()}).strict()
type Job={tabId?:number;ownerTabId:number;cancelled:boolean}

export function installBrowserAuto(){
 const jobs=new Map<string,Job>()
 const stop=(job:Job)=>{job.cancelled=true;if(job.tabId)void chrome.tabs.sendMessage(job.tabId,{kind:'ea-auto-stop'}).catch(()=>{})}
 chrome.permissions.onRemoved.addListener(()=>{for(const job of jobs.values())stop(job)})
 chrome.tabs.onRemoved.addListener(id=>{for(const job of jobs.values())if(job.ownerTabId===id||job.tabId===id)stop(job)})
 chrome.runtime.onMessage.addListener((message,sender,reply)=>{
  if(!['browser-auto-start','browser-auto-cancel'].includes(message?.kind))return
  const run=async()=>{
   if(sender.id!==chrome.runtime.id||!sender.tab||sender.frameId!==0||!sender.url)throw Error('Origen no autorizado')
   const url=new URL(sender.url),base=endpoint(url.origin)
   if(url.pathname!=='/'||url.search)throw Error('Origen no autorizado')
   const prior=jobs.get(base)
   if(prior){prior.cancelled=true;if(prior.tabId)await chrome.tabs.sendMessage(prior.tabId,{kind:'ea-auto-stop'}).catch(()=>{})}
   if(message.kind==='browser-auto-cancel')return {ok:true}
   const ticket=ticketSchema.parse(message.ticket)
   if(ticket.extension_id!==chrome.runtime.id)throw Error('Extensión distinta')
   const job:Job={cancelled:false,ownerTabId:sender.tab.id!};jobs.set(base,job)
   let credential=''
   const request=async(path:string,body:unknown)=>{
    const response=await fetch(base+'/api/'+path,{method:'POST',credentials:'omit',redirect:'error',
     headers:{'Content-Type':'application/json','X-Reader-Extension':chrome.runtime.id,...(credential?{Authorization:'Bearer '+credential}:{})},
     body:JSON.stringify(body),signal:AbortSignal.timeout(15000)})
    if(!response.ok)throw Error('backend')
    return response.json()
   }
   try{
    const grant=await request('reader/claim',{pairing_id:ticket.pairing_id,code:ticket.code});credential=grant.credential
    const tabs=(await chrome.tabs.query({url:'https://www.ea.com/*'})).filter(t=>t.url&&eaDiagnostic(t.url))
    const {officialTab}=await chrome.storage.session.get('officialTab')
    const selected=tabs.find(t=>t.id===officialTab)||(tabs.length===1?tabs[0]:undefined)
    if(!selected?.id)throw Error(tabs.length?'page_changed':'login_required')
    job.tabId=selected.id
    await chrome.scripting.executeScript({target:{tabId:selected.id},files:['ea-auto.js']})
    if(job.cancelled)throw Error('cancelled')
    const answer=await chrome.tabs.sendMessage(selected.id,{kind:'ea-auto-read',request_id:ticket.request_id})
    if(job.cancelled)throw Error('cancelled')
    if(!answer?.ok)throw Error(answer?.reason||'page_changed')
    const payload={...answer.snapshot,request_id:ticket.request_id}
    // Retry the same immutable observation, never a newly dated substitute.
    let result
    for(let attempt=0;attempt<2;attempt++){
     if(job.cancelled)throw Error('cancelled')
     try{result=await request('browser-auto/publish',payload);break}catch(error){if(attempt===1)throw error}
    }
    return {ok:true,status:result?.status}
   }catch(error){
    const code=error instanceof Error?error.message:''
    const reason=['login_required','permission_required','page_changed','cancelled','timeout'].includes(code)?code:'page_changed'
    if(credential&&!job.cancelled)await request('browser-auto/failure',{request_id:ticket.request_id,reason}).catch(()=>{})
    return {ok:false,reason}
   }finally{if(jobs.get(base)===job)jobs.delete(base)}
  }
  void run().then(reply).catch(()=>reply({ok:false,reason:'reader_unavailable'}))
  return true
 })
}
