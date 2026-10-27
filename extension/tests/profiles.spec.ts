import {test,expect,chromium,type Page} from '@playwright/test'
import http from 'node:http'
import path from 'node:path'
import {inspectRegion} from '../lib/inspect-region'
import {sensitiveText} from '../lib/privacy'
import {hash} from '../lib/contracts'
import {profileDefinition,extractProfile,structureHash,saveDefinition,recordSample,recordContrast,activateProfile,EXTRACTOR_REVISION} from '../lib/profile-extraction'
import type {Region,ProfileDefinition,Proof} from '../lib/profile-extraction'

const row=(name='Carta sintética')=>`<article class="card"><span class="name">${name}</span><span class="rating">88</span><span class="position">DC</span><span class="league" style="display:inline-block;width:10px;height:10px"></span></article>`
const html=()=>`<!doctype html><html lang="es"><body><main><section class="cards"><h2>Gallery Tokens</h2>${row()}${row('Otra carta sintética')}</section></main></body></html>`
const select=async(page:Page)=>page.evaluate(()=>{
 const range=document.createRange();range.selectNodeContents(document.querySelector('h2')!)
 const selection=getSelection()!;selection.removeAllRanges();selection.addRange(range)
})
async function inspect(page:Page){await select(page);return page.evaluate(inspectRegion,sensitiveText.source)}
async function definition(map:Region):Promise<ProfileDefinition>{
 return profileDefinition.parse({format:'club-lab-extractor-1',map_id:crypto.randomUUID(),view:'inventory',origin:'http://localhost:8090',route:'/reader-sample.html',language:'es',structure_hash:await structureHash(map),root_selector:'section.cards',record_selector:'article.card',fields:[
  {field:'name',selector:'span.name',source:'text',normalization:'text',required:true},
  {field:'rating',selector:'span.rating',source:'text',normalization:'integer',required:true},
  {field:'position',selector:'span.position',source:'text',normalization:'position',required:true},
  {field:'league',selector:'span.league',source:'text',normalization:'text',required:false},
 ]})
}

test('privacy distinguishes game tokens from credentials in headings and fields',async({page})=>{
 await page.setContent(html())
 for(const label of ['Token planner','Gallery Tokens','Tokens de Galería']){
  await page.locator('h2').evaluate((el,text)=>el.textContent=text,label)
  const map=await inspect(page)
  expect(map.blocked).toBeUndefined();expect(map.nodes?.some(n=>n.text===label)).toBe(true)
 }
 for(const label of ['access_token: abc','refresh-token xyz','session token','token=short','Token de acceso abc','Bearer abc','contraseña','MFA','OTP','Cookie','Verification code','abcdefghijklmnopqrstuvwxyz0123456789']){
  await page.locator('h2').evaluate((el,text)=>el.textContent=text,label)
  expect((await inspect(page)).blocked).toContain('reconocimiento detenido')
 }
 await page.locator('h2').evaluate(el=>el.textContent='Token planner')
 await page.locator('.name').first().evaluate(el=>el.textContent='access_token=abc')
 const map=await inspect(page)
 expect(map.coverage?.omitted.sensitive_fields).toBe(1)
 expect(JSON.stringify(map)).not.toContain('access_token')
 await page.locator('section').evaluate(el=>el.insertAdjacentHTML('beforeend','<input type="password" value="not-collected">'))
 expect((await inspect(page)).blocked).toContain('reconocimiento detenido')
})

test('inspector reports omitted media, mixed text, long requirements and forms without claiming complete coverage',async({page})=>{
 await page.setContent(html())
 await page.locator('section').evaluate(el=>{
  el.insertAdjacentHTML('beforeend','<div>Filtro <b>Media</b></div><p>'+('requisito largo '.repeat(400))+'</p><canvas>Private fallback</canvas><img width="20" height="20"><div class="host"></div><form><button>Never click</button></form>')
  el.querySelector('.host')!.attachShadow({mode:'open'}).innerHTML='<span>Shadow private</span>'
 })
 const map=await inspect(page),omitted=map.coverage!.omitted
 expect(omitted.long_fields).toBe(1);expect(omitted.mixed_text_nodes).toBe(1)
 expect(omitted.canvas).toBe(1);expect(omitted.images).toBe(1);expect(omitted.shadow_roots).toBe(1)
 expect(omitted.excluded_subtrees).toBe(1);expect(map.coverage?.partial).toBe(true)
 expect(map.coverage?.global_complete).toBe(false)
 for(const secret of ['Private fallback','Shadow private','Never click'])expect(JSON.stringify(map)).not.toContain(secret)
 await page.evaluate(()=>getSelection()!.removeAllRanges())
 expect((await page.evaluate(inspectRegion,sensitiveText.source)).blocked).toContain('Selecciona')
})

