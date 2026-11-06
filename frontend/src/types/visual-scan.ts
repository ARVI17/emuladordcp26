import type {VisualCard} from './assisted'
export type ScanState = 'scanning'|'paused_user'|'paused_sensitive'|'needs_review'|'committing'|'completed_partial'|'failed'|'cancelled'
export type VisualScan = {id:number;status:ScanState;source:string;section:string;sequence:number;pages:number;unique_candidates:number;pending:number;possible_duplicates:number;discarded:number;last_frame_at:string|null;coverage:'unknown';complete:false;images_saved:false;reason:string|null;snapshot_id:number|null;ocr_seconds:number|null}
export type ScanCandidate = VisualCard & {candidate_key:string;confidence:Record<string,number>;sightings:{reading_id:number;ordinal:number}[];copy_index:number;identity_uncertain:true;existing:{id:number;name:string;card_type:string;deleted:boolean;visual:boolean}[]}
export type ReviewedScanCard = VisualCard & {candidate_key:string}
export type ScanSnapshot = {id:number;previous_id:number|null;before_count:number;after_count:number;changes:{added:number[];updated:number[];removed:number[];preserved_unseen:number[];coverage:'partial';ea_mutated:false}}
