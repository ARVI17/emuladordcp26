import {fireEvent,screen,waitFor} from '@testing-library/react'
import {expect,it,vi} from 'vitest'
import {api} from '../api/client'
import {renderClub} from '../test/helpers'
import {ObjectiveSquadsPage} from './ObjectiveSquadsPage'

vi.mock('../api/client',async()=>({...await vi.importActual('../api/client'),api:vi.fn()}))
it('muestra progreso desconocido y guardar una propuesta no envía progreso',async()=>{
 window.location.hash='#/plantillas/objetivos?ids=11'
 const goal={id:11,name:'Objetivo sintético',description:'',category:'Objetivo',target:3,expires_at:null,rules:{reviewed:true,mode:'squad_battles',source_reference:'Fuente de prueba',observed_at:null},revision:1,expired:false,progress:{value:null,origin:'unknown',observed_at:null},definition_verified:false}
 vi.mocked(api).mockImplementation(async(path)=>{
  if(path.startsWith('/objective-planning?'))return {items:[goal],total:1}
  if(path==='/squads/formations')return {items:[{id:'4-3-3'}]}
  if(path==='/objective-planning/preview')return {status:'proposals',binding:{entry_id:1,snapshot_id:null},context:{compatible:true,mode:'squad_battles',min_difficulty:'professional',sessions:[]},objectives:[goal],actions_pending:[],proposals:[{key:'A',profiles:['Composición propia'],name:'Objetivos - prueba - FC27',token:'test-proposal',active_objective_verified:false,squad:{formation:'4-3-3',rating:80,lineup:[],bench:[],composition_ready:true,checklist:[]}}]}
  if(path==='/objective-planning/save')return {id:91}
  throw new Error(path)
 })
 renderClub(<ObjectiveSquadsPage generator/> )
 await waitFor(()=>expect(screen.getByRole('button',{name:'Comparar plantillas propias'})).toBeEnabled())
 expect(await screen.findByText('Progreso: Desconocido')).toBeInTheDocument()
 fireEvent.click(screen.getByRole('button',{name:'Comparar plantillas propias'}))
 fireEvent.click(await screen.findByRole('button',{name:'Guardar alternativa A'}))
 expect(await screen.findByText(/Alternativa #91 guardada/)).toBeInTheDocument()
 expect(vi.mocked(api).mock.calls.some(([path])=>path.includes('/progress'))).toBe(false)
 expect(vi.mocked(api)).toHaveBeenCalledWith('/objective-planning/save',{method:'POST',body:JSON.stringify({token:'test-proposal',name:'Objetivos - prueba - FC27',protect:false})})
 window.location.hash=''
})
