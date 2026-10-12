import {screen,fireEvent} from '@testing-library/react'
import {expect,it,vi} from 'vitest'
import {renderClub,player} from '../test/helpers'
import {ObservedPreferences} from './ObservedPreferences'
import {PlayerCard} from './PlayerCard'

it('separa los hechos observados de las preferencias y los datos desconocidos',()=>{
 const p=player({ownership_source:'observed',observed_at:'2026-10-12T12:00:00Z',metadata_pending:['chemistry','rare'],price:null})
 const save=vi.fn()
 renderClub(<><PlayerCard player={p}/><ObservedPreferences player={p} onSave={save} onCancel={()=>{}} pending={false} error={null}/></>)
 expect(screen.getByText(/Copia observada/)).toBeInTheDocument()
 expect(screen.getByText(/Química no disponible/)).toBeInTheDocument()
 expect(screen.queryByLabelText('Media')).not.toBeInTheDocument()
 fireEvent.change(screen.getByLabelText('Notas propias'),{target:{value:'Para mi alternativa'}})
 fireEvent.click(screen.getByRole('button',{name:'Guardar preferencias'}))
 expect(save).toHaveBeenCalledWith({notes:'Para mi alternativa',favorite:false,price:null})
})
