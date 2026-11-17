export default defineContentScript({
 matches:['http://localhost/*','http://127.0.0.1/*'],
 runAt:'document_idle',
 main(){
  const channel='club-lab-auto-v1'
  addEventListener('message',event=>{
   const m=event.data
   if(event.source!==window||event.origin!==location.origin||location.pathname!=='/'||!document.title.includes('Club Lab FC27')||m?.channel!==channel||typeof m.nonce!=='string'||m.nonce.length>40)return
   const reply=(data:object)=>window.postMessage({channel,nonce:m.nonce,...data},location.origin)
   if(m.kind==='discover'){reply({kind:'hello',extension_id:chrome.runtime.id,version:chrome.runtime.getManifest().version});return}
   if(!['start','cancel'].includes(m.kind))return
   void chrome.runtime.sendMessage({kind:'browser-auto-'+m.kind,ticket:m.ticket}).then(r=>reply({kind:'finished',ok:r?.ok===true})).catch(()=>reply({kind:'finished',ok:false}))
  })
 }
})
