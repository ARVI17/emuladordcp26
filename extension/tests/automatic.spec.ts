import {test,expect,chromium} from '@playwright/test'
import http from 'node:http'
import path from 'node:path'
import fs from 'node:fs'

// Synthetic UI only, intercepted in a disposable browser; no real EA request.
function fixture(spanish:boolean,total=20){return `<!doctype html><html><head><meta charset="utf-8"><title>FC Ultimate Team</title><style>
.ut-squad-slot-view .name,.ut-squad-slot-view .player-stats-data-component{display:none}
.ut-draggable{position:relative;height:290px;overflow:hidden}
.ut-squad-pitch-view,.ut-squad-slot-dock-view{display:flex;gap:4px;flex-wrap:wrap}
.ut-squad-slot-view{width:54px;height:66px}
.test-card-face{min-height:100%}
.test-docks{position:absolute;inset:0;pointer-events:none}
.test-docks .ut-squad-slot-dock-view{position:absolute;top:100%;left:0;right:0;min-height:140px;background:white;pointer-events:auto}
.ut-draggable.bench-open .test-docks .bench,.ut-draggable.reserve-open .test-docks .reserve{top:40px}
.test-dock-controls{position:absolute;left:0;right:0;bottom:4px;display:flex;justify-content:space-between}
.ut-draggable.bench-open .test-docks .bench{top:40px;bottom:0;z-index:2}
.test-dock-controls .ui-direction-down{z-index:3}
.ut-navigation-button-control::before{content:'\uE09B'}
.test-transition{position:fixed;inset:0;z-index:100;background:white}
</style></head><body>
<span class="view-navbar-clubinfo-name">${total>20?'':'Club automático SINTÉTICO'}</span><main id="view"></main><div id="detail"></div>
<nav><button onclick="show('club')">Club</button><button onclick="show('squads')">${spanish?'Plantillas':'Squads'}</button></nav>
<script>
const es=${spanish},positions=es?['POR','LD','DFC','DFC','LI','MC','MC','MC','ED','DC','EI']:['GK','RB','CB','CB','LB','CM','CM','CM','RW','ST','LW'];
const total=${total};let selected=0,kind='inventory',reverse=false,pageIndex=0;
if(total>20){
 const boot=document.createElement('button');boot.textContent='Login';
 boot.onclick=()=>{document.documentElement.dataset.testLoginClick='yes'};document.body.append(boot);
 setTimeout(()=>{boot.remove();document.querySelector('.view-navbar-clubinfo-name').textContent='Club automático SINTÉTICO'},1000);
}
const stats=()=>'<ul class="player-stats-data-component">'+(es?['RIT','TIR','PAS','REG','DEF','FIS']:['PAC','SHO','PAS','DRI','DEF','PHY']).map(s=>'<li>'+s+' 80</li>').join('')+'</ul>';
const card=i=>'<div class="name">Auto visible '+i+'</div><div class="rating">88</div><div class="position">'+positions[i%11]+'</div>'+stats();
function navbar(title,back){return '<header class="ut-navigation-bar-view navbar-style-secondary"><button class="ut-navigation-button-control" onclick="'+back+'"></button><h1>'+title+'</h1></header>'}
function choose(i){selected=i;document.getElementById('detail').innerHTML=(kind==='squad'?navbar(es?'Detalles del jugador':'Player Details','closeDetails()'):'')+'<button onclick="bio()">'+(es?'Datos del jugador':'Player Bio')+'</button>'}
function closeDetails(){document.getElementById('detail').innerHTML=''}
let missedReturns=0,ignoreOneReturn=false;
function returnFromBio(){
 if(ignoreOneReturn){ignoreOneReturn=false;missedReturns++;return}
 choose(selected);
}
function bio(){ignoreOneReturn=kind==='inventory'&&selected===0;document.getElementById('detail').innerHTML=navbar(es?'Datos del jugador':'Player Bio','returnFromBio()')+'<article class="ut-player-bio-view"><ul><li class="listFUTItem"></li></ul>'+card(selected)+'<p>'+(es?'Rareza':'Rarity')+'</p><p>Oro</p></article>';
 const bio=document.querySelector('article.ut-player-bio-view');
 const finish=()=>bio.insertAdjacentHTML('beforeend','<p>'+(es?'Liga':'League')+'</p><p>Liga prueba</p><p>Club</p><p>Club prueba</p><p>'+(es?'País/región':'Country/Region')+'</p><p>País prueba</p>');
 if(selected===5)setTimeout(finish,650);else finish()}
let holdTransition=false,overlayClicks=0,drawerOpens=0,reserveOpens=0;
function transition(){
 const mask=document.createElement('div');mask.className='test-transition';mask.textContent='Loading…';
 mask.addEventListener('mousedown',()=>overlayClicks++);document.body.append(mask);
 if(!holdTransition)setTimeout(()=>mask.remove(),700);
}
function renderDocks(){
 const pitch=document.querySelector('.ut-squad-pitch-view'),bench=document.querySelector('.ut-squad-slot-dock-view');
 const frame=document.createElement('div');frame.className='ut-draggable';pitch.replaceWith(frame);frame.append(pitch);
 const docks=document.createElement('div');docks.className='test-docks';frame.append(docks);bench.classList.add('bench');docks.append(bench);
 if(total>20){
  const reserves=document.createElement('div');reserves.className='ut-squad-slot-dock-view reserve';
  reserves.innerHTML=Array.from({length:5},(_,j)=>'<div class="ut-squad-slot-view" onclick="choose('+(18+j)+')">'+card(18+j)+'</div>').join('')+'<p>Drag any player to and from the pitch to swap reserves</p>';docks.append(reserves);
 }
 const controls=document.createElement('div');controls.className='test-dock-controls';frame.append(controls);
 let reserveStillSliding=true;
 for(const label of (es?['Suplentes','Reservas']:['Subs','Res'])){
  const toggle=document.createElement('button');toggle.className='dockTab';toggle.textContent=label;controls.append(toggle);
  const mode=label==='Subs'||label==='Suplentes'?'bench-open':'reserve-open';
  toggle.addEventListener('click',()=>{
   if(mode==='reserve-open'&&reserveStillSliding){reserveStillSliding=false;return}
   const open=frame.classList.toggle(mode);toggle.classList.toggle('ui-direction-down',open);
   if(open){drawerOpens++;if(mode==='reserve-open')reserveOpens++}
  });
 }
}
function show(next){if(next==='club')pageIndex=0;kind=next;document.getElementById('detail').innerHTML='';let html='';
if(next==='club')html='<h1 onclick="show(&quot;inventory&quot;)">'+(es?'Jugadores':'Players')+'</h1>';
if(next==='squads')html='<h1 onclick="show(&quot;squad&quot;)">'+(es?'Plantilla activa':'Active Squad')+'</h1>';
if(next==='inventory'){let order=Array.from({length:total},(_,i)=>i);if(reverse)order.reverse();order=order.slice(pageIndex*20,(pageIndex+1)*20);html='<h1>'+(es?'Jugadores de mi club':'My Club Players')+'</h1><button onclick="show(&quot;club&quot;)">'+(es?'Buscar':'Search')+'</button><div class="ut-club-search-results-view"><ul class="paginated">'+order.map(i=>'<li class="listFUTItem" onclick="choose('+i+')">'+card(i)+'</li>').join('')+'</ul></div><button '+(pageIndex===0?'disabled':'')+' onclick="pageIndex--;show(&quot;inventory&quot;)">'+(es?'Anterior':'Previous')+'</button><button '+((pageIndex+1)*20>=total?'disabled':'')+' onclick="pageIndex++;show(&quot;inventory&quot;)">'+(es?'Siguiente':'Next')+'</button>'}
if(next==='squad')html='<div>4-3-3</div><div class="ut-squad-pitch-view">'+Array.from({length:11},(_,i)=>'<div class="ut-squad-slot-view" onclick="choose('+i+')"><div class="ut-squad-slot-pedestal-view"><span class="label">'+positions[i]+'</span><span>++</span></div>'+card(i)+'</div>').join('')+'</div><div class="ut-squad-slot-dock-view">'+Array.from({length:7},(_,n)=>'<div class="ut-squad-slot-view" onclick="choose('+(n+11)+')">'+card(n+11)+'</div>').join('')+'<p>'+(es?'Arrastra jugadores para cambiar suplentes':'Drag any player to and from the pitch to swap subs')+'</p></div>';
document.getElementById('view').innerHTML=html;
if(next==='squad')renderDocks();
if(next==='squads'||next==='squad')transition()}
// English requires a press/release gesture. Ordinary click alone has no effect;
// this models the real navigation failure that click-only fixtures concealed.
function wireGestures(){if(es)return;document.querySelectorAll('[onclick]').forEach(e=>{if(total>20&&e.disabled&&e.textContent==='Next'){e.remove();return}const action=e.onclick;e.removeAttribute('onclick');let target=e;if(e.matches('.ut-squad-slot-view,.listFUTItem')){target=document.createElement('div');target.className='test-card-face';while(e.firstChild)target.append(e.firstChild);e.append(target)}let pressed=false;target.onmousedown=()=>{pressed=true};target.onmouseup=event=>{if(!pressed)return;pressed=false;action.call(e,event)}})}
new MutationObserver(wireGestures).observe(document.body,{childList:true,subtree:true});
show('inventory');
wireGestures();
</script></body></html>`}

