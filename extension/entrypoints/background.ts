import {reading,endpoint,admitted,eaDiagnostic,hash,forbidden} from '../lib/contracts'
type State={base:string;credential?:string;binding?:string;pending:Record<string,unknown>[];sequence:number;stream:string;message?:string;lastReceipt?:unknown;proposal?:unknown}
const initial=():State=>({base:'http://localhost:8080',pending:[],sequence:0,stream:crypto.randomUUID()})
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
  chrome.action.onClicked.addListener(tab=>{if(tab.id)void chrome.sidePanel.open({tabId:tab.id})})
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
      if(message.kind==='status')return {ok:true,extensionId:chrome.runtime.id,pending:s.pending.length,message:s.message,receipt:s.lastReceipt,proposal:s.proposal,paired:!!s.credential,base:s.base}
      if(message.kind==='pair'){
        if(s.pending.length)throw Error('Hay lotes pendientes; envíalos o desconecta antes de cambiar el contexto')
        const base=endpoint(String(message.base)), claim={pairing_id:String(message.pairing_id),code:String(message.code)}
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
        await save(initial());return {ok:true}
      }
      if(message.kind==='retry'){await flush(s);return {ok:true}}
      if(message.kind==='analyze'){s.proposal=await request(s,'proposal');await save(s);return {ok:true}}
      if(message.kind==='activate'){
        if(!s.credential)throw Error('Empareja antes de activar')
        const [tab]=await chrome.tabs.query({active:true,lastFocusedWindow:true})
        if(!tab?.id||!tab.url||!admitted(tab.url))throw Error('No hay extractor FC27 real contrastado. Abre una muestra admitida o usa Diagnóstico mínimo.')
        await pause()
        const [doc]=await chrome.scripting.executeScript({target:{tabId:tab.id},files:['reader.js']})
        if(!doc?.documentId)throw Error('Documento no disponible')
        const active={tabId:tab.id,documentId:doc.documentId,documentRef:crypto.randomUUID(),nonce:crypto.randomUUID()}
        await chrome.storage.session.set({active})
        return await chrome.tabs.sendMessage(tab.id,{kind:'start',...active})
      }
      if(message.kind==='diagnose'){
        const [tab]=await chrome.tabs.query({active:true,lastFocusedWindow:true})
        if(!tab?.id||!tab.url||!eaDiagnostic(tab.url))throw Error('Abre la Web App oficial y selecciona solo el texto de una carta o requisito visible.')
        const [result]=await chrome.scripting.executeScript({target:{tabId:tab.id},func:()=>{
          const selection=window.getSelection(),el=selection?.anchorNode?.parentElement
          if(!el||!selection?.rangeCount||selection.toString().length>240||el.closest('input,textarea,[contenteditable]')||document.querySelector('input[type=password]'))return {blocked:true}
          const text=selection.toString().trim()
          if(!text||/password|contrase[nñ]a|token|cookie|@|login|sign in|verification|bearer/i.test(text))return {blocked:true}
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
