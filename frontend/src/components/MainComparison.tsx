import type {MainComparison as Comparison} from '../types'
export function MainComparison({value}:{value?:Comparison}){
 if(!value)return null
 return <details><summary>Comparar con mi principal</summary><p>{value.reason}</p><p>Coste adicional: {value.additional_cost} monedas. La principal conserva su once, banquillo y táctica.</p>{value.available&&<><p>{value.main_formation} → {value.proposed_formation}</p><ul>{value.rows.map(row=><li key={row.slot}><strong>{row.slot}</strong>: {row.main_name||'Sin puesto equivalente'} → {row.proposed_name}. {row.delta===null?'Comparación pendiente':row.delta===0?'Mismo encaje local':`${row.delta>0?'Mejora':'Pérdida'} de ${Math.abs(row.delta).toLocaleString('es-CO')} puntos de encaje local`}.</li>)}</ul></>}</details>
}
