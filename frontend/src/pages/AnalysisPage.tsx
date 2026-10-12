import {useQuery} from '@tanstack/react-query'
import {api} from '../api/client'
import type {ClubAnalysis} from '../types'
import {useSeason} from '../lib/season'
import {Empty,ErrorBox,Loading,SectionTitle} from '../components/ui'
import {PlayerCard} from '../components/PlayerCard'

export function AnalysisPage({onBuild}:{onBuild:(formation:string)=>void}){
  const season=useSeason()
  const query=useQuery({queryKey:['club-analysis',season],queryFn:({signal})=>api<ClubAnalysis>(`/club/analysis?game_version=${season}`,{signal})})
  if(query.isLoading)return <Loading/>
  if(query.error||!query.data)return <ErrorBox error={query.error||new Error('No se recibió el análisis.')}/>
  const data=query.data,maximum=Math.max(1,...data.positions.map(item=>item.count))
  return <><SectionTitle title="Análisis de mi club" subtitle={`Fortalezas, profundidad y datos pendientes · ${season}`}/>
    <section className="analysis-hero panel"><div><span className="eyebrow">TU INVENTARIO, TUS OPCIONES</span><h3>{data.counts.players?`${data.counts.reviewed} cartas revisadas para decidir mejor`:'Empieza con tus jugadores'}</h3><p>El análisis usa los atributos y las posiciones que registraste. Los datos que faltan se muestran como pendientes.</p><button className="primary" disabled={!data.counts.reviewed||!data.recommended_formation} onClick={()=>{if(data.recommended_formation)onBuild(data.recommended_formation)}}>{data.recommended_formation?`Armar un ${data.recommended_formation}`:'Formaciones pendientes de revisión'}</button></div><div className="analysis-number"><strong>{data.average_rating.toFixed(1)}</strong><small>media del inventario</small></div></section>
    <section className="stat-grid"><div className="stat-tile"><span>Cartas revisadas</span><strong>{data.counts.reviewed}</strong></div><div className="stat-tile"><span>Por revisar</span><strong>{data.counts.unreviewed}</strong></div><div className="stat-tile"><span>Protegidas</span><strong>{data.counts.protected}</strong></div><div className="stat-tile"><span>Evoluciones</span><strong>{data.counts.evolutions}</strong></div></section>
    {data.warnings.length>0&&<div className="alert warning"><h3>Antes de elegir tu equipo</h3><ul>{data.warnings.map((warning,index)=><li key={index}>{warning}</li>)}</ul></div>}
    <div className="two-column"><section className="panel"><h3>Cobertura por posición</h3>{data.positions.length?<div className="position-bars">{data.positions.map(position=><div className="position-bar" key={position.position}><span>{position.position}</span><div className="track"><span style={{width:`${position.count/maximum*100}%`}}/></div><strong>{position.count}</strong><small>Mejor: {position.best_rating}</small></div>)}</div>:<Empty>Añade cartas para analizar posiciones.</Empty>}</section><section className="panel"><h3>Huecos por resolver</h3>{data.gaps.length?<div className="stack">{data.gaps.map((gap,index)=><div className="gap-card" key={index}><span className="position-badge">{gap.position}</span><p>{gap.reason}</p></div>)}</div>:<p>El inventario cubre las posiciones evaluadas. Compara formaciones para comprobar tu mejor combinación.</p>}<div className="data-summary"><span>{data.counts.loans} cesiones</span><span>{data.counts.holographic} holográficos</span><span>{data.counts.duplicates} duplicados</span></div></section></div>
    <section><SectionTitle title="Referentes del club" subtitle="Cartas destacadas de tu inventario registrado"/><div className="player-grid">{data.top_players.map(player=><PlayerCard key={player.id} player={player}/>)}</div></section>
  </>
}
