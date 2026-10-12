import {useRef,useState} from 'react'
import {useMutation,useQueryClient} from '@tanstack/react-query'
import {api,downloadInventory} from '../api/client'
import {invalidateClub} from '../lib/query'
import {useSeason} from '../lib/season'
import type {ImportPreview} from '../types'
import {ErrorBox,Notice,Pagination} from './ui'

type ReviewedFile={file:File;data:ImportPreview;generation:number}
export function InventoryImport(){
  const season=useSeason(),qc=useQueryClient()
  const [file,setFile]=useState<File|null>(null),[reviewed,setReviewed]=useState<ReviewedFile|null>(null),[page,setPage]=useState(1),[message,setMessage]=useState('')
  const generation=useRef(0),confirmationInFlight=useRef(false),fileInput=useRef<HTMLInputElement>(null)
  const review=useMutation({mutationFn:async(args:{file:File;generation:number})=>{
    const body=new FormData();body.append('file',args.file);body.append('confirm','false');body.append('game_version',season)
    return {file:args.file,generation:args.generation,data:await api<ImportPreview>('/players/import',{method:'POST',body})}
  },onSuccess:data=>{if(data.generation===generation.current){setReviewed(data);setPage(1)}},onError:(_error,args)=>{if(args.generation===generation.current)setReviewed(null)}})
  const confirm=useMutation({mutationFn:async(snapshot:ReviewedFile)=>{
    if(snapshot.generation!==generation.current||snapshot.file!==file||!snapshot.data.preview_token)throw new Error('El archivo cambió. Revisa el archivo seleccionado antes de importarlo.')
    const body=new FormData();body.append('file',snapshot.file);body.append('confirm','true');body.append('preview_token',snapshot.data.preview_token);body.append('game_version',season)
    return api<{imported:number;already_imported?:boolean;original_imported?:number;quarantined?:number;original_quarantined?:number}>('/players/import',{method:'POST',body})
  },onSuccess:data=>{setMessage(data.already_imported?`Este lote ya estaba importado (${data.original_imported??0} cartas). No se duplicó.`:`Activadas: ${data.imported}. En cuarentena: ${data.quarantined??0}. Las pendientes no participan en el club.`);generation.current++;setReviewed(null);setFile(null);if(fileInput.current)fileInput.current.value='';void invalidateClub(qc)},onSettled:()=>{confirmationInFlight.current=false}})
  const selectFile=(next:File|null)=>{generation.current++;setFile(next);setReviewed(null);setMessage('');setPage(1);review.reset();confirm.reset()}
  const submit=()=>{if(!reviewed||confirm.isPending||confirmationInFlight.current)return;confirmationInFlight.current=true;confirm.mutate(reviewed)}
  const download=useMutation({mutationFn:(format:'csv'|'xlsx')=>downloadInventory(format,season)})
  const visible=reviewed?.data.preview.slice((page-1)*20,page*20)||[]
  return <details className="panel import-panel"><summary>Importar y exportar inventario</summary>
    <p>Revisa el archivo de {season}. La confirmación queda vinculada a ese archivo y no se repite.</p>
    <div className="import-actions"><label className="file-label">CSV o Excel<input ref={fileInput} type="file" accept=".csv,.xlsx" disabled={confirm.isPending} onChange={e=>selectFile(e.target.files?.[0]||null)}/></label><button disabled={!file||review.isPending||confirm.isPending} onClick={()=>{if(file)review.mutate({file,generation:generation.current})}}>{review.isPending?'Revisando…':'Revisar archivo'}</button><button disabled={download.isPending} onClick={()=>download.mutate('csv')}>Exportar CSV</button><button disabled={download.isPending} onClick={()=>download.mutate('xlsx')}>Exportar Excel</button></div>
    {reviewed&&<div className="import-preview"><div className="split"><div><h3>{reviewed.file.name}</h3><p>{reviewed.data.total} filas detectadas · {season}</p></div><span className="safe-tag">Formato revisado</span></div>
      <div className="table-scroll"><table><thead><tr><th>Nombre</th><th>Media</th><th>Posición</th><th>Liga</th><th>Club</th><th>Verificación</th></tr></thead><tbody>{visible.map((player,index)=><tr key={index}><td>{player.name}</td><td>{player.rating}</td><td>{player.position}</td><td>{player.league}</td><td>{player.club}</td><td>{player.validation_status==='documented'?'Variante documentada':'Cuarentena'}</td></tr>)}</tbody></table></div>
      <Pagination page={page} total={reviewed.data.preview.length} pageSize={20} onPage={setPage}/>
      {reviewed.data.preview.length<reviewed.data.total&&<p className="meta">La vista previa muestra {reviewed.data.preview.length} de {reviewed.data.total} filas. La validación del servidor cubre el archivo completo.</p>}
      <button className="primary" disabled={confirm.isPending||review.isPending||!reviewed.data.preview_token} onClick={submit}>{confirm.isPending?'Importando…':'Confirmar importación'}</button>
    </div>}
    {message&&<Notice>{message}</Notice>}<ErrorBox error={review.error||confirm.error||download.error}/>
  </details>
}
