import {observedDate} from '../lib/i18n'
import {useState} from 'react'
import {useMutation,useQuery} from '@tanstack/react-query'
import {api,money} from '../api/client'
import {PlayerEditor} from '../components/PlayerEditor'
import {ErrorBox,Notice,SectionTitle} from '../components/ui'
import {positions} from '../lib/players'
import type {EntryState} from '../lib/entry'
import type {Player,PlayerInput} from '../types'

type Candidate={card:PlayerInput;quote_id:number}
type Choice={variant_id:string;name:string;price:number;improvement:number;why:string;market:string;observed_at:string;source_url:string}
type Comparison={owned_alternative:Player|null;tiers:Record<string,Choice|null>;decision:string;missing:string[]}
export function TransfersPage({entry}:{entry?:EntryState}){
 const [position,setPosition]=useState('MC'),[budget,setBudget]=useState(0),[reserve,setReserve]=useState(0),[quote,setQuote]=useState(''),[editing,setEditing]=useState(false),[candidates,setCandidates]=useState<Candidate[]>([])
 const quotes=useQuery({queryKey:['quotes'],queryFn:()=>api<{id:number;variant_id:string;amount:number;market:string;expired:boolean}[]>('/market/quotes')})
 const compare=useMutation({mutationFn:()=>api<Comparison>('/transfers/compare',{method:'POST',body:JSON.stringify({position,budget,reserve,candidates})})})
 const ready=entry?.mode==='live'&&entry.modules.transfers?.ready
 return <><SectionTitle title="Fichajes por presupuesto" subtitle="Compara variantes públicas y cotizaciones revisadas con tu mejor alternativa propia."/>
 {!ready&&<Notice>Integración pendiente: faltan inventario completo y monedas verificadas del club. Puedes preparar fichas públicas; la comparación personal se habilita tras una lectura autorizada vigente.</Notice>}
 <section className="panel"><div className="form-grid"><label>Puesto<select value={position} onChange={e=>setPosition(e.target.value)}>{positions.map(p=><option key={p}>{p}</option>)}</select></label><label>Presupuesto máximo<input type="number" min={0} value={budget} onChange={e=>setBudget(Number(e.target.value))}/></label><label>Reserva de monedas<input type="number" min={0} value={reserve} onChange={e=>setReserve(Number(e.target.value))}/></label><label>Cotización de la variante<select value={quote} onChange={e=>setQuote(e.target.value)}><option value="">Seleccionar cotización vigente</option>{quotes.data?.filter(q=>!q.expired).map(q=><option key={q.id} value={q.id}>{q.variant_id} · {q.market} · {money(q.amount)}</option>)}</select></label></div><p>Registra primero la evidencia de precio en Mercado. Cada ficha debe usar la misma variante. No se añade al inventario.</p><button disabled={!quote} onClick={()=>setEditing(true)}>Revisar ficha pública candidata</button><ErrorBox error={quotes.error}/></section>
 {editing&&<PlayerEditor buttonLabel="Añadir a esta comparación pública" initial={{card_id:quotes.data?.find(q=>q.id===Number(quote))?.variant_id}} onCancel={()=>setEditing(false)} onSave={card=>{setCandidates([...candidates,{card,quote_id:Number(quote)}]);setEditing(false);compare.reset()}}/>}
 <section className="panel"><h3>Candidatas revisadas</h3>{candidates.length?<ul>{candidates.map((c,i)=><li key={i}>{c.card.name} · {c.card.card_id} <button onClick={()=>{setCandidates(candidates.filter((_,n)=>n!==i));compare.reset()}}>Quitar {c.card.name}</button></li>)}</ul>:<p>Aún no hay fichas para comparar. No se inventan precios ni necesidades de compra.</p>}<button disabled={!ready||compare.isPending} onClick={()=>compare.mutate()}>Comparar con mi club verificado</button><ErrorBox error={compare.error}/></section>
 {compare.data&&<section className="panel"><h3>Alternativas por coste</h3><p>Sin compra: {compare.data.owned_alternative?.name||'Sin alternativa elegible en la cobertura verificada'}. {compare.data.decision==='conservar_y_ahorrar'?'Conservar y ahorrar: ninguna mejora justifica un gasto según los datos disponibles.':'Revisa las mejoras y sus límites antes de decidir.'}</p><div className="card-grid">{Object.entries(compare.data.tiers).map(([tier,c])=><article key={tier}><h4>{{economica:'Económica · hasta 25 %',intermedia:'Intermedia · 25–60 %',ambiciosa:'Ambiciosa · 60–100 %'}[tier]}</h4>{c?<><p>{c.name} · {money(c.price)} · {c.market}</p><p>Cambio de encaje estimado: {c.improvement}. {c.why}</p><a href={c.source_url} rel="noreferrer" target="_blank">Precio observado el {observedDate(c.observed_at)}</a></>:<p>Sin candidata revisada en este tramo.</p>}</article>)}</div><Notice>{compare.data.missing.join('. ')}</Notice></section>}
 </>
}
