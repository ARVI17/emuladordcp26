import {reading,endpoint,admitted,eaDiagnostic,hash,forbidden} from '../lib/contracts'
import {compatibility} from '../lib/compatibility'
import {inspectRegion} from '../lib/inspect-region'
import {sensitiveText} from '../lib/privacy'
import {viewProfile,viewType} from '../lib/view-profile'
import {draftForMap,bindDefinition,extractProfile,saveDefinition,recordSample,recordContrast,activateProfile,EXTRACTOR_REVISION} from '../lib/profile-extraction'
import type {ExtractorProfile,Proof} from '../lib/profile-extraction'
type State={base:string;credential?:string;binding?:string;pending:Record<string,unknown>[];sequence:number;stream:string;message?:string;lastReceipt?:unknown;proposal?:unknown;compatibility?:unknown}
const initial=():State=>({base:'http://localhost:8090',pending:[],sequence:0,stream:crypto.randomUUID()})
export default defineBackground(()=>{
  // Private to extension contexts. No credentials ever go to the content script.
  const ready=Promise.all([chrome.storage.local.setAccessLevel({accessLevel:'TRUSTED_CONTEXTS'}),chrome.storage.session.setAccessLevel({accessLevel:'TRUSTED_CONTEXTS'})])
  let serial=Promise.resolve()
  const state=async():Promise<State>=>(await chrome.storage.local.get('state')).state||initial()
  const save=async(s:State)=>chrome.storage.local.set({state:s})
  const request=async(s:State,path:string,body?:unknown)=>{
    const response=await fetch(endpoint(s.base)+'/api/reader/'+path,{method:body===undefined?'GET':'POST',credentials:'omit',redirect:'error',
      headers:{'Content-Type':'application/json','X-Reader-Extension':chrome.runtime.id,...(s.credential?{Authorization:'Bearer '+s.credential}:{})},
      body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(10000)})
    if(!response.ok)throw Error(`Backend ${response.status}; conserva la cola y revisa el emparejamiento.`)
    return response.json()
  }
  const flush=async(s:State)=>{
    if(!s.credential)throw Error('Empareja primero el lector')
    while(s.pending.length){
      const event=s.pending[0]!,receipt=await request(s,'events',event)
      if(receipt.event_id!==event.event_id)throw Error('Acuse incorrecto; lote conservado')
      s.pending.shift();s.lastReceipt=receipt;s.message='Lote recibido; revisa el lote en Mi cuenta de Club Lab.';await save(s)
    }
  }
  const pause=async()=>{
    const {active}=await chrome.storage.session.get('active')
    if(active)await chrome.tabs.sendMessage(active.tabId,{kind:'pause'}).catch(()=>{})
    await chrome.storage.session.remove('active')
  }
  chrome.action.onClicked.addListener(tab=>{if(tab.id){void chrome.storage.session.set({selectedTab:tab.id,...(tab.url&&eaDiagnostic(tab.url)?{officialTab:tab.id}:{})});void chrome.sidePanel.open({tabId:tab.id})}})
  chrome.tabs.onUpdated.addListener((id,change)=>{if(change.status==='loading')void chrome.storage.session.get('active').then(({active})=>{if(active?.tabId===id)return chrome.storage.session.remove('active')})})
  chrome.permissions.onRemoved.addListener(()=>{void pause()})
  chrome.runtime.onMessage.addListener((message,sender,reply)=>{
    serial=serial.then(async()=>{
      await ready
      if(JSON.stringify(message).length>128000)throw Error('Mensaje demasiado grande')
      const s=await state()
      if(sender.tab && sender.url!==chrome.runtime.getURL('sidepanel.html')){
        const {active}=await chrome.storage.session.get('active')
        if(!active || sender.id!==chrome.runtime.id || sender.frameId!==0 || sender.tab.id!==active.tabId || sender.documentId!==active.documentId || !admitted(sender.url||'') || message.nonce!==active.nonce || message.documentRef!==active.documentRef)throw Error('Documento no activado')
        if(message.kind==='reader-error'){s.message=String(message.message).slice(0,200);await save(s);return {ok:false,error:s.message}}
        if(message.kind!=='observation')throw Error('Mensaje no permitido')
        const data=reading.parse(message.data)
        if(forbidden.test(JSON.stringify(data)))throw Error('Campo sensible rechazado')
        if(!s.binding)throw Error('Empareja antes de leer')
        if(s.pending.length>=100)throw Error('Cola saturada; no se descartaron lotes. Reintenta el envío antes de continuar.')
        const observed=new Date(message.observed_at)
        if(!Number.isFinite(+observed)||Math.abs(Date.now()- +observed)>120000)throw Error('Fecha de lectura inválida')
        const event={...data,event_id:crypto.randomUUID(),schema_version:1,reader_version:'semantic-sample-1',context_binding:s.binding,
          stream_id:s.stream,sequence:s.sequence+1,document_ref:active.documentRef,observed_at:observed.toISOString(),completeness_evidence:'visible_subset'}
        const batch={...event,payload_hash:await hash(event)}
        if(new TextEncoder().encode(JSON.stringify([...s.pending,batch])).length>512000)throw Error('Cola saturada por tamaño; lote no aceptado, vuelve a leer tras enviarla.')
        s.pending.push(batch);s.sequence++;await save(s)
        try{await flush(s)}catch{ s.message='Sin acuse; lote guardado. Pulsa Reintentar envío al recuperar el backend.';await save(s)}
        return {ok:true}
      }
      if(sender.id!==chrome.runtime.id || sender.url!==chrome.runtime.getURL('sidepanel.html'))throw Error('Panel no autorizado')
      if(message.kind==='status')return {ok:true,version:chrome.runtime.getManifest().version,extensionId:chrome.runtime.id,pending:s.pending.length,message:s.message,receipt:s.lastReceipt,proposal:s.proposal,paired:!!s.credential,base:s.base,compatibility:s.compatibility,maps:(await chrome.storage.local.get('viewMaps')).viewMaps||[],profiles:(await chrome.storage.local.get('extractorProfiles')).extractorProfiles||[]}
      if(message.kind==='profile-draft'){
        const {viewMaps=[]}=await chrome.storage.local.get('viewMaps')
        const entry=viewMaps.find((m:any)=>m.map_id===message.map_id)
        if(!entry)throw Error('Selecciona un mapa privado existente.')
        return {ok:true,definition:draftForMap(entry.profile)}
      }
      if(message.kind==='profile-save'){
        const {viewMaps=[],extractorProfiles=[]}=await chrome.storage.local.get(['viewMaps','extractorProfiles'])
        const entry=viewMaps.find((m:any)=>m.map_id===message.definition?.map_id)
        if(!entry)throw Error('Importa una definición vinculada a un mapa privado existente; el archivo no acredita evidencia.')
        const definition=bindDefinition(message.definition,entry.profile,entry.map)
        const previous:ExtractorProfile|undefined=extractorProfiles.find((p:ExtractorProfile)=>p.id===message.profile_id)
        if(message.profile_id&&!previous)throw Error('Perfil no disponible.')
        if(!previous&&extractorProfiles.length>=8)throw Error('Límite de ocho perfiles privados.')
        const profile=await saveDefinition(definition,previous)
        await chrome.storage.session.remove('profileTrial')
        await chrome.storage.local.set({extractorProfiles:[...extractorProfiles.filter((p:ExtractorProfile)=>p.id!==profile.id),profile]})
        return {ok:true,profile}
      }
      if(['profile-test','profile-preview','profile-read','profile-contrast','profile-enable','profile-disable'].includes(message.kind)){
        const {extractorProfiles=[]}=await chrome.storage.local.get('extractorProfiles')
        const profile:ExtractorProfile|undefined=extractorProfiles.find((p:ExtractorProfile)=>p.id===message.profile_id)
        if(!profile)throw Error('Selecciona un perfil guardado.')
        const persist=async(next:ExtractorProfile)=>chrome.storage.local.set({extractorProfiles:extractorProfiles.map((p:ExtractorProfile)=>p.id===next.id?next:p)})
        if(message.kind==='profile-disable'){
          await chrome.storage.session.remove('profileTrial');await persist({...profile,status:'disabled'});return {ok:true}
        }
        if(message.kind==='profile-enable'){await persist(await activateProfile(profile));return {ok:true}}
        if(message.kind==='profile-read'&&profile.status!=='active')throw Error('El perfil no está activo; usa la prueba previa.')
        const {profileTrial}=await chrome.storage.session.get('profileTrial')
        await chrome.storage.session.remove('profileTrial')
        try{
          if(message.kind==='profile-read')await activateProfile(profile)
          const [tab]=await chrome.tabs.query({active:true,lastFocusedWindow:true})
          if(!tab?.id||!tab.url)throw Error('Selecciona la pestaña y la región que vas a comprobar.')
          const sample=message.kind==='profile-test'
          if(sample?!admitted(tab.url):!eaDiagnostic(tab.url))throw Error(sample?'La prueba requiere una muestra local propia.':'La vista real debe estar abierta y autorizada mediante el icono de la extensión.')
          const url=new URL(tab.url)
          if(!sample&&(url.origin!==profile.definition.origin||url.pathname+url.hash!==profile.definition.route))throw Error('Ruta distinta de la revisada en el mapa del perfil.')
          const [result]=await chrome.scripting.executeScript({target:{tabId:tab.id},func:inspectRegion,args:[sensitiveText.source]})
          if(!result?.documentId||!result.result)throw Error('Documento no disponible.')
          if((await chrome.tabs.get(tab.id)).url!==tab.url)throw Error('La vista cambió durante la lectura.')
          if(result.result.blocked)throw Error(result.result.blocked)
          const preview=await extractProfile(profile.definition,result.result)
          const proof:Proof={extractor_revision:EXTRACTOR_REVISION,definition_hash:await hash(profile.definition),observed_at:new Date().toISOString(),document_ref:crypto.randomUUID(),structure_hash:profile.definition.structure_hash,records:preview.records.length}
          const displayed={...preview,provenance:sample?'local_region_preview':'observed_page_preview',extractor_revision:EXTRACTOR_REVISION,profile_id:profile.id,revision:profile.revision,observed_at:proof.observed_at}
          if(sample){await persist(await recordSample(profile,proof));return {ok:true,preview:displayed}}
          if(message.kind==='profile-contrast'){
            if(message.reviewed!==true||!profileTrial||profileTrial.profile_id!==profile.id||profileTrial.revision!==profile.revision||profileTrial.document_id!==result.documentId||profileTrial.tab_id!==tab.id||Date.now()-Date.parse(profileTrial.proof.observed_at)>300000||profileTrial.preview_hash!==await hash(preview))throw Error('Repite la vista previa y compara los campos con la vista real antes de confirmar; la lectura cambió o caducó.')
            await persist(await recordContrast(profile,proof));return {ok:true,preview:displayed}
          }
          await chrome.storage.session.set({profileTrial:{profile_id:profile.id,revision:profile.revision,document_id:result.documentId,tab_id:tab.id,proof,preview_hash:await hash(preview)}})
          return {ok:true,preview:displayed}
        }catch(error){
          if(profile.contrast)await persist({...profile,status:'disabled',contrast:undefined})
          throw error
        }
      }
      if(message.kind==='check'){
        const base=endpoint(String(message.base))
        s.compatibility=await compatibility(base);await save(s);return {ok:true}
      }
      if(message.kind==='pair'){
        if(s.pending.length)throw Error('Hay lotes pendientes; envíalos o desconecta antes de cambiar el contexto')
        const base=endpoint(String(message.base)), claim={pairing_id:String(message.pairing_id),code:String(message.code)}
        if(base!==s.base&&message.confirm_destination!==true)throw Error(`Confirma el cambio de destino de ${s.base} a ${base}; son orígenes distintos.`)
        const compatible=await compatibility(base)
        if(!compatible.compatible)throw Error(compatible.reason)
        if(!/^[0-9]{6}$/.test(claim.code)||! /^[a-f0-9-]{36}$/.test(claim.pairing_id))throw Error('Código o emparejamiento inválido')
        const result=await request({...s,base,credential:undefined},'claim',claim)
        await pause();await save({...initial(),base,credential:result.credential,binding:result.context_binding,message:'Emparejado. Revisa el contexto antes de activar una muestra.'})
        return {ok:true}
      }
      if(message.kind==='pause'){await pause();return {ok:true}}
      if(message.kind==='disconnect'){
        await pause()
        // Do not erase observations silently. The explicit second action discards them.
        if(s.pending.length && message.discard!==true)throw Error(`Hay ${s.pending.length} lotes pendientes. Marca descartar cola si quieres desconectar.`)
        if(s.credential)await request(s,'disconnect',{})
        await save({...initial(),base:s.base});return {ok:true}
      }
      if(message.kind==='retry'){await flush(s);return {ok:true}}
      if(message.kind==='analyze'){s.proposal=await request(s,'proposal');await save(s);return {ok:true}}
      if(message.kind==='activate'){
        if(!s.credential)throw Error('Empareja antes de activar')
        const compatible=await compatibility(s.base)
        if(!compatible.compatible)throw Error(compatible.reason)
        const [tab]=await chrome.tabs.query({active:true,lastFocusedWindow:true})
        if(!tab?.id||!tab.url||!admitted(tab.url))throw Error('No hay extractor FC27 real contrastado. Abre una muestra admitida o usa Diagnóstico mínimo.')
        await pause()
        const [doc]=await chrome.scripting.executeScript({target:{tabId:tab.id},files:['reader.js']})
        if(!doc?.documentId)throw Error('Documento no disponible')
        const active={tabId:tab.id,documentId:doc.documentId,documentRef:crypto.randomUUID(),nonce:crypto.randomUUID()}
        await chrome.storage.session.set({active})
        return await chrome.tabs.sendMessage(tab.id,{kind:'start',...active})
      }
      if(message.kind==='official'){
        const {officialTab}=await chrome.storage.session.get('officialTab')
        const existing=typeof officialTab==='number'?await chrome.tabs.get(officialTab).catch(()=>null):null
        // Only reuse our own tab ID; no history/tabs/all-URLs permission is needed.
        // An unknown URL (lost activeTab grant) must not be navigated or inspected.
        if(existing){await chrome.tabs.update(existing.id!,{active:true});return {ok:true}}
        const tab=await chrome.tabs.create({url:'https://www.ea.com/es-es/ea-sports-fc/ultimate-team/web-app/'})
        await chrome.storage.session.set({officialTab:tab.id});return {ok:true}
      }
      if(message.kind==='select-tab'){
        const [tab]=await chrome.tabs.query({active:true,lastFocusedWindow:true})
        if(!tab?.id||!tab.url||!eaDiagnostic(tab.url))throw Error('Abre EA y pulsa el icono de la extensión en esa pestaña para conceder activeTab. No se solicita tu sesión.')
        await pause();await chrome.storage.session.set({selectedTab:tab.id,officialTab:tab.id})
        s.message='Pestaña oficial seleccionada. Identidad del proveedor sin verificar; navegación guiada.';await save(s);return {ok:true}
      }
      if(message.kind==='delete-maps'){await chrome.storage.local.remove('viewMaps');return {ok:true}}
      if(message.kind==='recognize'){
        await pause()
        const view=viewType.parse(message.view)
        const [tab]=await chrome.tabs.query({active:true,lastFocusedWindow:true})
        if(!tab?.id||!tab.url||(!eaDiagnostic(tab.url)&&!admitted(tab.url)))throw Error('Reconoce desde la pestaña oficial o la muestra propia, usando el icono de la extensión para autorizarla.')
        const source=admitted(tab.url)?'local_region_map':'observed_page_map'
        const [result]=await chrome.scripting.executeScript({target:{tabId:tab.id},func:inspectRegion,args:[sensitiveText.source]})
        if(!result?.documentId||!result.result)throw Error('No se pudo inspeccionar este documento')
        const latest=await chrome.tabs.get(tab.id)
        if(latest.url!==tab.url)throw Error('La pestaña cambió; repite el reconocimiento')
        if(result.result.blocked)throw Error(result.result.blocked)
        const map=result.result
        if(!map.nodes?.length||JSON.stringify(map).length>64000)throw Error('Región vacía o demasiado grande; selecciona una región menor')
        const url=new URL(tab.url),mapId=crypto.randomUUID()
        const structure=map.nodes.map(({parent,tag,selector,role,medium})=>({parent,tag,selector,role,medium}))
        const profile=viewProfile.parse({profile_id:crypto.randomUUID(),revision:1,edition:'FC27',view,
          origin:url.origin,route:url.pathname+url.hash,language:map.language,evidence_origin:source,map_id:mapId,
          structure_hash:await hash(structure),status:'proposed',recognition:[map.root_selector],
          preconditions:['Revisión humana del contexto, selectores y campos','Sin acceso, pago o verificación','Documento estable'],extractors:[],
          loading_selectors:['[aria-busy="true"]','[role="progressbar"]'],
          uncertainties:['Vista declarada por el usuario, todavía no reconocida por un perfil contrastado','Cobertura de una región; no acredita todo el club'],
          transitions:[],extraction_enabled:false,navigation_enabled:false})
        const {viewMaps=[]}=await chrome.storage.local.get('viewMaps')
        if(viewMaps.length>=8)throw Error('Hay ocho mapas privados. Exporta y elimina los revisados antes de acumular más.')
        const entry={map_id:mapId,observed_at:new Date().toISOString(),document_ref:crypto.randomUUID(),profile,map}
        await chrome.storage.local.set({viewMaps:[...viewMaps,entry]})
        s.message='Mapa privado guardado. Revisa su contenido: aún no es un perfil de extracción ni admite cartas.';await save(s)
        return {ok:true}
      }
      if(message.kind==='diagnose'){
        const [tab]=await chrome.tabs.query({active:true,lastFocusedWindow:true})
        if(!tab?.id||!tab.url||!eaDiagnostic(tab.url))throw Error('Abre la Web App oficial y selecciona solo el texto de una carta o requisito visible.')
        const [result]=await chrome.scripting.executeScript({target:{tabId:tab.id},args:[sensitiveText.source],func:(privacyPattern:string)=>{
          const selection=window.getSelection(),el=selection?.anchorNode?.parentElement
          if(!el||!selection?.rangeCount||selection.toString().length>240||el.closest('input,textarea,[contenteditable]')||document.querySelector('input[type=password]'))return {blocked:true}
          const text=selection.toString().trim()
          if(!text||new RegExp(privacyPattern,'i').test(text))return {blocked:true}
          // No HTML, IDs, URLs, input values or activity history are collected.
          return {text,element:el.tagName,ancestors:[el.parentElement?.tagName,el.parentElement?.parentElement?.tagName],children:Array.from(el.children).slice(0,8).map(c=>c.tagName),coverage:'selected_text_only',copy_id:null,variant_id:null}
        }})
        return {ok:true,diagnostic:result?.result}
      }
      throw Error('Acción no permitida')
    }).then(result=>reply(result)).catch(async error=>{const message=error instanceof Error?error.message:'Error local';const current=await state();current.message=message.slice(0,200);await save(current);reply({ok:false,error:message})})
    return true
  })
})
