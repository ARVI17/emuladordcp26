import {screen} from '@testing-library/react'
import {expect,it,vi} from 'vitest'
import {api} from './api/client'
import App from './App'
import {profile,renderClub} from './test/helpers'
import {openEntry,type EntryState} from './lib/entry'

vi.mock('./lib/entry',()=>({openEntry:vi.fn(async()=>({entry_id:1,mode:'local',modules:{}}))}))
vi.mock('./api/client',async()=>({...await vi.importActual('./api/client'),api:vi.fn()}))
it('solo ofrece FC27 sin selector de archivo',async()=>{
  vi.mocked(api).mockImplementation(async(path)=>{
    if(path==='/profile')return profile
    if(path==='/dashboard')return {mode:'local',profile,account:{identity_verified:false,name:null,platform:null,coins:null,fc_points:null,unassigned_count:null,observed_at:null},counts:{players:0,protected:0,duplicates:0,pending_challenges:0},objectives:[],alerts:[]}
    throw new Error(path)
  })
  renderClub(<App/>)
  await screen.findByRole('heading',{name:'Inicio'})
  expect(screen.getByRole('region',{name:'Artículos sin asignar'})).toHaveTextContent('Sin consultar')
  expect(screen.getByRole('heading',{name:'Club Lab FC27'})).toBeInTheDocument()
  expect(screen.queryByLabelText('Temporada activa')).not.toBeInTheDocument()
  expect(vi.mocked(api).mock.calls.every(([path])=>!path.includes('FC26'))).toBe(true)
})
it('conserva Mi club visible ante una lectura parcial o vencida sin habilitar cálculos',async()=>{
 window.location.hash='#/club'
 const entry:EntryState={observed_at:null,imported_at:null,last_attempt:null,next_action:'Revisar',label:'Parcial',entry_id:2,club_context_id:2,mode:'live',identity_verified:true,snapshot_id:9,status:'partial',modules:{analysis:{ready:false,missing:['inventory'],reason:'Lectura parcial'}}}
 vi.mocked(openEntry).mockResolvedValueOnce(entry)
 vi.mocked(api).mockImplementation(async(path)=>{
  if(path.includes('/sync-state'))return entry
  if(path==='/dashboard')return {account:{identity_verified:true,name:'Club sintético',platform:'PC'},mode:'live',profile,counts:{},objectives:[],alerts:[]}
  if(path.startsWith('/players?'))return {items:[],total:0}
  if(path.startsWith('/catalog/'))return {items:[],total:0}
  throw new Error(path)
 })
 renderClub(<App/> )
 expect(await screen.findByRole('heading',{name:/^Mi club$/})).toBeInTheDocument()
 expect(screen.queryByRole('heading',{name:'Lectura pendiente'})).not.toBeInTheDocument()
 window.location.hash=''
})
