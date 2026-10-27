import {z} from 'zod'
import {card,hash} from './contracts'
import {EXTRACTOR_REVISION,extractProfile,type ExtractorProfile} from './profile-extraction'

const title=z.string().min(1).max(120),quantity=z.number().int().min(0).max(2_000_000_000).nullable()
const domainCard=card.extend({slot:z.string().max(20).nullable()})
export const domainPayload=z.discriminatedUnion('domain',[
  z.object({domain:z.literal('account'),club_name:z.string().min(1).max(100).nullable(),balance:quantity,
    evidence:z.object({club_name:z.string().max(120).nullable(),balance:z.string().max(120).nullable()}).strict().optional()}).strict(),
  ...(['inventory','detail','squad'] as const).map(domain=>z.object({domain:z.literal(domain),records:z.array(domainCard).min(1).max(30)}).strict()),
  ...(['dcp','objective'] as const).map(domain=>z.object({domain:z.literal(domain),records:z.array(z.object({title,requirement_text:z.string().min(1).max(5000),progress_current:quantity,progress_target:quantity}).strict()).min(1).max(30),rules_verified:z.literal(false)}).strict()),
  z.object({domain:z.literal('gallery'),records:z.array(z.object({title,progress_current:quantity,progress_target:quantity}).strict()).min(1).max(30)}).strict(),
])
export type DomainPayload=z.infer<typeof domainPayload>

// All IDs, dates, fragments and hashes are created BEFORE persisting the queue.
// Retry sends the same bytes. No content-script code gets the local credential.
export async function observationEvents(profile:ExtractorProfile,preview:Awaited<ReturnType<typeof extractProfile>>,
  context:{binding:string;stream:string;sequence:number;documentRef:string;observedAt:string;source:'observed_page_dom'|'synthetic_dom'|'user_export_dom';page?:string;filters?:string;virtualized?:boolean|null}){
  const domain=profile.definition.view==='header'?'account':profile.definition.view
  const payloads:DomainPayload[]=[]
  for(let offset=0;offset<preview.records.length;offset+=30){
    const records=preview.records.slice(offset,offset+30).map((r,ordinal)=>{
      const v=r.values
      if(['inventory','detail','squad'].includes(domain)){
        const base=Object.fromEntries(Object.keys(card.shape).map(k=>[k,v[k]??null]))
        return {...base,ordinal,slot:v.slot??null,location:domain==='squad'?'squad':'club',
          evidence:Object.fromEntries(Object.entries(r.raw_values).filter(([,v])=>v!==null&&v.length<=120))}
      }
      return {title:v.title,progress_current:v.progress_current??null,progress_target:v.progress_target??null,
        ...(domain==='dcp'||domain==='objective'?{requirement_text:v.requirement_text}: {})}
    })
    const first=preview.records[0]!.values
    const raw=preview.records[0]!.raw_values
    const parsed=domainPayload.safeParse(domain==='account'?{domain,club_name:first.club_name??null,balance:first.balance??null,evidence:{club_name:raw.club_name??null,balance:raw.balance??null}}:
      {domain,records,...(domain==='dcp'||domain==='objective'?{rules_verified:false}: {})})
    if(!parsed.success)throw Error('Campos incompatibles con el contrato de esta vista. Revisa nombres, posiciones, puestos y valores; no se envió contenido.')
    payloads.push(parsed.data)
  }
  if(['account','detail'].includes(domain)&&preview.records.length!==1)throw Error('La cabecera o ficha debe tener un solo registro.')
  const manifest=await Promise.all(payloads.map(hash)),observation_id=crypto.randomUUID()
  const events=[]
  for(let index=0;index<payloads.length;index++){
    const event={schema_version:2,reader_version:EXTRACTOR_REVISION,event_id:crypto.randomUUID(),observation_id,
      context_binding:context.binding,stream_id:context.stream,sequence:context.sequence+index+1,
      document_ref:context.documentRef,observed_at:context.observedAt,source_updated_at:null,source_kind:context.source,
      profile:{profile_id:profile.id,revision:profile.revision,definition_hash:await hash(profile.definition),
        structure_hash:profile.definition.structure_hash,origin:profile.definition.origin,route:profile.definition.route,
        language:profile.definition.language,edition:'FC27',omissions:preview.coverage.omitted},
      scope:{page:context.page||domain,filters:context.filters||'',location:domain==='squad'?'squad':['inventory','detail'].includes(domain)?'club':'unknown',
        visible_count:preview.records.length,virtualized:context.virtualized??preview.coverage.virtualized,global_complete:false},
      fragment_index:index,fragment_count:payloads.length,manifest,payload:payloads[index]}
    const complete={...event,payload_hash:await hash(event)}
    if(new TextEncoder().encode(JSON.stringify(complete)).length>128000)throw Error('Fragmento mayor de 128 KB; selecciona una región menor. No se recortó contenido.')
    events.push(complete)
  }
  return events
}
