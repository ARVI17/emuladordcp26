import {useQuery} from '@tanstack/react-query'
import {api} from '../api/client'
import {frontendBuild,buildCompatibility,type BuildInfo} from '../lib/build'
import type {EntryState} from '../lib/entry'
export function BuildStatus({entry}:{entry?:EntryState}){
 const health=useQuery({queryKey:['api-health'],queryFn:()=>api<{status:string}>('/health'),retry:false,refetchInterval:60000})
 const build=useQuery({queryKey:['api-build'],queryFn:()=>api<BuildInfo>('/build'),retry:false,refetchInterval:60000})
 const compatibility=build.data?buildCompatibility(frontendBuild,build.data):'unknown'
 return <div className="build-status"><p>Entorno: {frontendBuild.environment} · {health.data?.status==='healthy'?'API saludable':health.isPending?'Comprobando API':'API sin respuesta válida'} · Cuenta EA: {entry?.identity_verified?'identidad observada, revisar vigencia':'no vinculada'}</p>
  <p data-testid="build-reference">{frontendBuild.edition} · Build {frontendBuild.revision}{frontendBuild.source_dirty?' (cambios sin confirmar)':''} · {frontendBuild.built_at}</p>
  {compatibility==='mismatch'&&<p role="alert">La interfaz y la API son de versiones distintas. Conserva tu trabajo y revisa el despliegue antes de continuar.</p>}
  {compatibility==='unknown'&&<p>Versión de la API sin acreditar{build.error?' o ruta /api/build no disponible':''}.</p>}
  {frontendBuild.environment==='review'&&<p>Revisión desechable: la base se pierde al detener el contenedor. No guardes aquí tu único inventario.</p>}
 </div>
}
