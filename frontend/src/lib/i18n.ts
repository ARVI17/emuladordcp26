import {z} from 'zod'
// IDs remain stable; presentation alone is translated. Explicit field messages win.
z.setErrorMap(issue=>({message:issue.code==='too_small'?'El valor es demasiado pequeño o falta información':issue.code==='too_big'?'El valor supera el límite permitido':issue.code==='invalid_type'?'Revisa el tipo de dato de este campo':'Valor no válido; revisa este campo'}))
export const es={unknown:'Sin consultar',loading:'Cargando…',retry:'Reintentar',help:'Ayúdame con esto',unofficial:'Asistente no oficial de FC27'} as const
const statuses:Record<string,string>={timeout:'Tiempo agotado',data_missing:'Datos pendientes',draft:'Borrador',prepared:'Preparado',queued:'En cola',running:'En curso',completed:'Completado localmente',failed:'Falló',cancelled:'Cancelado',unavailable:'No disponible',unknown:'Desconocido',available:'Disponible',absent:'Ausente en la última lectura completa',review_required:'Requiere revisión',ready:'Listo',partial:'Parcial',observed:'Observado',syncing:'Consultando',sync_required:'Lectura pendiente',unlinked:'Sin vincular',local:'Registro local',live:'Cuenta',stale:'Lectura vencida',feasible:'Viable',infeasible:'Sin combinación',optimal:'Óptimo calculado',reserved:'Reservado',approved:'Aprobado',expired:'Vencido',active:'Activo',pending:'Pendiente'}
export const statusLabel=(value:string)=>statuses[value]||'Estado por revisar'
export const timeZones=['America/Bogota','America/Mexico_City','America/Argentina/Buenos_Aires','America/New_York','Europe/Madrid','UTC']
export function timeZone(){try{const value=localStorage.getItem('time-zone')||'America/Bogota';new Intl.DateTimeFormat('es-CO',{timeZone:value});return value}catch{return 'America/Bogota'}}
export function setTimeZone(value:string){new Intl.DateTimeFormat('es-CO',{timeZone:value});try{localStorage.setItem('time-zone',value)}catch{/* Preferences may be unavailable. */}}
export function observedDate(value?:string|null){if(!value)return es.unknown;const date=new Date(value);return Number.isNaN(date.getTime())?'Fecha por revisar':new Intl.DateTimeFormat('es-CO',{dateStyle:'medium',timeStyle:'short',timeZone:timeZone()}).format(date)}
export function zonedInput(value?:string|null){
  if(!value||Number.isNaN(new Date(value).getTime()))return ''
  const parts=new Intl.DateTimeFormat('en-CA',{timeZone:timeZone(),year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date(value))
  const get=(key:string)=>parts.find(p=>p.type===key)?.value
  return `${get('year')}-${get('month')}-${get('day')}T${get('hour')}:${get('minute')}`
}
export function inputInstant(value:string){
  if(!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value))throw new Error('Fecha y hora no válidas')
  const target=Date.parse(value+'Z');let instant=target
  for(let i=0;i<4;i++){const offset=Date.parse(zonedInput(new Date(instant).toISOString())+'Z')-target;if(!offset)break;instant-=offset}
  if(zonedInput(new Date(instant).toISOString())!==value)throw new Error('Esta hora no existe en la zona elegida; revisa el cambio de horario')
  return new Date(instant).toISOString()
}
