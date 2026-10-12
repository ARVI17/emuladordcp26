import {TransfersPage} from './pages/TransfersPage'
import {PlannerPage} from './pages/PlannerPage'
import {MarketPage} from './pages/MarketPage'
import {KnowledgePage} from './pages/KnowledgePage'
import {openEntry,type EntryState} from './lib/entry'
import {ConnectionsPage} from './pages/ConnectionsPage'
import {BuildStatus} from './components/BuildStatus'
import {useEffect,useRef,useState,type ReactNode} from 'react'
import {useQuery,useQueryClient} from '@tanstack/react-query'
import {api} from './api/client'
import {ErrorBox,Loading} from './components/ui'
import {SeasonContext} from './lib/season'
import type {Page} from './lib/navigation'
import type {GameVersion,Profile} from './types'
import {ClubPage} from './pages/ClubPage'
import {AnalysisPage} from './pages/AnalysisPage'
import {SquadsPage} from './pages/SquadsPage'
import {ChallengesPage} from './pages/ChallengesPage'
import {GalleryPage} from './pages/GalleryPage'
import {EvolutionsPage} from './pages/EvolutionsPage'
import {UpdatesPage} from './pages/UpdatesPage'
import {CompanionPage} from './pages/CompanionPage'
import {AiPage,DashboardPage,DuplicatesPage,ObjectivesPage,SettingsPage} from './pages/OverviewPages'

const navigation:{id:Page;label:string;icon:string}[]=[
  {id:'conexiones',label:'Mi cuenta',icon:'◎'},
  {id:'fichajes',label:'Fichajes',icon:'↔'},
  {id:'planes',label:'Planes',icon:'✓'},
  {id:'mercado',label:'Mercado',icon:'◇'},
  {id:'referencias',label:'Referencias',icon:'≡'},
  {id:'inicio',label:'Inicio',icon:'⌂'},
  {id:'club',label:'Mi club',icon:'♙'},
  {id:'analisis',label:'Análisis',icon:'◉'},
  {id:'plantillas',label:'Plantillas',icon:'▦'},
  {id:'dcp',label:'DCP',icon:'◇'},
  {id:'galeria',label:'Galería',icon:'▧'},
  {id:'evoluciones',label:'Evoluciones',icon:'↗'},
  {id:'novedades',label:'Novedades',icon:'✧'},
  {id:'objetivos',label:'Objetivos',icon:'◎'},
  {id:'duplicados',label:'Duplicados',icon:'⧉'},
  {id:'ia',label:'IA local',icon:'✦'},
  {id:'emulador',label:'Emulador',icon:'▣'},
  {id:'configuracion',label:'Ajustes',icon:'⚙'},
]
const dependencies:Partial<Record<Page,string>>={inicio:'analysis',club:'analysis',analisis:'analysis',plantillas:'squads',planes:'analysis',dcp:'dcp',galeria:'gallery',evoluciones:'evolutions',duplicados:'analysis',ia:'chat'}
function storedTheme(){try{return localStorage.getItem('theme')!=='light'}catch{return true}}

