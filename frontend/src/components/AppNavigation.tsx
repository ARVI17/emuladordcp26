import {useEffect,useRef} from 'react'
import {assistantPages,primaryPages,sections,navigate,type Page} from '../lib/navigation'

export function AppNavigation({page}:{page:Page}){
  const dialog=useRef<HTMLDialogElement>(null)
  useEffect(()=>{dialog.current?.close()},[page])
  function links(){
    const button=(id:Page)=><button key={id} aria-current={page===id||(id==='plantillas'&&['recomendadas','plantillas-objetivos'].includes(page))?'page':undefined} onClick={()=>{navigate(id);dialog.current?.close()}}><span aria-hidden="true">{sections[id].icon}</span>{sections[id].label}</button>
    return <>{primaryPages.map(button)}<details open={assistantPages.includes(page)}><summary>Asistente</summary>{assistantPages.map(button)}</details><div className="nav-account">{button('conexiones')}{button('configuracion')}</div></>
  }
  return <><button className="mobile-menu" aria-label="Abrir menú" onClick={()=>dialog.current?.showModal()}>☰ <span>Menú</span></button><aside className="app-sidebar"><p className="eyebrow">CLUB LAB / FC27</p><nav aria-label="Navegación principal">{links()}</nav></aside><dialog className="mobile-drawer" ref={dialog} aria-label="Menú de secciones"><button className="drawer-close" onClick={()=>dialog.current?.close()}>Cerrar menú ×</button><nav aria-label="Navegación móvil">{links()}</nav></dialog></>
}
