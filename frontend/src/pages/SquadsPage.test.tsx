import {fireEvent,screen,waitFor} from '@testing-library/react'
import {expect,it,vi} from 'vitest'
import {api} from '../api/client'
import {SquadsPage} from './SquadsPage'
import {player,renderClub} from '../test/helpers'

vi.mock('../api/client',async()=>({...await vi.importActual('../api/client'),api:vi.fn()}))
it('selecciona la formación por nombre accesible y guarda la edición y los puestos de la propuesta',async()=>{
  const positions=['POR','LD','DFC','DFC','LI','MCD','MC','MC','ED','DC','EI']
  const counts:Record<string,number>={}
  const bench=Array.from({length:7},(_,index)=>player({id:20+index,name:`Suplente ${index+1}`,game_version:'FC27'}))
  const lineup=positions.map((position,index)=>({slot:`${position}-${counts[position]=(counts[position]||0)+1}`,position,player:player({id:index+1,name:`Jugador ${index+1}`,game_version:'FC27',position}),fit_score:82,used_alternate_position:false,explanation:'Posición principal compatible.'}))
  vi.mocked(api).mockImplementation(async(path)=>{
    if(path==='/squads/formations')return {items:[{id:'4-3-3',name:'4-3-3',slots:lineup.map(({slot,position})=>({slot,position}))},{id:'4-4-2',name:'4-4-2',slots:[]}]}
    if(path==='/squads/recommend')return {game_version:'FC27',formation:'4-3-3',recommendation:true,simulation:true,complete:true,rating:82,chemistry:0,chemistry_approximate:true,players:lineup.map(item=>item.player),lineup,bench,gaps:[],warnings:[],explanations:['Se respetan las posiciones registradas.'],style:'balanced',eligible_count:18}
    if(path==='/squads')return {id:1}
    if(path.startsWith('/squads?'))return []
    throw new Error(path)
  })
  renderClub(<SquadsPage initialFormation="4-4-2"/>,'FC27')
  await waitFor(()=>expect(screen.getByRole('button',{name:'Proponer once y suplentes'})).toBeEnabled())
  const formation=screen.getByRole('combobox',{name:'Formación'})
  expect(formation).toHaveValue('4-4-2')
  fireEvent.change(formation,{target:{value:'4-3-3'}})
  expect(formation).toHaveValue('4-3-3')
  fireEvent.click(screen.getByRole('button',{name:'Proponer once y suplentes'}))
  await waitFor(()=>expect(vi.mocked(api)).toHaveBeenCalledWith('/squads/recommend',{method:'POST',body:JSON.stringify({formation:'4-3-3',style:'balanced',locked_player_ids:[],excluded_player_ids:[],bench_size:7,include_loans:true,avoid_main:false,include_unreviewed:false,use_alternate_positions:true})}))
  fireEvent.click(await screen.findByRole('button',{name:'Guardar plantilla'}))
  await waitFor(()=>expect(vi.mocked(api)).toHaveBeenCalledWith('/squads',{method:'POST',body:JSON.stringify({game_version:'FC27',name:'Mi equipo',formation:'4-3-3',player_ids:[...lineup.map(item=>item.player.id),...bench.map(p=>p.id)],slots:[...lineup.map(item=>item.slot),...bench.map((_,i)=>`BENCH-${i+1}`)]})}))
  expect(await screen.findByText('Plantilla guardada. Puedes proteger el equipo completo.')).toBeInTheDocument()
})
