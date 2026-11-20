import {useQuery} from '@tanstack/react-query'
import {api,money} from '../api/client'
import {navigate} from '../lib/navigation'
import type {EntryState} from '../lib/entry'
import {es,observedDate} from '../lib/i18n'
import type {Dashboard} from '../types'
import {ClubAnalysis} from '../components/ClubAnalysis'
import {ClubAdvisor,type AdvisorStyle} from '../components/ClubAdvisor'
import {ErrorBox,Loading,SectionTitle} from '../components/ui'
export function HomePage({entry,onBuild}:{entry:EntryState;onBuild:(formation:string,style:AdvisorStyle)=>void}){
 const query=useQuery({queryKey:['dashboard','FC27'],queryFn:()=>api<Dashboard>('/dashboard')})
 if(query.isLoading)return <Loading/>
 if(!query.data)return <ErrorBox error={query.error}/>
 const {account,mode,counts,profile}=query.data
 return <><SectionTitle title="Inicio"/><ClubAdvisor entry={entry} onBuild={onBuild}/>
  <nav className="advisor-shortcuts" aria-label="Herramientas de mi club">
    <button onClick={()=>navigate('club')}>Mis cartas</button><button onClick={()=>navigate('plantillas')}>Mi plantilla principal</button>
    <button onClick={()=>navigate('evoluciones')}>Evoluciones</button><button onClick={()=>navigate('objetivos')}>Objetivos</button>
  </nav>
  <section className="panel" aria-label="Artículos sin asignar"><h3>Artículos sin asignar</h3><p>{account.unassigned_count==null?es.unknown:`${money(account.unassigned_count)} artículos pendientes`}</p>{account.unassigned_types&&<p>{Object.entries(account.unassigned_types).map(([kind,count])=>`${({player:'Jugadores',players:'Jugadores',packs:'Sobres',consumable:'Consumibles',consumables:'Consumibles',other:'Otros',unknown:'Tipo pendiente'} as Record<string,string>)[kind]||'Tipo pendiente'} · ${money(count)}`).join(' / ')}</p>}<small>Última lectura · {observedDate((account.facts?.unassigned_types||account.facts?.unassigned_count)?.observed_at)}</small></section>
  {mode==='local'?<ClubAnalysis/>:mode==='assisted'&&<details className="panel"><summary>Historial del análisis asistido</summary><ClubAnalysis/></details>}
  {mode==='local'&&<section className="panel local-summary"><h3>Tu registro local</h3><p>{counts.players} cartas revisadas · {counts.protected} protegidas · {counts.duplicates} duplicados. Presupuesto local DCP: {money(profile.max_budget)}.</p><p>Estos datos de planificación no acreditan recursos ni progreso actuales en EA.</p><button onClick={()=>navigate('club')}>Revisar registro</button></section>}
 </>
}
export function StorePage(){return <><SectionTitle title="Tienda" subtitle="Contenido y saldo sin consultar"/><section className="panel"><h3>Ofertas no disponibles</h3><p>Esta aplicación todavía no tiene acceso autorizado a la tienda de tu cuenta. Consulta las ofertas y sus condiciones en la Web App oficial.</p><a className="official-entry" href="https://www.ea.com/es-es/ea-sports-fc/ultimate-team/web-app/" target="_blank" rel="noopener noreferrer">Abrir FC27 oficial ↗</a><p>Abre otra pestaña. Las decisiones y operaciones se realizan allí.</p></section></>}
