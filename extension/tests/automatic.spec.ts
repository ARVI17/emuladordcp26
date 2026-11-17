import {test,expect,chromium} from '@playwright/test'
import http from 'node:http'
import path from 'node:path'
import fs from 'node:fs'

// Synthetic UI only, intercepted in a disposable browser; no real EA request.
function fixture(spanish:boolean){return `<!doctype html><html><head><meta charset="utf-8"><title>FC Ultimate Team</title><style>.ut-squad-slot-view .name{display:none}</style></head><body>
<span class="view-navbar-clubinfo-name">Club automático SINTÉTICO</span><main id="view"></main><div id="detail"></div>
<nav><button onclick="show('club')">Club</button><button onclick="show('squads')">${spanish?'Plantillas':'Squads'}</button></nav>
<script>
const es=${spanish},positions=es?['POR','LD','DFC','DFC','LI','MC','MC','MC','ED','DC','EI']:['GK','RB','CB','CB','LB','CM','CM','CM','RW','ST','LW'];
let selected=0,kind='inventory',reverse=false;
const stats=()=>'<ul class="player-stats-data-component">'+(es?['RIT','TIR','PAS','REG','DEF','FIS']:['PAC','SHO','PAS','DRI','DEF','PHY']).map(s=>'<li>'+s+' 80</li>').join('')+'</ul>';
const card=i=>'<div class="name">Auto visible '+i+'</div><div class="rating">88</div><div class="position">'+positions[i%11]+'</div>'+stats();
function choose(i){selected=i;document.getElementById('detail').innerHTML=(kind==='squad'?'<h1>'+(es?'Detalles del jugador':'Player Details')+'</h1><button onclick="closeDetails()">\uE09B</button>':'')+'<button onclick="bio()">'+(es?'Datos del jugador':'Player Bio')+'</button>'}
function closeDetails(){document.getElementById('detail').innerHTML=''}
function bio(){document.getElementById('detail').innerHTML='<button onclick="choose(selected)">\uE09B</button><article class="ut-player-bio-view">'+card(selected)+'<p>'+(es?'Rareza':'Rarity')+'</p><p>Oro</p><p>'+(es?'Liga':'League')+'</p><p>Liga prueba</p><p>Club</p><p>Club prueba</p><p>'+(es?'País/región':'Country/Region')+'</p><p>País prueba</p></article>'}
function show(next){kind=next;document.getElementById('detail').innerHTML='';let html='';
if(next==='club')html='<h1 onclick="show(&quot;inventory&quot;)">'+(es?'Jugadores':'Players')+'</h1>';
if(next==='squads')html='<h1 onclick="show(&quot;squad&quot;)">'+(es?'Plantilla activa':'Active Squad')+'</h1>';
if(next==='inventory'){let order=Array.from({length:20},(_,i)=>i);if(reverse)order.reverse();html='<h1>'+(es?'Jugadores de mi club':'My Club Players')+'</h1><ul>'+order.map(i=>'<li class="listFUTItem" onclick="choose('+i+')">'+card(i)+'</li>').join('')+'</ul>'}
if(next==='squad')html='<div>4-3-3</div><div class="ut-squad-pitch-view">'+Array.from({length:11},(_,i)=>'<div class="ut-squad-slot-view" onclick="choose('+i+')"><div class="ut-squad-slot-pedestal-view"><span class="label">'+positions[i]+'</span><span>++</span></div>'+card(i)+'</div>').join('')+'</div><div class="ut-squad-slot-dock-view">'+Array.from({length:7},(_,n)=>'<div class="ut-squad-slot-view" onclick="choose('+(n+11)+')">'+card(n+11)+'</div>').join('')+'<p>'+(es?'Arrastra jugadores para cambiar suplentes':'Drag any player to and from the pitch to swap subs')+'</p></div>';
document.getElementById('view').innerHTML=html}
show('inventory');
</script></body></html>`}

