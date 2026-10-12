import {afterEach,expect,it,vi} from 'vitest'
import {shareTab,stopTracks,captureFrame} from './capture'
afterEach(()=>vi.unstubAllGlobals())
it('solicita permiso cada vez, nunca audio, y detiene todas las pistas al cerrar',async()=>{
 const stop=vi.fn(),track={stop,getSettings:()=>({displaySurface:'browser'})},stream={getTracks:()=>[track],getVideoTracks:()=>[track],getAudioTracks:()=>[]}
 const getDisplayMedia=vi.fn().mockResolvedValue(stream)
 vi.stubGlobal('navigator',{mediaDevices:{getDisplayMedia}})
 const first=await shareTab();await shareTab();expect(getDisplayMedia).toHaveBeenCalledTimes(2)
 expect(getDisplayMedia).toHaveBeenCalledWith({video:{displaySurface:'browser'},audio:false})
 stopTracks(first);expect(stop).toHaveBeenCalledOnce()
})
it('no sustituye un permiso denegado por otra captura',async()=>{
 const getDisplayMedia=vi.fn().mockRejectedValue(new DOMException('Denied','NotAllowedError'))
 vi.stubGlobal('navigator',{mediaDevices:{getDisplayMedia}})
 await expect(shareTab()).rejects.toMatchObject({name:'NotAllowedError'})
 expect(getDisplayMedia).toHaveBeenCalledOnce()
})
it('ofrece captura adjunta si no existe la API y rechaza una pantalla completa',async()=>{
 vi.stubGlobal('navigator',{})
 await expect(shareTab()).rejects.toThrow('Adjunta una captura')
 const stop=vi.fn(),track={stop,getSettings:()=>({displaySurface:'monitor'})}
 vi.stubGlobal('navigator',{mediaDevices:{getDisplayMedia:async()=>({getTracks:()=>[track],getVideoTracks:()=>[track],getAudioTracks:()=>[]})}})
 await expect(shareTab()).rejects.toThrow('Selecciona una pestaña')
 expect(stop).toHaveBeenCalledOnce()
})
it('no produce imágenes de una pista todavía vacía',async()=>{
 await expect(captureFrame(document.createElement('video'))).rejects.toThrow('Espera a que aparezca')
})
