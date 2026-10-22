import {z} from 'zod'
import {hash} from './contracts'
import {sensitiveText} from './privacy'
import type {inspectRegion} from './inspect-region'
import type {ViewProfile} from './view-profile'

// Exact selectors produced by the bounded inspector, not arbitrary CSS/JS.
const locator=z.string().max(180).regex(/^[a-z][a-z0-9-]*(?:\.[a-z][a-z_-]{1,40}){0,3}$/i)
const fields={
  header:['club_name','balance'],account:['club_name','balance'],
  inventory:['name','rating','position','card_type','league','club','nationality','is_loan','is_evolution','tradable','rare','special','first_owner','gallery_score'],
  detail:['name','rating','position','card_type','league','club','nationality','is_loan','is_evolution','tradable','rare','special','first_owner','gallery_score'],
  squad:['name','rating','position','slot'],
  dcp:['title','requirement_text'],objective:['title','requirement_text','progress_current','progress_target'],
  gallery:['title','progress_current','progress_target'],unknown:[],
} satisfies Record<ViewProfile['view'],string[]>
const integers=new Set(['rating','balance','gallery_score','progress_current','progress_target'])
const booleans=new Set(['is_loan','is_evolution','tradable','rare','special','first_owner'])
const positions=new Set(['POR','LD','DFC','LI','CAD','CAI','MCD','MC','MCO','MD','MI','ED','EI','SD','DC'])
const requiredFields:Partial<Record<ViewProfile['view'],string[]>>={inventory:['name','rating','position'],detail:['name','rating','position'],squad:['name','rating','position','slot'],dcp:['title','requirement_text'],objective:['title','requirement_text']}
export const profileDefinition=z.object({
  format:z.literal('club-lab-extractor-1'),map_id:z.string().uuid(),view:z.enum(['header','account','inventory','detail','squad','dcp','objective','gallery']),
  origin:z.string().url().max(120),route:z.string().max(160),language:z.string().min(1).max(16),structure_hash:z.string().regex(/^[a-f0-9]{64}$/),
  root_selector:locator,record_selector:locator.nullable(),
  fields:z.array(z.object({field:z.string().max(40),selector:locator,source:z.enum(['text','label']),
    normalization:z.enum(['text','integer','boolean','position']),required:z.boolean()}).strict()).min(1).max(20),
}).strict().superRefine((p,ctx)=>{
  const names=p.fields.map(f=>f.field)
  if(new Set(names).size!==names.length)ctx.addIssue({code:'custom',message:'Campos repetidos'})
  if(!p.fields.some(f=>f.required))ctx.addIssue({code:'custom',message:'Declara al menos un campo obligatorio para reconocer esta vista'})
  if(!['header','account','detail'].includes(p.view)&&!p.record_selector)ctx.addIssue({code:'custom',message:'Indica el ámbito de cada registro'})
  for(const f of p.fields){
    const expected=integers.has(f.field)?'integer':booleans.has(f.field)?'boolean':f.field==='position'?'position':'text'
    if(!(fields[p.view] as string[]).includes(f.field)||f.normalization!==expected)ctx.addIssue({code:'custom',message:'Campo o normalización incompatible con la vista'})
  }
  for(const name of requiredFields[p.view]||[])if(!p.fields.some(f=>f.field===name&&f.required))ctx.addIssue({code:'custom',message:'Falta un campo obligatorio de la vista'})
})
export type ProfileDefinition=z.infer<typeof profileDefinition>
export type Region=NonNullable<ReturnType<typeof inspectRegion>>
export type ProfileStatus='draft'|'sample_tested'|'observed_contrasted'|'active'|'disabled'
// Bump when extraction semantics change: old proofs must not activate new code.
export const EXTRACTOR_REVISION='bounded-region-1'
export type Proof={extractor_revision:string;definition_hash:string;observed_at:string;document_ref:string;structure_hash:string;records:number}
export type ExtractorProfile={id:string;revision:number;definition:ProfileDefinition;status:ProfileStatus;sample?:Proof;contrast?:Proof}

export function draftForMap(profile:ViewProfile){
  return {format:'club-lab-extractor-1',map_id:profile.map_id,view:profile.view,origin:profile.origin,route:profile.route,
    language:profile.language,structure_hash:profile.structure_hash,root_selector:profile.recognition[0],record_selector:null,fields:[]}
}
export function bindDefinition(input:unknown,profile:ViewProfile,region:Region):ProfileDefinition {
  const parsed=profileDefinition.safeParse(input)
  if(!parsed.success)throw Error('Perfil inválido: revisa campos, ámbitos y normalizaciones. No se admite código ni estados importados.')
  const p=parsed.data
  for(const key of ['map_id','view','origin','route','language','structure_hash'] as const){
    if(p[key]!==profile[key])throw Error('La definición no corresponde al mapa privado seleccionado.')
  }
  if(!region.nodes||p.root_selector!==region.root_selector)throw Error('El ámbito debe ser la región revisada.')
  const selectors=new Set(region.nodes.map(n=>n.selector))
  if([p.record_selector,...p.fields.map(f=>f.selector)].some(s=>s&&!selectors.has(s)))throw Error('Localizador ausente del mapa; reconoce y revisa esa región primero.')
  return p
}
export async function structureHash(map:Region){
  if(!map.nodes)throw Error('No hay una región legible.')
  return hash(map.nodes.map(({parent,tag,selector,role,medium})=>({parent,tag,selector,role,medium})))
}

