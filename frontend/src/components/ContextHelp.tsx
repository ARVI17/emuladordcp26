import type {AccountSummary} from '../types'
import {createContext,useContext,useEffect,useState,type ReactNode} from 'react'
import {useQuery} from '@tanstack/react-query'
import {api} from '../api/client'
import {es,observedDate} from '../lib/i18n'
import {navigate,sections,type Page} from '../lib/navigation'
import type {EntryState} from '../lib/entry'
import type {MainSquadStatus} from './MainSquadProtection'
import {ErrorBox} from './ui'
type Selection={player_ids?:number[];segment_id?:number;objective_ids?:number[];formation?:string}
const HelpContext=createContext<(value:Selection)=>void>(()=>{})
export function useHelpSelection(selection:Selection){const set=useContext(HelpContext),encoded=JSON.stringify(selection);useEffect(()=>{set(JSON.parse(encoded));return()=>set({})},[set,encoded])}
const advice:Partial<Record<Page,string>>={
 inicio:'Los artículos sin asignar pueden ser jugadores u otros tipos. Revisa su tipo, transferibilidad y protección antes de elegir un destino. Conservar o dejar pendiente no exige consumirlos.',
 club:'Selecciona una carta para revisar su copia, procedencia y protección. Una variante del catálogo no acredita que la poseas.',
 plantillas:'Revisa el once, banquillo y reservas antes de proteger tu principal. Cambiar de principal conserva las protecciones anteriores.',
 recomendadas:'Compara formaciones y atributos disponibles. Puedes jugar con copias protegidas o activar «No reutilizar mi principal». Guardar crea otra plantilla local.',
 'plantillas-objetivos':'Verifica composición, modalidad, dificultad y acciones pendientes. Un once válido no acredita goles, victorias ni premios.',
 objetivos:'Separa el progreso observado de las condiciones de composición. No marques progreso por generar o guardar una plantilla.',
 dcp:'Los filtros reducen candidatas; las protecciones y reservas siempre prevalecen. Revisa la solución y sus requisitos antes de confirmar el registro local.',
 galeria:'Comprueba la versión de cada carta, la fuente y los requisitos. Registrar una observación local no reclama recompensas en EA.',
 evoluciones:'Compara requisitos, ruta y vencimiento; las proyecciones no aplican mejoras en el juego.',
 mercado:'Compara cotizaciones por mercado y fecha. Un precio desconocido no es cero; el diario solo recoge operaciones que hayas contrastado.',
 conexiones:'Abrir la Web App oficial no conecta esta aplicación. Consulta aquí el diagnóstico y la cobertura autorizada disponible.',
}
export function ContextHelpScope({page,entry,account,children}:{page:Page;entry?:EntryState;account?:AccountSummary;children:ReactNode}){
 const [selection,setSelection]=useState<Selection>({}),[open,setOpen]=useState(false)
 const main=useQuery({queryKey:['main-squad'],enabled:open&&!!entry,queryFn:()=>api<MainSquadStatus>('/squads/main')})
 return <HelpContext.Provider value={setSelection}>{children}<details className="context-help panel" onToggle={e=>setOpen(e.currentTarget.open)}><summary>{es.help}</summary>{open&&<><h3>{sections[page].label}: contexto actual</h3><p>Cuenta: {account?.identity_verified?(account.name||'Nombre no disponible'):'Sin identidad verificada'} · Plataforma: {account?.platform||'No disponible'}</p><p>{advice[page]||'Consulta la procedencia y fecha de cada dato. Las propuestas y registros de este asistente son locales; revisa las acciones en el juego.'}</p><p>{entry?.mode==='local'?'Registro local sin vincular':`Lectura ${entry?.snapshot_id??'pendiente'}`} · {observedDate(entry?.observed_at)}</p>{selection.player_ids?.length? <p>Copias seleccionadas ({selection.player_ids.length}): {selection.player_ids.slice(0,20).join(', ')}{selection.player_ids.length>20?'…':''}</p>:<p>Sin cartas seleccionadas en esta vista.</p>}{selection.segment_id&&<p>Segmento en revisión: #{selection.segment_id}</p>}{selection.objective_ids?.length? <p>Objetivos elegidos: {selection.objective_ids.join(', ')}</p>:null}{selection.formation&&<p>Formación elegida: {selection.formation}</p>}<p>{main.data?.complete?'Tu principal está identificada y protegida para operaciones de consumo.':main.data?.reason||'Protección de la principal pendiente de consultar.'}</p><ErrorBox error={main.error}/><p className="meta">Orientación basada en esta pantalla y sus datos. Funciona sin IA y no ejecuta operaciones.</p><button onClick={()=>navigate('conexiones')}>Revisar fuente y conexión</button></>}</details></HelpContext.Provider>
}
