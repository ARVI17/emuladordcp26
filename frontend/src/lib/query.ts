import type {QueryClient} from '@tanstack/react-query'

export const clubQueryKeys=['domain-observation','assisted-readings','visual-existing-copies','gallery-scenarios','structured-reader','structured-event','journal-goals','objective-journal','objective-planning','main-squad','dcp-exclusions','players','dashboard','duplicates','squads','challenges','objectives','club-analysis','gallery','gallery-entries','gallery-sets','evolutions','submissions','quarantine','pending-definitions']
export function invalidateClub(qc:QueryClient){return Promise.all(clubQueryKeys.map(key=>qc.invalidateQueries({queryKey:[key]})))}
