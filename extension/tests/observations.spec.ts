import {test,expect,chromium} from '@playwright/test'
import http from 'node:http'
import path from 'node:path'
import {localInteger} from '../lib/profile-extraction'
import {domainPayload} from '../lib/observation'

const positions=['POR','LD','DFC','DFC','LI','MC','MC','MC','ED','DC','EI']
const html=(count=65)=>`<!doctype html><html lang="es"><body><main><section class="cards"><h2>MUESTRA SINTÉTICA FC27</h2>${Array.from({length:count},(_,i)=>`<article class="card"><span class="name">Sintética ${i}</span><span class="rating">88</span><span class="position">${positions[i%11]}</span><span class="cardtype">Oro</span><span class="loan">No</span><span class="evo">No</span><span class="tradable">No</span></article>`).join('')}</section></main></body></html>`

test('compiled visual mapping → 65 records → lost ack/restarted worker → PostgreSQL admission → proposal',async()=>{
 let offline=false,loseAck=false,receipts=0,bytes=0,ocr=0,llm=0
 const durations:number[]=[]
 const server=http.createServer(async(req,res)=>{
  if(req.url==='/reader-sample.html'){res.setHeader('Content-Type','text/html; charset=utf-8');res.end(html());return}
  if(offline){res.statusCode=503;res.end('{}');return}
  if(/^\/api\/(ai|ollama)\b/.test(req.url||''))llm++
  if(/^\/api\/ocr\b|\/sessions\/[^/]+\/read$/.test(req.url||''))ocr++
  const chunks:Buffer[]=[];for await(const chunk of req)chunks.push(Buffer.from(chunk))
  const body=Buffer.concat(chunks),start=Date.now();bytes+=body.length
  const forwarded=Object.fromEntries(Object.entries(req.headers).filter(([,v])=>typeof v==='string')) as Record<string,string>
  const upstream=http.request((process.env.READER_TEST_UPSTREAM||'http://nginx')+req.url,{method:req.method,headers:{...forwarded,host:'localhost:8090'}},response=>{
   if(req.url==='/api/reader/events'&&response.statusCode===200){durations.push(Date.now()-start);receipts++;if(loseAck){loseAck=false;offline=true;response.resume();res.destroy();return}}
   res.writeHead(response.statusCode||502,response.headers);response.pipe(res)
  });upstream.on('error',()=>{res.statusCode=502;res.end('{}')});upstream.end(body)
 })
 await new Promise<void>(r=>server.listen(8090,'127.0.0.1',r))
 const extension=path.resolve('.output/chrome-mv3'),base='http://localhost:8090'
 const context=await chromium.launchPersistentContext('',{channel:'chromium',headless:true,args:[`--disable-extensions-except=${extension}`,`--load-extension=${extension}`]})
 const start=Date.now()
 try{
  let worker=context.serviceWorkers()[0]||await context.waitForEvent('serviceworker')
  const id=new URL(worker.url()).hostname,panel=await context.newPage()
  await panel.goto(`chrome-extension://${id}/sidepanel.html`)
  const send=(kind:string,extra={})=>panel.evaluate(m=>chrome.runtime.sendMessage(m),{kind,...extra})
  const session=await (await context.request.post(base+'/api/app/session')).json()
  const headers={'X-CSRF-Token':session.csrf_token,'X-App-Entry':''}
  const local=await (await context.request.post(base+'/api/app/entries',{headers,data:{nonce:crypto.randomUUID(),mode:'local'}})).json();headers['X-App-Entry']=String(local.entry_id)
  const club=await (await context.request.post(base+'/api/assisted/contexts',{headers,data:{name:'Flujo v2 SINTÉTICO',phrase:'INICIAR LECTURA ASISTIDA'}})).json()
  const entry=await (await context.request.post(base+'/api/app/entries',{headers,data:{nonce:crypto.randomUUID(),mode:'assisted',context_id:club.id}})).json();headers['X-App-Entry']=String(entry.entry_id)
  const pairing=await (await context.request.post(base+'/api/reader/pairings',{headers,data:{extension_id:id,confirmation:'EMPAREJAR LECTOR'}})).json()
  expect((await send('pair',{base,pairing_id:pairing.pairing_id,code:pairing.code})).ok).toBe(true)
  const page=await context.newPage();await page.goto(base+'/reader-sample.html');await page.bringToFront()
  const select=()=>page.evaluate(()=>{const r=document.createRange();r.selectNodeContents(document.querySelector('h2')!);getSelection()!.removeAllRanges();getSelection()!.addRange(r)})
  await select();expect((await send('recognize',{view:'inventory'})).ok).toBe(true)
  const map=(await send('status')).maps[0]
  await panel.locator('#profile-map').selectOption(map.map_id)
  await panel.locator('#profile-draft').click()
  await panel.locator('#mapping-record').selectOption('article.card')
  for(const [field,selector] of Object.entries({name:'name',rating:'rating',position:'position',card_type:'cardtype',is_loan:'loan',is_evolution:'evo',tradable:'tradable'}))await panel.locator(`select[data-field="${field}"]`).selectOption(`span.${selector}|text`)
  await panel.locator('#mapping-apply').click()
  await expect.poll(async()=>(await send('status')).profiles.length).toBe(1)
  const profile=(await send('status')).profiles[0],profile_id=profile.id
  const trial=await send('profile-test-map',{profile_id});expect(trial.ok,trial.error).toBe(true);expect(trial.preview.records).toHaveLength(65)
  await page.bringToFront();await select()
  expect((await send('profile-send',{profile_id})).error).toContain('Confirma')
  loseAck=true
  const sent=await send('profile-send',{profile_id,context_confirmed:true});expect(sent.ok,sent.error).toBe(true)
  expect((await send('status')).pending).toBe(3)
  expect(receipts).toBe(1)
  const saved=await worker.evaluate(()=>chrome.storage.local.get('state')),events=saved.state.pending
  expect(events.map((e:any)=>e.payload.records.length)).toEqual([30,30,5])
  expect(events.every((e:any)=>e.source_kind==='synthetic_dom')).toBe(true)
  const cdp=await context.newCDPSession(page),targets=await cdp.send('Target.getTargets')
  const target=targets.targetInfos.find((t:any)=>t.type==='service_worker'&&t.url.startsWith(`chrome-extension://${id}/`))!
  await cdp.send('Target.closeTarget',{targetId:target.targetId});await cdp.detach()
  offline=false;expect((await send('retry')).ok).toBe(true)
  expect((await send('status')).pending).toBe(0)
  const detail=await (await context.request.get(base+'/api/reader/observations/'+events[0].observation_id,{headers})).json()
  expect(detail.status).toBe('review_required');expect(detail.missing_fragments).toEqual([])
  expect(new Date(detail.observed_at).toISOString()).toBe(events[0].observed_at)
  const auth={'X-Reader-Extension':id,Authorization:'Bearer '+saved.state.credential}
  for(let i=0;i<20;i++){const replay=await context.request.post(base+'/api/reader/events',{headers:auth,data:events[0]});expect(replay.ok()).toBe(true);expect((await replay.json()).status).toBe('partial')}
  const review=await context.request.post(base+'/api/reader/observations/'+events[0].observation_id+'/review',{headers,data:{confirmation:'REVISAR OBSERVACION DOM',context_confirmed:true}});expect(review.ok(),await review.text()).toBe(true)
  expect((await (await context.request.get(base+'/api/players',{headers})).json()).total).toBe(65)
  expect((await send('analyze')).ok).toBe(true)
  expect((await send('status')).proposal.proposal.groups.some((g:any)=>g.squad.lineup.length===11)).toBe(true)
  // Same shape, fewer rows, no synthetic-to-real promotion and no new copies.
  await page.locator('article').evaluateAll(rows=>rows.slice(10).forEach(r=>r.remove()))
  await select()
  expect((await send('profile-send',{profile_id,context_confirmed:true})).ok).toBe(true)
  const latest=await (await context.request.get(base+'/api/reader/status',{headers})).json()
  const next=latest.observations.find((o:any)=>o.observation_id!==events[0].observation_id)
  expect(next.count).toBe(10)
  expect((await context.request.post(base+'/api/reader/observations/'+next.observation_id+'/review',{headers,data:{confirmation:'REVISAR OBSERVACION DOM',context_confirmed:true}})).ok()).toBe(true)
  expect((await (await context.request.get(base+'/api/players',{headers})).json()).total).toBe(65)
  await send('pause');await page.locator('.rating').first().evaluate(el=>el.textContent='89');await page.waitForTimeout(500)
  expect((await send('status')).pending).toBe(0)
  expect(ocr+llm).toBe(0)
  await panel.setViewportSize({width:390,height:844});expect(await panel.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  await panel.screenshot({path:'test-results/domain-mapping.png',fullPage:true})
  const values=events.flatMap((e:any)=>e.payload.records.flatMap((r:any)=>Object.entries(r).filter(([k])=>!['ordinal','evidence'].includes(k)).map(([,v])=>v)))
  const heap=await panel.evaluate(()=>(performance as any).memory?.usedJSHeapSize??null)
  console.log('SYNTHETIC_DOMAIN_METRICS '+JSON.stringify({records:65,fragments:3,receipts,bytes,elapsed_ms:Date.now()-start,
    known_fields:values.filter((v:any)=>v!==null).length,unknown_fields:values.filter((v:any)=>v===null).length,panel_js_heap_bytes:heap,
    event_roundtrips_ms:durations,local_ocr_calls:ocr,local_llm_calls:llm}))
 }finally{await context.close();await new Promise<void>(r=>server.close(()=>r()))}
})

test('typed payloads reject private or unrepresented facts and locale parsing keeps placeholders unknown',()=>{
 expect(localInteger('1.234','es')).toBe(1234);expect(localInteger('1,234','en')).toBe(1234)
 expect(localInteger('000,000','en')).toBeNull();expect(localInteger('0','es')).toBe(0)
 expect(localInteger('1,2','en')).toBeNull()
 expect(domainPayload.safeParse({domain:'account',club_name:'Club',balance:0,cookies:'private'}).success).toBe(false)
 expect(domainPayload.safeParse({domain:'dcp',records:[{title:'Ejemplo',requirement_text:'Exactamente 2 ligas',progress_current:null,progress_target:null}],rules_verified:true}).success).toBe(false)
})
