import {useEffect,useRef,useState} from 'react'
import {useQueryClient} from '@tanstack/react-query'
import {api} from '../api/client'
import {invalidateClub} from '../lib/query'
import {stopTracks} from '../lib/capture'
import {StableFrames,drawMasked,drawMaskedSource,shareVisualSource,type Mask} from '../lib/scan-sampler'
import {observedDate} from '../lib/i18n'
import type {VisualScan,ScanCandidate,ReviewedScanCard,ScanSnapshot} from '../types/visual-scan'
import {ErrorBox} from './ui'

const labels = {scanning:'Escaneando',paused_user:'Pausado',paused_sensitive:'Pausa de privacidad',needs_review:'Pendiente de revisión',committing:'Guardando',completed_partial:'Guardado · cobertura parcial',failed:'Escaneo detenido por error',cancelled:'Cancelado'}
const positions = ['POR','LD','DFC','LI','CAD','CAI','MCD','MC','MCO','MD','MI','ED','EI','SD','DC']
function editable(c:ScanCandidate):ReviewedScanCard {
  return {candidate_key:c.candidate_key,ordinal:c.ordinal,name:c.name,rating:c.rating,position:c.position,
    card_type:c.card_type||null,league:null,club:null,nationality:null,is_loan:null,is_evolution:null,
    tradable:null,rare:null,special:null,is_holographic:null,location:'club',slot:null,existing_player_id:null}
}

