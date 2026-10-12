import {it,expect} from 'vitest'
import {buildCompatibility,type BuildInfo} from './build'
const build:BuildInfo={edition:'FC27',revision:'a'.repeat(40),built_at:'2026-10-12',environment:'review',source_dirty:false}
it('detecta una interfaz antigua contra otra API aunque ambas respondan',()=>{
 expect(buildCompatibility(build,{...build,revision:'b'.repeat(40)})).toBe('mismatch')
 expect(buildCompatibility(build,{...build,edition:'FC26'})).toBe('mismatch')
 expect(buildCompatibility(build,{...build,environment:'local'})).toBe('mismatch')
 expect(buildCompatibility(build,{...build,source_dirty:true})).toBe('mismatch')
 expect(buildCompatibility(build,build)).toBe('matching')
 expect(buildCompatibility(build,{...build,revision:'unknown'})).toBe('unknown')
})
