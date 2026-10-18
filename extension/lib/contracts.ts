import {z} from 'zod'
const short = z.string().min(1).max(100)
export const card = z.object({
  ordinal:z.number().int().min(0).max(29),name:short,rating:z.number().int().min(40).max(99),
  position:z.enum(['POR','LD','DFC','LI','CAD','CAI','MCD','MC','MCO','MD','MI','ED','EI','SD','DC']),
  card_type:z.string().max(40).nullable(),league:short.nullable(),club:short.nullable(),nationality:short.nullable(),
  is_loan:z.boolean().nullable(),is_evolution:z.boolean().nullable(),tradable:z.boolean().nullable(),
  rare:z.boolean().nullable(),special:z.boolean().nullable(),is_holographic:z.boolean().nullable(),
  first_owner:z.boolean().nullable(),holographic_level:z.number().int().min(0).max(100).nullable(),
  gallery_score:z.number().int().min(0).max(2000000000).nullable(),
  evidence:z.record(z.string().max(120)),location:z.enum(['club','squad','unknown']),
}).strict()
export const reading = z.object({
  view:z.enum(['inventory','detail','squad','result']),edition:z.literal('FC27'),
  source_kind:z.enum(['synthetic_dom','user_export_dom']),records:z.array(card).max(30),
  scope:z.object({page:short,filters:z.string().max(240),location:z.enum(['club','squad','unknown']),visible_count:z.number().int().min(0).max(30),
    loading:z.literal(false),virtualized:z.boolean().nullable(),terminal_observed:z.boolean(),global_complete:z.literal(false)}).strict(),
  unknown_fields:z.array(z.string().max(80)).max(40),
}).strict()
export type Reading = z.infer<typeof reading>
export const forbidden = /password|contrase[nñ]a|bearer\s|access[_ -]?token|\S+@\S+|sign\s?in|log\s?in|iniciar sesi[oó]n|verification code|c[oó]digo de (seguridad|verificaci[oó]n)/i
export function endpoint(value:string) {
  const u = new URL(value)
  if(u.protocol!=='http:' || !['127.0.0.1','localhost'].includes(u.hostname) || u.username || u.password || u.search || u.hash || !['','/'].includes(u.pathname)) throw Error('Usa una dirección local HTTP sin ruta, por ejemplo http://localhost:8080')
  return u.origin
}
export function admitted(url:string) {
  const u=new URL(url)
  return ['127.0.0.1','localhost'].includes(u.hostname) && u.protocol==='http:' && u.pathname==='/reader-sample.html' && !u.search && !u.hash
}
export function eaDiagnostic(url:string) {
  const u=new URL(url)
  return u.protocol==='https:' && u.hostname==='www.ea.com' && /^\/(?:[a-z]{2}-[a-z]{2}\/)?ea-sports-fc\/ultimate-team\/web-app\/$/.test(u.pathname) && !/login|payment|checkout|auth/i.test(u.hash+u.search)
}
export function canonical(value:unknown):string {
  if(Array.isArray(value)) return '['+value.map(canonical).join(',')+']'
  if(value!==null && typeof value==='object') return '{'+Object.entries(value).sort(([a],[b])=>a<b?-1:a>b?1:0).map(([k,v])=>JSON.stringify(k)+':'+canonical(v)).join(',')+'}'
  return JSON.stringify(value)
}
export async function hash(value:unknown) {
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(canonical(value))))).map(n=>n.toString(16).padStart(2,'0')).join('')
}
