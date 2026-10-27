import {useEffect} from 'react'
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query'
import {api} from '../api/client'
import {navigate} from '../lib/navigation'
import {observedDate} from '../lib/i18n'
import {invalidateClub} from '../lib/query'
import type {AnalysisWorkflow} from '../types/workflow'
import {ErrorBox} from './ui'

const labels:Record<string,string>={complete:'Comprobado',partial:'Parcial',pending:'Pendiente',blocked:'Requiere una acción'}
export function ClubAnalysis(){
 const qc=useQueryClient()
 const query=useQuery({queryKey:['club-analysis-workflow'],queryFn:()=>api<AnalysisWorkflow>('/club/analysis-workflow'),refetchInterval:q=>q.state.data?.status==='active'?5000:false})
 const start=useMutation({mutationFn:()=>api<AnalysisWorkflow>('/club/analyze',{method:'POST',body:'{}'}),onSuccess:d=>qc.setQueryData(['club-analysis-workflow'],d)})
 const control=useMutation({mutationFn:(action:string)=>api<AnalysisWorkflow>('/club/analysis-workflow/action',{method:'POST',body:JSON.stringify({action})}),onSuccess:d=>qc.setQueryData(['club-analysis-workflow'],d)})
 const data=query.data,r=data?.report
 useEffect(()=>{if(data?.updated_at)void invalidateClub(qc)},[data?.updated_at,qc])
 return <section className="panel club-analysis" aria-label="Analizar mi club"><div className="analysis-heading"><div><span className="eyebrow">FC27 · ASISTENTE LOCAL</span><h2>Analizar mi club</h2><p>Lecturas observadas, protección de tu principal y propuestas calculadas en esta instalación.</p></div><button className="primary" disabled={start.isPending} onClick={()=>start.mutate()}>{start.isPending?'Calculando con tus datos…':'Analizar mi club'}</button></div>
 {!r&&<p>El análisis comprueba tus datos locales y solicita la vista al panel emparejado. Concede el permiso temporal desde el icono de la extensión; su ausencia se mostrará como pendiente.</p>}
 {r&&<><ol className="analysis-stages" aria-label="Progreso del análisis">{r.stages.map(s=><li key={s.key} data-state={s.status}><strong>{s.label}</strong><span>{labels[s.status]}</span><small>{s.evidence}</small></li>)}</ol>
 <div role="status"><h3>{data.status==='cancelled'?'Análisis cancelado':data.status==='paused'?'Análisis pausado':'Siguiente acción'}</h3><p>{data.status==='active'?r.next_action:'Historial conservado. No se admiten lecturas automáticamente mientras el recorrido está detenido.'}</p><p>Siguiente sección a abrir: <strong>{r.next_section}</strong>. Navega personalmente en EA.</p><button onClick={()=>navigate('conexiones')}>Revisar lector y observaciones</button>
 {data.status==='active'?<button onClick={()=>control.mutate('pause')}>Pausar lectura</button>:<button disabled={control.isPending} onClick={()=>control.mutate('resume')}>Reanudar análisis</button>}
 {data.status!=='cancelled'&&<button disabled={control.isPending} onClick={()=>control.mutate('cancel')}>Cancelar recorrido</button>}</div>
 <h3>Mis cartas observadas</h3><p>{r.inventory_count} cartas admitidas · {r.protected_count} protegidas · {r.ambiguous_count} identidades pendientes · {r.pending_observations} observaciones por revisar.</p>
 {r.source_counts.synthetic_dom>0&&<p className="warning">Incluye {r.source_counts.synthetic_dom} cartas SINTÉTICAS. No acreditan datos de tu cuenta EA.</p>}
 {!!r.source_counts.declared_local&&<p>{r.source_counts.declared_local} cartas declaradas en el registro local; no acreditan posesión observada.</p>}
 <p>{r.main.unchanged?'Principal local sin cambios':'La versión local de la principal cambió desde que comenzó este recorrido'} · revisión {r.main.revision}. {r.main.reason}</p>
 <details><summary>Cobertura y datos pendientes por sección</summary><ul>{r.sections.map(s=><li key={s.domain}>{s.label}: {s.observations} observaciones, {s.loaded_scopes} ámbitos y {s.reviewed} revisadas. Última lectura: {observedDate(s.last_observed_at)}.</li>)}</ul><p>Las filas y páginas observadas pueden solaparse. No se acredita el total del club ni se eliminan cartas ausentes de una página filtrada.</p></details>
 <h3>Propuestas y por qué</h3><p>Calculadas: {observedDate(r.calculated_at)} · {r.metrics.calculation_ms} ms · {r.metrics.llm_calls} llamadas a IA. Simulaciones sobre datos admitidos.</p>
 <details><summary>Equipos para jugar</summary><p>{r.modules.squads.reason}</p>{r.modules.squads.result?.groups.map((g,i)=><article key={i}><h4>{g.profiles.join(' / ')} · {g.squad.formation}</h4><p>{g.why}</p><ul>{g.squad.lineup.map(p=><li key={p.slot}>{p.slot}: {p.player.name} ({p.player.rating})</li>)}</ul><p>{g.squad.warnings.join(' ')}</p></article>)}<button onClick={()=>navigate('plantillas')}>Revisar equipos y banquillos</button></details>
 <details><summary>DCP con cartas aptas</summary><p>{r.modules.dcp.reason}</p>{r.modules.dcp.proposals.map(p=><article key={p.reading_id}><h4>{p.name||'DCP pendiente'}</h4><p>{p.reason}</p>{p.solutions?.length?p.solutions.map((s,i)=><p key={i}>Alternativa {i+1}: {s.players.map(p=>`${p.name} (${p.rating})`).join(', ')}</p>):<p>Sin solución acreditada con el subconjunto disponible.</p>}</article>)}<button onClick={()=>navigate('dcp')}>Revisar requisitos y alternativas</button></details>
 <details><summary>Equipos para objetivos</summary><p>{r.modules.objectives.reason}</p>{r.modules.objectives.proposals.map((p,i)=><article key={i}><p>{p.reason}</p>{p.proposals?.map(s=><p key={s.name}>{s.name}: {s.squad.lineup.map(p=>`${p.slot}: ${p.player.name}`).join(', ')}</p>)}</article>)}<button onClick={()=>navigate('objetivos')}>Revisar objetivos y diario</button></details>
 <details><summary>Galería y caso Birmingham City femenino</summary><p>{r.modules.gallery.scenarios.length} escenarios locales evaluados. {r.modules.gallery.reason}</p><p>{r.modules.gallery.birmingham.plan}</p><p>Referencia pública: {r.modules.gallery.birmingham.required_players} futbolistas del {r.modules.gallery.birmingham.team}. Historial, posesión y coste personal desconocidos.</p><ul>{r.modules.gallery.birmingham.missing.map(m=><li key={m}>{m}</li>)}</ul><a href={r.modules.gallery.birmingham.source_url} target="_blank" rel="noopener noreferrer">Consultar fuente del conjunto</a><button onClick={()=>navigate('galeria')}>Abrir planificador de Galería</button></details>
 <details><summary>Evoluciones y mercado</summary><p>{r.modules.evolutions.reason}</p><p>{r.modules.market.reason}</p><button onClick={()=>navigate('evoluciones')}>Revisar evoluciones</button><button onClick={()=>navigate('mercado')}>Revisar mercado</button></details>
 <h3>Cómo aplicarla en EA</h3><p>Comprueba las copias y crea una alternativa personalmente. Reutilizar titulares para jugar no los consume. Las propuestas no cambian tu plantilla activa, entregan DCP ni ejecutan compras, ventas o premios.</p>
 </>}
 <ErrorBox error={query.error||start.error||control.error}/></section>
}
