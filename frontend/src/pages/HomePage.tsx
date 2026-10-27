import {useQuery} from '@tanstack/react-query'
import {api,money} from '../api/client'
import {navigate,type Page} from '../lib/navigation'
import {es,observedDate} from '../lib/i18n'
import type {Dashboard} from '../types'
import {ClubAnalysis} from '../components/ClubAnalysis'
import {ErrorBox,Loading,SectionTitle} from '../components/ui'
const cards:{page:Page;title:string;text:string;icon:string}[]=[
 {page:'objetivos',title:'Centro FC',text:'Objetivos, condiciones y temporada',icon:'◎'},
 {page:'plantillas',title:'Plantillas',text:'Tu principal y equipos alternativos para jugar',icon:'▦'},
 {page:'dcp',title:'Desafíos de creación de plantillas',text:'Revisa requisitos y compara combinaciones',icon:'◇'},
 {page:'galeria',title:'Galería',text:'Consulta tu colección y planifica conjuntos',icon:'▧'},
 {page:'evoluciones',title:'Evoluciones',text:'Explora rutas de mejora para tus cartas',icon:'↗'},
 {page:'club',title:'Mi club',text:'Jugadores, copias y protecciones',icon:'♙'},
]
export function HomePage(){
 const query=useQuery({queryKey:['dashboard','FC27'],queryFn:()=>api<Dashboard>('/dashboard')})
 if(query.isLoading)return <Loading/>
 if(!query.data)return <ErrorBox error={query.error}/>
 const {account,mode,counts,profile}=query.data
 return <><SectionTitle title="Inicio" subtitle="Tu espacio para preparar la siguiente decisión"/><ClubAnalysis/><section className="unassigned-panel" aria-label="Artículos sin asignar"><span className="unassigned-icon" aria-hidden="true">▱</span><div><span className="eyebrow">PENDIENTES DE ASIGNAR</span><h2>Artículos sin asignar</h2><p>{account.unassigned_count==null?es.unknown:`${money(account.unassigned_count)} artículos pendientes`}</p>{account.unassigned_types&&<p className="unassigned-types">{Object.entries(account.unassigned_types).map(([kind,count])=>`${({player:'Jugadores',players:'Jugadores',packs:'Sobres',consumable:'Consumibles',consumables:'Consumibles',other:'Otros',unknown:'Tipo pendiente'} as Record<string,string>)[kind]||'Tipo pendiente'}: ${money(count)}`).join(' · ')}</p>}<small>Puede incluir jugadores y consumibles. Lectura: {observedDate((account.facts?.unassigned_types||account.facts?.unassigned_count)?.observed_at)}</small></div><button onClick={()=>navigate('conexiones')}>Consultar mi cuenta</button></section>
  <div className="home-cards">{cards.map(card=><button key={card.page} className={'home-card home-'+card.page} onClick={()=>navigate(card.page)}><span className="card-art" aria-hidden="true">{card.icon}</span><span className="eyebrow">FC27 · {card.page==='club'&&account.observed_copies!=null?`${money(account.observed_copies)} copias observadas`:'Progreso sin consultar'}</span><h3>{card.title}</h3><p>{card.text}</p><span className="card-open">Abrir sección →</span></button>)}</div>
  {mode==='local'&&<section className="panel local-summary"><h3>Tu registro local</h3><p>{counts.players} cartas revisadas · {counts.protected} protegidas · {counts.duplicates} duplicados. Presupuesto local DCP: {money(profile.max_budget)}.</p><p>Estos datos de planificación no acreditan recursos ni progreso actuales en EA.</p><button onClick={()=>navigate('club')}>Revisar registro</button></section>}
 </>
}
export function StorePage(){return <><SectionTitle title="Tienda" subtitle="Contenido y saldo sin consultar"/><section className="panel"><h3>Ofertas no disponibles</h3><p>Esta aplicación todavía no tiene acceso autorizado a la tienda de tu cuenta. Consulta las ofertas y sus condiciones en la Web App oficial.</p><a className="official-entry" href="https://www.ea.com/es-es/ea-sports-fc/ultimate-team/web-app/" target="_blank" rel="noopener noreferrer">Abrir FC27 oficial ↗</a><p>Abre otra pestaña. Las decisiones y operaciones se realizan allí.</p></section></>}
