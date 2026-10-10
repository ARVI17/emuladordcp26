import type {ReactNode} from 'react'
import {render} from '@testing-library/react'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {SeasonContext} from '../lib/season'
import {emptyPlayer} from '../lib/players'
import type {GameVersion,Player,Profile} from '../types'

export function renderClub(ui:ReactNode,season:GameVersion='FC27'){
  const client=new QueryClient({defaultOptions:{queries:{retry:false,gcTime:0},mutations:{retry:false}}})
  return {...render(<QueryClientProvider client={client}><SeasonContext.Provider value={season}>{ui}</SeasonContext.Provider></QueryClientProvider>),client}
}
export const profile:Profile={id:1,name:'Mi club',coins:10000,platform:'Consola',max_budget:50000,risk_level:'medio',preferences:{},game_version:'FC27'}
export function player(overrides:Partial<Player>={}):Player{return {...emptyPlayer('FC27'),id:1,name:'Carta revisada',rating:82,position:'MC',league:'Liga local',club:'Club local',nationality:'Colombia',deleted:false,created_at:'2026-10-10T12:00:00Z',data_reviewed:true,...overrides}}
export function deferred<T>(){let resolve!:(value:T)=>void;let reject!:(error:unknown)=>void;const promise=new Promise<T>((yes,no)=>{resolve=yes;reject=no});return {promise,resolve,reject}}
