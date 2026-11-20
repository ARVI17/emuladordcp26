import {test,expect,chromium} from '@playwright/test'
import http from 'node:http'
import path from 'node:path'

// Controlled local fixture only. No EA session, selectors, credentials or data.
const positions=['POR','LD','DFC','DFC','LI','MC','MC','MC','ED','DC','EI']
const slots=['POR-1','LD-1','DFC-1','DFC-2','LI-1','MC-1','MC-2','MC-3','ED-1','DC-1','EI-1']
const cards=(squad=false)=>Array.from({length:squad?18:20},(_,i)=>`<article data-card><span data-field="name">Prueba veinte ${i}</span><span data-field="rating">88</span><span data-field="position">${positions[i%11]}</span><span data-field="card_type">Oro</span><span data-field="is_loan">No</span><span data-field="is_evolution">No</span><span data-field="tradable">No</span>${squad?`<span data-field="slot">${i<11?slots[i]:`BENCH-${i-10}`}</span>`:''}</article>`).join('')
const markup=()=>`<!doctype html><html lang="es"><body><main><section class="cards" data-club-lab-sample="1" data-edition="FC27" data-source="synthetic_dom" data-view="inventory" data-page="1" data-context-label="first20-synthetic"><h2>MUESTRA SINTÉTICA · 20 cartas</h2><div class="rows">${cards()}</div></section></main></body></html>`

