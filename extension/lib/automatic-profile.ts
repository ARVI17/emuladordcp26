import {fields,isRequired,normalizationFor,profileDefinition,structureHash,extractProfile,EXTRACTOR_REVISION,type Region,type ExtractorProfile} from './profile-extraction'
import {hash} from './contracts'

// Only the documented schema of the user's OWN local sample/export. These are
// not EA selectors. Real DOM proposals never reach this automatic extractor.
export async function automaticProfile(map:Region,origin:string,profiles:ExtractorProfile[]){
 if(!map.nodes||!map.sample||map.sample.edition!=='FC27')throw Error('La muestra no declara FC27.')
 const view=map.sample.view
 if(!view||view==='unknown'||!(view in fields))throw Error('Vista declarada desconocida.')
 const kind=view as keyof typeof fields
 const selectors=[...new Set(map.nodes.map(n=>n.selector))]
 const declarations=(fields[kind] as string[]).flatMap(field=>{
  const matches=selectors.filter(s=>s.endsWith(`[data-field="${field}"]`))
  if(matches.length>1)throw Error('Campo de muestra ambiguo: '+field)
  return matches.length?[{field,selector:matches[0]!,source:'text' as const,normalization:normalizationFor(field),required:isRequired(kind,field)}]:[]
 })
 const recordSelectors=selectors.filter(s=>s.endsWith('[data-card]'))
 if(recordSelectors.length>1)throw Error('Ámbitos de muestra ambiguos.')
 const shape=await structureHash(map)
 const previous=profiles.find(p=>p.definition.origin===origin&&p.definition.view===view&&p.definition.language===map.language&&p.definition.structure_hash===shape)
 const definition=profileDefinition.parse({format:'club-lab-extractor-1',map_id:previous?.definition.map_id||crypto.randomUUID(),
  view,origin,route:'/reader-sample.html',language:map.language,structure_hash:shape,root_selector:map.root_selector,
  record_selector:['header','account','detail'].includes(view)?null:recordSelectors[0]||null,fields:declarations})
 const preview=await extractProfile(definition,map)
 const profile:ExtractorProfile=previous||{id:crypto.randomUUID(),revision:1,definition,status:'sample_tested',sample:{
  extractor_revision:EXTRACTOR_REVISION,definition_hash:await hash(definition),observed_at:new Date().toISOString(),document_ref:crypto.randomUUID(),structure_hash:shape,records:preview.records.length}}
 return {profile,preview}
}
