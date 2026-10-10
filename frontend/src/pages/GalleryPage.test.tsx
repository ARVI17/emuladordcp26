import {fireEvent,screen,waitFor} from '@testing-library/react'
import {expect,it,vi} from 'vitest'
import {api} from '../api/client'
import {GalleryPage} from './GalleryPage'
import {renderClub} from '../test/helpers'

vi.mock('../api/client',async()=>({...await vi.importActual('../api/client'),api:vi.fn()}))
it('mantiene visible la carta histórica y deja sus puntos desconocidos sin inventarlos',async()=>{
  vi.mocked(api).mockImplementation(async(path)=>{
    if(path==='/gallery/record-inventory')return {created:0,updated:1,message:'Historial comprobado'}
    if(path.startsWith('/gallery/entries'))return {items:[{id:1,item_key:'base-1',game_version:'FC27',player_id:null,name:'Carta consumida',rating:82,position:'MC',league:'Liga',club:'Club',nationality:'Colombia',card_type:'Oro',is_holographic:false,gallery_score:null,recorded_at:'2026-10-10',owned:false,current_player_ids:[]}],total:1}
    if(path.startsWith('/gallery/sets'))return []
    if(path.startsWith('/gallery?'))return {game_version:'FC27',entries_count:1,eligible_owned_count:0,unrecorded_count:0,excluded_loans:0,unresolved_evolutions:0,sets:[],message:''}
    throw new Error(path)
  })
  renderClub(<GalleryPage/>)
  expect(await screen.findByText('Carta consumida')).toBeInTheDocument()
  expect(screen.getByText('En el historial')).toBeInTheDocument()
  expect(screen.getByLabelText('Puntos observados')).toHaveValue(null)
  fireEvent.click(screen.getByRole('button',{name:'Registrar mi colección'}))
  await waitFor(()=>expect(vi.mocked(api)).toHaveBeenCalledWith('/gallery/record-inventory',{method:'POST',body:'{}'}))
  expect(await screen.findByText('Historial comprobado')).toBeInTheDocument()
})
