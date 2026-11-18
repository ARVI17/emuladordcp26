// Runs in the isolated extension world, on the official Web App only.
// Only rendered DOM and navigation controls: no page JS objects, network hooks,
// cookies, EA credentials, screenshots, trade actions or final submissions.
export default defineUnlistedScript(()=>{
 const world=globalThis as typeof globalThis&{clubLabAutoInstalled?:boolean}
 if(world.clubLabAutoInstalled)return
 world.clubLabAutoInstalled=true
 console.info('Club Lab visible reader: 0.7.3')
 let cancelled=false,running=false,deadline=0,phase='idle',activeStep=''
 let currentOrdinal:number|undefined
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
 const loginVisible=()=>all('input[type=password]').length>0||
  byLabel('button',['Login','Log in','Sign in','Iniciar sesión']).length>0||
  byLabel('h1,h2',['Cannot Authenticate','No se puede autenticar']).length>0
 const check=(requireSession=true)=>{
  if(cancelled)throw Error('cancelled')
  if(Date.now()>deadline)throw Error('timeout')
  if(location.origin!=='https://www.ea.com'||!/^\/(?:[a-z]{2}-[a-z]{2}\/)?ea-sports-fc\/ultimate-team\/web-app\/$/.test(location.pathname))throw Error('page_changed')
  if(requireSession&&loginVisible())throw Error('login_required')
 }
 const wait=async<T>(read:()=>T|undefined,ms=10000,requireSession=true):Promise<T>=>{
  const until=Date.now()+ms
  while(Date.now()<until){check(requireSession);const value=read();if(value!==undefined)return value;await new Promise(r=>setTimeout(r,150))}
  throw Error('page_changed')
 }
 type Control=HTMLElement|(()=>HTMLElement|undefined)
 const unique=(elements:HTMLElement[])=>elements.length===1?elements[0]:undefined
 const surface=(e:HTMLElement)=>{
  if(!e.isConnected||!visible(e)||e.matches(':disabled,[aria-disabled="true"]'))return
  const rect=e.getBoundingClientRect()
  const clientX=rect.left+rect.width/2,clientY=rect.top+rect.height/2
  if(!rect.width||!rect.height||clientX<0||clientY<0||clientX>=innerWidth||clientY>=innerHeight)return
  const target=document.elementFromPoint(clientX,clientY)
  if(!target||!e.contains(target))return
  const nested=target.closest('a,button,input,select,textarea,[role="button"]')
  if(nested&&nested!==e&&e.contains(nested))return
  return {target,clientX,clientY}
 }
 const click=async(control:Control)=>{
  let scrolled:HTMLElement|undefined
  const {target,clientX,clientY}=await wait(()=>{
   const e=typeof control==='function'?control():control
   if(!e)return
   const reachable=surface(e)
   if(reachable)return reachable
   // Scrolling a clipped pitch would move the pitch behind the dock. EA
   // exposes buttons for opening the docks. Ordinary lists can scroll.
   if(e.isConnected&&visible(e)&&e!==scrolled&&!e.closest('.ut-draggable')){
    scrolled=e
    e.scrollIntoView({block:'center',inline:'nearest',behavior:'instant'})
   }
  })
  const point={clientX,clientY,button:0,bubbles:true,cancelable:true,composed:true,view:window}
  target.dispatchEvent(new PointerEvent('pointerdown',{...point,buttons:1,pointerId:1,pointerType:'mouse',isPrimary:true}))
  target.dispatchEvent(new MouseEvent('mousedown',{...point,buttons:1}))
  await new Promise(r=>setTimeout(r,40));check()
  target.dispatchEvent(new PointerEvent('pointerup',{...point,buttons:0,pointerId:1,pointerType:'mouse',isPrimary:true}))
  target.dispatchEvent(new MouseEvent('mouseup',{...point,buttons:0}))
  if(target.isConnected&&visible(target))target.dispatchEvent(new MouseEvent('click',{...point,buttons:0,detail:1}))
  await new Promise(r=>setTimeout(r,180));check()
 }
 const labelled=(selector:string,labels:string[])=>click(()=>unique(byLabel(selector,labels)))
 const bioTitles=['Player Bio','Datos del jugador','Biografía del jugador','Biografía']
 const detailTitles=['Player Details','Detalles del jugador','Datos del futbolista']
 const back=(titles:string[])=>click(()=>{
  // In EA the visible back arrow is generated by CSS. Each open view has
  // its own navigation bar, so pair the arrow with the current heading.
  const bars=byLabel('h1',titles).map(e=>e.closest<HTMLElement>('.ut-navigation-bar-view')).filter((e):e is HTMLElement=>!!e)
  if(bars.length){
   if(bars.length!==1)return
   return unique(all('button.ut-navigation-button-control',bars[0]).filter(b=>
    b.textContent?.includes('\uE09B')||getComputedStyle(b,'::before').content.includes('\uE09B')||
    ['back','atras','volver'].includes(norm(b.getAttribute('aria-label')||''))))
  }
  return unique(buttons().filter(e=>e.textContent?.trim()==='\uE09B'))
 })
 const clubName=()=>{
  const value=text('.view-navbar-clubinfo-name',document)
  if(!value||value.length>100||/@|password|contrase[nñ]a/i.test(value))throw Error('page_changed')
  return value
 }
 const waitForClub=async()=>{
  let loginSince:number|undefined
  return wait(()=>{
   if(loginVisible()){
    loginSince??=Date.now()
    if(Date.now()-loginSince>2500)throw Error('login_required')
    return
   }
   loginSince=undefined
   if(text('.view-navbar-clubinfo-name',document))return clubName()
  },20000,false)
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
 const loadedCard=(e:HTMLElement,allowMissingName=false)=>{
  if(!text('div.rating',e)||!text('div.position',e)||(!allowMissingName&&!text('div.name',e)))return
  return basic(e,allowMissingName)
 }
 type Card=ReturnType<typeof basic>&ReturnType<typeof bioFields>&{ordinal:number;location:'club'|'squad';slot:string|null;alternate_positions:string[]|null}
 const detailed=async(root:HTMLElement,ordinal:number,location:'club'|'squad',slot:string|null):Promise<Card>=>{
  currentOrdinal=ordinal
  phase=location+'.select'
  // The real pitch hides the name; obtain it only after opening the visible bio.
  const before=basic(root,location==='squad')
  await click(root)
  phase=location+'.open_bio'
  await labelled('button',bioTitles)
  phase=location+'.read_bio'
  const {bio,bioCard,facts}=await wait(()=>{
   const bio=unique(all('article.ut-player-bio-view'))
   if(!bio)return
   const bioCard=loadedCard(bio)
   if(!bioCard||(before.name&&before.name!==bioCard.name)||before.rating!==bioCard.rating||before.position!==bioCard.position)return
   const facts=bioFields(bio)
   if(facts.card_type)return {bio,bioCard,facts}
  })
  const alternatives=all('.alternate-positions .position,.alternative-positions .position',bio).map(e=>pos(clean(e.textContent)))
  const record={...bioCard,...facts,attributes:bioCard.attributes||before.attributes,ordinal,location,slot,
   alternate_positions:alternatives.length?Array.from(new Set(alternatives)):null}
  phase=location+'.close_bio'
  await back(bioTitles)
  await wait(()=>all('article.ut-player-bio-view').length===0?true:undefined)
  if(byLabel('h1',detailTitles).length){
   phase=location+'.close_detail'
   await back(detailTitles)
   await wait(()=>byLabel('h1',detailTitles).length===0?true:undefined)
  }
  return record
 }
 const inventoryRows=()=>all('li.listFUTItem').filter(row=>!row.closest('article.ut-player-bio-view'))
 const disabled=(e:HTMLElement)=>e.hasAttribute('disabled')||e.getAttribute('aria-disabled')==='true'||e.classList.contains('disabled')
 const pager=(direction:'next'|'previous')=>{
  const labels=direction==='next'?['Next','Siguiente']:['Previous','Anterior']
  const found=buttons().filter(e=>labels.some(label=>norm(e.textContent||'')===norm(label)||norm(e.getAttribute('aria-label')||'')===norm(label)||norm(e.getAttribute('title')||'')===norm(label)))
  if(found.length>1)throw Error('page_changed')
  return found[0]
 }
 const pageFrame=()=>{
  const rows=inventoryRows(),cards=rows.map(row=>loadedCard(row))
  if(!cards.length||cards.some(card=>!card))return
  const signature=JSON.stringify(cards.map(card=>JSON.stringify(card)).sort())
  return {rows,cards,signature}
 }
 const move=async(direction:'next'|'previous')=>{
  phase='inventory.'+direction
  const control=pager(direction);if(!control||disabled(control))throw Error('page_changed')
  const before=(await wait(pageFrame)).signature
  await click(control)
  await wait(()=>{const page=pageFrame();if(page&&page.signature!==before)return page},20000)
 }
 const readInventory=async(first:boolean,offset:number)=>{
  phase='inventory.navigation'
  if(first){
   await labelled('nav button',['Club'])
   await labelled('h1,h2,button',['Players','Jugadores'])
   const resetLabels=['Reset','Restablecer','Reiniciar']
   const searchLabels=['Search','Buscar']
   const view=await wait(()=>{
    if(pageFrame())return 'results'
    if(unique(byLabel('button',resetLabels))&&unique(byLabel('button',searchLabels)))return 'filters'
   })
   if(view==='filters'){
    await labelled('button',resetLabels)
    await labelled('button',searchLabels)
    await wait(pageFrame)
   }
   // Do not silently start in the middle of a previous search.
   for(let n=0;n<50;n++){
    const previous=pager('previous');if(!previous||disabled(previous))break
    await move('previous');if(n===49)throw Error('page_changed')
   }
  }else await move('next')
  const {cards:expected,signature}=await wait(pageFrame)
  const count=expected.length,result:Card[]=[]
  if(!count||count>30||offset+count>1000)throw Error('page_changed')
  for(let i=0;i<count;i++){
   phase='inventory.restore_list'
   const root=await wait(()=>{
    const row=inventoryRows()[i]
    if(row&&JSON.stringify(loadedCard(row))===JSON.stringify(expected[i]))return row
   })
   result.push(await detailed(root,offset+i,'club',null))
  }
  const next=pager('next')
  // The observed final EA page removes Next rather than disabling it. Require
  // the recognized list plus Previous (or a short first page), not absence alone.
  const terminalList=byLabel('h1',['My Club Players','Jugadores de mi club']).length===1&&(!!pager('previous')||count<20)
  return {cards:result,signature,end:next?(disabled(next)?'end':'next'):terminalList?'end':'unknown'}
 }
 const squadSlots=()=>all('.ut-squad-slot-view').filter(e=>all('div.rating',e).length>0)
 const isOpenDock=(toggle:HTMLElement)=>toggle.classList.contains('ui-direction-down')||toggle.getAttribute('aria-expanded')==='true'
 const showSlot=async(root:HTMLElement,slot:string)=>{
  if(surface(root))return
  const toggles=all('button.dockTab')
  const dock=root.closest('.ut-squad-slot-dock-view')
  if(!toggles.length)return
  if(!dock){
   const open=unique(toggles.filter(isOpenDock))
   if(open)await click(open)
   return
  }
  const labels=slot.startsWith('BENCH-')?['subs','suplentes']:['res','reserves','reservas']
  const toggle=unique(toggles.filter(e=>labels.includes(norm(e.textContent||''))))
  if(toggle&&!isOpenDock(toggle))await click(toggle)
 }
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
  const expected=await wait(()=>{
   const cards=squadSlots().map(e=>loadedCard(e,true))
   if(cards.length===slots.length&&cards.every(Boolean))return cards
  })
  for(let i=0;i<slots.length;i++){
   currentOrdinal=i
   phase='squad.show_slot'
   const root=await wait(()=>{
    const candidate=squadSlots()[i]
    if(candidate&&JSON.stringify(loadedCard(candidate,true))===JSON.stringify(expected[i]))return candidate
   })
   const slot=slots[i]!
   await showSlot(root,slot)
   result.push(await detailed(root,i,'squad',slot))
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
  phase='session';currentOrdinal=undefined
  addEventListener('pointerdown',interrupted,true);addEventListener('keydown',interrupted,true)
  reply({ok:true})
  void (async()=>{
   let result:object
   try{
    const name=await waitForClub()
    const club_fingerprint=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(norm(name))))).map(n=>n.toString(16).padStart(2,'0')).join('')
    const data=message.phase==='squad'?await readSquad():await readInventory(message.phase==='inventory-start',message.offset)
    check();if(clubName()!==name)throw Error('page_changed')
    result={ok:true,data:{...data,identity:{club_fingerprint,club_name:name}}}
   }catch(error){
    const code=error instanceof Error?error.message:''
    const reason=['cancelled','timeout','login_required'].includes(code)?code:'page_changed'
    console.warn('Club Lab reader stopped: '+phase+(currentOrdinal===undefined?'':' #'+(currentOrdinal+1))+' ('+reason+')')
    result={ok:false,reason}
   }
   finally{running=false;removeEventListener('pointerdown',interrupted,true);removeEventListener('keydown',interrupted,true)}
   lastResult={kind:'browser-auto-step-result',request_id:message.request_id,step:message.step,...result}
   await deliver(lastResult)
  })()
 })
})
