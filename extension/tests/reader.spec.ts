import {test,expect,chromium} from '@playwright/test'
import http from 'node:http'
import {readFile} from 'node:fs/promises'
import path from 'node:path'
import {canonical,hash} from '../lib/contracts'

const positions=['GK','RB','CB','CB','LB','CM','CM','CM','RW','ST','LW']
function fixture(language='en'){
 const es=['POR','LD','DFC','DFC','LI','MC','MC','MC','ED','DC','EI']
 return `<!doctype html><html lang="${language}"><title>MUESTRA SINTÉTICA, NO EA</title><body><h1>Solo prueba sintética</h1><section data-club-lab-sample="1" data-edition="FC27" data-source="synthetic_dom" data-page="1" data-view="inventory" data-virtualized="true">${positions.map((p,i)=>`<article data-card><span data-field="name">Muestra sintética ${i}</span><span data-field="rating">88</span><span data-field="position">${language==='es'?es[i]:p}</span><span data-field="card_type">Oro</span><span data-field="is_loan">${language==='es'?'No':'false'}</span><span data-field="is_evolution">false</span><span data-field="tradable">false</span><span data-field="gallery_score">${language==='es'?'1.000':'1,000'}</span></article>`).join('')}</section></body></html>`
}

test('compiled MV3 → loopback → Nginx → PostgreSQL → review → proposal, retries and worker suspension',async()=>{
 const target=process.env.READER_TEST_UPSTREAM||'http://nginx'
 let offline=false,loseAck=false,receipts=0,receivedBytes=0,llmRequests=0,ocrRequests=0
 const eventRoundTrips:number[]=[]
 const server=http.createServer(async(req,res)=>{
  const sentAt=Date.now()
  if(req.url==='/reader-sample.html'){res.setHeader('Content-Type','text/html; charset=utf-8');res.end(fixture());return}
  if(/^\/api\/(ai|chat|ollama)\b/.test(req.url||''))llmRequests++
  if(/^\/api\/(ocr|assisted\/sessions\/[^/]+\/read)\b/.test(req.url||''))ocrRequests++
  if(offline){res.statusCode=503;res.end();return}
  const chunks:Buffer[]=[];for await(const chunk of req)chunks.push(Buffer.from(chunk))
  const body=Buffer.concat(chunks);receivedBytes+=body.length
  const forwarded=Object.fromEntries(Object.entries(req.headers).filter(([,v])=>typeof v==='string')) as Record<string,string>
  const upstream=http.request(target+req.url,{method:req.method,headers:{...forwarded,host:'127.0.0.1:8090'}},response=>{
   if(req.url==='/api/reader/events'&&response.statusCode===200){eventRoundTrips.push(Date.now()-sentAt);receipts++;if(loseAck){loseAck=false;offline=true;response.resume();res.destroy();return}}
   res.writeHead(response.statusCode||502,response.headers);response.pipe(res)
  })
  upstream.on('error',()=>{res.statusCode=502;res.end()});upstream.end(body)
 })
 await new Promise<void>(resolve=>server.listen(8090,'127.0.0.1',resolve))
 const base='http://127.0.0.1:8090', extension=path.resolve('.output/chrome-mv3')
 const context=await chromium.launchPersistentContext('',{channel:'chromium',headless:true,args:[`--disable-extensions-except=${extension}`,`--load-extension=${extension}`]})
 const metrics={observations:0,bytes:0,receipts:0,local_http_llm_requests:0,local_http_ocr_requests:0,elapsed_ms:0,known_fields:0,unknown_fields:0}
 let publicRequests=0
 context.on('request',request=>{const url=new URL(request.url());if(['http:','https:'].includes(url.protocol)&&!['127.0.0.1','localhost'].includes(url.hostname))publicRequests++})
 const started=Date.now()
 try{
  let worker=context.serviceWorkers()[0]||await context.waitForEvent('serviceworker')
  const id=new URL(worker.url()).hostname
  const panel=await context.newPage();await panel.goto(`chrome-extension://${id}/sidepanel.html`)
  const manifest=JSON.parse(await readFile(path.join(extension,'manifest.json'),'utf8'))
  expect(manifest.permissions).not.toContain('cookies');expect(manifest.host_permissions).toEqual(['http://localhost/*','http://127.0.0.1/*'])
  const s=await context.request.post(base+'/api/app/session');expect(s.ok()).toBeTruthy()
  const session=await s.json()
  let headers={'X-CSRF-Token':session.csrf_token,'X-App-Entry':''}
  const start=await context.request.post(base+'/api/app/entries',{headers,data:{nonce:crypto.randomUUID(),mode:'local'}})
  headers['X-App-Entry']=String((await start.json()).entry_id)
  const c=await context.request.post(base+'/api/assisted/contexts',{headers,data:{name:'Extensión SINTÉTICA',phrase:'INICIAR LECTURA ASISTIDA'}});expect(c.ok()).toBeTruthy()
  const entry=await context.request.post(base+'/api/app/entries',{headers,data:{nonce:crypto.randomUUID(),mode:'assisted',context_id:(await c.json()).id}})
  headers['X-App-Entry']=String((await entry.json()).entry_id)
  const p=await context.request.post(base+'/api/reader/pairings',{headers,data:{extension_id:id,confirmation:'EMPAREJAR LECTOR'}});expect(p.ok()).toBeTruthy()
  const pair=await p.json()
  await panel.locator('#base').fill(base);await panel.locator('#pairing').fill(pair.pairing_id);await panel.locator('#code').fill(pair.code)
  await panel.locator('#pair').click();await expect(panel.locator('#status')).toContainText('Emparejado')
  const page=await context.newPage();await page.goto(base+'/reader-sample.html');await page.bringToFront()
  const send=(kind:string,extra={})=>panel.evaluate(m=>chrome.runtime.sendMessage(m),{kind,...extra})
  // Backend receives the event but the connection drops before its acknowledgement.
  loseAck=true
  expect((await send('activate')).ok).toBeTruthy()
  await expect.poll(async()=>(await send('status')).pending).toBe(1)
  await expect.poll(async()=>receipts).toBe(1)
  // Close worker through CDP, with no DevTools window or keepalive connection.
  const cdp=await context.newCDPSession(page)
  const targets=await cdp.send('Target.getTargets')
  const workerTarget=targets.targetInfos.find((t:any)=>t.type==='service_worker'&&t.url.startsWith(`chrome-extension://${id}/`))
  expect(workerTarget).toBeTruthy()
  await cdp.send('Target.closeTarget',{targetId:workerTarget!.targetId});await cdp.detach()
  offline=false
  expect((await send('retry')).ok).toBeTruthy()
  await expect.poll(async()=>(await send('status')).pending).toBe(0)
  worker=context.serviceWorkers().find(w=>w.url().startsWith(`chrome-extension://${id}/`))||await context.waitForEvent('serviceworker')
  const saved=await worker.evaluate(()=>chrome.storage.local.get('state'))
  const auth={'X-Reader-Extension':id,Authorization:'Bearer '+saved.state.credential}
  const status=await (await context.request.get(base+'/api/reader/status',{headers})).json()
  expect(status.events).toHaveLength(1)
  const eventId=status.events[0].event_id
  const detail=await (await context.request.get(base+'/api/reader/events/'+eventId,{headers})).json()
  const event=detail.payload
  expect(event.records[0].gallery_score).toBe(1000);expect(event.records[0].first_owner).toBeNull()
  expect(event.scope.virtualized).toBe(true);expect(event.scope.global_complete).toBe(false)
  const receipt=await (await context.request.post(base+'/api/reader/events',{headers:auth,data:event})).json()
  for(let i=0;i<20;i++)expect(await (await context.request.post(base+'/api/reader/events',{headers:auth,data:event})).json()).toEqual(receipt)
  expect((await context.request.post(base+'/api/reader/events/'+eventId+'/review',{headers,data:{confirmation:'REVISAR LOTE DOM'}})).ok()).toBeTruthy()
  expect((await send('analyze')).ok).toBeTruthy()
  await expect(panel.locator('#proposal')).toContainText('Muestra sintética 0')
  const proposal=(await send('status')).proposal
  expect(proposal.proposal.groups.some((g:any)=>g.squad.lineup.length===11)).toBe(true)
  const mainBefore=await (await context.request.get(base+'/api/squads/main',{headers})).json()
  expect(proposal.writes_performed).toBe(false)
  expect(await (await context.request.get(base+'/api/squads/main',{headers})).json()).toEqual(mainBefore)
  // ES rendering of same rows, loading sentinel, no accidental full-club claim.
  offline=true
  await page.evaluate(()=>document.querySelector('section')!.setAttribute('aria-busy','true'))
  await page.evaluate(()=>{
   document.documentElement.lang='es'
   const positions=['POR','LD','DFC','DFC','LI','MC','MC','MC','ED','DC','EI']
   document.querySelectorAll('[data-field=position]').forEach((el,i)=>el.textContent=positions[i]??null)
   document.querySelectorAll('[data-field=is_loan]').forEach(el=>el.textContent='No')
   document.querySelectorAll('[data-field=gallery_score]').forEach(el=>el.textContent='1.000')
  })
  await page.locator('[data-field=rating]').first().evaluate(el=>el.textContent='89')
  await page.waitForTimeout(600)
  expect((await send('status')).pending).toBe(0)
  await page.evaluate(()=>document.querySelector('section')!.setAttribute('aria-busy','false'))
  await expect.poll(async()=>(await send('status')).pending).toBe(1)
  offline=false;expect((await send('retry')).ok).toBeTruthy()
  const statusAfterReview=await context.request.get(base+'/api/reader/status',{headers})
  expect(statusAfterReview.ok()).toBeTruthy()
  const latest=await statusAfterReview.json()
  expect(latest.events).toHaveLength(2)
  expect(latest.events.find((e:any)=>e.event_id===eventId).status).toBe('reviewed')
  const second=latest.events.find((e:any)=>e.event_id!==eventId)
  const spanishResponse=await context.request.get(base+'/api/reader/events/'+second.event_id,{headers})
  expect(spanishResponse.ok()).toBeTruthy()
  const spanish=await spanishResponse.json()
  expect(spanish.payload.records.map((r:any)=>r.position)).toEqual(['POR','LD','DFC','DFC','LI','MC','MC','MC','ED','DC','EI'])
  expect(spanish.payload.records.every((r:any)=>r.is_loan===false&&r.gallery_score===1000)).toBe(true)
  await send('pause')
  await page.locator('[data-field=rating]').first().evaluate(el=>el.textContent='90')
  await page.waitForTimeout(600);expect((await send('status')).pending).toBe(0)
  expect((await context.request.post(base+'/api/reader/grants/'+saved.state.binding+'/revoke',{headers,data:{}})).ok()).toBeTruthy()
  expect((await send('analyze')).ok).toBe(false)
  metrics.local_http_llm_requests=llmRequests;metrics.local_http_ocr_requests=ocrRequests;expect(llmRequests+ocrRequests).toBe(0)
  metrics.observations=2;metrics.bytes=receivedBytes;metrics.receipts=receipts;metrics.elapsed_ms=Date.now()-started
  metrics.unknown_fields=event.records.reduce((n:number,r:any)=>n+Object.entries(r).filter(([k,v])=>!['ordinal','evidence'].includes(k)&&v===null).length,0)
  metrics.known_fields=event.records.reduce((n:number,r:any)=>n+Object.entries(r).filter(([k,v])=>!['ordinal','evidence'].includes(k)&&v!==null).length,0)
  const performance=await context.newCDPSession(panel);await performance.send('Performance.enable')
  const measured=await performance.send('Performance.getMetrics');await performance.detach()
  const panelJsHeap=measured.metrics.find(m=>m.name==='JSHeapUsedSize')?.value??null
  expect(publicRequests).toBe(0)
  console.log('SYNTHETIC_READER_METRICS '+JSON.stringify({...metrics,browser_public_http_requests:publicRequests,panel_js_heap_bytes:panelJsHeap,event_roundtrips_ms:eventRoundTrips}))
 }finally{await context.close();await new Promise<void>(resolve=>server.close(()=>resolve()))}
})

test('sample contract rejects private fields, FC26 and malicious field values',async()=>{
 const {reading,forbidden}=await import('../lib/contracts')
 expect(forbidden.test('Bearer synthetic-secret')).toBe(true)
 expect(reading.safeParse({edition:'FC26',cookies:'no'}).success).toBe(false)
 expect(canonical({z:1,a:{c:3,b:2}})).toBe('{"a":{"b":2,"c":3},"z":1}')
 expect(await hash({a:1})).toHaveLength(64)
})
