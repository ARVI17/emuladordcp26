import {fireEvent,screen,waitFor} from '@testing-library/react'
import {expect,it,vi} from 'vitest'
import {api} from '../api/client'
import {SettingsPage} from './OverviewPages'
import {profile,renderClub} from '../test/helpers'

vi.mock('../api/client',async()=>({...await vi.importActual('../api/client'),api:vi.fn()}))
it('muestra el rechazo del servidor al guardar el perfil y permite corregirlo',async()=>{
  vi.mocked(api).mockImplementation(async(path,options)=>{
    if(path==='/profile'&&options?.method==='PATCH')throw new Error('name: El nombre no es válido para este perfil.')
    if(path==='/profile')return profile
    if(path.startsWith('/submissions?'))return {items:[],total:0}
    throw new Error(path)
  })
  renderClub(<SettingsPage dark setDark={()=>{}}/>)
  await waitFor(()=>expect(screen.getByLabelText('Nombre local')).toHaveValue('Mi club'))
  fireEvent.change(screen.getByLabelText('Nombre local'),{target:{value:'Nuevo club'}})
  fireEvent.click(screen.getByRole('button',{name:'Guardar preferencias'}))
  expect(await screen.findByRole('alert')).toHaveTextContent('El nombre no es válido para este perfil.')
  expect(screen.getByLabelText('Nombre local')).toHaveValue('Nuevo club')
  expect(screen.getByRole('button',{name:'Guardar preferencias'})).toBeEnabled()
})
