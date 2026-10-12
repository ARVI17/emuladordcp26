import type {EntryState} from '../lib/entry'
import {useQuery} from '@tanstack/react-query'
import {api} from '../api/client'
import {ErrorBox,SectionTitle} from '../components/ui'
export function ConnectionsPage({entry,busy,error,onEnter,onSelect}:{entry?:EntryState;busy:boolean;error:unknown;onEnter:(mode:'live'|'local')=>void;onSelect?:(id:number,mode:'live'|'local')=>void}){
 const contexts=useQuery({queryKey:['club-contexts'],enabled:!!entry,queryFn:()=>api<{id:number;name:string;verified:boolean;platform:string|null;game_version:string}[]>('/club-contexts')})
 return <><SectionTitle title="Conexiones y estado del club" subtitle="Comprueba la procedencia y vigencia antes de tomar decisiones."/>
  {contexts.data&&contexts.data.length>1&&<label>Cuenta y club<select value={entry?.club_context_id} disabled={busy} onChange={e=>{const id=Number(e.target.value);onSelect?.(id,contexts.data.find(c=>c.id===id)?.verified?'live':'local')}}>{contexts.data.map(c=><option key={c.id} value={c.id}>{c.name} · {c.game_version} · {c.platform||'Plataforma sin verificar'}</option>)}</select></label>}
  <section className="panel"><span className="eyebrow">EA SPORTS FC 27</span><h3>{busy?'Comprobando acceso…':entry?.label||'Integración pendiente'}</h3>
   <p>No hay una conexión autorizada de esta aplicación con EA. Se necesita aprobación para el proyecto y documentación de acceso, permisos, identidad, copias y paginación.</p>
   <p><a href="https://help.ea.com/en/articles/ea-sports-fc/community-api/" target="_blank" rel="noreferrer">EA: conexión con socios aprobados</a></p>
   <dl className="status-list"><dt>Cuenta y club</dt><dd>{entry?.identity_verified?'Identidad verificada':'Sin verificar'}</dd><dt>Última lectura remota válida</dt><dd>{entry?.observed_at?new Date(entry.observed_at).toLocaleString('es-CO'):'Ninguna'}</dd><dt>Último intento local</dt><dd>{entry?.last_attempt?new Date(entry.last_attempt).toLocaleString('es-CO'):'Pendiente'}</dd></dl>
   <button disabled={busy} onClick={()=>onEnter('live')}>Comprobar conexión</button><ErrorBox error={error}/>
  </section>
  <section className="panel"><h3>Registro local sin vincular</h3><p>Puedes revisar los datos anteriores y utilizar las simulaciones locales. No verifican tu cuenta, no leen todo tu club y no sustituyen la sincronización solicitada.</p><button disabled={busy} onClick={()=>onEnter('local')}>Abrir registro local</button></section>
  {entry&&<section className="panel"><h3>Datos necesarios por función</h3><ul>{Object.entries(entry.modules).map(([key,value])=><li key={key}><strong>{{squads:'Plantillas',analysis:'Análisis',transfers:'Fichajes',dcp:'DCP',gallery:'Galería',evolutions:'Evoluciones',chat:'IA',market:'Mercado'}[key]||key}</strong>: {value.ready?'Listo':'Pendiente de datos verificados'}</li>)}</ul></section>}
 </>
}
