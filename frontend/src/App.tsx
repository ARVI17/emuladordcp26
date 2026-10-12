import {ContextHelpScope} from './components/ContextHelp'
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
import {Loading,SectionTitle} from './components/ui'
import {AppNavigation} from './components/AppNavigation'
import {AccountHeader} from './components/AccountHeader'
import {HomePage,StorePage} from './pages/HomePage'
import {PracticeAgenda} from './components/PracticeAgenda'
import {SeasonContext} from './lib/season'
import {currentPage,navigate,sections,type Page} from './lib/navigation'
import type {GameVersion,Dashboard} from './types'
import {ClubPage} from './pages/ClubPage'
import {AnalysisPage} from './pages/AnalysisPage'
import {SquadsPage} from './pages/SquadsPage'
import {ChallengesPage} from './pages/ChallengesPage'
import {GalleryPage} from './pages/GalleryPage'
import {EvolutionsPage} from './pages/EvolutionsPage'
import {UpdatesPage} from './pages/UpdatesPage'
import {CompanionPage} from './pages/CompanionPage'
import {AiPage,DuplicatesPage,ObjectivesPage,SettingsPage} from './pages/OverviewPages'

const dependencies:Partial<Record<Page,string>>={club:'analysis',analisis:'analysis',plantillas:'squads',recomendadas:'squads','plantillas-objetivos':'squads',planes:'analysis',dcp:'dcp',galeria:'gallery',evoluciones:'evolutions',duplicados:'analysis',ia:'chat'}
function storedTheme(){try{return localStorage.getItem('theme')!=='light'}catch{return true}}

export default function App(){
  const qc=useQueryClient()
  const [page,setPage]=useState<Page>(()=>currentPage()),[dark,setDark]=useState(storedTheme),[initialFormation,setInitialFormation]=useState('4-3-3')
  const [entry,setEntry]=useState<EntryState>(),[entryError,setEntryError]=useState<unknown>(),[entering,setEntering]=useState(true)
  const entryGeneration=useRef(0),mode=useRef<'live'|'local'>('live')
  const enter=async(next?:'live'|'local',reason='open',contextId?:number)=>{const generation=++entryGeneration.current;setEntry(undefined);setEntering(true);setEntryError(undefined);await qc.cancelQueries();qc.clear();try{const result=await openEntry(next,reason,contextId);if(generation===entryGeneration.current){mode.current=result.mode;setEntry(result)}}catch(error){if(generation===entryGeneration.current)setEntryError(error)}finally{if(generation===entryGeneration.current)setEntering(false)}}
  useEffect(()=>{void enter();let hiddenAt=0;const resume=()=>{if(document.hidden)hiddenAt=Date.now();else if(hiddenAt&&Date.now()-hiddenAt>=300000){hiddenAt=0;void enter(mode.current,'resume')}};document.addEventListener('visibilitychange',resume);return()=>document.removeEventListener('visibilitychange',resume)},[])
  useEffect(()=>{const update=()=>setPage(currentPage());window.addEventListener('hashchange',update);return()=>window.removeEventListener('hashchange',update)},[])
  const freshness=useQuery({queryKey:['entry-state',entry?.entry_id],enabled:!!entry&&entry.mode==='live',refetchInterval:60000,queryFn:()=>api<EntryState>(`/club-contexts/${entry!.club_context_id}/sync-state`)})
  const effectiveEntry=freshness.data||entry
  const dashboard=useQuery({queryKey:['dashboard','FC27'],enabled:!!entry&&!entering,queryFn:()=>api<Dashboard>('/dashboard')})
  const season:GameVersion='FC27'
  useEffect(()=>{document.documentElement.dataset.theme=dark?'dark':'light';try{localStorage.setItem('theme',dark?'dark':'light')}catch{/* El tema sigue funcionando sin almacenamiento. */}},[dark])
  useEffect(()=>{document.title=`${sections[page].label} · Club Lab FC27`;document.getElementById('contenido')?.focus({preventScroll:true});window.scrollTo({top:0})},[page,season])
  const pages:Record<Page,ReactNode>={
    fichajes:<TransfersPage entry={effectiveEntry}/>,planes:<PlannerPage/>,mercado:<MarketPage/>,referencias:<KnowledgePage/>,
    conexiones:<ConnectionsPage entry={entry} busy={entering} error={entryError} onEnter={next=>void enter(next,'retry')} onSelect={(id,next)=>void enter(next,'switch',id)}/>,
    inicio:<HomePage/>,tienda:<StorePage/>,club:<ClubPage/>,practica:<><SectionTitle title="Práctica" subtitle="Rutinas y registros locales"/><PracticeAgenda/></>,
    analisis:<AnalysisPage onBuild={formation=>{setInitialFormation(formation);navigate('recomendadas')}}/>,
    plantillas:<SquadsPage view="principal"/>,recomendadas:<SquadsPage initialFormation={initialFormation}/>,
    'plantillas-objetivos':<ObjectivesPage/>,dcp:<ChallengesPage/>,
    galeria:<GalleryPage/>,evoluciones:<EvolutionsPage/>,novedades:<UpdatesPage/>,
    objetivos:<ObjectivesPage/>,duplicados:<DuplicatesPage/>,ia:<AiPage/>,
    emulador:<CompanionPage/>,configuracion:<SettingsPage dark={dark} setDark={setDark}/>,
  }
  const observedClub=page==='club'&&effectiveEntry?.identity_verified&&!!effectiveEntry.snapshot_id
  const blocked=!observedClub&&entry?.mode==='live'&&!!dependencies[page]&&!effectiveEntry?.modules[dependencies[page]!]?.ready
  const squadSection=['plantillas','recomendadas','plantillas-objetivos'].includes(page)
  return <SeasonContext.Provider value={season}><div className="app-shell single-app">
    <a className="skip-link" href="#contenido" onClick={e=>{e.preventDefault();document.getElementById('contenido')?.focus()}}>Saltar al contenido</a>
    <AccountHeader page={page} account={dashboard.data?.account}/><AppNavigation page={page}/>
    <main id="contenido" className="content" tabIndex={-1}>{entry?.mode==='local'&&<div className="season-banner">Registro local sin vincular · Simulaciones limitadas a los datos revisados. <button onClick={()=>navigate('conexiones')}>Ver conexión</button></div>}
      {squadSection&&<nav className="section-tabs" aria-label="Secciones de Plantillas">{(['plantillas','recomendadas','plantillas-objetivos'] as Page[]).map(id=><button key={id} aria-current={page===id?'page':undefined} onClick={()=>navigate(id)}>{id==='plantillas'?'Principal':sections[id].label}</button>)}</nav>}
      {entering?<Loading/>:!entry?<ConnectionsPage entry={entry} busy={entering} error={entryError} onEnter={next=>void enter(next,'retry')}/>:blocked?<><SectionTitle title={sections[page].label}/><section className="panel"><h3>Lectura pendiente</h3><p>{effectiveEntry?.modules[dependencies[page]!]?.reason||'Esta sección requiere datos revisados de tu club.'}</p><button onClick={()=>navigate('conexiones')}>Revisar Mi cuenta</button></section></>:<div className="page-content" key={`${page}-${season}`}><ContextHelpScope page={page} entry={effectiveEntry} account={dashboard.data?.account}>{pages[page]}</ContextHelpScope></div>}</main>
    <footer className="app-footer"><BuildStatus entry={effectiveEntry}/></footer>
  </div></SeasonContext.Provider>
}
