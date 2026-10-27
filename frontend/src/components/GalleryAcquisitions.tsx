import {useQuery} from '@tanstack/react-query'
import {api,money} from '../api/client'
import {observedDate} from '../lib/i18n'
import {navigate} from '../lib/navigation'
import {ErrorBox} from './ui'
export type Acquisition={variant_id:string;purchase_quote_id:number;resale_quote_id:number|null;keep:boolean}
type Quote={id:number;variant_id:string;market:string;currency:string;kind:string;amount:number;expired:boolean;observed_at:string}
export function GalleryAcquisitions({market,value,onChange}:{market:string;value:Acquisition[];onChange:(v:Acquisition[])=>void}){
 const quotes=useQuery({queryKey:['quotes'],queryFn:()=>api<Quote[]>('/market/quotes')})
 const current=quotes.data?.filter(q=>q.market===market&&q.currency==='coins'&&!q.expired&&q.amount>0)||[]
 const purchases=current.filter(q=>q.kind==='listing')
 const update=(index:number,change:Partial<Acquisition>)=>onChange(value.map((c,i)=>i===index?{...c,...change}:c))
 const label=(q:Quote)=>`${q.variant_id} · ${money(q.amount)} · ${observedDate(q.observed_at)}`
 return <><p>Elige anuncios y salidas ya registrados. El servidor comprueba variante, puntos y vigencia. Una adquisición compartida se paga una vez; las cotizaciones no acreditan una venta tuya.</p>
 {!purchases.length&&<p>No hay anuncios vigentes de este mercado. Registra una cotización revisada en Transferibles.</p>}
 <button onClick={()=>navigate('mercado')}>Ver cotizaciones en Transferibles</button>
 {value.map((c,i)=><fieldset key={i}><legend>Adquisición propuesta {i+1}</legend>
 <label>Compra candidata {i+1}<select value={c.purchase_quote_id} onChange={e=>{const q=purchases.find(q=>q.id===Number(e.target.value));if(q)update(i,{purchase_quote_id:q.id,variant_id:q.variant_id,resale_quote_id:null})}}>{purchases.map(q=><option key={q.id} value={q.id}>{label(q)}</option>)}</select></label>
 <label>Salida estimada de candidata {i+1}<select value={c.resale_quote_id??''} onChange={e=>update(i,{resale_quote_id:e.target.value?Number(e.target.value):null})}><option value="">Desconocida</option>{current.filter(q=>q.variant_id===c.variant_id&&['listing','observed_sale'].includes(q.kind)).map(q=><option key={q.id} value={q.id}>{label(q)}</option>)}</select></label>
 <label className="check"><input type="checkbox" checked={c.keep} onChange={e=>update(i,{keep:e.target.checked})}/>Conservar la carta; no descontar una reventa</label>
 <button onClick={()=>onChange(value.filter((_,n)=>n!==i))}>Quitar candidata {i+1}</button></fieldset>)}
 <button disabled={value.length>=10||!purchases.some(q=>!value.some(c=>c.variant_id===q.variant_id))} onClick={()=>{const q=purchases.find(q=>!value.some(c=>c.variant_id===q.variant_id));if(q)onChange([...value,{variant_id:q.variant_id,purchase_quote_id:q.id,resale_quote_id:null,keep:true}])}}>Añadir adquisición candidata</button><ErrorBox error={quotes.error}/></>
}
