import {observedDate} from '../lib/i18n'
import {money} from '../api/client'
import type {Player} from '../types'
import {attributeLabels} from '../lib/players'

export function PlayerCard({player:p,onEdit,onProtect,onDelete,pending=false,compact=false}:{player:Player;onEdit?:()=>void;onProtect?:()=>void;onDelete?:()=>void;pending?:boolean;compact?:boolean}){
  if(p.game_version!=='FC27'||!['documented','provider_verified'].includes(p.validation_status||''))return null
  const protectedNow=p.effective_protected??p.protected
  const pendingFields=p.metadata_pending||[]
  const labels:Record<string,string>={league:'liga',club:'club',nationality:'nacionalidad',card_type:'tipo',rare:'rareza',special:'especial',chemistry:'química',alternate_positions:'posiciones alternativas',attributes:'atributos',playstyles:'PlayStyles',roles:'roles',is_loan:'cesión',is_evolution:'evolución',tradable:'transferibilidad',is_holographic:'holográfico'}
  const attributes=Object.entries(p.attributes||{}).slice(0,6)
  return <article className={`player-card ${p.special?'special':''} ${protectedNow?'is-protected':''} ${p.is_holographic?'holographic':''}`}>
    <div className="rating"><strong>{p.rating}</strong><span>{p.position}</span></div>
    <div className="player-info"><h3 title={p.name}>{p.name}</h3><p>{p.club} · {p.league}</p><div className="tags">
      {p.is_evolution&&<span>Evolución</span>}{p.is_holographic&&<span>Holográfico</span>}{p.is_loan&&<span>Cesión</span>}{p.duplicate_untradeable&&<span className="warning-tag">Duplicado</span>}{protectedNow&&<span className="safe-tag">Protegido</span>}{p.availability&&p.availability!=='available'&&<span className="warning-tag">Disponibilidad por revisar: {p.availability==='absent'?'ausente en la lectura':'no utilizable'}</span>}{!p.data_reviewed&&<span className="warning-tag">Datos pendientes</span>}
    </div></div>
    <div className="player-price"><strong>{money(p.price)}</strong><small>monedas registradas</small></div>
    {!compact&&<div className="player-detail"><div className="tags"><span>{p.nationality}</span><span>{p.card_type}</span>{(p.alternate_positions||[]).map(position=><span key={position}>{position}</span>)}</div>
      {attributes.length>0?<dl className="attribute-grid">{attributes.map(([key,value])=><div key={key}><dt>{attributeLabels[key as keyof typeof attributeLabels]||key}</dt><dd>{value}</dd></div>)}</dl>:<p className="meta">Atributos detallados no disponibles; el encaje utiliza la media registrada.</p>}
      {(p.playstyles_plus||[]).length>0&&<p className="meta accent">PlayStyles+ · {p.playstyles_plus.join(' · ')}</p>}
      <div className="card-foot"><span>{p.tradable===null?'Transferibilidad desconocida':p.tradable?'Transferible':'Intransferible'} · {pendingFields.includes('chemistry')?'Química no disponible':`Química registrada ${p.chemistry}/3`}</span>{p.gallery_score!=null&&<span>Galería {money(p.gallery_score)} pt</span>}</div>
      <p className="meta">{p.ownership_source==='observed'?`Copia observada · ${observedDate(p.observed_at)}`:'Registro manual revisado'}</p>{pendingFields.length>0&&<p className="meta">Metadatos pendientes: {pendingFields.map(key=>labels[key]||key).join(', ')}.</p>}
    </div>}
    {(onEdit||onProtect||onDelete)&&<div className="card-actions">{onProtect&&<button disabled={pending} onClick={onProtect}>{p.protected?'Quitar protección manual':'Proteger'}</button>}{onEdit&&<button disabled={pending} onClick={onEdit}>Editar</button>}{onDelete&&<button className="danger" disabled={pending} onClick={onDelete}>Archivar</button>}</div>}
  </article>
}
