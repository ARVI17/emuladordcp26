import {money} from '../api/client'
import {es,observedDate} from '../lib/i18n'
import {navigate,sections,type Page} from '../lib/navigation'
import type {AccountSummary} from '../types'
export function AccountHeader({page,account}:{page:Page;account?:AccountSummary}){
  return <header className="account-header"><div className="brand"><span className="brand-mark" aria-hidden="true">F<span>27</span></span><div><h1>Club Lab FC27</h1><span className="meta">{es.unofficial}</span></div></div><div className="section-name">{sections[page].label}</div><div className="account-facts"><strong>{account?.name||'Club sin verificar'}</strong><span>{account?.platform||'Plataforma sin consultar'}</span><div><span>Monedas <b>{account?.coins==null?es.unknown:money(account.coins)}</b></span><span>FC Points <b>{account?.fc_points==null?es.unknown:money(account.fc_points)}</b></span></div><small>{account?.identity_verified?'Identidad observada':'Cuenta no vinculada'} · {account?.observation_mode==='visual_assisted'?'Observación visual revisada':'Lectura'}: {observedDate(account?.observed_at)}</small><button onClick={()=>navigate('conexiones')}>Mi cuenta</button></div></header>
}
