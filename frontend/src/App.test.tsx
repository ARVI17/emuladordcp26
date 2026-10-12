import {screen} from '@testing-library/react'
import {expect,it,vi} from 'vitest'
import {api} from './api/client'
import App from './App'
import {profile,renderClub} from './test/helpers'

vi.mock('./lib/entry',()=>({openEntry:vi.fn(async()=>({entry_id:1,mode:'local',modules:{}}))}))
vi.mock('./api/client',async()=>({...await vi.importActual('./api/client'),api:vi.fn()}))
it('solo ofrece FC27 sin selector de archivo',async()=>{
  vi.mocked(api).mockImplementation(async(path)=>{
    if(path==='/profile')return profile
    if(path.startsWith('/dashboard?'))return {profile,counts:{players:0,protected:0,duplicates:0,pending_challenges:0},objectives:[],alerts:[]}
    throw new Error(path)
  })
  renderClub(<App/>)
  await screen.findByRole('button',{name:'Añadir mis jugadores'})
  expect(screen.getByRole('heading',{name:'Club Lab FC27'})).toBeInTheDocument()
  expect(screen.queryByLabelText('Temporada activa')).not.toBeInTheDocument()
  expect(vi.mocked(api).mock.calls.every(([path])=>!path.includes('FC26'))).toBe(true)
})