test('same reader scopes duplicate field selectors per row, preserves unknowns and fails on ambiguity or drift',async({page})=>{
 await page.setContent(html())
 const map=await inspect(page),p=await definition(map),preview=await extractProfile(p,map)
 expect(preview.records.map(r=>r.values.name)).toEqual(['Carta sintética','Otra carta sintética'])
 expect(preview.records.every(r=>r.values.rating===88&&r.values.league===null)).toBe(true)
 expect(preview.unknown_fields).toEqual(['league'])
 expect(preview.ingestion_enabled).toBe(false);expect(preview.provider_verified).toBe(false)
 await page.locator('.rating').first().evaluate(el=>el.textContent='88 puntos')
 await expect(extractProfile(p,await inspect(page))).rejects.toThrow('obligatorio')
 await page.locator('.rating').first().evaluate(el=>el.textContent='88')
 await page.locator('section').evaluate(el=>el.setAttribute('aria-busy','true'))
 await expect(extractProfile(p,await inspect(page))).rejects.toThrow('cargando')
 await page.locator('section').evaluate(el=>el.removeAttribute('aria-busy'))
 await page.evaluate(()=>document.documentElement.lang='en')
 await expect(extractProfile(p,await inspect(page))).rejects.toThrow('Idioma')
 await page.evaluate(()=>document.documentElement.lang='es')
 await page.locator('article').first().evaluate(el=>el.insertAdjacentHTML('beforeend','<span class="name">Duplicado</span>'))
 await expect(extractProfile(p,await inspect(page))).rejects.toThrow('no único dentro del registro')
 const ambiguous=await inspect(page),newDefinition=await definition(ambiguous)
 await expect(extractProfile(newDefinition,ambiguous)).rejects.toThrow('no único dentro del registro')
})

test('profile lifecycle binds evidence to definitions and rejects imported status or executable configuration',async({page})=>{
 await page.setContent(html())
 const p=await definition(await inspect(page))
 for(const extra of [{status:'active'},{script:'alert(1)'},{transitions:[{click:'button'}]}])expect(profileDefinition.safeParse({...p,...extra}).success).toBe(false)
 for(const selector of ['body','input[value]','span:nth-child(1)','div,script','javascript:alert(1)']){
  // Even a syntactically simple selector must exist in the linked reviewed map;
  // CSS attributes, expressions and comma lists are not part of the language.
  if(selector!=='body')expect(profileDefinition.safeParse({...p,root_selector:selector}).success).toBe(false)
 }
 let saved=await saveDefinition(p)
 expect(saved.status).toBe('draft')
 const proof:Proof={extractor_revision:EXTRACTOR_REVISION,definition_hash:await hash(p),observed_at:new Date().toISOString(),document_ref:crypto.randomUUID(),structure_hash:p.structure_hash,records:2}
 await expect(activateProfile(saved)).rejects.toThrow('Faltan')
 await expect(recordContrast(saved,proof)).rejects.toThrow('Prueba primero')
 saved=await recordSample(saved,proof);expect(saved.status).toBe('sample_tested')
 saved=await recordContrast(saved,proof);expect(saved.status).toBe('observed_contrasted')
 saved=await activateProfile(saved);expect(saved.status).toBe('active')
 await expect(activateProfile({...saved,contrast:{...proof,extractor_revision:'old-reader'}})).rejects.toThrow('Faltan')
 const changed=await saveDefinition({...p,fields:p.fields.map(f=>f.field==='league'?{...f,required:true}:f)},saved)
 expect(changed.revision).toBe(2);expect(changed.status).toBe('draft');expect(changed.sample).toBeUndefined();expect(changed.contrast).toBeUndefined()
 await expect(activateProfile(changed)).rejects.toThrow('Faltan')
 await expect(recordSample(changed,proof)).rejects.toThrow('otra revisión')
})

