import {expect,it,vi} from 'vitest'
import {api,setSessionHeaders} from '../api/client'
import {openEntry} from './entry'
import {deferred} from '../test/helpers'
vi.mock('../api/client',()=>({api:vi.fn(),setSessionHeaders:vi.fn(),requestNonce:()=> 'synthetic-nonce'}))
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
