import { describe, expect, it } from 'vitest'
import { money, shortDate } from './client'

describe('formato local',()=>{
  it('formatea monedas sin perder el valor',()=>expect(money(325000).replace(/\D/g,'')).toBe('325000'))
  it('explica fechas ausentes',()=>expect(shortDate(null)).toBe('Sin vencimiento'))
})
