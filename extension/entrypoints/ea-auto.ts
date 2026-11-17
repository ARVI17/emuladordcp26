// Runs in the isolated extension world, on the official Web App only.
// Only rendered DOM and navigation controls: no page JS objects, network hooks,
// cookies, EA credentials, screenshots, trade actions or final submissions.
export default defineUnlistedScript(()=>{
 const world=globalThis as typeof globalThis&{clubLabAutoInstalled?:boolean}
 if(world.clubLabAutoInstalled)return
 world.clubLabAutoInstalled=true
 let cancelled=false,running=false,deadline=0,phase='idle',activeStep=''
 let lastResult:Record<string,unknown>|undefined
 const deliver=async(result:Record<string,unknown>)=>{
  for(let i=0;i<3;i++){try{await chrome.runtime.sendMessage(result);return}catch{await new Promise(r=>setTimeout(r,1000))}}
 }
 const positions:Record<string,string>={GK:'POR',RB:'LD',CB:'DFC',LB:'LI',RWB:'CAD',LWB:'CAI',CDM:'MCD',CM:'MC',CAM:'MCO',RM:'MD',LM:'MI',RW:'ED',LW:'EI',CF:'SD',ST:'DC'}
 const validPositions=new Set(['POR','LD','DFC','LI','CAD','CAI','MCD','MC','MCO','MD','MI','ED','EI','SD','DC'])
 const stats:Record<string,string>={PAC:'pace',RIT:'pace',SHO:'shooting',TIR:'shooting',PAS:'passing',DRI:'dribbling',REG:'dribbling',DEF:'defending',PHY:'physical',FIS:'physical',DIV:'diving',EST:'diving',HAN:'handling',PAR:'handling',KIC:'kicking',SAQ:'kicking',REF:'reflexes',SPD:'speed',VEL:'speed',POS:'positioning',COL:'positioning'}
 const visible=(e:Element)=>e.getClientRects().length>0&&getComputedStyle(e).visibility!=='hidden'&&getComputedStyle(e).display!=='none'
 const clean=(s:string|null)=>String(s||'').replace(/[\uE000-\uF8FF]/g,'').replace(/\s+/g,' ').trim()
 const norm=(s:string)=>clean(s).normalize('NFD').replace(/\p{Diacritic}/gu,'').toLowerCase()
 const all=(selector:string,root:ParentNode=document)=>Array.from(root.querySelectorAll<HTMLElement>(selector)).filter(visible)
 const text=(selector:string,root:ParentNode)=>clean(all(selector,root)[0]?.textContent||'')
 const pos=(s:string)=>{const p=positions[s]||s;if(!validPositions.has(p))throw Error('page_changed');return p}
 const buttons=()=>all('button')
 const byLabel=(selector:string,labels:string[])=>all(selector).filter(e=>labels.some(label=>norm(e.textContent||'')===norm(label)))
 const check=()=>{
  if(cancelled)throw Error('cancelled')
  if(Date.now()>deadline)throw Error('timeout')
  if(location.origin!=='https://www.ea.com'||!/^\/(?:[a-z]{2}-[a-z]{2}\/)?ea-sports-fc\/ultimate-team\/web-app\/$/.test(location.pathname))throw Error('page_changed')
  if(all('input[type=password]').length||byLabel('button',['Login','Log in','Sign in','Iniciar sesión']).length||byLabel('h1,h2',['Cannot Authenticate','No se puede autenticar']).length)throw Error('login_required')
 }
 const wait=async<T>(read:()=>T|undefined,ms=10000):Promise<T>=>{
  const until=Date.now()+ms
  while(Date.now()<until){check();const value=read();if(value!==undefined)return value;await new Promise(r=>setTimeout(r,150))}
  throw Error('page_changed')
 }
 const click=async(e:HTMLElement)=>{
  check();if(!visible(e))throw Error('page_changed')
  // EA navigation uses a press/release gesture; HTMLElement.click() alone left
  // the real Squads button unchanged. Use DOM input events, never page internals.
  const rect=e.getBoundingClientRect(),point={clientX:rect.left+rect.width/2,clientY:rect.top+rect.height/2,button:0,bubbles:true,cancelable:true,composed:true,view:window}
  e.dispatchEvent(new PointerEvent('pointerdown',{...point,buttons:1,pointerId:1,pointerType:'mouse',isPrimary:true}))
  e.dispatchEvent(new MouseEvent('mousedown',{...point,buttons:1}))
  await new Promise(r=>setTimeout(r,40));check()
  e.dispatchEvent(new PointerEvent('pointerup',{...point,buttons:0,pointerId:1,pointerType:'mouse',isPrimary:true}))
  e.dispatchEvent(new MouseEvent('mouseup',{...point,buttons:0}))
  if(e.isConnected&&visible(e))e.dispatchEvent(new MouseEvent('click',{...point,buttons:0,detail:1}))
  await new Promise(r=>setTimeout(r,180));check()
 }
 const labelled=async(selector:string,labels:string[])=>{
  const e=await wait(()=>{const found=byLabel(selector,labels);return found.length===1?found[0]:undefined})
  await click(e)
 }
 const back=async()=>{
  const candidates=buttons().filter(e=>(e.textContent||'').trim()==='\uE09B')
  const e=candidates.at(-1);if(!e)throw Error('page_changed');await click(e)
 }
 const clubName=()=>{
  const value=text('.view-navbar-clubinfo-name',document)
  if(!value||value.length>100||/@|password|contrase[nñ]a/i.test(value))throw Error('page_changed')
  return value
 }
 const basic=(root:HTMLElement,allowMissingName=false)=>{
  const name=text('div.name',root),rating=Number(text('div.rating',root)),position=pos(text('div.position',root))
  if((!name&&!allowMissingName)||name.length>100||!Number.isInteger(rating)||rating<40||rating>99)throw Error('page_changed')
  const attributes:Record<string,number>={}
  for(const line of all('.player-stats-data-component li',root)){
   const m=clean(line.textContent).match(/^([A-ZÁÉÍÓÚ]{2,3})\s*(\d{1,2})$/)
   const key=m?.[1]?stats[m[1]]:undefined
   if(m&&key)attributes[key]=Number(m[2])
  }
  // Some pitch cards omit attributes; the bio shows the complete visible card.
  return {name,rating,position,attributes:Object.keys(attributes).length===6?attributes:null}
 }
 const bioFields=(bio:HTMLElement)=>{
  const lines=bio.innerText.split('\n').map(clean).filter(Boolean)
  const value=(labels:string[])=>{const i=lines.findIndex(l=>labels.some(label=>norm(l)===norm(label)));return i>=0&&lines[i+1]&&lines[i+1]!=='---'?lines[i+1]:null}
  return {card_type:value(['Rarity','Rareza']),league:value(['League','Liga']),club:value(['Club']),nationality:value(['Country/Region','País/región','Pais/Region','Nacionalidad'])}
 }
 type Card=ReturnType<typeof basic>&ReturnType<typeof bioFields>&{ordinal:number;location:'club'|'squad';slot:string|null;alternate_positions:string[]|null}
 const detailed=async(root:HTMLElement,ordinal:number,location:'club'|'squad',slot:string|null):Promise<Card>=>{
  phase=location+'.select'
  // The real pitch hides the name; obtain it only after opening the visible bio.
  const before=basic(root,location==='squad')
  await click(root)
  phase=location+'.open_bio'
  await labelled('button',['Player Bio','Datos del jugador','Biografía del jugador'])
  const bio=await wait(()=>all('article.ut-player-bio-view').find(e=>bioFields(e).card_type!==null))
  phase=location+'.read_bio'
  const facts=bioFields(bio)
  // Card names can be abbreviated in both views; reject a changed selection.
  const bioCard=basic(bio)
  if((before.name&&before.name!==bioCard.name)||before.rating!==bioCard.rating||before.position!==bioCard.position)throw Error('page_changed')
  const alternatives=all('.alternate-positions .position,.alternative-positions .position',bio).map(e=>pos(clean(e.textContent)))
  const record={...bioCard,...facts,attributes:bioCard.attributes||before.attributes,ordinal,location,slot,
   alternate_positions:alternatives.length?Array.from(new Set(alternatives)):null}
  await back()
  phase=location+'.close_bio'
  await wait(()=>all('article.ut-player-bio-view').length===0?true:undefined)
  if(location==='squad'&&byLabel('h1',['Player Details','Detalles del jugador']).length){
   await back()
   await wait(()=>byLabel('h1',['Player Details','Detalles del jugador']).length===0?true:undefined)
  }
  return record
 }
 const inventoryRows=()=>all('li.listFUTItem')
 const disabled=(e:HTMLElement)=>e.hasAttribute('disabled')||e.getAttribute('aria-disabled')==='true'||e.classList.contains('disabled')
 const pager=(direction:'next'|'previous')=>{
  const labels=direction==='next'?['Next','Siguiente']:['Previous','Anterior']
  const found=buttons().filter(e=>labels.some(label=>norm(e.textContent||'')===norm(label)||norm(e.getAttribute('aria-label')||'')===norm(label)||norm(e.getAttribute('title')||'')===norm(label)))
  if(found.length>1)throw Error('page_changed')
  return found[0]
 }
 const pageSignature=()=>JSON.stringify(inventoryRows().map(e=>basic(e)).sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b))))
 const move=async(direction:'next'|'previous')=>{
  const control=pager(direction);if(!control||disabled(control))throw Error('page_changed')
  const before=pageSignature();await click(control)
  await wait(()=>inventoryRows().length>0&&pageSignature()!==before?true:undefined,20000)
 }
 const readInventory=async(first:boolean,offset:number)=>{
  phase='inventory.navigation'
  if(first){
   await labelled('nav button',['Club'])
   await labelled('h1,h2,button',['Players','Jugadores'])
   const reset=byLabel('button',['Reset','Restablecer','Reiniciar']).length===1
   if(reset)await labelled('button',['Reset','Restablecer','Reiniciar'])
   if(byLabel('button',['Search','Buscar']).length===1&&(reset||inventoryRows().length===0))await labelled('button',['Search','Buscar'])
   await wait(()=>inventoryRows().length>0?true:undefined)
   // Do not silently start in the middle of a previous search.
   for(let n=0;n<50;n++){
    const previous=pager('previous');if(!previous||disabled(previous))break
    await move('previous');if(n===49)throw Error('page_changed')
   }
  }else await move('next')
  const count=inventoryRows().length,result:Card[]=[]
  if(!count||count>30||offset+count>1000)throw Error('page_changed')
  const signature=pageSignature(),expected=inventoryRows().map(e=>basic(e))
  for(let i=0;i<count;i++){
   const root=inventoryRows()[i]
   if(!root||JSON.stringify(basic(root))!==JSON.stringify(expected[i]))throw Error('page_changed')
   result.push(await detailed(root,offset+i,'club',null))
  }
  const next=pager('next')
  return {cards:result,signature,end:next?(disabled(next)?'end':'next'):'unknown'}
 }
 const squadSlots=()=>all('.ut-squad-slot-view').filter(e=>all('div.rating',e).length>0)
 const readSquad=async()=>{
  phase='squad.navigation.squads'
  await labelled('nav button',['Squads','Plantillas'])
  phase='squad.navigation.active'
  await labelled('h1,h2,button',['Active Squad','Plantilla activa'])
  phase='squad.navigation.slots'
  await wait(()=>squadSlots().length>=18?true:undefined)
  const formations=Array.from(new Set(all('button,option,span,div').filter(e=>e.children.length===0).map(e=>clean(e.textContent)).filter(v=>/^\d(?:-\d){2,4}(?:\s*\(\d\))?$/.test(v))))
  if(formations.length!==1)throw Error('page_changed')
  const counts:Record<string,number>={},slots=squadSlots().map(e=>{
   const label=text('.ut-squad-slot-pedestal-view .label',e)
   const dock=e.closest<HTMLElement>('.ut-squad-slot-dock-view')
   // Both real docks have the same class: use their rendered, explicit captions.
   const caption=norm(dock?.innerText||'')
   const prefix=dock?(/\breserves\b|\breservas\b/.test(caption)?'RESERVE':/\bsubs\b|\bsuplentes\b/.test(caption)?'BENCH':null):pos(label)
   if(!prefix)throw Error('page_changed')
   counts[prefix]=(counts[prefix]||0)+1
   return `${prefix}-${counts[prefix]}`
  })
  if(slots.length>30||slots.filter(s=>s.startsWith('BENCH-')).length!==7||slots.filter(s=>!s.startsWith('BENCH-')&&!s.startsWith('RESERVE-')).length!==11)throw Error('page_changed')
  const result:Card[]=[]
  const expected=squadSlots().map(e=>basic(e,true))
  for(let i=0;i<slots.length;i++){
   const root=squadSlots()[i];if(!root||JSON.stringify(basic(root,true))!==JSON.stringify(expected[i]))throw Error('page_changed')
   result.push(await detailed(root,i,'squad',slots[i]!))
  }
  return {cards:result,formation:formations[0]}
 }
 // User interaction cancels the current stage. No private page objects or network hooks.
 const interrupted=(event:Event)=>{if(event.isTrusted)cancelled=true}
 chrome.runtime.onMessage.addListener((message,sender,reply)=>{
  if(sender.id!==chrome.runtime.id)return
  if(message?.kind==='ea-auto-stop'){cancelled=true;reply({ok:true});return}
  if(message?.kind!=='ea-auto-step')return
  if(running){reply({ok:activeStep===message.step,reason:'busy'});return}
  if(lastResult&&lastResult.step===message.step){reply({ok:true});void deliver(lastResult);return}
  if(!['squad','inventory-start','inventory-next'].includes(message.phase)||!Number.isInteger(message.offset)||message.offset<0||message.offset>999){reply({ok:false});return}
  running=true;cancelled=false;activeStep=message.step;deadline=Date.now()+120000
  addEventListener('pointerdown',interrupted,true);addEventListener('keydown',interrupted,true)
  reply({ok:true})
  void (async()=>{
   let result:object
   try{
    check()
    // EA can finish loading the document before rendering its signed-in club.
    // Keep checking for Login while waiting; never read credentials or page state.
    const name=await wait(()=>text('.view-navbar-clubinfo-name',document)?clubName():undefined,20000)
    const club_fingerprint=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(norm(name))))).map(n=>n.toString(16).padStart(2,'0')).join('')
    const data=message.phase==='squad'?await readSquad():await readInventory(message.phase==='inventory-start',message.offset)
    check();if(clubName()!==name)throw Error('page_changed')
    result={ok:true,data:{...data,identity:{club_fingerprint,club_name:name}}}
   }catch(error){const code=error instanceof Error?error.message:'';console.warn('Club Lab reader stopped: '+phase);result={ok:false,reason:['cancelled','timeout','login_required'].includes(code)?code:'page_changed'}}
   finally{running=false;removeEventListener('pointerdown',interrupted,true);removeEventListener('keydown',interrupted,true)}
   lastResult={kind:'browser-auto-step-result',request_id:message.request_id,step:message.step,...result}
   await deliver(lastResult)
  })()
 })
})
