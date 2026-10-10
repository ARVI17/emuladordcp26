import type {QueryClient} from '@tanstack/react-query'

export const clubQueryKeys=['players','dashboard','duplicates','squads','challenges','objectives','club-analysis','gallery','gallery-entries','gallery-sets','evolutions','submissions']
export function invalidateClub(qc:QueryClient){return Promise.all(clubQueryKeys.map(key=>qc.invalidateQueries({queryKey:[key]})))}
