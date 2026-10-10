import {useEffect,useState} from 'react'
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query'
import {api} from '../api/client'
import {invalidateClub} from '../lib/query'
import {useSeason} from '../lib/season'
import {positions} from '../lib/players'
import type {Player,PlayerInput} from '../types'
import {PlayerCard} from '../components/PlayerCard'
import {PlayerEditor} from '../components/PlayerEditor'
import {InventoryImport} from '../components/InventoryImport'
import {Empty,ErrorBox,Loading,Notice,Pagination,SectionTitle} from '../components/ui'

export function ClubPage(){
  const season=useSeason(),qc=useQueryClient()
  const [search,setSearch]=useState(''),[debounced,setDebounced]=useState(''),[position,setPosition]=useState(''),[protection,setProtection]=useState(''),[sort,setSort]=useState('rating'),[page,setPage]=useState(1)
  const [editor,setEditor]=useState<Player|'new'|null>(null),[message,setMessage]=useState('')
  useEffect(()=>{const timer=setTimeout(()=>{setDebounced(search);setPage(1)},250);return()=>clearTimeout(timer)},[search])
  const params=new URLSearchParams({game_version:season,search:debounced,position,sort,order:sort==='name'?'asc':'desc',limit:'24',offset:String((page-1)*24)})
  if(protection)params.set('protected',protection)
  const query=useQuery({queryKey:['players',season,debounced,position,protection,sort,page],queryFn:({signal})=>api<{items:Player[];total:number}>(`/players?${params}`,{signal})})
  useEffect(()=>{if(query.data&&page>1&&query.data.items.length===0)setPage(Math.max(1,Math.ceil(query.data.total/24)))},[query.data,page])
  const save=useMutation({mutationFn:(player:PlayerInput)=>api<Player>(typeof editor==='object'&&editor?`/players/${editor.id}`:'/players',{method:typeof editor==='object'&&editor?'PATCH':'POST',body:JSON.stringify(player)}),onSuccess:()=>{setEditor(null);setMessage('Carta guardada. El análisis y la Galería ya pueden usar sus datos revisados.');void invalidateClub(qc)}})
  const protect=useMutation({mutationFn:(id:number)=>api(`/players/${id}/protect`,{method:'POST'}),onSuccess:()=>invalidateClub(qc)})
  const remove=useMutation({mutationFn:(id:number)=>api(`/players/${id}`,{method:'DELETE'}),onSuccess:()=>{setMessage('Carta archivada del inventario disponible.');void invalidateClub(qc)}})
  const busy=save.isPending||protect.isPending||remove.isPending
  return <><SectionTitle title="Mi club" subtitle={`${query.data?.total??'…'} cartas disponibles · ${season}`} action={<button className="primary compact" onClick={()=>{save.reset();setEditor('new');setMessage('')}}>+ Jugador</button>}/>
    {editor&&<PlayerEditor key={editor==='new'?'new':editor.id} initial={editor==='new'?undefined:editor} onSave={player=>save.mutate(player)} onCancel={()=>setEditor(null)} pending={save.isPending} error={save.error}/>}
    <div className="toolbar club-toolbar"><label>Buscar<input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Nombre, club o nacionalidad"/></label><label>Posición<select value={position} onChange={e=>{setPosition(e.target.value);setPage(1)}}><option value="">Todas</option>{positions.map(value=><option key={value}>{value}</option>)}</select></label><label>Protección<select value={protection} onChange={e=>{setProtection(e.target.value);setPage(1)}}><option value="">Todas las cartas</option><option value="true">Protegidas</option><option value="false">Sin protección</option></select></label><label>Ordenar<select value={sort} onChange={e=>{setSort(e.target.value);setPage(1)}}><option value="rating">Mayor media</option><option value="name">Nombre A–Z</option><option value="price">Mayor precio</option></select></label></div>
    <InventoryImport/>{message&&<Notice>{message}</Notice>}<ErrorBox error={protect.error||remove.error}/>
    {query.isLoading?<Loading/>:query.error?<ErrorBox error={query.error}/>:!query.data?.items.length?<Empty>No hay cartas que coincidan. Añade jugadores o importa tu inventario de {season}.</Empty>:<><Pagination page={page} total={query.data.total} pageSize={24} onPage={setPage} disabled={query.isFetching}/><div className="player-grid">{query.data.items.map(player=><PlayerCard key={player.id} player={player} pending={busy} onEdit={()=>{save.reset();setEditor(player)}} onProtect={()=>protect.mutate(player.id)} onDelete={()=>{if(window.confirm(`¿Archivar ${player.name} del inventario disponible?`))remove.mutate(player.id)}}/>)}</div><Pagination page={page} total={query.data.total} pageSize={24} onPage={setPage} disabled={query.isFetching}/></>}
  </>
}
