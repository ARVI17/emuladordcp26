import {describe,expect,it} from 'vitest'
import {imageCoordinates} from './screen'
describe('coordenadas de capturas contenidas',()=>{
  const rect={left:10,top:20,width:390,height:680}
  it('traduce el centro respetando bordes y bandas laterales',()=>expect(imageCoordinates(rect,1080,2400,205,360,3)).toEqual({x:540,y:1200}))
  it('no envía toques en la banda exterior de una imagen estrecha',()=>expect(imageCoordinates(rect,1080,2400,15,360,3)).toBeNull())
  it('no traduce una imagen todavía sin dimensiones',()=>expect(imageCoordinates(rect,0,0,50,50)).toBeNull())
})
