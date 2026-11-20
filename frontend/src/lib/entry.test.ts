import {expect,it,vi} from 'vitest'
import {api,ApiError,setSessionHeaders} from '../api/client'
import {openEntry,rememberAutomaticClub} from './entry'
import {deferred} from '../test/helpers'
vi.mock('../api/client',async()=>({...await vi.importActual('../api/client'),api:vi.fn(),setSessionHeaders:vi.fn(),requestNonce:()=> 'synthetic-nonce'}))
it('serializa aperturas simultáneas sin cruzar cookie, CSRF o entrada',async()=>{
 const pending=deferred<{csrf_token:string;mode:string;entry_id:null}>(),paths:string[]=[]
 vi.mocked(api).mockImplementation(async(path)=>{
  paths.push(path)
  if(paths.length===1)return pending.promise
  if(path==='/app/session')return {csrf_token:'test-csrf',mode:'local',entry_id:1}
  return {entry_id:1,mode:'local'}
 })
 const first=openEntry(),second=openEntry('local')
 await Promise.resolve()
 expect(paths).toEqual(['/app/session'])
 pending.resolve({csrf_token:'test-csrf',mode:'live',entry_id:null})
 await Promise.all([first,second])
 expect(paths).toEqual(['/app/session','/app/entries','/app/session','/app/entries'])
 expect(setSessionHeaders).toHaveBeenLastCalledWith('test-csrf',1)
})
it('retoma solo el club automático elegido al vencer la sesión y descarta un contexto revocado',async()=>{
 rememberAutomaticClub(6)
 const attempts:unknown[]=[]
 let revoked=false
 vi.mocked(api).mockImplementation(async(path,options)=>{
   if(path==='/app/session')return {csrf_token:'new-token',mode:'live',entry_id:null}
   const body=JSON.parse(String(options?.body));attempts.push([body.mode,body.context_id])
   if(revoked&&body.mode==='assisted')throw new ApiError('Contexto no disponible',404)
   return {entry_id:4,mode:body.mode}
 })
 await openEntry()
 revoked=true
 await openEntry()
 await openEntry()
 expect(attempts).toEqual([['assisted',6],['assisted',6],['live',undefined],['live',undefined]])
 expect(localStorage.length===0||!Object.values(localStorage).includes('new-token')).toBe(true)
})
