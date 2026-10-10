import {useState} from 'react'
import {useQuery} from '@tanstack/react-query'
import {api} from '../api/client'
import {useSeason} from '../lib/season'
import type {Player} from '../types'
import {ErrorBox} from './ui'

export function PlayerPicker({label,selected,onChange}:{label:string;selected:Player[];onChange:(players:Player[])=>void}){
  const season=useSeason(),[search,setSearch]=useState('')
  const query=useQuery({queryKey:['players','picker',season,search],enabled:search.trim().length>=2,queryFn:({signal})=>api<{items:Player[]}>(`/players?game_version=${season}&search=${encodeURIComponent(search)}&limit=12`,{signal})})
  return <div className="player-picker"><label>{label}<input value={search} onChange={event=>setSearch(event.target.value)} placeholder="Busca por nombre (2 letras)"/></label><div className="selected-chips">{selected.map(player=><button key={player.id} type="button" onClick={()=>onChange(selected.filter(item=>item.id!==player.id))} aria-label={`Quitar ${player.name}`}>{player.name} ×</button>)}</div>{search.trim().length>=2&&<div className="picker-results">{query.data?.items.filter(player=>!selected.some(item=>item.id===player.id)).map(player=><button type="button" key={player.id} onClick={()=>{onChange([...selected,player]);setSearch('')}}><strong>{player.rating} {player.position}</strong><span>{player.name}</span></button>)}{query.data?.items.length===0&&<p>No hay coincidencias.</p>}</div>}<ErrorBox error={query.error}/></div>
}
