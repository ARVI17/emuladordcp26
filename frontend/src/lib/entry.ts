import {api,setSessionHeaders,requestNonce} from '../api/client'
export type EntryState={entry_id:number;club_context_id:number;status:string;label:string;identity_verified:boolean;snapshot_id:number|null;observed_at:string|null;imported_at:string|null;last_attempt:string|null;mode:'live'|'local';next_action:string;modules:Record<string,{ready:boolean;missing:string[];reason:string|null}>}
// A first session creates an HttpOnly cookie. Concurrent initial requests could
// otherwise bind the second cookie to the first response's CSRF token.
let opening:Promise<unknown>=Promise.resolve()
export function openEntry(mode?:'live'|'local',reason='open',contextId?:number):Promise<EntryState>{
  const next=opening.then(()=>performEntry(mode,reason,contextId))
  opening=next.catch(()=>undefined)
  return next
}
async function performEntry(mode?:'live'|'local',reason='open',contextId?:number):Promise<EntryState>{
  const session=await api<{csrf_token:string;mode:'live'|'local';entry_id:number|null}>('/app/session',{method:'POST'})
  setSessionHeaders(session.csrf_token,null)
  const entry=await api<EntryState>('/app/entries',{method:'POST',body:JSON.stringify({nonce:requestNonce(),mode:mode||(session.entry_id?session.mode:'live'),reason,context_id:contextId})})
  setSessionHeaders(session.csrf_token,entry.entry_id)
  return entry
}
