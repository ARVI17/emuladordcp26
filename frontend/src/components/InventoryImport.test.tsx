import {act,fireEvent,screen,waitFor} from '@testing-library/react'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {api} from '../api/client'
import {InventoryImport} from './InventoryImport'
import {deferred,player,renderClub} from '../test/helpers'
import type {ImportPreview} from '../types'

vi.mock('../api/client',async()=>({...await vi.importActual('../api/client'),api:vi.fn()}))
const mocked=vi.mocked(api)
const preview=(name:string,token:string):ImportPreview=>({total:1,preview:[{...player({name}),tradable:false,is_loan:false,is_evolution:false}],requires_confirmation:true,content_hash:`hash-${token}`,preview_token:token})
const select=(file:File)=>fireEvent.change(screen.getByLabelText('CSV o Excel'),{target:{files:[file]}})
function open(){renderClub(<InventoryImport/>);fireEvent.click(screen.getByText('Importar y exportar inventario'))}
beforeEach(()=>{mocked.mockReset()})

describe('importación vinculada a la revisión',()=>{
  it('descarta una revisión tardía cuando se selecciona otro archivo',async()=>{
    const first=deferred<ImportPreview>()
    mocked.mockReturnValueOnce(first.promise)
    open()
    select(new File(['A'],'A.csv',{type:'text/csv'}))
    fireEvent.click(screen.getByRole('button',{name:'Revisar archivo'}))
    await waitFor(()=>expect(mocked).toHaveBeenCalledTimes(1))
    select(new File(['B'],'B.csv',{type:'text/csv'}))
    await act(async()=>first.resolve(preview('Carta A','token-A')))
    expect(screen.queryByRole('button',{name:'Confirmar importación'})).not.toBeInTheDocument()
    expect(screen.queryByText('Carta A')).not.toBeInTheDocument()
    mocked.mockResolvedValueOnce(preview('Carta B','token-B'))
    fireEvent.click(screen.getByRole('button',{name:'Revisar archivo'}))
    expect(await screen.findByText('Carta B')).toBeInTheDocument()
  })
  it('envía el mismo archivo y token una sola vez aun con dos clics seguidos',async()=>{
    const importing=deferred<{imported:number}>()
    mocked.mockResolvedValueOnce(preview('Carta A','verified-token')).mockReturnValueOnce(importing.promise)
    open()
    const file=new File(['contenido A'],'A.csv',{type:'text/csv'})
    select(file)
    fireEvent.click(screen.getByRole('button',{name:'Revisar archivo'}))
    const button=await screen.findByRole('button',{name:'Confirmar importación'})
    act(()=>{button.click();button.click()})
    await waitFor(()=>expect(mocked).toHaveBeenCalledTimes(2))
    const body=mocked.mock.calls[1][1]?.body as FormData
    expect(body.get('file')).toBe(file)
    expect(body.get('preview_token')).toBe('verified-token')
    expect(body.get('confirm')).toBe('true')
    expect(screen.getByLabelText('CSV o Excel')).toBeDisabled()
    await act(async()=>importing.resolve({imported:1}))
    expect(await screen.findByText('Activadas: 1. En cuarentena: 0. Las pendientes no participan en el club.')).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Confirmar importación'})).not.toBeInTheDocument()
  })
  it('explica una repetición idempotente sin anunciar nuevas cartas',async()=>{
    mocked.mockResolvedValueOnce(preview('Carta A','token')).mockResolvedValueOnce({imported:0,already_imported:true,original_imported:1})
    open();select(new File(['A'],'A.csv'))
    fireEvent.click(screen.getByRole('button',{name:'Revisar archivo'}))
    fireEvent.click(await screen.findByRole('button',{name:'Confirmar importación'}))
    expect(await screen.findByText(/Este lote ya estaba importado.*No se duplicó/)).toBeInTheDocument()
  })
})
