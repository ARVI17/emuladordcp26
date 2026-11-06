import {expect,it} from 'vitest'
import {StableFrames} from './scan-sampler'

it('espera estabilidad y no envía páginas repetidas ni animaciones',()=>{
  const sampler=new StableFrames(),frame=(value:number)=>new Uint8ClampedArray(160*90*4).fill(value)
  expect(sampler.inspect(frame(20))).toBe(false)
  expect(sampler.inspect(frame(50))).toBe(false)
  expect(sampler.inspect(frame(51))).toBe(true)
  expect(sampler.inspect(frame(51))).toBe(false)
  expect(sampler.inspect(frame(52))).toBe(false)
  expect(sampler.inspect(frame(80))).toBe(false)
  expect(sampler.inspect(frame(80))).toBe(true)
  sampler.reset()
  expect(sampler.inspect(frame(80))).toBe(false)
  expect(sampler.inspect(frame(80))).toBe(true)
})

it('detecta un cambio pequeño de nombre aunque la mayoría de la página no cambie',()=>{
 const sampler=new StableFrames(),first=new Uint8ClampedArray(160*90*4).fill(255),second=first.slice()
 expect(sampler.inspect(first)).toBe(false);expect(sampler.inspect(first)).toBe(true)
 for(let y=30;y<36;y++)for(let x=80;x<86;x++)for(let c=0;c<3;c++)second[(y*160+x)*4+c]=0
 expect(sampler.inspect(second)).toBe(false);expect(sampler.inspect(second)).toBe(true)
})