test('first 20: repeated transport and fresh reads preserve copy IDs; explicit XI + 7 remain protected',async()=>{
 test.setTimeout(180000)
 const server=http.createServer(async(req,res)=>{
  if(req.url==='/reader-sample.html'){res.setHeader('Content-Type','text/html; charset=utf-8');res.end(markup());return}
  const chunks:Buffer[]=[];for await(const chunk of req)chunks.push(Buffer.from(chunk))
  const forwarded=Object.fromEntries(Object.entries(req.headers).filter(([,v])=>typeof v==='string')) as Record<string,string>
  const upstream=http.request((process.env.READER_TEST_UPSTREAM||'http://nginx')+req.url,{method:req.method,headers:{...forwarded,host:'localhost:8090'}},response=>{
   res.writeHead(response.statusCode||502,response.headers);response.pipe(res)
  })
  upstream.on('error',()=>{res.statusCode=502;res.end('{}')});upstream.end(Buffer.concat(chunks))
 })
 await new Promise<void>(resolve=>server.listen(8090,'127.0.0.1',resolve))
 const extension=path.resolve('.output/chrome-mv3'),base='http://localhost:8090'
 const context=await chromium.launchPersistentContext('',{channel:'chromium',headless:true,args:[`--disable-extensions-except=${extension}`,`--load-extension=${extension}`]})
 try{
  const worker=context.serviceWorkers()[0]||await context.waitForEvent('serviceworker')
  const extensionId=new URL(worker.url()).hostname,panel=await context.newPage()
  const panelErrors:string[]=[];panel.on('pageerror',error=>panelErrors.push(error.message))
  await panel.goto(`chrome-extension://${extensionId}/sidepanel.html`)
  const send=(kind:string,extra={})=>panel.evaluate(m=>chrome.runtime.sendMessage(m),{kind,...extra})
  const session=await (await context.request.post(base+'/api/app/session')).json()
  const headers={'X-CSRF-Token':session.csrf_token,'X-App-Entry':''}
  const request=async(route:string,data?:unknown)=>{
   const response=data===undefined?await context.request.get(base+'/api'+route,{headers}):await context.request.post(base+'/api'+route,{headers,data})
   expect(response.ok(),`${route}: ${await response.text()}`).toBe(true)
   return response.json()
  }
  const local=await request('/app/entries',{nonce:crypto.randomUUID(),mode:'local'});headers['X-App-Entry']=String(local.entry_id)
  const club=await request('/assisted/contexts',{name:'Primeras veinte SINTÉTICAS '+crypto.randomUUID(),phrase:'INICIAR LECTURA ASISTIDA'})
  const entry=await request('/app/entries',{nonce:crypto.randomUUID(),mode:'assisted',context_id:club.id});headers['X-App-Entry']=String(entry.entry_id)
  const pairing=await request('/reader/pairings',{extension_id:extensionId,confirmation:'EMPAREJAR LECTOR'})
  expect((await send('pair',{base,pairing_id:pairing.pairing_id,code:pairing.code})).ok).toBe(true)
  const page=await context.newPage();await page.goto(base+'/reader-sample.html');await page.bringToFront()
  const begin=await send('analyze-club');expect(begin.ok,begin.error).toBe(true)
  // A pending report must render without throwing, including absent results.
  await expect(panel.locator('#status')).toContainText('Emparejado')
  await expect(panel.locator('#workflow-results')).toContainText('Todavía no hay cartas admitidas')
  expect((await request('/players')).total).toBe(0)
  const first=(await request('/reader/status')).observations[0]
  expect(first.count).toBe(20);expect(first.source_kind).toBe('synthetic_dom')
  const review=(id:string)=>request(`/reader/observations/${id}/review`,{confirmation:'REVISAR OBSERVACION DOM',context_confirmed:true})
  await review(first.observation_id)
  const original=await request('/players'),ids=original.items.map((p:any)=>p.id).sort((a:number,b:number)=>a-b)
  expect(original.total).toBe(20);expect(new Set(ids).size).toBe(20)
  // No main squad is inferred from list order, ratings or the first eighteen.
  expect((await request('/squads/main')).identified).toBe(false)
  const observed=new Set([first.observation_id])
  for(let pass=1;pass<=2;pass++){
   // Same page reactivation reuses its receipt; changed page forces a NEW read.
   expect((await send('analyze-club')).ok).toBe(true)
   expect((await request('/reader/status')).observations).toHaveLength(observed.size)
   await page.locator('section').evaluate((el,n)=>el.setAttribute('data-page',String(n)),pass+1)
   await expect.poll(async()=>(await request('/reader/status')).observations.length,{timeout:20000}).toBe(observed.size+1)
   const fresh=(await request('/reader/status')).observations.find((o:any)=>!observed.has(o.observation_id))
   observed.add(fresh.observation_id)
   const saved=await review(fresh.observation_id)
   expect(saved.reused_copies).toBe(20);expect(saved.pending_records).toEqual([])
   const replay=await review(fresh.observation_id)
   expect(replay.reading_ids).toEqual(saved.reading_ids)
   const inventory=await request('/players')
   expect(inventory.total).toBe(20)
   expect(inventory.items.map((p:any)=>p.id).sort((a:number,b:number)=>a-b)).toEqual(ids)
  }
  // Refresh real calculated results through the worker, not a mocked panel.
  expect((await send('analyze-club')).ok).toBe(true)
  const report=(await send('status')).workflow.report
  expect(report.modules.squads.result.groups.length).toBeGreaterThan(0)
  await expect(panel.locator('#workflow-results')).toContainText('Prueba veinte')
  await expect(panel.locator('#workflow-results')).toContainText('SINTÉTICAS')
  expect(panelErrors).toEqual([])
  // Explicit squad evidence has eleven positions and SEVEN different bench IDs.
  await page.locator('section').evaluate((el,rows)=>{
   el.setAttribute('data-view','squad');el.setAttribute('data-page','principal-18')
   el.querySelector('.rows')!.innerHTML=rows
  },cards(true))
  await expect.poll(async()=>(await request('/reader/status')).observations.filter((o:any)=>o.domain==='squad').length,{timeout:20000}).toBe(1)
  const squad=(await request('/reader/status')).observations.find((o:any)=>o.domain==='squad')
  const squadReview=await review(squad.observation_id)
  expect(squadReview.reused_copies).toBe(18);expect(squadReview.pending_records).toEqual([])
  const before=await request('/squads/main');expect(before.identified).toBe(false)
  const main=await request('/assisted/main',{reading_ids:squadReview.reading_ids,formation:'4-3-3',complete:true,expected_hash:before.state_hash,phrase:'REGISTRAR MI PRINCIPAL'})
  expect(main.complete).toBe(true);expect(main.protected_copy_ids).toHaveLength(18)
  const expectedProtected=original.items.filter((p:any)=>Number(p.name.split(' ').at(-1))<18).map((p:any)=>p.id).sort((a:number,b:number)=>a-b)
  expect([...main.protected_copy_ids].sort((a:number,b:number)=>a-b)).toEqual(expectedProtected)
  for(const id of expectedProtected)expect((await context.request.delete(base+'/api/players/'+id,{headers})).status()).toBe(409)
  // Reobserving inventory after protection preserves identities and the main hash.
  await page.locator('section').evaluate((el,rows)=>{
   el.setAttribute('data-view','inventory');el.setAttribute('data-page','despues-de-proteger')
   el.querySelector('.rows')!.innerHTML=rows
  },cards())
  await expect.poll(async()=>(await request('/reader/status')).observations.filter((o:any)=>o.domain==='inventory').length,{timeout:20000}).toBe(4)
  const last=(await request('/reader/status')).observations.find((o:any)=>o.domain==='inventory'&&!observed.has(o.observation_id))
  expect((await review(last.observation_id)).reused_copies).toBe(20)
  expect((await request('/squads/main')).state_hash).toBe(main.state_hash)
  expect((await request('/players')).total).toBe(20)
  expect((await send('workflow-control',{action:'cancel'})).ok).toBe(true)
  expect(panelErrors).toEqual([])
  console.log('SYNTHETIC_FIRST20 '+JSON.stringify({cards:20,fresh_repeats:2,copy_ids_unchanged:true,protected_starters:11,protected_bench:7,protected_delete_rejected:18,real_club:false}))
 }finally{await context.close();await new Promise<void>(resolve=>server.close(()=>resolve()))}
})
