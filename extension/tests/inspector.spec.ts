import {test,expect,chromium} from '@playwright/test'
import http from 'node:http'
import path from 'node:path'
import {eaDiagnostic,admitted} from '../lib/contracts'
import {viewProfile} from '../lib/view-profile'

test('compiled inspector: private bounded maps, no forms or clicks; old backend and explicit destination',async()=>{
 let posted=0
 const server=http.createServer((req,res)=>{
  if(req.method==='POST')posted++
  if(req.url==='/reader-sample.html'){
   res.setHeader('Content-Type','text/html; charset=utf-8')
   res.end('<main><section class="card-list"><h2>Club</h2><article class="card"><span>Jugador de prueba</span><span>88</span><img alt="No recoger URL" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"><canvas></canvas><span hidden>SECRETO OCULTO</span><span>Bearer no-exportar</span><form><input value="NO LEER FORMULARIO"><label>Dato privado</label></form></article><button onclick="window.clicked=true">Continuar</button><div class="card">Otra carta</div></section></main>');return
  }
  res.setHeader('Content-Type','application/json')
  if(req.url==='/build.json'||req.url==='/api/build'){res.end(JSON.stringify({edition:'FC27',revision:'old-build'}));return}
  if(req.url==='/api/openapi.json'){res.end('{"paths":{}}');return}
  res.statusCode=404;res.end('{}')
 })
 await new Promise<void>(r=>server.listen(8090,'127.0.0.1',r))
 const extension=path.resolve('.output/chrome-mv3')
 const context=await chromium.launchPersistentContext('',{channel:'chromium',headless:true,args:[`--disable-extensions-except=${extension}`,`--load-extension=${extension}`]})
 try{
  const worker=context.serviceWorkers()[0]||await context.waitForEvent('serviceworker')
  const id=new URL(worker.url()).hostname
  const panel=await context.newPage();await panel.goto(`chrome-extension://${id}/sidepanel.html`)
  const send=(kind:string,extra={})=>panel.evaluate(m=>chrome.runtime.sendMessage(m),{kind,...extra})
  expect((await send('status')).base).toBe('http://localhost:8090')
  expect((await send('check',{base:'http://127.0.0.1:8090'})).ok).toBe(true)
  const checked=await send('status');expect(checked.compatibility.reader).toBe(false)
  expect(checked.compatibility.reason).toContain('Backend anterior')
  expect(checked.base).toBe('http://localhost:8090')
  expect((await send('pair',{base:'http://127.0.0.1:8090',pairing_id:crypto.randomUUID(),code:'123456'})).error).toContain('Confirma')
  expect(posted).toBe(0)
  // A valid old preference survives refresh and explicit disconnect.
  await worker.evaluate(async()=>{const {state}=await chrome.storage.local.get('state');await chrome.storage.local.set({state:{...state,base:'http://localhost:8080'}})})
  await panel.reload();await expect(panel.locator('#base')).toHaveValue('http://localhost:8080')
  expect((await send('disconnect')).ok).toBe(true);expect((await send('status')).base).toBe('http://localhost:8080')
  const page=await context.newPage();await page.goto('http://127.0.0.1:8090/reader-sample.html');await page.bringToFront()
  const select=()=>page.evaluate(()=>{const range=document.createRange();range.selectNodeContents(document.querySelector('h2')!);const s=getSelection()!;s.removeAllRanges();s.addRange(range)})
  await select();expect((await send('recognize',{view:'inventory'})).ok).toBe(true)
  let maps=(await send('status')).maps
  expect(maps).toHaveLength(1);expect(maps[0].profile.evidence_origin).toBe('local_region_map')
  expect(viewProfile.safeParse(maps[0].profile).success).toBe(true)
  expect(maps[0].profile.extraction_enabled).toBe(false)
  const encoded=JSON.stringify(maps)
  for(const secret of ['SECRETO OCULTO','NO LEER FORMULARIO','Dato privado','Bearer no-exportar','data:image','outerHTML'])expect(encoded).not.toContain(secret)
  expect(maps[0].map.navigation_candidates[0].approved).toBe(false)
  expect(maps[0].map.nodes.some((n:any)=>n.medium==='canvas')).toBe(true)
  expect(maps[0].map.nodes.some((n:any)=>n.matches>1)).toBe(true)
  expect(await page.evaluate(()=>(window as any).clicked)).toBeUndefined()
  const signature=maps[0].profile.structure_hash
  await page.locator('article span').first().evaluate(el=>el.textContent='Nombre cambiado')
  await select();expect((await send('recognize',{view:'detail'})).ok).toBe(true)
  maps=(await send('status')).maps;expect(maps[1].profile.structure_hash).toBe(signature)
  await page.locator('section').evaluate(el=>{const input=document.createElement('input');input.type='password';el.append(input)})
  await select();expect((await send('recognize',{view:'account'})).error).toContain('reconocimiento detenido')
  expect((await send('status')).maps).toHaveLength(2)
  expect((await send('delete-maps')).ok).toBe(true);expect((await send('status')).maps).toEqual([])
  expect(posted).toBe(0)
  await panel.setViewportSize({width:390,height:844})
  expect(await panel.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  await panel.screenshot({path:'test-results/inspector-panel.png',fullPage:true})
 }finally{await context.close();await new Promise<void>(r=>server.close(()=>r()))}
})

test('production URL policy never enables EA as a sample or an auth surface',()=>{
 const official='https://www.ea.com/es-es/ea-sports-fc/ultimate-team/web-app/'
 expect(eaDiagnostic(official)).toBe(true);expect(admitted(official)).toBe(false)
 expect(eaDiagnostic(official+'#/club')).toBe(true)
 for(const url of [official+'?token=secret',official+'#login',official+'#token=abc',official+'#access_token_abc',official+'#%74oken=abc',official+'#a@b.com',official.replace('www.ea.com','www.ea.com.evil.test'),'https://accounts.ea.com/login'])expect(eaDiagnostic(url)).toBe(false)
})
