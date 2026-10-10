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
  if(options.body&&!(options.body instanceof FormData))headers.set('Content-Type','application/json')
  const response=await fetch(`${API_URL}${path}`,{...options,headers})
  if(!response.ok){
    let detail=`No se pudo completar la solicitud (${response.status}).`
    try{detail=errorDetail(await response.json(),detail)}catch{/* respuesta sin JSON */}
    throw new ApiError(detail,response.status)
  }
  if(response.status===204)return undefined as T
  return response.json() as Promise<T>
}
export const money=(value:number)=>new Intl.NumberFormat('es-CO').format(value)
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
