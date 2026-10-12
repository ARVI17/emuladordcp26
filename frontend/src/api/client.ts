let csrfToken:string|null=null,appEntry:number|null=null
export function setSessionHeaders(csrf:string|null,entry:number|null){csrfToken=csrf;appEntry=entry}
export function sessionHeaders(){const headers=new Headers();if(csrfToken)headers.set('X-CSRF-Token',csrfToken);if(appEntry)headers.set('X-App-Entry',String(appEntry));return headers}
export function requestNonce(){return Array.from(crypto.getRandomValues(new Uint8Array(24)),value=>value.toString(16).padStart(2,'0')).join('')}
export const API_URL=import.meta.env.VITE_API_URL||'/api'

export class ApiError extends Error {
  status:number
  constructor(message:string,status:number){super(message);this.name='ApiError';this.status=status}
}
export function errorDetail(body:unknown,fallback:string):string{
  if(!body||typeof body!=='object')return fallback
  const detail=(body as {detail?:unknown}).detail
  const errors=(body as {errors?:{field?:string;message?:string}[]}).errors
  if(Array.isArray(errors)&&errors.length){const fields=errors.map(error=>`${error.field?.replace(/^body\./,'')||'Dato'}: ${error.message||'Valor no válido'}`).join('. ');return typeof detail==='string'?`${detail}. ${fields}`:fields}
  if(typeof detail==='string')return detail
  if(Array.isArray(detail))return detail.map(item=>{
    const field=Array.isArray(item?.loc)?item.loc.filter((part:unknown)=>part!=='body').join(' · '):''
    return `${field?`${field}: `:''}${item?.msg||'Valor no válido'}`
  }).join('. ')||fallback
  if(detail&&typeof detail==='object'){
    const d=detail as {message?:string;violations?:string[]}
    return [d.message,...(d.violations||[])].filter(Boolean).join('. ')||fallback
  }
  return fallback
}
export async function api<T>(path:string,options:RequestInit={}):Promise<T>{
  const headers=new Headers(options.headers)
  if(csrfToken)headers.set("X-CSRF-Token",csrfToken)
  if(appEntry)headers.set("X-App-Entry",String(appEntry))
  if(options.body&&!(options.body instanceof FormData))headers.set('Content-Type','application/json')
  const response=await fetch(`${API_URL}${path}`,{...options,headers})
  if(!response.ok){
    let detail=`No se pudo completar la solicitud (${response.status}).`
    try{detail=errorDetail(await response.json(),detail)}catch{/* respuesta sin JSON */}
    throw new ApiError(detail,response.status)
  }
  if(response.status===204)return undefined as T
  const data:unknown=await response.json()
  assertFC27(data)
  return data as T
}
export function assertFC27(data:unknown):void{
  if(!data||typeof data!=='object')return
  if(Array.isArray(data)){data.forEach(assertFC27);return}
  const row=data as Record<string,unknown>
  if('game_version' in row&&row.game_version!==null&&row.game_version!=='FC27')throw new ApiError('Respuesta bloqueada: contiene una edición ajena a FC27',409)
  Object.values(row).forEach(assertFC27)
}
export const money=(value:number|null)=>value===null?'Desconocido':new Intl.NumberFormat('es-CO').format(value)
export async function downloadInventory(format:'csv'|'xlsx',season:string){
  const response=await fetch(`${API_URL}/players/export?format=${format}&game_version=${season}`,{headers:sessionHeaders(),cache:'no-store'})
  if(!response.ok)throw new ApiError(errorDetail(await response.json(),'No se pudo exportar el inventario'),response.status)
  const url=URL.createObjectURL(await response.blob()),link=document.createElement('a')
  link.href=url;link.download=`inventario-local-${season}.${format}`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
}
export const shortDate=(value:string|null|undefined)=>{
  if(!value)return 'Sin vencimiento'
  const date=new Date(value)
  return Number.isNaN(date.getTime())?'Fecha por revisar':new Intl.DateTimeFormat('es-CO',{day:'2-digit',month:'short',year:'numeric'}).format(date)
}

export const dateTimeInput=(value:string|null|undefined)=>{
  if(!value)return ''
  const date=new Date(value)
  if(Number.isNaN(date.getTime()))return ''
  return new Date(date.getTime()-date.getTimezoneOffset()*60000).toISOString().slice(0,16)
}
