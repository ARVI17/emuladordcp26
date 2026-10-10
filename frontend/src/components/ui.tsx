import type {ReactNode} from 'react'

export function Loading(){return <div className="state" role="status"><span className="spinner"/>Cargando datos locales…</div>}
export function ErrorBox({error}:{error:unknown}){return error?<div className="error-box" role="alert">{error instanceof Error?error.message:'No fue posible completar esta acción.'}</div>:null}
export function SectionTitle({title,subtitle,action}:{title:string;subtitle?:string;action?:ReactNode}){return <div className="section-title"><div><h2>{title}</h2>{subtitle&&<p>{subtitle}</p>}</div>{action}</div>}
export function Empty({children}:{children:ReactNode}){return <div className="empty">{children}</div>}
export function Notice({children}:{children:ReactNode}){return <div className="alert info" role="status">{children}</div>}
export function Pagination({page,total,pageSize,onPage,disabled=false}:{page:number;total:number;pageSize:number;onPage:(page:number)=>void;disabled?:boolean}){
  const pages=Math.max(1,Math.ceil(total/pageSize))
  return <nav className="pagination" aria-label="Paginación"><span>{total?`${(page-1)*pageSize+1}–${Math.min(total,page*pageSize)} de ${total}`:'Sin resultados'}</span><div><button disabled={disabled||page<=1} onClick={()=>onPage(page-1)}>Anterior</button><span aria-live="polite">{page} / {pages}</span><button disabled={disabled||page>=pages} onClick={()=>onPage(page+1)}>Siguiente</button></div></nav>
}
