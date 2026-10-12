import {fireEvent,screen} from '@testing-library/react'
import {it,expect,vi} from 'vitest'
import {renderClub} from '../test/helpers'
import {ConnectionsPage} from './ConnectionsPage'
it('explica la integración pendiente y exige elegir el registro local',()=>{
 const enter=vi.fn()
 renderClub(<ConnectionsPage busy={false} error={undefined} onEnter={enter}/>)
 expect(screen.getByRole('heading',{name:'Integración pendiente'})).toBeInTheDocument()
 expect(enter).not.toHaveBeenCalled()
 fireEvent.click(screen.getByRole('button',{name:'Abrir registro local'}))
 expect(enter).toHaveBeenCalledWith('local')
})