for(const spanish of [false,true])test(`automatic open ${spanish?'ES':'EN'}: 20 copies twice again, XI and seven locked`,async()=>{
 test.setTimeout(300000)
 let base=''
 const server=http.createServer(async(req,res)=>{
  const chunks:Buffer[]=[];for await(const chunk of req)chunks.push(Buffer.from(chunk))
  const headers=Object.fromEntries(Object.entries(req.headers).filter(([,v])=>typeof v==='string')) as Record<string,string>
  // Nginx forwards Host $host without the test proxy's ephemeral port.
  if(headers.origin===base)headers.origin='http://localhost'
  const proxy=http.request((process.env.READER_TEST_UPSTREAM||'http://nginx')+req.url,{method:req.method,headers:{...headers,host:'localhost:8090'}},r=>{res.writeHead(r.statusCode||502,r.headers);r.pipe(res)})
  proxy.on('error',()=>{res.statusCode=502;res.end()});proxy.end(Buffer.concat(chunks))
 })
 await new Promise<void>(resolve=>server.listen(0,'0.0.0.0',resolve))
 base='http://localhost:'+(server.address() as import('node:net').AddressInfo).port
 const extension=path.resolve('.output/chrome-mv3'),manifest=JSON.parse(fs.readFileSync(path.join(extension,'manifest.json'),'utf8'))
 expect(manifest.permissions).not.toContain('cookies');expect(manifest.permissions).not.toContain('debugger')
 expect(manifest.host_permissions).toEqual(['http://localhost/*','http://127.0.0.1/*','https://www.ea.com/*'])
 const context=await chromium.launchPersistentContext('',{channel:'chromium',headless:true,args:[`--disable-extensions-except=${extension}`,`--load-extension=${extension}`]})
 try{
  await context.route('https://www.ea.com/**',route=>route.fulfill({contentType:'text/html; charset=utf-8',body:fixture(spanish)}))
  const ea=await context.newPage()
  ea.on('pageerror',error=>console.log('AUTO_FIXTURE_ERROR '+error.message))
  ea.on('console',message=>{if(message.text().startsWith('Club Lab reader stopped:'))console.log(message.text())})
  await ea.goto('https://www.ea.com/ea-sports-fc/ultimate-team/web-app/')
  await expect(ea.locator('li.listFUTItem')).toHaveCount(20)
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
   await expect.poll(async()=>{status=await request('/browser-auto/status');return !!status.request_id&&status.request_id!==previous&&!['disabled','ready','reading'].includes(status.status)},{timeout:100000}).toBe(true)
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
  await expect(activate).toBeEnabled({timeout:15000});await activate.click()
  const panel=page.getByRole('region',{name:'Actualización automática del club'})
  await waitUpdated()
  await expect(panel).toContainText('principal y suplentes protegidos',{timeout:100000})
  // Refresh request headers after the SPA creates its entry; the extension never gets them.
  await refreshHeaders()
  const first=await request('/players?limit=100'),ids=first.items.map((c:any)=>c.id).sort((a:number,b:number)=>a-b)
  expect(first.total).toBe(20)
  const main=await request('/squads/main');expect(main.complete).toBe(true);expect(main.protected_copy_ids).toHaveLength(18)
  let receipt=(await request('/browser-auto/status')).result.request_id
  for(let pass=0;pass<2;pass++){
   await ea.evaluate('reverse = !reverse')
   await page.reload()
   await waitUpdated(receipt)
   await expect(panel).toContainText('principal y suplentes protegidos',{timeout:100000})
   await refreshHeaders()
   await expect.poll(async()=>(await request('/browser-auto/status')).result.request_id,{timeout:100000}).not.toBe(receipt)
   const state=await request('/browser-auto/status');receipt=state.result.request_id
   expect(state.result.pending).toEqual([])
   const cards=await request('/players?limit=100');expect(cards.total).toBe(20)
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
  expect((await request('/players')).total).toBe(20)
  expect((await request('/squads/main')).protected_copy_ids).toEqual(main.protected_copy_ids)
  console.log('AUTO_SYNTHETIC '+JSON.stringify({language:spanish?'es':'en',cards:20,reopens:2,protected:18,real_club:false}))
 }catch(error){for(const tab of context.pages())if(tab.url().startsWith('https://www.ea.com/'))console.log('AUTO_SYNTHETIC_LAST_VIEW '+(await tab.locator('body').innerText()).slice(0,600));throw error}
 finally{await context.close();await new Promise<void>(resolve=>server.close(()=>resolve()))}
})
