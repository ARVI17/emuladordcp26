export function safeExternalUrl(value:string|null|undefined){try{const url=new URL(value||'');return url.protocol==='https:'?url.href:undefined}catch{return undefined}}