export default function App(){
  const qc=useQueryClient()
  const [page,setPage]=useState<Page>('conexiones'),[dark,setDark]=useState(storedTheme),[initialFormation,setInitialFormation]=useState('4-3-3')
  const [entry,setEntry]=useState<EntryState>(),[entryError,setEntryError]=useState<unknown>(),[entering,setEntering]=useState(true)
  const entryGeneration=useRef(0),mode=useRef<'live'|'local'>('live')
  const enter=async(next:'live'|'local',reason='open',contextId?:number)=>{const generation=++entryGeneration.current;mode.current=next;setEntry(undefined);setEntering(true);setEntryError(undefined);await qc.cancelQueries();qc.clear();try{const result=await openEntry(next,reason,contextId);if(generation===entryGeneration.current){setEntry(result);if(result.mode==='local')setPage('inicio')}}catch(error){if(generation===entryGeneration.current)setEntryError(error)}finally{if(generation===entryGeneration.current)setEntering(false)}}
  useEffect(()=>{void enter('live');let hiddenAt=0;const resume=()=>{if(document.hidden)hiddenAt=Date.now();else if(hiddenAt&&Date.now()-hiddenAt>=300000){hiddenAt=0;void enter(mode.current,'resume')}};document.addEventListener('visibilitychange',resume);return()=>document.removeEventListener('visibilitychange',resume)},[])
  const freshness=useQuery({queryKey:['entry-state',entry?.entry_id],enabled:!!entry&&entry.mode==='live',refetchInterval:60000,queryFn:()=>api<EntryState>(`/club-contexts/${entry!.club_context_id}/sync-state`)})
  const effectiveEntry=freshness.data||entry
  const profile=useQuery({queryKey:['profile'],enabled:!!entry&&!entering,queryFn:()=>api<Profile>('/profile')})
  const season:GameVersion='FC27'
  useEffect(()=>{document.documentElement.dataset.theme=dark?'dark':'light';try{localStorage.setItem('theme',dark?'dark':'light')}catch{/* El tema sigue funcionando sin almacenamiento. */}},[dark])
  useEffect(()=>{document.title='Club Lab FC27';document.getElementById('contenido')?.scrollIntoView?.({block:'start'})},[page,season])
  const pages:Record<Page,ReactNode>={
    fichajes:<TransfersPage entry={effectiveEntry}/>,planes:<PlannerPage/>,mercado:<MarketPage/>,referencias:<KnowledgePage/>,
    conexiones:<ConnectionsPage entry={entry} busy={entering} error={entryError} onEnter={next=>void enter(next,'retry')} onSelect={(id,next)=>void enter(next,'switch',id)}/>,
    inicio:<DashboardPage go={setPage}/>,club:<ClubPage/>,
    analisis:<AnalysisPage onBuild={formation=>{setInitialFormation(formation);setPage('plantillas')}}/>,
    plantillas:<SquadsPage initialFormation={initialFormation}/>,dcp:<ChallengesPage/>,
    galeria:<GalleryPage/>,evoluciones:<EvolutionsPage/>,novedades:<UpdatesPage/>,
    objetivos:<ObjectivesPage/>,duplicados:<DuplicatesPage/>,ia:<AiPage/>,
    emulador:<CompanionPage/>,configuracion:<SettingsPage dark={dark} setDark={setDark}/>,
  }
  return <SeasonContext.Provider value={season}><div className="app-shell">
    <a className="skip-link" href="#contenido">Saltar al contenido</a>
    <header className="topbar"><div className="brand"><span className="brand-mark" aria-hidden="true">F<span>27</span></span><div><span className="eyebrow">TU CLUB. TUS DECISIONES.</span><h1>Club Lab FC27</h1></div></div><div className="header-controls"><span className="local-pill"><span aria-hidden="true">●</span> Local</span></div></header>
    <nav className="bottom-nav" aria-label="Navegación principal">{navigation.map(item=><button key={item.id} className={page===item.id?'active':''} onClick={()=>setPage(item.id)} aria-current={page===item.id?'page':undefined}><span aria-hidden="true">{item.icon}</span><small>{item.label}</small></button>)}</nav>
    <main id="contenido" className="content" tabIndex={-1}>{entry?.mode==='local'&&<div className="season-banner">Registro local sin vincular · Simulaciones limitadas a los datos revisados. <button onClick={()=>setPage('conexiones')}>Ver conexión</button></div>}{entering?<Loading/>:!entry||(entry.mode==='live'&&!!dependencies[page]&&!effectiveEntry?.modules[dependencies[page]!]?.ready)?<ConnectionsPage entry={entry} busy={entering} error={entryError} onEnter={next=>void enter(next,'retry')} onSelect={(id,next)=>void enter(next,'switch',id)}/>:profile.isLoading?<Loading/>:profile.error?<><ErrorBox error={profile.error}/><button onClick={()=>profile.refetch()}>Reintentar conexión local</button></>:<div className="page-content" key={`${page}-${season}`}>{pages[page]}</div>}</main>
    <footer className="app-footer"><BuildStatus entry={effectiveEntry}/></footer>
  </div></SeasonContext.Provider>
}
