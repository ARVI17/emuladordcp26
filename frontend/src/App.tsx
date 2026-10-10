import {useEffect,useState,type ReactNode} from 'react'
import {useIsMutating,useMutation,useQuery,useQueryClient} from '@tanstack/react-query'
import {api} from './api/client'
import {ErrorBox,Loading} from './components/ui'
import {SeasonContext,seasonLabel} from './lib/season'
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
function storedTheme(){try{return localStorage.getItem('theme')!=='light'}catch{return true}}

export default function App(){
  const qc=useQueryClient(),pendingMutations=useIsMutating()
  const [page,setPage]=useState<Page>('inicio'),[dark,setDark]=useState(storedTheme),[initialFormation,setInitialFormation]=useState('4-3-3')
  const profile=useQuery({queryKey:['profile'],queryFn:()=>api<Profile>('/profile')})
  const season:GameVersion=profile.data?.game_version==='FC26'?'FC26':'FC27'
  const changeSeason=useMutation({
    mutationFn:(game_version:GameVersion)=>api<Profile>('/profile',{method:'PATCH',body:JSON.stringify({game_version})}),
    onSuccess:async(data)=>{await qc.cancelQueries();qc.setQueryData(['profile'],data);await qc.invalidateQueries({predicate:query=>query.queryKey[0]!=='profile'})},
  })
  useEffect(()=>{document.documentElement.dataset.theme=dark?'dark':'light';try{localStorage.setItem('theme',dark?'dark':'light')}catch{/* El tema sigue funcionando sin almacenamiento. */}},[dark])
  useEffect(()=>{document.title=`${seasonLabel(season)} Club Lab`;document.getElementById('contenido')?.scrollIntoView?.({block:'start'})},[page,season])
  const pages:Record<Page,ReactNode>={
    inicio:<DashboardPage go={setPage}/>,club:<ClubPage/>,
    analisis:<AnalysisPage onBuild={formation=>{setInitialFormation(formation);setPage('plantillas')}}/>,
    plantillas:<SquadsPage initialFormation={initialFormation}/>,dcp:<ChallengesPage/>,
    galeria:<GalleryPage/>,evoluciones:<EvolutionsPage/>,novedades:<UpdatesPage/>,
    objetivos:<ObjectivesPage/>,duplicados:<DuplicatesPage/>,ia:<AiPage/>,
    emulador:<CompanionPage/>,configuracion:<SettingsPage dark={dark} setDark={setDark}/>,
  }
  return <SeasonContext.Provider value={season}><div className="app-shell">
    <a className="skip-link" href="#contenido">Saltar al contenido</a>
    <header className="topbar"><div className="brand"><span className="brand-mark" aria-hidden="true">F<span>27</span></span><div><span className="eyebrow">TU CLUB. TUS DECISIONES.</span><h1>{seasonLabel(season)} Club Lab</h1></div></div><div className="header-controls"><label className="season-control"><span>Temporada</span><select aria-label="Temporada activa" disabled={pendingMutations>0||profile.isLoading||!profile.data} value={season} onChange={event=>changeSeason.mutate(event.target.value as GameVersion)}><option value="FC27">FC 27</option><option value="FC26">FC 26 · archivo</option></select></label><span className="local-pill"><span aria-hidden="true">●</span> Local</span></div></header>
    <nav className="bottom-nav" aria-label="Navegación principal">{navigation.map(item=><button key={item.id} className={page===item.id?'active':''} onClick={()=>setPage(item.id)} aria-current={page===item.id?'page':undefined}><span aria-hidden="true">{item.icon}</span><small>{item.label}</small></button>)}</nav>
    <main id="contenido" className="content" tabIndex={-1}><ErrorBox error={changeSeason.error}/>{season==='FC26'&&<div className="season-banner">Archivo FC 26 · Su inventario y progreso se mantienen separados de FC 27.</div>}{profile.isLoading||changeSeason.isPending?<Loading/>:profile.error?<><ErrorBox error={profile.error}/><button onClick={()=>profile.refetch()}>Reintentar conexión local</button></>:<div className="page-content" key={`${page}-${season}`}>{pages[page]}</div>}</main>
    <footer className="app-footer">Club Lab · Datos locales · Revisa tus decisiones antes de aplicarlas en el juego.</footer>
  </div></SeasonContext.Provider>
}
