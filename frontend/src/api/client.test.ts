import { describe, expect, it } from 'vitest'
import { money, shortDate } from './client'

describe('formato local',()=>{
  it('formatea monedas sin perder el valor',()=>expect(money(325000).replace(/\D/g,'')).toBe('325000'))
  it('explica fechas ausentes',()=>expect(shortDate(null)).toBe('Sin vencimiento'))
})

import {errorDetail} from './client'
describe('errores de API comprensibles',()=>{
  it('conserva campo y mensaje de una validación 422',()=>{
    expect(errorDetail({detail:[{loc:['body','gallery_score'],msg:'Input should be a valid integer'}]},'Falló')).toBe('gallery_score: Input should be a valid integer')
  })
  it('expone el motivo y las restricciones de un rechazo del dominio',()=>{
    expect(errorDetail({detail:{message:'No se puede confirmar',violations:['Carta protegida','Edición diferente']}},'Falló')).toBe('No se puede confirmar. Carta protegida. Edición diferente')
  })
})

import {dateTimeInput} from './client'
import {vi} from 'vitest'
import {api} from './client'
it('envía píxeles binarios sin convertirlos en JSON ni multipart',async()=>{
 const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response('{}',{status:200,headers:{'Content-Type':'application/json'}}))
 const blob=new Blob(['synthetic'],{type:'image/png'})
 await api('/visual-scans/1/frames?sequence=1',{method:'POST',body:blob,headers:{'Content-Type':'image/png'}})
 const init=fetch.mock.calls[0][1]!
 expect(new Headers(init.headers).get('Content-Type')).toBe('image/png')
 expect(init.body).toBe(blob)
 fetch.mockRestore()
})
it('conserva la hora local al editar el vencimiento de una evolución',()=>{
  vi.spyOn(Date.prototype,'getTimezoneOffset').mockReturnValue(300)
  expect(dateTimeInput('2026-10-10T20:15:00Z')).toBe('2026-10-10T15:15')
})

it('muestra los campos del manejador 422 real de FastAPI',()=>{
  expect(errorDetail({detail:'Datos de entrada inválidos',errors:[{field:'body.gallery_score',message:'Debe ser un entero'}]},'Falló')).toBe('Datos de entrada inválidos. gallery_score: Debe ser un entero')
})
