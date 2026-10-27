// Only emits a debounced signal. Extraction/credentials stay in the worker;
// the observer never reads values, navigates, scrolls or presses controls.
export default defineUnlistedScript(()=>{
 const world=globalThis as typeof globalThis&{clubLabWatchInstalled?:boolean}
 if(world.clubLabWatchInstalled)return
 world.clubLabWatchInstalled=true
 let observer:MutationObserver|null=null,timer:ReturnType<typeof setTimeout>|undefined,nonce='',documentRef=''
 const stop=()=>{observer?.disconnect();observer=null;clearTimeout(timer)}
 chrome.runtime.onMessage.addListener((message,_sender,reply)=>{
  if(message.kind==='pause'){stop();reply({ok:true});return}
  if(message.kind!=='watch-start')return
  stop()
  if(!['localhost','127.0.0.1'].includes(location.hostname)||location.pathname!=='/reader-sample.html'){reply({ok:false});return}
  const roots=document.querySelectorAll('[data-club-lab-sample="1"]')
  if(roots.length!==1){reply({ok:false});return}
  nonce=message.nonce;documentRef=message.documentRef
  observer=new MutationObserver(()=>{clearTimeout(timer);timer=setTimeout(()=>void chrome.runtime.sendMessage({kind:'view-changed',nonce,documentRef}).catch(()=>{}),700)})
  observer.observe(roots[0]!,{subtree:true,childList:true,characterData:true,attributes:true,
   attributeFilter:['aria-busy','data-page','data-context-label','data-source','data-edition','data-view','data-filters','data-virtualized']})
  reply({ok:true})
 })
 addEventListener('pagehide',stop,{once:true})
})
