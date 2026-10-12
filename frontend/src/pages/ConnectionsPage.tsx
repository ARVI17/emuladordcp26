import type {EntryState} from '../lib/entry'
import {useQuery} from '@tanstack/react-query'
import {api} from '../api/client'
import {ErrorBox,SectionTitle} from '../components/ui'
import type {Dashboard} from '../types'
type Capabilities={provider:string;status:string;authorization_supported:boolean;blocker:string;reviewed_on:string;capabilities:Record<string,{status:string}>}
export function ConnectionsPage({entry,busy,error,onEnter,onSelect}:{entry?:EntryState;busy:boolean;error:unknown;onEnter:(mode:'live'|'local')=>void;onSelect?:(id:number,mode:'live'|'local')=>void}){
 const diagnosis=useQuery({queryKey:['connection-capabilities'],queryFn:()=>api<Capabilities>('/connections/capabilities'),retry:false})
 const dashboard=useQuery({queryKey:['dashboard','FC27'],enabled:!!entry,queryFn:()=>api<Dashboard>('/dashboard')})
 const account=dashboard.data?.account
 const contexts=useQuery({queryKey:['club-contexts'],enabled:!!entry,queryFn:()=>api<{id:number;name:string;verified:boolean;platform:string|null;game_version:string}[]>('/club-contexts')})
 return <><SectionTitle title="Mi cuenta / Mi club" subtitle="Accede a FC27 y comprueba qué datos puede leer esta aplicación."/>
  <section className="panel account-entry"><span className="eyebrow">EA SPORTS FC 27</span><h3>Abre tu club en EA</h3>
   <p>Inicia sesión en la Web App oficial con tu cuenta EA.</p>
   <a className="official-entry" href="https://www.ea.com/es-es/ea-sports-fc/ultimate-team/web-app/" target="_blank" rel="noopener noreferrer">Abrir FC27 oficial ↗</a>
   <p>Se abre en otra pestaña. Abrir EA no vincula este planificador ni le da acceso a tu club.</p>
  </section>
  {contexts.data&&contexts.data.length>1&&<label>Cuenta y club<select value={entry?.club_context_id} disabled={busy} onChange={e=>{const id=Number(e.target.value);onSelect?.(id,contexts.data.find(c=>c.id===id)?.verified?'live':'local')}}>{contexts.data.map(c=><option key={c.id} value={c.id}>{c.name} · {c.game_version} · {c.platform||'Plataforma sin verificar'}</option>)}</select></label>}
  <section className="panel"><h3>Integración pendiente</h3>
   <p>{diagnosis.data?.blocker||'No hay una conexión autorizada de esta aplicación con EA. Faltan la aprobación para este proyecto y el protocolo de acceso.'}</p>
   <p><a href="https://help.ea.com/es/articles/ea-sports-fc/community-api/" target="_blank" rel="noreferrer">EA: conexión con socios aprobados</a>. Los permisos de FUTBIN, FUT.GG y FUTWIZ no se transfieren a este proyecto.</p>
   <dl className="status-list"><dt>Cuenta EA</dt><dd>{account?.identity_verified?'Identidad observada; consulta fecha y cobertura':'No vinculada'}</dd><dt>Club / plataforma</dt><dd>{account?.name||'Sin verificar'} / {account?.platform||'Sin verificar'}</dd><dt>Monedas</dt><dd>{account?.coins==null?'Sin verificar':account.coins.toLocaleString('es-CO')}</dd><dt>Jugadores</dt><dd>{account?.observed_copies==null?'No sincronizados':`${account.observed_copies} copias observadas · ${account.inventory_complete?'cobertura completa':'lectura parcial'}`}</dd><dt>DCP / Galería / Objetivos</dt><dd>Progreso sin consultar</dd><dt>Última observación remota</dt><dd>{account?.observed_at?new Date(account.observed_at).toLocaleString('es-CO'):'Ninguna'}</dd><dt>Última apertura local</dt><dd>{entry?.last_attempt?new Date(entry.last_attempt).toLocaleString('es-CO'):'Pendiente'}</dd><dt>Proveedor de esta aplicación</dt><dd>{diagnosis.data?`${diagnosis.data.provider}: no disponible`:'Diagnóstico sin obtener'}</dd></dl>
   <p>Actualizar el diagnóstico consulta esta API local. No inicia sesión en EA ni realiza una lectura remota.</p>
   <button disabled={diagnosis.isFetching} onClick={()=>void diagnosis.refetch()}>Actualizar diagnóstico local</button>
   {error!=null&&<button disabled={busy} onClick={()=>onEnter('live')}>Reintentar apertura local</button>}
   <ErrorBox error={error||diagnosis.error||dashboard.error}/>
  </section>
  <section className="panel"><h3>Registro local sin vincular</h3><p>Puedes revisar los datos anteriores y utilizar las simulaciones locales. No verifican tu cuenta, no leen todo tu club y no sustituyen la sincronización solicitada.</p><button disabled={busy} onClick={()=>onEnter('local')}>Abrir registro local</button></section>
  {entry&&<section className="panel"><h3>Datos necesarios por función</h3><ul>{Object.entries(entry.modules).map(([key,value])=><li key={key}><strong>{{squads:'Plantillas',analysis:'Análisis',transfers:'Fichajes',dcp:'DCP',gallery:'Galería',evolutions:'Evoluciones',chat:'IA',market:'Mercado'}[key]||key}</strong>: {value.ready?'Listo':'Pendiente de datos verificados'}</li>)}</ul></section>}
 </>
}
