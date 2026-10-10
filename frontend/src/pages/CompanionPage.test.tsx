import {fireEvent,screen,waitFor} from '@testing-library/react'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {api} from '../api/client'
import {CompanionPage} from './CompanionPage'
import {renderClub} from '../test/helpers'
import type {InventoryScan} from '../types'

vi.mock('../api/client',async()=>({...await vi.importActual('../api/client'),api:vi.fn()}))
const mocked=vi.mocked(api)
const scan:InventoryScan={id:1,status:'review',device_serial:'local-device',screen_size:[1080,2400],captured_pages:1,candidates:[],imported_player_ids:[],imported_count:0,last_error:null,confirmation_phrase:'IMPORTAR 1',archive_demo_phrase:'ARCHIVAR DEMO',images_saved:false,requires_review:true,created_at:'2026-10-10',imported_at:null,game_version:'FC27',is_active:true,can_capture:true,can_continue:false}
function responses(active:InventoryScan){mocked.mockImplementation(async(path)=>{
  if(path==='/emulator/status')return {enabled:true,available:true,devices:[{serial:'local-device',state:'device',details:''}],config:{serial:'local-device'},message:null}
  if(path.startsWith('/emulator/plans'))return []
  if(path==='/emulator/scans/1/cancel')return {...active,status:'cancelled',is_active:false,can_capture:false}
  if(path.startsWith('/emulator/scans?'))return [active]
  throw new Error(`Ruta inesperada: ${path}`)
})}
beforeEach(()=>{mocked.mockReset()})
describe('revisión de inventario Companion',()=>{
  it('permite iniciar otra lectura inmediatamente después de cancelar',async()=>{
    responses(scan);renderClub(<CompanionPage/>)
    const cancel=await screen.findByRole('button',{name:'Cancelar lectura'})
    expect(screen.getByRole('button',{name:'Nueva lectura'})).toBeDisabled()
    fireEvent.click(cancel)
    await waitFor(()=>expect(screen.getByRole('button',{name:'Nueva lectura'})).toBeEnabled())
    expect(screen.queryByRole('button',{name:'Cancelar lectura'})).not.toBeInTheDocument()
  })
  it('deja la media desconocida vacía e impide seleccionar cartas sin revisar',async()=>{
    responses({...scan,candidates:[{candidate_id:1,name:'Jugador leído',rating:null,position:'',source_page:1,confidence:{}}]})
    renderClub(<CompanionPage/>)
    const edit=await screen.findByRole('button',{name:'Revisar carta'})
    expect(screen.getByLabelText('Seleccionar para importar')).toBeDisabled()
    fireEvent.click(edit)
    expect(screen.getByLabelText('Media')).toHaveValue(null)
    expect(screen.getByLabelText('Posición principal')).toHaveValue('')
    expect(screen.getByLabelText('Liga')).toHaveValue('')
    expect(screen.getByLabelText('Club')).toHaveValue('')
    expect(screen.getByRole('button',{name:'Importar inventario revisado'})).toBeDisabled()
  })
  it('permite avanzar desde la primera página heredada de un lote continuado',async()=>{
    responses({...scan,id:2,captured_pages:0,source_scan_id:1,can_capture:true})
    renderClub(<CompanionPage/>)
    expect(await screen.findByRole('button',{name:'Avanzar y leer siguiente'})).toBeEnabled()
  })
  it('respeta el límite de captura aunque ya se hayan importado candidatos',async()=>{
    responses({...scan,candidates:[],captured_pages:8,can_capture:false,can_continue:true})
    renderClub(<CompanionPage/>)
    expect(await screen.findByRole('button',{name:'Avanzar y leer siguiente'})).toBeDisabled()
    expect(screen.getByRole('button',{name:'Leer página actual'})).toBeDisabled()
    expect(screen.getByRole('button',{name:'Continuar en otro lote'})).toBeEnabled()
  })
})
