import {test,expect} from '@playwright/test'
import {createServer,request,type Server} from 'node:http'

// An actual loopback origin exercises the same secure-context boundary as the host.
const isolated=process.env.PLAYWRIGHT_DISPOSABLE_DB==='1'
test.use(isolated?{baseURL:'http://127.0.0.1:8082'}:{})
let proxy:Server|undefined
test.beforeAll(async()=>{
  if(!isolated)return
  proxy=createServer((incoming,outgoing)=>{
    const upstream=request(new URL(incoming.url!,process.env.PLAYWRIGHT_BASE_URL!),{method:incoming.method,headers:incoming.headers},response=>{outgoing.writeHead(response.statusCode!,response.headers);response.pipe(outgoing)})
    upstream.on('error',()=>{outgoing.writeHead(502);outgoing.end()});incoming.pipe(upstream)
  })
  await new Promise<void>(resolve=>proxy!.listen(8082,'127.0.0.1',resolve))
})
test.afterAll(async()=>{if(proxy){proxy.closeAllConnections();await new Promise<void>(resolve=>proxy!.close(()=>resolve()))}})

test('pestaña sintética: estabilidad, scroll solapado, correcciones, snapshot y parada',async({page},info)=>{
  test.skip(process.env.PLAYWRIGHT_DISPOSABLE_DB!=='1','Requiere PostgreSQL desechable.')
  test.skip(info.project.name!=='Escritorio Chromium','La pista de canvas se prueba en Chromium de escritorio.')
  test.setTimeout(120000)
  await page.goto('/#/cuenta')
  await page.getByLabel('Nombre para un nuevo contexto de lectura').fill(`Escaneo ${Date.now()}`)
  await page.getByRole('button',{name:'Iniciar lectura asistida en otro contexto'}).click()
  const scanner=page.locator('.visual-scanner')
  await expect(scanner.getByRole('heading',{name:'Escanear mi club',exact:true})).toBeVisible()
  await page.evaluate(()=>{
    const canvas=document.createElement('canvas');canvas.width=1100;canvas.height=650
    const ctx=canvas.getContext('2d')!
    const state=window as unknown as {paint:(start:number)=>void;sharedTrack?:MediaStreamTrack;shareCalls:number}
    state.shareCalls=0
    const names=['Alfa','Bravo','Charlie','Delta','Eco','Foxtrot','Golf','Hotel','India','Julieta','Kilo','Lima']
    state.paint=start=>{ctx.fillStyle='white';ctx.fillRect(0,0,1100,650);ctx.fillStyle='black';ctx.font='32px monospace';ctx.fillText('FC27 Mi club',30,50);for(let i=0;i<8;i++)ctx.fillText(`84 MC Carta ${names[i+start]}`,30,110+i*60)}
    state.paint(0)
    Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{getDisplayMedia:async()=>{state.shareCalls++;const stream=canvas.captureStream(5);const track=stream.getVideoTracks()[0];state.sharedTrack=track;const pump=setInterval(()=>{if(track.readyState==='ended')clearInterval(pump);else ctx.drawImage(canvas,0,0)},200);return stream}}})
  })
  await expect(scanner.getByRole('button',{name:'Compartir pestaña y comenzar escaneo'})).toBeDisabled()
  expect(await page.evaluate(()=>(window as any).shareCalls)).toBe(0)
  await scanner.getByLabel('Autorizo el procesamiento visual local de las pantallas que comparta').check()
  await scanner.getByRole('button',{name:'Compartir pestaña y comenzar escaneo'}).click()
  await expect(scanner.getByText('Cartas candidatas únicas: 8')).toBeVisible({timeout:30000})
  await page.evaluate(()=>(window as any).paint(4))
  await expect(scanner.getByText('Cartas candidatas únicas: 12')).toBeVisible({timeout:30000})
  await scanner.getByRole('button',{name:'Detener escaneo',exact:true}).click()
  expect(await page.evaluate(()=>(window as any).sharedTrack.readyState)).toBe('ended')
  await expect(scanner.locator('.scan-review-card')).toHaveCount(12)
  await scanner.locator('.scan-review-card').nth(0).getByLabel('Nombre',{exact:true}).fill('Futbolista Alfa corregido')
  await scanner.locator('.scan-review-card').nth(1).getByLabel('Media',{exact:true}).fill('85')
  for(const checkbox of await scanner.getByRole('checkbox',{name:/^Incluir /}).all())await checkbox.check()
  await scanner.getByLabel('Revisé FC27, propiedad, variantes y que las observaciones agrupadas representan la misma copia').check()
  await scanner.getByLabel('Escribe GUARDAR SINCRONIZACION').fill('GUARDAR SINCRONIZACION')
  await scanner.getByRole('button',{name:'Guardar sincronización',exact:true}).click()
  await expect(scanner.getByText(/Snapshot #\d+: 12 cartas nuevas/)).toBeVisible()
  await scanner.getByRole('heading',{name:'Escanear mi club',exact:true}).scrollIntoViewIfNeeded()
  await page.screenshot({path:info.outputPath('escaneo-revisado.png')})
  // A fresh share requires another explicit gesture; internal navigation stops it.
  await scanner.getByRole('button',{name:'Compartir pestaña y comenzar escaneo'}).click()
  await expect(scanner.getByText(/Escaneando · Captura activa/)).toBeVisible()
  await page.evaluate(()=>{window.location.hash='/club'})
  await expect.poll(()=>page.evaluate(()=>(window as any).sharedTrack.readyState)).toBe('ended')
  expect(await page.evaluate(()=>(window as any).shareCalls)).toBe(2)
})

test('sin permiso: captura pendiente y diseño móvil sin desbordamiento',async({page})=>{
  test.skip(process.env.PLAYWRIGHT_DISPOSABLE_DB!=='1','Requiere PostgreSQL desechable.')
  await page.goto('/#/cuenta')
  await page.getByLabel('Nombre para un nuevo contexto de lectura').fill(`Permiso ${Date.now()}`)
  await page.getByRole('button',{name:'Iniciar lectura asistida en otro contexto'}).click()
  const scanner=page.locator('.visual-scanner')
  await page.evaluate(()=>Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{getDisplayMedia:async()=>{throw new DOMException('Denied','NotAllowedError')}}}))
  await scanner.getByLabel('Autorizo el procesamiento visual local de las pantallas que comparta').check()
  await scanner.getByRole('button',{name:'Compartir pestaña y comenzar escaneo'}).click()
  await expect(scanner.getByText('Permiso cancelado. El escaneo sigue pendiente; no se inició otra captura.')).toBeVisible()
  await expect(scanner.getByText('Escaneo pendiente · Captura inactiva')).toBeVisible()
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true)
  await scanner.getByRole('heading',{name:'Escanear mi club',exact:true}).scrollIntoViewIfNeeded()
  await page.screenshot({path:test.info().outputPath('escaneo-sin-permiso.png')})
})
