import {useEffect,useRef,useState,type ReactNode} from 'react'
import {useQuery,useQueryClient} from '@tanstack/react-query'
import {api,requestNonce} from '../api/client'
import {invalidateClub} from '../lib/query'
import {observedDate} from '../lib/i18n'
import {rememberAutomaticClub,type EntryState} from '../lib/entry'

type Bridge={id:string;version:string}
type SyncStatus={enabled:boolean;extension_id:string|null;status:string;message:string;request_id?:string;progress?:{pages_read:number;cards_read:number;phase:string};result:{request_id?:string;observed_at?:string;pages_read?:number;traversal_end?:string;inventory_ids?:number[];pending?:unknown[];main_complete?:boolean;protected_copy_ids?:number[]}}
const channel='club-lab-auto-v1'

export function AutoClubSync({entry,settings=false,children}:{entry:EntryState;settings?:boolean;children?:ReactNode}){
 const qc=useQueryClient(),[bridge,setBridge]=useState<Bridge>(),[error,setError]=useState(''),[busy,setBusy]=useState(false)
 const [discoveryWaited,setDiscoveryWaited]=useState(false)
 const nonce=useRef(requestNonce().slice(0,32)),started=useRef(false),lastResult=useRef<string|undefined>(undefined)
 const lastHello=useRef(0),boundId=useRef<string|null>(null)
 const status=useQuery({queryKey:['browser-auto',entry.club_context_id],queryFn:()=>api<SyncStatus>('/browser-auto/status'),refetchInterval:3000})
 boundId.current=status.data?.extension_id||null
 const matchingBridge=!!bridge&&(!boundId.current||boundId.current===bridge.id)
 const send=(kind:string,data:object={})=>window.postMessage({channel,nonce:nonce.current,kind,...data},location.origin)
 useEffect(()=>{
  if(status.data)rememberAutomaticClub(status.data.enabled?entry.club_context_id:null)
 },[entry.club_context_id,status.data?.enabled])
 useEffect(()=>{
  const receive=(event:MessageEvent)=>{
   if(event.source!==window||event.origin!==location.origin||event.data?.channel!==channel||event.data.nonce!==nonce.current)return
   const d=event.data
   if(d.kind==='hello'&&/^[a-p]{32}$/.test(d.extension_id)&&typeof d.version==='string'&&/^0\.(?:[7-9]|[1-9]\d)\./.test(d.version)&&(!boundId.current||boundId.current===d.extension_id)){
    lastHello.current=Date.now()
    setBridge(previous=>previous&&previous.id===d.extension_id&&previous.version===d.version?previous:{id:d.extension_id,version:d.version})
   }
   if(d.kind==='finished'){void status.refetch();if(!d.ok)setError('La lectura no terminó. Consulta el estado y conserva la sesión de EA abierta.')}
  }
  window.addEventListener('message',receive)
  send('discover')
  const timer=setInterval(()=>{
   if(lastHello.current&&Date.now()-lastHello.current>10000)setBridge(undefined)
   send('discover')
  },3000)
  const discoveryTimer=setTimeout(()=>setDiscoveryWaited(true),6000)
  return()=>{send('cancel');clearInterval(timer);clearTimeout(discoveryTimer);window.removeEventListener('message',receive)}
 },[])
 const start=async()=>{
  if(!matchingBridge||busy)return
  setBusy(true);setError('')
  try{
   const ticket=await api<Record<string,unknown>>('/browser-auto/start',{method:'POST',body:'{}'})
   send('start',{ticket})
   await status.refetch()
  }catch(e){setError(e instanceof Error?e.message:'No se pudo iniciar la lectura local.')}
  finally{setBusy(false)}
 }
 useEffect(()=>{
  if(!busy&&status.data?.enabled&&matchingBridge&&!started.current){
   started.current=true
   if(status.data.status!=='reading')void start()
  }
 },[matchingBridge,status.data?.enabled,status.data?.status,busy])
 useEffect(()=>{
  const id=status.data?.result.request_id
  if(id&&lastResult.current!==id){lastResult.current=id;void invalidateClub(qc)}
 },[status.data?.result.request_id])
 const configure=async(enabled:boolean)=>{
  const id=status.data?.extension_id||bridge?.id
  if(!id)return
  setError('');setBusy(true)
  try{
   await api('/browser-auto/settings',{method:'POST',body:JSON.stringify({extension_id:id,enabled,protect_main:true,confirmation:'ACTIVAR LECTURA LOCAL AUTOMATICA'})})
   if(!enabled)send('cancel')
   started.current=false
   await status.refetch()
  }catch(e){setError(e instanceof Error?e.message:'No se pudo guardar la preferencia.')}
  finally{setBusy(false)}
 }
 const stop=async()=>{setError('');send('cancel');try{await api('/browser-auto/cancel',{method:'POST',body:'{}'});await status.refetch()}catch{setError('No se confirmó la detención en el servidor. Conserva la última lectura y vuelve a abrir la app.')}}
 if(!settings&&!status.data?.extension_id)return <>{children}</>
 return <><section className="panel" aria-label="Actualización automática del club">
  <h3>Actualización al abrir Club Lab</h3>
  <p role="status">{status.data?.enabled&&!matchingBridge?(discoveryWaited?'Esperando al lector de Chrome. El plan usa las cartas guardadas.':'Buscando la extensión local de Club Lab…'):status.data?.message||'Comprobando el lector local…'}</p>
  {matchingBridge&&<p>Lector {bridge?.version} conectado a esta pestaña.</p>}
  {status.data?.extension_id&&!status.data.result.observed_at&&<p>Aún no hay una lectura automática guardada para este club.</p>}
  {status.data?.status==='reading'&&status.data.progress&&<p>En segundo plano: {status.data.progress.phase==='squad'?'comprobando once y suplentes':status.data.progress.phase==='publishing'?'guardando la lectura':`${status.data.progress.pages_read} páginas y ${status.data.progress.cards_read} cartas leídas`}. Puedes seguir usando Club Lab.</p>}
  {status.data?.result.observed_at&&<p>Última lectura: {observedDate(status.data.result.observed_at)} · {status.data.result.inventory_ids?.length||0} cartas leídas · {status.data.result.protected_copy_ids?.length||0} cartas protegidas · {status.data.result.main_complete?'principal protegida':'principal pendiente'}. Cobertura parcial{status.data.result.pages_read?` · ${status.data.result.pages_read} páginas`:''}.</p>}
  {settings&&<><p>Lectura por páginas de tus jugadores y de la plantilla activa, en la web oficial de EA. El lector avanza en una pestaña de segundo plano; no necesitas copiar cartas ni cambiar de página. Chrome debe permanecer abierto y EA puede pedirte iniciar sesión. Cada recorrido tiene un límite de 50 páginas, 1000 cartas o 30 minutos; no incluye todavía almacén DCP, mercado ni Galería. Los datos se guardan en este equipo; la extensión no solicita tu contraseña ni conecta tu cuenta a otros sitios.</p>
   <p>Lector no oficial. <a href="https://help.ea.com/en/articles/ea-sports-fc/fc-rules/" target="_blank" rel="noreferrer">EA restringe las automatizaciones</a>; no se garantiza ausencia de sanciones.</p>
   {!matchingBridge&&!status.data?.enabled&&<p>{status.data?.extension_id?'Ya vinculaste un lector a este club. Puedes activar la actualización y empezará cuando Chrome lo detecte.':'Activa el lector de Club Lab en el perfil de Chrome donde usas EA.'}</p>}
   {status.data?.enabled&&<button disabled={busy} onClick={()=>void configure(false)}>Desactivar actualización automática</button>}
  </>}
  {status.data&&!status.data.enabled&&<button disabled={(!matchingBridge&&!status.data.extension_id)||busy} onClick={()=>void configure(true)}>Activar actualización automática y proteger mi equipo</button>}
  {status.data?.enabled&&<><button disabled={!matchingBridge||busy||status.data.status==='reading'} onClick={()=>void start()}>Actualizar ahora</button>{status.data.status==='reading'&&<button onClick={()=>void stop()}>Detener lectura</button>}</>}
  {(error||status.error)&&<p role="alert">{error||'No se pudo consultar la actualización local.'}</p>}
 </section>{status.data?.enabled?(settings&&<details><summary>Herramientas manuales opcionales e historial</summary>{children}</details>):children}</>
}
