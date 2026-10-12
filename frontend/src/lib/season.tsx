import {createContext,useContext} from 'react'
import type {GameVersion} from '../types'

export const SeasonContext=createContext<GameVersion>('FC27')
export const useSeason=()=>useContext(SeasonContext)
export const seasonLabel=(_season:GameVersion)=>'FC 27'
