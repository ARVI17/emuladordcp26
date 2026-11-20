import {useState} from 'react'
import {useMutation} from '@tanstack/react-query'
import {api} from '../api/client'
import type {VisualReading} from '../types/assisted'
import {ErrorBox} from './ui'

export function BrowserTextReader({onPreview}:{onPreview:(reading:VisualReading)=>void}){
 const [text,setText]=useState(''),[page,setPage]=useState('Primeras 20 cartas')
 const preview=useMutation({mutationFn:()=>api<VisualReading>('/assisted/text-preview',{method:'POST',body:JSON.stringify({text,page})}),onSuccess:reading=>{setText('');onPreview(reading)}})
 return <section className="panel"><h2>Leer cartas desde texto visible</h2>
 <p>Copia o transcribe las cartas de tu club abierto en Chrome. Una carta por línea: media, posición y nombre. Acepta posiciones en inglés y español. Primero revisarás el resultado; pegar texto no guarda cartas.</p>
 <p>Es una transcripción revisada, sin autenticar la cuenta de EA. No incluyas datos de acceso.</p>
 <label>Página del texto<input maxLength={80} value={page} onChange={e=>setPage(e.target.value)}/></label>
 <label>Texto visible de las cartas<textarea rows={8} maxLength={8000} value={text} onChange={e=>setText(e.target.value)} placeholder={'85 CB Nombre de la carta\n84 POR Nombre del portero'}/></label>
 <details><summary>Añadir atributos visibles</summary><p>Opcionalmente añade una barra y los atributos, por ejemplo: 85 CB Nombre | PAC 70 SHO 40 PAS 65 DRI 60 DEF 85 PHY 80. También admite RIT, TIR, REG y FIS. Para porteros: DIV, HAN, KIC, REF, SPD y POS.</p></details>
 <button className="primary" disabled={!text.trim()||!page.trim()||preview.isPending} onClick={()=>preview.mutate()}>Preparar revisión del texto</button><ErrorBox error={preview.error}/>
 </section>
}
