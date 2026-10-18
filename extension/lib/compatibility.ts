import {endpoint,canonical} from './contracts'

export async function compatibility(base:string) {
  const origin=endpoint(base)
  const get=async(path:string)=>{
    const response=await fetch(origin+path,{credentials:'omit',redirect:'error',signal:AbortSignal.timeout(10000),headers:{'X-Reader-Extension':chrome.runtime.id}})
    if(!response.ok)throw Error(`No se pudo comprobar ${path}: HTTP ${response.status}. Destino conservado: ${origin}`)
    const text=await response.text()
    if(text.length>2000000)throw Error('Respuesta de compatibilidad demasiado grande')
    return JSON.parse(text)
  }
  const [front,back,spec]=await Promise.all([get('/build.json'),get('/api/build'),get('/api/openapi.json')])
  const synchronized=canonical(front)===canonical(back)&&back.edition==='FC27'&&typeof back.revision==='string'
  const reader=!!spec.paths?.['/reader/claim']?.post&&!!spec.paths?.['/reader/events']?.post
  const capabilities=spec.paths?.['/reader/capabilities']?.get?await get('/api/reader/capabilities'):null
  const version=capabilities?.protocol
  const supported=version===1&&capabilities.reader_versions?.includes('semantic-sample-1')&&capabilities.max_batch_records>=30
  return {origin,revision:String(back.revision).slice(0,64),synchronized,reader,
    compatible:synchronized&&reader&&supported,
    reason:!synchronized?'Frontend y API no corresponden a la misma compilación.':!reader?
      'Backend anterior al lector: no ofrece /reader. No es un fallo de acceso a EA. El inspector funciona sin emparejar.':
      !supported?'Backend sin capacidades compatibles; actualiza el backend antes de emparejar.':'Lector v1 disponible; la compatibilidad del DOM de EA sigue pendiente.',capabilities}
}
