import {fireEvent,screen,waitFor} from '@testing-library/react'
import {expect,it,vi} from 'vitest'
import {api} from '../api/client'
import {SquadsPage} from './SquadsPage'
import {player,renderClub} from '../test/helpers'

vi.mock('../api/client',async()=>({...await vi.importActual('../api/client'),api:vi.fn()}))
it('guarda la edición y los puestos exactos de la propuesta revisada',async()=>{
  const positions=['POR','LD','DFC','DFC','LI','MCD','MC','MC','ED','DC','EI']
  const counts:Record<string,number>={}
  const lineup=positions.map((position,index)=>({slot:`${position}-${counts[position]=(counts[position]||0)+1}`,position,player:player({id:index+1,name:`Jugador ${index+1}`,game_version:'FC26',position}),fit_score:82,used_alternate_position:false,explanation:'Posición principal compatible.'}))
  vi.mocked(api).mockImplementation(async(path)=>{
    if(path==='/squads/formations')return {items:[{id:'4-3-3',name:'4-3-3',slots:lineup.map(({slot,position})=>({slot,position}))}]}
    if(path==='/squads/recommend')return {game_version:'FC26',formation:'4-3-3',recommendation:true,simulation:true,complete:true,rating:82,chemistry:0,chemistry_approximate:true,players:lineup.map(item=>item.player),lineup,bench:[],gaps:[],warnings:[],explanations:['Se respetan las posiciones registradas.'],style:'balanced',eligible_count:11}
    if(path==='/squads')return {id:1}
    if(path.startsWith('/squads?'))return []
    throw new Error(path)
  })
  renderClub(<SquadsPage/>,'FC26')
  await waitFor(()=>expect(screen.getByRole('button',{name:'Proponer once y suplentes'})).toBeEnabled())
  fireEvent.click(screen.getByRole('button',{name:'Proponer once y suplentes'}))
  fireEvent.click(await screen.findByRole('button',{name:'Guardar plantilla'}))
  await waitFor(()=>expect(vi.mocked(api)).toHaveBeenCalledWith('/squads',{method:'POST',body:JSON.stringify({game_version:'FC26',name:'Mi equipo',formation:'4-3-3',player_ids:lineup.map(item=>item.player.id),slots:lineup.map(item=>item.slot)})}))
  expect(await screen.findByText('Plantilla guardada. Puedes proteger el equipo completo.')).toBeInTheDocument()
})
