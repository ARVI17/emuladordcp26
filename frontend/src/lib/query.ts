import type {QueryClient} from '@tanstack/react-query'

export const clubQueryKeys=['main-squad','dcp-exclusions','players','dashboard','duplicates','squads','challenges','objectives','club-analysis','gallery','gallery-entries','gallery-sets','evolutions','submissions','quarantine','pending-definitions']
export function invalidateClub(qc:QueryClient){return Promise.all(clubQueryKeys.map(key=>qc.invalidateQueries({queryKey:[key]})))}