for(const [spanish,total] of [[false,20],[true,20],[false,65]] as const)test(`automatic open ${spanish?'ES':'EN'}: ${total} copies twice again, XI and seven locked`,async()=>{
 test.setTimeout(420000)
 let base=''
 let interruptedProgress=false
 const server=http.createServer(async(req,res)=>{
  const chunks:Buffer[]=[];for await(const chunk of req)chunks.push(Buffer.from(chunk))
  const headers=Object.fromEntries(Object.entries(req.headers).filter(([,v])=>typeof v==='string')) as Record<string,string>
  // Nginx forwards Host $host without the test proxy's ephemeral port.
  if(headers.origin===base)headers.origin='http://localhost'
  const proxy=http.request((process.env.READER_TEST_UPSTREAM||'http://nginx')+req.url,{method:req.method,headers:{...headers,host:'localhost:8090'}},r=>{
   // Kill the worker in the exact gap between durable progress and the next
   // command: no content-script event remains to wake it. Only its alarm can.
   if(total>20&&!interruptedProgress&&req.url==='/api/browser-auto/progress'&&JSON.parse(Buffer.concat(chunks).toString()).pages_read===1){
    interruptedProgress=true;r.resume()
    const timer=setTimeout(()=>res.destroy(),30000);timer.unref();res.on('close',()=>clearTimeout(timer));return
   }
   res.writeHead(r.statusCode||502,r.headers);r.pipe(res)
  })
  proxy.on('error',()=>{res.statusCode=502;res.end()});proxy.end(Buffer.concat(chunks))
 })
 await new Promise<void>(resolve=>server.listen(0,'0.0.0.0',resolve))
 base='http://localhost:'+(server.address() as import('node:net').AddressInfo).port
 const extension=path.resolve('.output/chrome-mv3'),manifest=JSON.parse(fs.readFileSync(path.join(extension,'manifest.json'),'utf8'))
 const expectedProtected=total>20?23:18
 expect(manifest.permissions).not.toContain('cookies');expect(manifest.permissions).not.toContain('debugger')
 expect(manifest.host_permissions).toEqual(['http://localhost/*','http://127.0.0.1/*','https://www.ea.com/*'])
 const context=await chromium.launchPersistentContext('',{channel:'chromium',headless:true,args:[`--disable-extensions-except=${extension}`,`--load-extension=${extension}`,'--host-resolver-rules=MAP www.ea.com ~NOTFOUND']})
 context.setDefaultTimeout(15000)
 const bounded=async<T>(task:Promise<T>,label:string):Promise<T>=>{
  let timer:ReturnType<typeof setTimeout>|undefined
  try{return await Promise.race([task,new Promise<never>((_,reject)=>{timer=setTimeout(()=>reject(Error('Timed out at '+label)),15000)})])}
  finally{if(timer)clearTimeout(timer)}
 }
 const stage=(name:string)=>console.log('AUTO_SYNTHETIC_STAGE '+JSON.stringify({language:spanish?'es':'en',cards:total,stage:name,real_club:false}))
 try{
  const loggedOutUrl='https://www.ea.com/es-es/ea-sports-fc/ultimate-team/web-app/'
  await context.route('https://www.ea.com/**',route=>route.fulfill({contentType:'text/html; charset=utf-8',
   body:route.request().url()===loggedOutUrl?'<h1>Signed Into Another Device</h1><button>Login</button>':fixture(spanish,total)}))
  let ea=await context.newPage()
  ea.on('pageerror',error=>console.log('AUTO_FIXTURE_ERROR '+error.message))
  ea.on('console',message=>{if(message.text().startsWith('Club Lab reader stopped:'))console.log(message.text())})
  await ea.goto('https://www.ea.com/ea-sports-fc/ultimate-team/web-app/')
  await expect(ea.locator('li.listFUTItem')).toHaveCount(20)
  if(!spanish){
   await ea.getByRole('button',{name:'Squads',exact:true}).evaluate((e:HTMLElement)=>e.click())
   await expect(ea.getByRole('heading',{name:'My Club Players',exact:true})).toBeVisible()
   await ea.locator('li.listFUTItem').first().evaluate(e=>{e.dispatchEvent(new MouseEvent('mousedown',{bubbles:true}));e.dispatchEvent(new MouseEvent('mouseup',{bubbles:true}))})
   await expect(ea.getByRole('button',{name:'Player Bio',exact:true})).toHaveCount(0)
  }
  const session=await (await context.request.post(base+'/api/app/session')).json()
  const headers={'X-CSRF-Token':session.csrf_token,'X-App-Entry':''}
  const request=async(route:string,data?:unknown)=>{
   const r=data===undefined?await context.request.get(base+'/api'+route,{headers}):await context.request.post(base+'/api'+route,{headers,data})
   expect(r.ok(),route+': '+await r.text()).toBe(true);return r.json()
  }
  async function refreshHeaders(){const s=await (await context.request.post(base+'/api/app/session')).json();headers['X-CSRF-Token']=s.csrf_token;headers['X-App-Entry']=String(s.entry_id)}
  async function waitUpdated(previous?:string){
   // Wait for the SPA's new entry after reload before reading its session headers.
   await expect(page.getByRole('region',{name:'Actualización automática del club'})).toBeVisible()
   await refreshHeaders()
   let status:any
   await expect.poll(async()=>{status=await request('/browser-auto/status');return !!status.request_id&&status.request_id!==previous&&!['disabled','ready','reading'].includes(status.status)},{timeout:150000}).toBe(true)
   expect(status.status,JSON.stringify(status.result)).toBe('updated')
  }
  const local=await request('/app/entries',{nonce:crypto.randomUUID(),mode:'local'});headers['X-App-Entry']=String(local.entry_id)
  const club=await request('/assisted/contexts',{name:'Auto E2E '+crypto.randomUUID(),phrase:'INICIAR LECTURA ASISTIDA'})
  const entry=await request('/app/entries',{nonce:crypto.randomUUID(),mode:'assisted',context_id:club.id});headers['X-App-Entry']=String(entry.entry_id)
  const page=await context.newPage()
  page.on('pageerror',error=>console.log('AUTO_PAGE_ERROR '+error.message))
  page.on('response',response=>{if(response.status()>=400)console.log('AUTO_HTTP_ERROR '+response.status()+' '+new URL(response.url()).pathname)})
  await page.goto(base+'/#/conexiones')
  const activate=page.getByRole('button',{name:'Activar actualización automática y proteger mi equipo'})
  await expect(activate).toBeEnabled({timeout:15000})
  const loggedOut=!spanish&&total===20?await context.newPage():undefined
  if(loggedOut){
   await loggedOut.goto(loggedOutUrl)
   const worker=context.serviceWorkers()[0]||await context.waitForEvent('serviceworker')
   await worker.evaluate(async url=>{
    const [old]=await chrome.tabs.query({url})
    await chrome.storage.session.set({officialTab:old!.id})
   },loggedOutUrl)
  }
  if(total>20){
   stage('creating_inactive_tab')
   await ea.close()
   const opened=context.waitForEvent('page')
   await activate.click();ea=await opened
   await expect(ea.locator('nav')).toBeVisible()
   const worker=context.serviceWorkers()[0]||await context.waitForEvent('serviceworker')
   expect(await bounded(worker.evaluate(async()=>{const tabs=await chrome.tabs.query({url:'https://www.ea.com/*'});return tabs.length===1&&tabs[0]?.active===false}),'inactive_tab')).toBe(true)
  }else await activate.click()
  const panel=page.getByRole('region',{name:'Actualización automática del club'})
  if(total>20){
   stage('waiting_first_page')
   await refreshHeaders()
   await expect.poll(async()=>(await request('/browser-auto/status')).progress?.pages_read||0,{timeout:120000}).toBeGreaterThan(0)
   // Suppress the content script's three immediate transport retries in this
   // disposable fixture, so they cannot hide a missing alarm-based recovery.
   const recoveryWorker=context.serviceWorkers()[0]||await context.waitForEvent('serviceworker')
   await bounded(recoveryWorker.evaluate(async()=>{
    const tabs=await chrome.tabs.query({url:'https://www.ea.com/*'})
    if(tabs.length!==1||!tabs[0]?.id)throw Error('Missing isolated EA fixture tab')
    await chrome.scripting.executeScript({target:{tabId:tabs[0].id},func:()=>{
     const runtime=chrome.runtime as unknown as {sendMessage:(message:any)=>Promise<unknown>}
     const original=runtime.sendMessage.bind(runtime),until=Date.now()+10000
     let dropped=0
     const replacement=(message:any)=>{
      if(message?.kind==='browser-auto-step-result'&&Date.now()<until){
       document.documentElement.setAttribute('data-test-reader-drops',String(++dropped))
       return Promise.reject(Error('Synthetic temporary transport loss'))
      }
      return original(message)
     }
     runtime.sendMessage=replacement
     if(runtime.sendMessage!==replacement)throw Error('Fixture transport fault was not installed')
    }})
   }),'temporary_content_transport_loss')
   stage('stopping_worker')
   const cdp=await bounded(context.newCDPSession(page),'cdp_session'),targets=await bounded(cdp.send('Target.getTargets'),'worker_target')
   const target=targets.targetInfos.find((t:any)=>t.type==='service_worker'&&t.url.startsWith('chrome-extension://'))
   if(!target)throw Error('The isolated extension worker was not found')
   await bounded(cdp.send('Target.closeTarget',{targetId:target.targetId}),'worker_stop');await bounded(cdp.detach(),'cdp_detach')
  }
  stage('waiting_first_publication')
  await waitUpdated()
  if(total>20)await expect(ea.getByRole('button',{name:'Next',exact:true})).toHaveCount(0)
  if(total>20){expect(interruptedProgress).toBe(true);expect(Number(await ea.locator('html').getAttribute('data-test-reader-drops'))).toBeGreaterThanOrEqual(2)}
  await expect(panel).toContainText('principal y suplentes protegidos',{timeout:150000})
  // Refresh request headers after the SPA creates its entry; the extension never gets them.
  await refreshHeaders()
  const first=await request('/players?limit=100'),ids=first.items.map((c:any)=>c.id).sort((a:number,b:number)=>a-b)
  expect(first.total).toBe(total)
  const main=await request('/squads/main');expect(main.complete).toBe(true);expect(main.protected_copy_ids).toHaveLength(expectedProtected)
  expect(main.snapshot.members.filter((m:any)=>m.slot.startsWith('BENCH-'))).toHaveLength(7)
  expect(main.snapshot.members.filter((m:any)=>m.slot.startsWith('RESERVE-'))).toHaveLength(expectedProtected-18)
  let receipt=(await request('/browser-auto/status')).result.request_id
  for(let pass=0;pass<2;pass++){
   stage('reopen_'+(pass+1))
   if(loggedOut&&pass===0){
    const worker=context.serviceWorkers()[0]||await context.waitForEvent('serviceworker')
    await worker.evaluate(()=>chrome.storage.session.remove('officialTab'))
   }
   await ea.evaluate('reverse = !reverse')
   await page.reload()
   await waitUpdated(receipt)
   await expect(panel).toContainText('principal y suplentes protegidos',{timeout:150000})
   await refreshHeaders()
   await expect.poll(async()=>(await request('/browser-auto/status')).result.request_id,{timeout:150000}).not.toBe(receipt)
   const state=await request('/browser-auto/status');receipt=state.result.request_id
   expect(state.result.pending).toEqual([])
   expect(state.result.pages_read).toBe(Math.ceil(total/20));expect(state.result.traversal_end).toBe('end')
   const cards=await request('/players?limit=100');expect(cards.total).toBe(total)
   expect(cards.items.map((c:any)=>c.id).sort((a:number,b:number)=>a-b)).toEqual(ids)
   const protectedMain=await request('/squads/main');expect(protectedMain.complete).toBe(true)
   expect(protectedMain.protected_copy_ids).toEqual(main.protected_copy_ids)
  }
  for(const id of main.protected_copy_ids)expect((await context.request.delete(base+'/api/players/'+id,{headers})).status()).toBe(409)
  await page.getByRole('button',{name:'Actualizar ahora',exact:true}).click()
  await expect(page.getByRole('button',{name:'Detener lectura'})).toBeVisible()
  await page.getByRole('button',{name:'Detener lectura'}).click()
  await expect(panel).toContainText('Lectura detenida')
  await refreshHeaders()
  expect((await request('/players')).total).toBe(total)
  expect((await request('/squads/main')).protected_copy_ids).toEqual(main.protected_copy_ids)
  expect(await ea.evaluate('drawerOpens')).toBeGreaterThanOrEqual(3)
  expect(await ea.evaluate('missedReturns')).toBeGreaterThanOrEqual(3)
  if(total>20)expect(await ea.evaluate('reserveOpens')).toBeGreaterThanOrEqual(3)
  expect(await ea.locator('html').getAttribute('data-test-login-click')).toBeNull()
  if(!spanish&&total===20){
   await expect(loggedOut!.getByRole('heading',{name:'Signed Into Another Device'})).toBeVisible()
   // A second signed-in club with no explicit selection must never be read or published.
   await loggedOut!.goto('https://www.ea.com/en-us/ea-sports-fc/ultimate-team/web-app/')
   await loggedOut!.locator('.view-navbar-clubinfo-name').evaluate(e=>{e.textContent='Otro club SINTÉTICO'})
   await page.getByRole('button',{name:'Actualizar ahora',exact:true}).click()
   await expect(panel).toContainText('La vista cambió',{timeout:25000})
   expect((await request('/browser-auto/status')).result.request_id).toBe(receipt)
   await expect(loggedOut!.getByRole('heading',{name:'My Club Players'})).toBeVisible()
   await loggedOut!.close()
   await ea.evaluate('holdTransition=true')
   await page.getByRole('button',{name:'Actualizar ahora',exact:true}).click()
   await expect(panel).toContainText('La vista cambió',{timeout:25000})
   expect((await request('/browser-auto/status')).result.request_id).toBe(receipt)
  }
  expect(await ea.evaluate('overlayClicks')).toBe(0)
  console.log('AUTO_SYNTHETIC '+JSON.stringify({language:spanish?'es':'en',cards:total,reopens:2,protected:expectedProtected,real_club:false}))
 }catch(error){for(const tab of context.pages())if(tab.url().startsWith('https://www.ea.com/'))console.log('AUTO_SYNTHETIC_LAST_VIEW '+(await tab.locator('body').innerText({timeout:1000}).catch(()=>'(unavailable)')).slice(0,600));throw error}
 finally{await context.close();await new Promise<void>(resolve=>server.close(()=>resolve()))}
})
