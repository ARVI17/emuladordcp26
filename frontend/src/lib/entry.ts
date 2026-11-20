import {api,ApiError,setSessionHeaders,requestNonce} from '../api/client'
export type EntryState={entry_id:number;club_context_id:number;status:string;label:string;identity_verified:boolean;snapshot_id:number|null;observed_at:string|null;imported_at:string|null;last_attempt:string|null;mode:'live'|'local'|'assisted';next_action:string;modules:Record<string,{ready:boolean;missing:string[];reason:string|null}>}
// A first session creates an HttpOnly cookie. Concurrent initial requests could
// otherwise bind the second cookie to the first response's CSRF token.
let opening:Promise<unknown>=Promise.resolve()
const preferredClubKey='club-lab.automatic-context'
export function rememberAutomaticClub(id:number|null){
  try{
    if(id===null)localStorage.removeItem(preferredClubKey)
    else if(Number.isSafeInteger(id)&&id>1)localStorage.setItem(preferredClubKey,String(id))
  }catch{/* Browser storage is optional. */}
}
function preferredAutomaticClub(){
  try{
    const id=Number(localStorage.getItem(preferredClubKey))
    return Number.isSafeInteger(id)&&id>1?id:undefined
  }catch{return undefined}
}
export function openEntry(mode?:'live'|'local'|'assisted',reason='open',contextId?:number):Promise<EntryState>{
  const next=opening.then(()=>performEntry(mode,reason,contextId))
  opening=next.catch(()=>undefined)
  return next
}
async function performEntry(mode?:'live'|'local'|'assisted',reason='open',contextId?:number):Promise<EntryState>{
  const session=await api<{csrf_token:string;mode:'live'|'local'|'assisted';entry_id:number|null}>('/app/session',{method:'POST'})
  setSessionHeaders(session.csrf_token,null)
  // Only a previously enabled reading context is remembered. The server checks ownership
  // on every entry, and checks the extension grant again before a new read.
  const preferred=!mode&&!contextId&&!session.entry_id&&reason==='open'?preferredAutomaticClub():undefined
  const enter=(next:EntryState['mode'],target?:number)=>api<EntryState>('/app/entries',{method:'POST',
    body:JSON.stringify({nonce:requestNonce(),mode:next,reason,context_id:target})})
  let entry:EntryState
  try{
    entry=await enter(mode||(preferred?'assisted':session.entry_id?session.mode:'live'),contextId??preferred)
  }catch(error){
    if(!preferred||!(error instanceof ApiError)||![404,409].includes(error.status))throw error
    rememberAutomaticClub(null)
    entry=await enter('live')
  }
  if(mode&&(mode!=='assisted'||(contextId&&contextId!==preferredAutomaticClub())))rememberAutomaticClub(null)
  setSessionHeaders(session.csrf_token,entry.entry_id)
  return entry
}
