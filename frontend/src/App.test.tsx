import {fireEvent,screen,waitFor} from '@testing-library/react'
import {expect,it,vi} from 'vitest'
import {api} from './api/client'
import App from './App'
import {profile,renderClub} from './test/helpers'

vi.mock('./lib/entry',()=>({openEntry:vi.fn(async()=>({entry_id:1,mode:'local',modules:{}}))}))
vi.mock('./api/client',async()=>({...await vi.importActual('./api/client'),api:vi.fn()}))
it('cambia la edición del perfil y consulta los datos de la temporada elegida',async()=>{
  vi.mocked(api).mockImplementation(async(path,options)=>{
    if(path==='/profile'&&options?.method==='PATCH')return {...profile,game_version:'FC26'}
    if(path==='/profile')return profile
    if(path.startsWith('/dashboard?'))return {profile,counts:{players:0,protected:0,duplicates:0,pending_challenges:0},objectives:[],alerts:[]}
    throw new Error(path)
  })
  renderClub(<App/>)
  await screen.findByRole('button',{name:'Añadir mis jugadores'})
  fireEvent.change(screen.getByLabelText('Temporada activa'),{target:{value:'FC26'}})
  expect(await screen.findByRole('heading',{name:'FC 26 Club Lab'})).toBeInTheDocument()
  await waitFor(()=>expect(vi.mocked(api)).toHaveBeenCalledWith('/dashboard?game_version=FC26'))
  expect(vi.mocked(api)).toHaveBeenCalledWith('/profile',{method:'PATCH',body:'{"game_version":"FC26"}'})
  expect(screen.getByText(/Su inventario y progreso se mantienen separados/)).toBeInTheDocument()
})
