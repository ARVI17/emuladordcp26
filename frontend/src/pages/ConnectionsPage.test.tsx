import {fireEvent,screen} from '@testing-library/react'
import {it,expect,vi} from 'vitest'
import {renderClub} from '../test/helpers'
import {ConnectionsPage} from './ConnectionsPage'
it('explica la integración pendiente y exige elegir el registro local',()=>{
 const enter=vi.fn()
 renderClub(<ConnectionsPage busy={false} error={undefined} onEnter={enter}/>)
 expect(screen.getByRole('heading',{name:'Integración pendiente'})).toBeInTheDocument()
 expect(enter).not.toHaveBeenCalled()
 expect(screen.getByRole('link',{name:'Abrir acceso oficial a FC27 ↗'})).toHaveAttribute('href','https://www.ea.com/es-es/ea-sports-fc/ultimate-team/web-app/')
 fireEvent.click(screen.getByRole('button',{name:'Seleccionar pestaña de FC27'}))
 expect(screen.getByText(/El inspector funciona aunque/)).toBeInTheDocument()
 expect(screen.getByText('No vinculada')).toBeInTheDocument()
 expect(screen.getByText('No sincronizados')).toBeInTheDocument()
 expect(screen.getByText('Progreso sin consultar')).toBeInTheDocument()
 expect(screen.queryByRole('button',{name:'Comprobar conexión'})).not.toBeInTheDocument()
 fireEvent.click(screen.getByRole('button',{name:'Abrir registro local'}))
 expect(enter).toHaveBeenCalledWith('local')
})