export function VisualScanner({visible}:{visible:boolean}) {
  const qc=useQueryClient(),video=useRef<HTMLVideoElement>(null),stream=useRef<MediaStream|null>(null)
  const session=useRef<number|null>(null),generation=useRef(0),timer=useRef<ReturnType<typeof setTimeout>|undefined>(undefined)
  const request=useRef<AbortController|null>(null),sampler=useRef(new StableFrames()),sequence=useRef(0)
  const canvas=useRef<HTMLCanvasElement|null>(null),thumb=useRef<HTMLCanvasElement|null>(null),dimensions=useRef('')
  const [consent,setConsent]=useState(false),[section,setSection]=useState('club'),[scan,setScan]=useState<VisualScan>()
  const [sharing,setSharing]=useState(false),[busy,setBusy]=useState(false),[starting,setStarting]=useState(false),[error,setError]=useState<unknown>()
  const [masks,setMasks]=useState<Mask[]>([]),[mask,setMask]=useState<Mask>({x:0,y:0,width:100,height:8})
  const [crop,setCrop]=useState(false),[region,setRegion]=useState([0,0,100,100])
  const [rows,setRows]=useState<ScanCandidate[]>([]),[total,setTotal]=useState(0),[offset,setOffset]=useState(0)
  const [edits,setEdits]=useState<Record<string,ReviewedScanCard>>({}),[selected,setSelected]=useState<Record<string,boolean>>({})
  const [phrase,setPhrase]=useState(''),[identityReviewed,setIdentityReviewed]=useState(false),[snapshot,setSnapshot]=useState<ScanSnapshot>()
  const [history,setHistory]=useState<VisualScan[]>([])

  function clearLocal() {
    generation.current++;clearTimeout(timer.current);request.current?.abort();request.current=null
    stopTracks(stream.current);stream.current=null;sampler.current.reset();dimensions.current=''
    if(video.current){video.current.pause();video.current.srcObject=null}
    if(canvas.current)canvas.current.width=canvas.current.height=0
    if(thumb.current)thumb.current.width=thumb.current.height=0
  }
  async function loadCandidates(id:number,start=0) {
    const result=await api<{items:ScanCandidate[];total:number}>(`/visual-scans/${id}/candidates?offset=${start}`)
    if(session.current!==id)return
    setRows(result.items);setTotal(result.total);setOffset(start)
    setEdits(previous=>{const next={...previous};result.items.forEach(c=>{next[c.candidate_key]??=editable(c)});return next})
  }
  async function stop(action:'pause'|'stop'|'cancel'='stop') {
    clearLocal();setSharing(false);setStarting(false);setBusy(false)
    const id=session.current
    if(!id)return
    try{const result=await api<VisualScan>(`/visual-scans/${id}/transition`,{method:'POST',body:JSON.stringify({action}),keepalive:true});setScan(result);await loadCandidates(id)}catch(e){setError(e)}
  }
  useEffect(()=>{
    const close=()=>{clearLocal();const id=session.current;if(id)void api(`/visual-scans/${id}/transition`,{method:'POST',body:JSON.stringify({action:'stop'}),keepalive:true}).catch(()=>undefined)}
    window.addEventListener('pagehide',close)
    return()=>{window.removeEventListener('pagehide',close);close()}
  },[])
  useEffect(()=>{if(!visible)void stop()},[visible])
  const apply=(next:VisualScan)=>{setScan(next);if(next.status!=='scanning'){clearLocal();setSharing(false);setBusy(false);setStarting(false);if(next.reason)setError(new Error(next.reason));void loadCandidates(next.id).catch(setError)}}
  async function sendFrame(blob:Blob,ticket:number) {
    const id=session.current;if(!id||ticket!==generation.current)return
    const controller=new AbortController();request.current=controller
    const result=await api<VisualScan|{stopped:true}>(`/visual-scans/${id}/frames?sequence=${++sequence.current}`,{method:'POST',body:blob,headers:{'Content-Type':blob.type||'image/png'},signal:controller.signal})
    if(ticket===generation.current&&'status' in result)apply(result)
  }
  async function sample(ticket:number,activeMasks:Mask[]) {
    if(ticket!==generation.current||!stream.current)return
    try {
      const v=video.current!
      if(v.readyState>=2&&v.videoWidth){
        const size=`${v.videoWidth}x${v.videoHeight}`
        if(dimensions.current&&dimensions.current!==size)throw new Error('Cambió la resolución. Comparte otra vez y revisa las máscaras.')
        dimensions.current=size
        const full=canvas.current??=document.createElement('canvas'),small=thumb.current??=document.createElement('canvas')
        drawMasked(v,full,activeMasks);small.width=160;small.height=90
        const ctx=small.getContext('2d',{willReadFrequently:true})!;ctx.drawImage(full,0,0,160,90)
        if(sampler.current.inspect(ctx.getImageData(0,0,160,90).data)){
          const blob=await new Promise<Blob|null>(resolve=>full.toBlob(resolve,'image/png'))
          full.width=full.height=0
          if(blob)await sendFrame(blob,ticket)
        } else {full.width=full.height=0}
      }
    }catch(e){if(ticket===generation.current){setError(e);await stop()}}
    if(ticket===generation.current&&stream.current)timer.current=setTimeout(()=>void sample(ticket,activeMasks),1200)
  }
  async function start() {
    if(!consent)return
    setError(undefined);setStarting(true);const ticket=++generation.current;let media:MediaStream|null=null
    try{
      // This call stays before any await unrelated to the browser permission gesture.
      media=await shareVisualSource()
      if(ticket!==generation.current){stopTracks(media);return}
      const resuming=scan?.status==='paused_user'&&scan.section===section&&scan.source==='shared_tab'
      const created=resuming?await api<VisualScan>(`/visual-scans/${scan.id}/transition`,{method:'POST',body:JSON.stringify({action:'resume'})}):await api<VisualScan>('/visual-scans',{method:'POST',body:JSON.stringify({consent:true,section,source:'shared_tab',region:crop?region:null})})
      if(ticket!==generation.current){stopTracks(media);await api(`/visual-scans/${created.id}/transition`,{method:'POST',body:JSON.stringify({action:'stop'})});return}
      session.current=created.id;sequence.current=created.sequence;setScan(created);setEdits({});setSelected({});setRows([]);setSnapshot(undefined);setPhrase('');setIdentityReviewed(false)
      stream.current=media;setSharing(true);sampler.current.reset()
      media.getVideoTracks()[0].addEventListener('ended',()=>void stop(),{once:true})
      if(video.current){video.current.srcObject=media;await video.current.play()}
      void sample(ticket,masks)
    }catch(e){stopTracks(media);clearLocal();setSharing(false);setError(e instanceof DOMException&&e.name==='NotAllowedError'?new Error('Permiso cancelado. El escaneo sigue pendiente; no se inició otra captura.'):e);if(session.current)void stop()}
    finally{setStarting(false)}
  }
  async function upload(file?:File) {
    if(!file||!consent)return
    if(file.size>4*1024*1024){setError(new Error('La imagen supera 4 MB.'));return}
    setBusy(true);setError(undefined);const ticket=++generation.current
    try{
      const created=await api<VisualScan>('/visual-scans',{method:'POST',body:JSON.stringify({consent:true,section,source:'screenshot',region:crop?region:null})})
      if(ticket!==generation.current){await api(`/visual-scans/${created.id}/transition`,{method:'POST',body:JSON.stringify({action:'stop'})});return}
      session.current=created.id;sequence.current=0;setScan(created);setEdits({});setSelected({});setSnapshot(undefined)
      let blob:Blob=file
      if(masks.length){
        const bitmap=await createImageBitmap(file),target=document.createElement('canvas')
        try{drawMaskedSource(bitmap,bitmap.width,bitmap.height,target,masks);blob=await new Promise<Blob>((resolve,reject)=>target.toBlob(value=>value?resolve(value):reject(new Error('No se pudo enmascarar la imagen.')),'image/png'))}
        finally{bitmap.close();target.width=target.height=0}
      }
      await sendFrame(blob,ticket);if(ticket===generation.current)await stop()
    }catch(e){if(ticket===generation.current){setError(e);await stop()}}finally{if(ticket===generation.current)setBusy(false)}
  }
  async function save() {
    if(!scan)return
    setBusy(true);setError(undefined)
    try{
      const cards=Object.values(edits).filter(c=>selected[c.candidate_key])
      const result=await api<ScanSnapshot>(`/visual-scans/${scan.id}/commit`,{method:'POST',body:JSON.stringify({phrase,edition:'FC27',cards})})
      setSnapshot(result);setScan({...scan,status:'completed_partial'});await invalidateClub(qc);await qc.invalidateQueries({queryKey:['assisted-readings']})
    }catch(e){setError(e)}finally{setBusy(false)}
  }
  const change=(key:string,value:Partial<ReviewedScanCard>)=>setEdits(previous=>({...previous,[key]:{...previous[key],...value}}))
  const count=Object.values(selected).filter(Boolean).length
  return <section className="panel visual-scanner" hidden={!visible}>
    <h2>Escanear mi club</h2>
    <p>Abre el club, comparte su vista y navega manualmente. Se leen solo fotogramas estables; ninguna acción se ejecuta en EA.</p>
    <a className="button" href="https://www.ea.com/es-es/ea-sports-fc/ultimate-team/web-app/" target="_blank" rel="noopener noreferrer">Abrir aplicación oficial de FC 27</a>
    <p>Vas a compartir contenido visual de la pestaña seleccionada. Solo se procesarán pantallas de juego; puedes detenerlo cuando quieras.</p>
    <label className="check"><input type="checkbox" checked={consent} disabled={sharing} onChange={e=>setConsent(e.target.checked)}/>Autorizo el procesamiento visual local de las pantallas que comparta</label>
    <label>Sección que voy a recorrer<select value={section} disabled={sharing||starting} onChange={e=>setSection(e.target.value)}>{Object.entries({club:'Jugadores de Mi club',squad:'Plantilla',duplicates:'Duplicados',tradable:'Transferibles',untradeable:'Intransferibles'}).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label>
    <details><summary>Seleccionar región de lectura</summary><label className="check"><input type="checkbox" checked={crop} disabled={sharing||starting||scan?.status==='paused_user'} onChange={e=>setCrop(e.target.checked)}/>Extraer cartas solo de esta región</label><p>Se comprueba primero la pantalla completa para detectar contenido sensible. Para cambiar la región de un lote pausado, detén ese lote y comienza otro.</p><div className="form-grid">{['Izquierda','Arriba','Ancho','Alto'].map((label,i)=><label key={label}>{label} de región (%)<input type="number" min={0} max={100} disabled={sharing||starting||scan?.status==='paused_user'} value={region[i]} onChange={e=>setRegion(values=>values.map((value,n)=>n===i?Number(e.target.value):value))}/></label>)}</div></details>
    <details><summary>Máscaras de privacidad antes de compartir</summary><p>Las zonas negras se aplican en el navegador antes del envío. Conserva visible el título del club. La detección de pantallas sensibles es heurística; no compartas acceso, correo, perfil ni pagos.</p><div className="form-grid">{(['x','y','width','height'] as const).map((key,i)=><label key={key}>{['Izquierda','Arriba','Ancho','Alto'][i]} de máscara (%)<input type="number" min={0} max={100} disabled={sharing} value={mask[key]} onChange={e=>setMask({...mask,[key]:Number(e.target.value)})}/></label>)}</div><button disabled={sharing||masks.length>=5||mask.width<=0||mask.height<=0||mask.x<0||mask.y<0||mask.x+mask.width>100||mask.y+mask.height>100} onClick={()=>setMasks([...masks,mask])}>Añadir máscara</button><button disabled={sharing} onClick={()=>setMasks([])}>Quitar máscaras</button><p>{masks.length} máscaras activas</p></details>
    <div className="button-row"><button className="primary" disabled={!consent||sharing||starting||busy} onClick={()=>void start()}>{scan?.status==='paused_user'?'Volver a compartir y reanudar':'Compartir pestaña y comenzar escaneo'}</button><button disabled={!sharing&&!starting} onClick={()=>void stop('pause')}>Pausar escaneo</button><button disabled={!sharing&&!starting&&!busy} onClick={()=>void stop()}>Detener escaneo</button></div>
    <label>Alternativa: imagen de lista<input type="file" accept="image/png,image/jpeg,image/webp" disabled={!consent||sharing||starting||busy} onChange={e=>{void upload(e.target.files?.[0]);e.target.value=''}}/></label>
    <video ref={video} className="capture-preview" muted playsInline hidden={!sharing} aria-label="Vista privada del escaneo"/>
    <p role="status">{starting?'Esperando selección de pestaña':scan?labels[scan.status]:'Escaneo pendiente'} · {sharing?'Captura activa · sin audio':'Captura inactiva'}</p>
    {scan&&<><div className="scan-metrics"><p>Páginas observadas: <strong>{scan.pages}</strong></p><p>Cartas candidatas únicas: <strong>{scan.unique_candidates}</strong></p><p>Posibles duplicados: <strong>{scan.possible_duplicates}</strong></p><p>Capturas descartadas: <strong>{scan.discarded}</strong></p></div><p>Cobertura sin determinar · Último fotograma: {scan.last_frame_at?observedDate(scan.last_frame_at):'Ninguno'}</p><p>{sharing?'Desplázate hasta el siguiente grupo y espera a que se estabilice.':'Revisa las cartas y su variante antes de guardar. No se eliminan cartas que no aparezcan.'}</p></>}
    <ErrorBox error={error}/>
    {!sharing&&scan&&<><div className="button-row"><button onClick={()=>void loadCandidates(scan.id).catch(setError)} disabled={busy}>Revisar lote detectado</button><button onClick={()=>void stop('cancel')} disabled={busy||scan.status==='completed_partial'}>Cancelar lote</button></div>
      {rows.map(c=>{const e=edits[c.candidate_key]||editable(c);return <fieldset className="scan-review-card" key={c.candidate_key}><legend>{c.name} · copia observada {c.copy_index}</legend><p>{c.sightings.length} vistas coincidentes · confianza OCR {Math.round((c.confidence?.name||0)*100)} %. Identidad y cantidad requieren revisión.</p><label className="check"><input type="checkbox" checked={!!selected[c.candidate_key]} onChange={event=>setSelected({...selected,[c.candidate_key]:event.target.checked})}/>Incluir {c.name}</label><div className="form-grid">
        <label>Nombre<input maxLength={100} value={e.name} onChange={event=>change(c.candidate_key,{name:event.target.value})}/></label><label>Media<input type="number" min={40} max={99} value={e.rating} onChange={event=>change(c.candidate_key,{rating:Number(event.target.value)})}/></label><label>Posición<select value={e.position} onChange={event=>change(c.candidate_key,{position:event.target.value})}>{positions.map(p=><option key={p}>{p}</option>)}</select></label>
        <label>Variante visible<input maxLength={40} placeholder="Desconocida" value={e.card_type||''} onChange={event=>change(c.candidate_key,{card_type:event.target.value||null})}/></label>
        {(['league','club','nationality'] as const).map((key,i)=><label key={key}>{['Liga','Club','Nacionalidad'][i]}<input maxLength={80} value={e[key]||''} placeholder="Desconocida" onChange={event=>change(c.candidate_key,{[key]:event.target.value||null})}/></label>)}
        {(['is_loan','is_evolution','tradable','rare','special','is_holographic'] as const).map((key,i)=><label key={key}>{['Cesión','Evolución','Transferible','Rara','Especial','Holográfica'][i]}<select value={e[key]==null?'':String(e[key])} onChange={event=>change(c.candidate_key,{[key]:event.target.value===''?null:event.target.value==='true'})}><option value="">Desconocido</option><option value="true">Sí, revisado</option><option value="false">No, revisado</option></select></label>)}
        <label>Correspondencia de copia<select value={e.existing_player_id||''} onChange={event=>change(c.candidate_key,{existing_player_id:event.target.value?Number(event.target.value):null})}><option value="">Nueva copia: conservar duda si coincide</option>{c.existing.map(p=><option key={p.id} value={p.id} disabled={p.deleted||!p.visual}>#{p.id} · {p.card_type||'Variante desconocida'}{p.deleted?' · Retirada':''}</option>)}</select></label>
      </div></fieldset>})}
      {total>20&&<div className="button-row"><button disabled={offset===0} onClick={()=>void loadCandidates(scan.id,offset-20).catch(setError)}>20 anteriores</button><span>{offset+1}–{Math.min(total,offset+20)} de {total}</span><button disabled={offset+20>=total} onClick={()=>void loadCandidates(scan.id,offset+20).catch(setError)}>20 siguientes</button></div>}
      {!!total&&<><p>{count} cartas seleccionadas. Las coincidencias entre vistas se agrupan provisionalmente. Si representan variantes o copias distintas, no confirmes ese grupo: lee las fichas por separado con la lectura manual.</p><label className="check"><input type="checkbox" checked={identityReviewed} onChange={e=>setIdentityReviewed(e.target.checked)}/>Revisé FC27, propiedad, variantes y que las observaciones agrupadas representan la misma copia</label><label>Escribe GUARDAR SINCRONIZACION<input value={phrase} onChange={e=>setPhrase(e.target.value)}/></label><button className="primary" disabled={busy||!identityReviewed||!count||phrase!=='GUARDAR SINCRONIZACION'||!['paused_user','paused_sensitive','needs_review'].includes(scan.status)} onClick={()=>void save()}>Guardar sincronización</button></>}
    </>}
    {snapshot&&<div role="status">Snapshot #{snapshot.id}: {snapshot.changes.added.length} cartas nuevas, {snapshot.changes.updated.length} actualizadas, {snapshot.changes.preserved_unseen.length} conservadas. Cobertura parcial. Ninguna modificación en EA.</div>}
    <details><summary>Recuperar lotes de esta entrada</summary><button onClick={()=>void api<VisualScan[]>('/visual-scans').then(setHistory).catch(setError)}>Actualizar lotes</button>{history.map(s=><p key={s.id}><button disabled={sharing||busy} onClick={()=>{session.current=s.id;setScan(s);setEdits({});setSelected({});setSnapshot(undefined);void loadCandidates(s.id).catch(setError)}}>Lote #{s.id} · {labels[s.status]}</button></p>)}</details>
  </section>
}