test('long requirements, nested record scopes and oversized regions fail without trimming or inventing rules',async({page})=>{
 await page.setContent(html())
 await page.locator('section').evaluate(el=>{el.innerHTML='<h2>DCP sintético</h2><article class="requirement"><span class="title">Una regla</span><span class="text">Media mínima 80</span></article>'})
 const map=await inspect(page)
 const dcp=profileDefinition.parse({...await definition(map),view:'dcp',record_selector:'article.requirement',fields:[
  {field:'title',selector:'span.title',source:'text',normalization:'text',required:true},
  {field:'requirement_text',selector:'span.text',source:'text',normalization:'text',required:true},
 ]})
 const preview=await extractProfile(dcp,map)
 expect(preview.records[0]?.values).toEqual({title:'Una regla',requirement_text:'Media mínima 80'})
 expect(preview.ingestion_enabled).toBe(false)
 await page.locator('.text').evaluate(el=>el.textContent='Requisito largo '.repeat(20))
 expect((await extractProfile(dcp,await inspect(page))).records[0]?.values.requirement_text).toBe('Requisito largo '.repeat(20).trim())
 await page.locator('.text').evaluate(el=>el.textContent='Requisito largo '.repeat(400))
 await expect(extractProfile(dcp,await inspect(page))).rejects.toThrow('obligatorio')
 await page.locator('.text').evaluate(el=>el.textContent='Media mínima 80')
 await page.locator('section').evaluate(el=>{const row=el.querySelector('article')!;for(let i=1;i<31;i++)el.append(row.cloneNode(true))})
 const large=await inspect(page)
 expect((await extractProfile(dcp,large)).records).toHaveLength(31)
 await page.locator('section').evaluate(el=>{el.innerHTML='<h2>DCP sintético</h2><article class="requirement"><span class="title">Una regla</span><article class="requirement"><span class="text">No solapar</span></article></article>'})
 const nested=await inspect(page)
 await expect(extractProfile({...dcp,structure_hash:await structureHash(nested)},nested)).rejects.toThrow('solapados')
})

test('compiled panel edits and tests a scoped profile without backend or real-source promotion',async()=>{
 let posted=0
 const server=http.createServer((req,res)=>{if(req.method==='POST')posted++;res.setHeader('Content-Type','text/html; charset=utf-8');res.end(html())})
 await new Promise<void>(r=>server.listen(8090,'127.0.0.1',r))
 const extension=path.resolve('.output/chrome-mv3')
 const context=await chromium.launchPersistentContext('',{channel:'chromium',headless:true,args:[`--disable-extensions-except=${extension}`,`--load-extension=${extension}`]})
 try{
  const worker=context.serviceWorkers()[0]||await context.waitForEvent('serviceworker'),id=new URL(worker.url()).hostname
  const panel=await context.newPage();await panel.goto(`chrome-extension://${id}/sidepanel.html`);await panel.locator("#technical > summary").click();await panel.locator("#pairing-settings > summary").click();await panel.locator("#legacy-tools > summary").click()
  const send=(kind:string,extra={})=>panel.evaluate(m=>chrome.runtime.sendMessage(m),{kind,...extra})
  const page=await context.newPage();await page.goto('http://127.0.0.1:8090/reader-sample.html');await page.bringToFront();await select(page)
  expect((await send('recognize',{view:'inventory'})).ok).toBe(true)
  const entry=(await send('status')).maps[0]
  const draft=(await send('profile-draft',{map_id:entry.map_id})).definition
  const configured={...draft,record_selector:'article.card',fields:(await definition(entry.map)).fields}
  expect((await send('profile-save',{definition:{...configured,status:'active'}})).ok).toBe(false)
  expect((await send('profile-save',{definition:{...configured,root_selector:'body'}})).ok).toBe(false)
  const saved=await send('profile-save',{definition:configured});expect(saved.ok,saved.error).toBe(true)
  const profile_id=saved.profile.id
  expect((await send('profile-enable',{profile_id})).ok).toBe(false)
  const trial=await send('profile-test',{profile_id});expect(trial.ok).toBe(true)
  expect(trial.preview.records).toHaveLength(2)
  expect((await send('status')).profiles[0].status).toBe('sample_tested')
  expect((await send('profile-contrast',{profile_id,reviewed:true})).ok).toBe(false)
  expect((await send('profile-enable',{profile_id})).ok).toBe(false)
  expect((await send('profile-read',{profile_id})).ok).toBe(false)
  await panel.locator('#profile-choice').selectOption(profile_id)
  await expect(panel.locator('#profile-state')).toContainText('Definición probada')
  expect(JSON.parse(await panel.locator('#profile-definition').inputValue())).toEqual(configured)
  expect((await send('profile-disable',{profile_id})).ok).toBe(true)
  expect((await send('status')).profiles[0].status).toBe('disabled')
  expect(posted).toBe(0)
  await panel.setViewportSize({width:390,height:844});expect(await panel.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
  await panel.screenshot({path:'test-results/profile-panel.png',fullPage:true})
 }finally{await context.close();await new Promise<void>(r=>server.close(()=>r()))}
})
