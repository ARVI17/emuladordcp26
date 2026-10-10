import {createContext,useContext} from 'react'
import type {GameVersion} from '../types'

export const SeasonContext=createContext<GameVersion>('FC27')
export const useSeason=()=>useContext(SeasonContext)
export const seasonLabel=(season:GameVersion)=>season==='FC27'?'FC 27':'FC 26'