// Both a trial and an active one-shot preview call this exact reader. It reads
// only a fresh bounded inspector map, never document-wide selectors or scripts.
export async function extractProfile(definition:ProfileDefinition,map:Region){
  const p=profileDefinition.parse(definition)
  if(!map.nodes||!map.coverage)throw Error('Selecciona la región revisada antes de probar el perfil.')
  if(map.coverage.truncated||map.coverage.loading)throw Error('Región truncada o cargando; no se publica una lectura parcial como válida.')
  if(map.language!==p.language||p.language==='unknown')throw Error('Idioma distinto o desconocido; revisa una nueva definición.')
  if(map.root_selector!==p.root_selector||await structureHash(map)!==p.structure_hash)throw Error('La estructura cambió; reconoce la región y revisa el perfil.')
  const nodes=map.nodes
  const descendant=(child:number,parent:number)=>{
    for(let steps=0;steps<=7;steps++){
      if(child===parent)return true
      const next=nodes[child]?.parent
      if(next==null)return false
      child=next
    }
    return false
  }
  const rows=p.record_selector?nodes.flatMap((n,i)=>n.selector===p.record_selector?[i]:[]):[0]
  if(!rows.length||rows.length>30)throw Error('La vista debe contener entre 1 y 30 registros; no se recortan filas.')
  if(rows.some((r,i)=>rows.some((other,j)=>i!==j&&descendant(r,other))))throw Error('Ámbitos de registros solapados; revisa el localizador.')
  const unknown=new Set<string>()
  const records=rows.map((row,ordinal)=>{
    const values:Record<string,string|number|boolean|null>={}
    for(const f of p.fields){
      const matches=nodes.filter((n,i)=>n.selector===f.selector&&descendant(i,row))
      if(matches.length>1)throw Error(`Localizador no único dentro del registro: ${f.field}.`)
      const raw=matches[0]?.[f.source]
      let value:string|number|boolean|null=raw&&!sensitiveText.test(raw)?raw:null
      if(value!==null){
        if(f.normalization==='integer')value=/^\d+$/.test(raw!)?Number(raw):null
        if(f.normalization==='boolean')value=/^(true|sí|si|yes)$/i.test(raw!)?true:/^(false|no)$/i.test(raw!)?false:null
        if(f.normalization==='position')value=positions.has(raw!)?raw!:null
        if(typeof value==='number'&&(!Number.isSafeInteger(value)||value>2_000_000_000||(f.field==='rating'&&(value<40||value>99))))value=null
      }
      if(value===null){
        if(f.required)throw Error(`Campo obligatorio ausente, omitido o ambiguo: ${f.field}.`)
        unknown.add(f.field)
      }
      values[f.field]=value
    }
    return {ordinal,values}
  })
  return {view:p.view,records,unknown_fields:[...unknown],coverage:map.coverage,provider_verified:false as const,ingestion_enabled:false as const}
}

export async function saveDefinition(definition:ProfileDefinition,previous?:ExtractorProfile):Promise<ExtractorProfile>{
  const same=previous&&await hash(previous.definition)===await hash(definition)
  // Import/save never accepts lifecycle claims from JSON. Changed definitions
  // revoke every proof; an identical save does not fabricate a new test.
  if(same)return previous
  return {id:previous?.id||crypto.randomUUID(),revision:(previous?.revision||0)+1,definition,status:'draft'}
}
export async function recordSample(profile:ExtractorProfile,proof:Proof):Promise<ExtractorProfile>{
  if(proof.extractor_revision!==EXTRACTOR_REVISION||proof.definition_hash!==await hash(profile.definition))throw Error('Prueba de otra revisión.')
  return {...profile,status:'sample_tested',sample:proof,contrast:undefined}
}
export async function recordContrast(profile:ExtractorProfile,proof:Proof):Promise<ExtractorProfile>{
  if(!profile.sample||profile.sample.extractor_revision!==EXTRACTOR_REVISION||proof.extractor_revision!==EXTRACTOR_REVISION||profile.sample.definition_hash!==await hash(profile.definition)||proof.definition_hash!==profile.sample.definition_hash)throw Error('Prueba primero esta definición con una muestra propia.')
  return {...profile,status:'observed_contrasted',contrast:proof}
}
export async function activateProfile(profile:ExtractorProfile):Promise<ExtractorProfile>{
  if(!profile.sample||!profile.contrast||profile.sample.extractor_revision!==EXTRACTOR_REVISION||profile.contrast.extractor_revision!==EXTRACTOR_REVISION||profile.sample.definition_hash!==await hash(profile.definition)||profile.contrast.definition_hash!==profile.sample.definition_hash)throw Error('Faltan prueba de muestra y contraste manual de esta revisión en la vista real.')
  return {...profile,status:'active'}
}
