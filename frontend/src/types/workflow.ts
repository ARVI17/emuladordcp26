type ObjectiveTeam={name:string;squad:{lineup:{slot:string;player:{name:string}}[]}}
type ObjectiveResult={reason?:string;proposals?:ObjectiveTeam[]}
export type AnalysisWorkflow={
 id?:string;status:'idle'|'active'|'paused'|'cancelled';requested_at?:string;updated_at?:string;approved_profiles?:number;
 report:null|{
  stages:{key:string;label:string;status:'complete'|'partial'|'pending'|'blocked';evidence:string}[];
  sections:{domain:string;label:string;observations:number;loaded_scopes:number;reviewed:number;observed_rows:number;last_observed_at:string|null;complete:false}[];
  inventory_count:number;source_counts:Record<string,number>;protected_count:number;ambiguous_count:number;pending_observations:number;unknown_fields:Record<string,number>;
  main:{complete:boolean;unchanged:boolean;revision:number;reason:string|null;protected_copy_ids:number[]};
  next_action:string;next_section:string;calculated_at:string;metrics:{calculation_ms:number;llm_calls:number;ocr_calls:number};
  modules:{
   squads:{status:string;reason?:string;result?:{groups:{profiles:string[];why:string;squad:{formation:string;lineup:{slot:string;player:{id:number;name:string;rating:number}}[];warnings:string[]}}[]}};
   dcp:{status:string;reason?:string;proposals:{reading_id:number;name?:string;reason?:string;solutions?:{players:{id:number;name:string;rating:number}[]}[]}[]};
   objectives:{status:string;reason?:string;proposals:ObjectiveResult[]};
   gallery:{status:string;reason:string;scenarios:unknown[];birmingham:{source_url:string;required_players:number;team:string;missing:string[];plan:string}};
   evolutions:{status:string;reason:string};market:{status:string;reason:string};
  };
 };
}
