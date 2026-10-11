import {money} from '../api/client'
import type {Player} from '../types'
import {attributeLabels} from '../lib/players'

export function PlayerCard({player:p,onEdit,onProtect,onDelete,pending=false,compact=false}:{player:Player;onEdit?:()=>void;onProtect?:()=>void;onDelete?:()=>void;pending?:boolean;compact?:boolean}){
  const protectedNow=p.effective_protected??p.protected
  const attributes=Object.entries(p.attributes||{}).slice(0,6)
  return <article className={`player-card ${p.special?'special':''} ${protectedNow?'is-protected':''} ${p.is_holographic?'holographic':''}`}>
    <div className="rating"><strong>{p.rating}</strong><span>{p.position}</span></div>
    <div className="player-info"><h3 title={p.name}>{p.name}</h3><p>{p.club} · {p.league}</p><div className="tags">
      {p.game_version==='FC26'&&p.rare&&<span>Raro</span>}{p.is_evolution&&<span>Evolución</span>}{p.is_holographic&&<span>Holográfico</span>}{p.is_loan&&<span>Cesión</span>}{p.duplicate_untradeable&&<span className="warning-tag">Duplicado</span>}{protectedNow&&<span className="safe-tag">Protegido</span>}{p.availability&&p.availability!=='available'&&<span className="warning-tag">Disponibilidad por revisar: {p.availability==='absent'?'ausente en la lectura':'no utilizable'}</span>}{!p.data_reviewed&&<span className="warning-tag">Datos pendientes</span>}
    </div></div>
    <div className="player-price"><strong>{money(p.price)}</strong><small>monedas registradas</small></div>
    {!compact&&<div className="player-detail"><div className="tags"><span>{p.nationality}</span><span>{p.card_type}</span>{(p.alternate_positions||[]).map(position=><span key={position}>{position}</span>)}</div>
      {attributes.length>0?<dl className="attribute-grid">{attributes.map(([key,value])=><div key={key}><dt>{attributeLabels[key as keyof typeof attributeLabels]||key}</dt><dd>{value}</dd></div>)}</dl>:<p className="meta">Añade atributos para afinar el análisis por posición.</p>}
      {(p.playstyles_plus||[]).length>0&&<p className="meta accent">PlayStyles+ · {p.playstyles_plus.join(' · ')}</p>}
      <div className="card-foot"><span>{p.tradable===null?'Transferibilidad desconocida':p.tradable?'Transferible':'Intransferible'} · Química {p.chemistry}/3</span>{p.gallery_score!=null&&<span>Galería {money(p.gallery_score)} pt</span>}</div>
    </div>}
    {(onEdit||onProtect||onDelete)&&<div className="card-actions">{onProtect&&<button disabled={pending} onClick={onProtect}>{p.protected?'Quitar protección manual':'Proteger'}</button>}{onEdit&&<button disabled={pending} onClick={onEdit}>Editar</button>}{onDelete&&<button className="danger" disabled={pending} onClick={onDelete}>Archivar</button>}</div>}
  </article>
}
