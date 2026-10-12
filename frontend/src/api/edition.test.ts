import {expect,it} from 'vitest'
import {assertFC27} from './client'

it('rechaza cruces anidados antes de entregar datos a las vistas',()=>{
 expect(()=>assertFC27({items:[{game_version:'FC26',name:'Histórico'}]})).toThrow(/ajena a FC27/)
 expect(()=>assertFC27({snapshot:{players:[{game_version:'FC25'}]}})).toThrow()
 expect(()=>assertFC27({items:[{game_version:'FC27'}]})).not.toThrow()
})
