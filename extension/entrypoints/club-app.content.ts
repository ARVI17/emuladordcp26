export default defineContentScript({
 matches:['http://localhost/*','http://127.0.0.1/*'],
 runAt:'document_idle',
 main(ctx){
  const channel='club-lab-auto-v1'
  const world=globalThis as typeof globalThis & {disconnectClubLabBridge?:()=>void}
  world.disconnectClubLabBridge?.()
  const receive=(event:MessageEvent)=>{
   const m=event.data
   if(!chrome.runtime?.id||event.source!==window||event.origin!==location.origin||location.pathname!=='/'||location.search||!document.title.includes('Club Lab FC27')||m?.channel!==channel||typeof m.nonce!=='string'||m.nonce.length>40)return
   const reply=(data:object)=>window.postMessage({channel,nonce:m.nonce,...data},location.origin)
   if(m.kind==='discover'){reply({kind:'hello',extension_id:chrome.runtime.id,version:chrome.runtime.getManifest().version});return}
   if(!['start','cancel'].includes(m.kind))return
   void chrome.runtime.sendMessage({kind:'browser-auto-'+m.kind,ticket:m.ticket}).then(r=>reply({kind:'finished',ok:r?.ok===true})).catch(()=>reply({kind:'finished',ok:false}))
  }
  const ping=(message:{kind?:string},sender:chrome.runtime.MessageSender,reply:(value:unknown)=>void)=>{
   if(message?.kind==='club-app-bridge-ping'&&sender.id===chrome.runtime.id)reply({ready:true})
  }
  const disconnect=()=>{
   removeEventListener('message',receive)
   if(chrome.runtime?.id)chrome.runtime.onMessage.removeListener(ping)
   if(world.disconnectClubLabBridge===disconnect)delete world.disconnectClubLabBridge
  }
  world.disconnectClubLabBridge=disconnect
  addEventListener('message',receive)
  chrome.runtime.onMessage.addListener(ping)
  ctx.onInvalidated(disconnect)
 }
})
