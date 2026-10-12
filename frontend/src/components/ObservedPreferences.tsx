import {useState} from 'react'
import type {Player} from '../types'
import {observedDate} from '../lib/i18n'
import {ErrorBox} from './ui'

export type ObservedEdits=Pick<Player,'notes'|'favorite'|'price'>
export function ObservedPreferences({player,onSave,onCancel,pending,error}:{player:Player;onSave:(value:ObservedEdits)=>void;onCancel:()=>void;pending:boolean;error:unknown}){
 const [notes,setNotes]=useState(player.notes||''),[favorite,setFavorite]=useState(!!player.favorite),[price,setPrice]=useState(player.price?.toString()||'')
 return <form className="panel" onSubmit={e=>{e.preventDefault();onSave({notes,favorite,price:price===''?null:Number(price)})}}>
  <h3>Preferencias de {player.name}</h3><p>Hechos de la copia observados el {observedDate(player.observed_at)}. Una nueva lectura autorizada puede actualizarlos.</p>
  <div className="form-grid"><label>Notas propias<textarea maxLength={2000} value={notes} onChange={e=>setNotes(e.target.value)}/></label><label>Precio local registrado<input type="number" min={0} max={100000000} step={1} value={price} onChange={e=>setPrice(e.target.value)}/></label><label className="check"><input type="checkbox" checked={favorite} onChange={e=>setFavorite(e.target.checked)}/>Favorita: proteger frente a consumo</label></div>
  <p className="meta">El precio es una estimación tuya; no acredita una cotización ni una venta.</p><ErrorBox error={error}/><div className="button-row"><button type="submit" disabled={pending}>Guardar preferencias</button><button type="button" disabled={pending} onClick={onCancel}>Cancelar</button></div>
 </form>
}
