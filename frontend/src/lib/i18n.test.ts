import {afterEach,describe,expect,it} from 'vitest'
import {currentPage,sections} from './navigation'
import {inputInstant,observedDate,setTimeZone,zonedInput} from './i18n'
afterEach(()=>localStorage.clear())
describe('rutas y fecha colombiana',()=>{
 it('resuelve todas las secciones y conserva alias anteriores',()=>{
  for(const [id,section] of Object.entries(sections))expect(currentPage('#/'+section.path)).toBe(id)
  expect(currentPage('#/plantillas')).toBe('plantillas')
  expect(currentPage('#/desconocida')).toBe('inicio')
 })
 it('conserva UTC entre formulario y presentación sin usar la zona del navegador',()=>{
  expect(inputInstant('2026-10-12T09:30')).toBe('2026-10-12T14:30:00.000Z')
  expect(zonedInput('2026-10-12T14:30:00Z')).toBe('2026-10-12T09:30')
  setTimeZone('Europe/Madrid')
  expect(zonedInput('2026-10-12T14:30:00Z')).toBe('2026-10-12T16:30')
  expect(inputInstant('2026-10-12T16:30')).toBe('2026-10-12T14:30:00.000Z')
  expect(observedDate(null)).toBe('Sin consultar')
 })
 it('rechaza la hora inexistente de un cambio de horario',()=>{
  setTimeZone('America/New_York')
  expect(()=>inputInstant('2026-03-08T02:30')).toThrow('Esta hora no existe')
 })
})
