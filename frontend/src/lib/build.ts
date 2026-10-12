export type BuildInfo={edition:string;revision:string;built_at:string;environment:string;source_dirty:boolean}
export const frontendBuild:BuildInfo=__BUILD_INFO__
export function buildCompatibility(front:BuildInfo,back:BuildInfo):'matching'|'mismatch'|'unknown'{
 if(front.edition!==back.edition)return 'mismatch'
 if([front.revision,back.revision].some(value=>!value||value==='unknown'))return 'unknown'
 return front.revision===back.revision&&front.environment===back.environment&&front.source_dirty===back.source_dirty?'matching':'mismatch'
}
