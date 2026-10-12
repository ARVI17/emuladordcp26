export type GameVersion = 'FC27'
export type PendingDefinition = {id:number;game_version:'FC27';validation_status:'pending_verification';available:false;message:string}
export type PendingDefinitionsResponse = {game_version:'FC27';counts:Record<string,number>;validation_status:'pending_verification';message:string}
export type AttributeKey = 'pace'|'shooting'|'passing'|'dribbling'|'defending'|'physical'|'diving'|'handling'|'kicking'|'reflexes'|'speed'|'positioning'
export type Player = {
  validation_status?:string;variant_evidence?:Record<string,unknown>;
  id:number; name:string; rating:number; position:string; league:string; club:string; nationality:string;
  card_type:string; rare:boolean; special:boolean; tradable:boolean|null; price:number|null; chemistry:number;
  favorite?:boolean;notes?:string;athlete_id?:string|null;
  protected:boolean; effective_protected?:boolean; starter:boolean; squad_role:string; usefulness:number;
  duplicate_untradeable:boolean; deleted:boolean; created_at:string; game_version:GameVersion;
  card_id:string|null; base_card_id:string|null; alternate_positions:string[];
  attributes:Partial<Record<AttributeKey,number>>; playstyles:string[]; playstyles_plus:string[]; roles:Record<string,string>;
  skill_moves:number|null; weak_foot:number|null; is_loan:boolean|null; is_evolution:boolean|null; is_holographic:boolean;
  unknown_fields?:string[]; availability?:string;
  gallery_score:number|null; data_source:string; data_reviewed:boolean;
}
export type PlayerInput = Omit<Player,'id'|'deleted'|'created_at'|'effective_protected'|'unknown_fields'|'availability'|'tradable'|'is_loan'|'is_evolution'>&{tradable:boolean;is_loan:boolean;is_evolution:boolean}
export type Profile = {id:number;name:string;coins:number;platform:string;max_budget:number;risk_level:string;preferences:Record<string,unknown>;game_version:GameVersion}
export type Segment = {id:number;name:string;requirements:Record<string,unknown>;completed:boolean;current_score?:number;target_score?:number;remaining_score?:number}
export type Challenge = {id:number;name:string;description:string;reward:string;completed:boolean;expires_at:string|null;segments:Segment[];game_version?:GameVersion}
export type Objective = {id:number;name:string;description:string;category:string;progress:number;target:number;completed:boolean;expires_at:string|null}
export type TacticNotes = {style:string;opponent:string;instructions:string;practice_focus:string;reference_ids:string[]}
export type SquadBinding = {entry_id:number;club_context_id:number;revision:number;snapshot_id:number|null;game_version:GameVersion}
export type Squad = {id:number;name:string;formation:string;primary:boolean;protected:boolean;rating:number;chemistry:number;tactic?:Partial<TacticNotes>;players:{slot:string;player:Player;available?:boolean}[]}
export type AccountSummary = {identity_verified:boolean;provider:string|null;name:string|null;platform:string|null;coins:number|null;fc_points:number|null;unassigned_count:number|null;unassigned_types:Record<string,number>|null;facts:Record<string,{value:unknown;status:string;source:string|null;snapshot_id:number|null;observed_at:string|null;coverage:Record<string,unknown>}>;observed_copies:number|null;inventory_complete:boolean;snapshot_id:number|null;observed_at:string|null;coverage:Record<string,{complete?:boolean}>;progress:Record<string,string>}
export type Dashboard = {account:AccountSummary;mode:'live'|'local';profile:Profile;counts:{players:number;protected:number;duplicates:number;pending_challenges:number};objectives:Objective[];alerts:{level:string;message:string}[]}
export type Solution = {review_token:string;player_ids:number[];players:Player[];total_cost:number|null;optimization_score?:number;rating:number;chemistry:number;valid:boolean;violations:string[];uses_protected:boolean;duplicate_count:number;score_contribution?:number;current_score?:number;projected_score?:number;remaining_score?:number;partial?:boolean;will_complete?:boolean}
export type Formation = {id:string;name:string;slots:{slot:string;position:string}[]}
export type SquadRecommendation = {binding?:SquadBinding;game_version:GameVersion;formation:string;recommendation:true;simulation:true;complete:boolean;rating:number;chemistry:number;chemistry_approximate:true;players:Player[];lineup:{slot:string;position:string;player:Player;fit_score:number;used_alternate_position:boolean;explanation:string}[];bench:Player[];gaps:{slot:string;position:string;reason:string}[];warnings:string[];explanations:string[];style:string;eligible_count:number}
export type ClubAnalysis = {game_version:GameVersion;counts:{players:number;reviewed:number;unreviewed:number;protected:number;loans:number;evolutions:number;holographic:number;duplicates:number};average_rating:number;positions:{position:string;count:number;best_rating:number;best_player_id:number}[];top_players:Player[];gaps:{position:string;reason:string}[];warnings:string[];recommended_formation:string|null;simulation:true}
export type EmulatorDevice = {serial:string;state:string;details:string}
export type EmulatorStatus = {game_version?:GameVersion;compatibility_status?:'pending_verification';app_build?:null;visual_actions_allowed?:false;enabled:boolean;available:boolean;devices:EmulatorDevice[];config:{address?:string;serial?:string;calibration?:EmulatorCalibration|null};message:string|null}
export type EmulatorCalibration = {screen_width:number;screen_height:number;open_search_x:number;open_search_y:number;search_field_x:number;search_field_y:number;first_result_x:number;first_result_y:number;add_player_x:number;add_player_y:number;wait_ms:number}
export type AutomationPlan = {id:number;name:string;plan_type:string;status:string;device_serial:string|null;segment_id:number|null;player_ids:number[];solution_snapshot:{players:{id:number;name:string;rating:number;position:string;duplicate:boolean}[];validated:boolean;delivery_requires_manual_confirmation:boolean};steps:{action:string;label:string}[];progress_step:number;last_error:string|null;confirmation_phrase:string|null;final_submission_automated:boolean;created_at:string;worker_active?:boolean;can_prepare?:boolean}
export type InventoryScanCandidate = {candidate_id:number;name:string;rating:number|null;position:string;source_page:number;confidence:Record<string,number>}
export type InventoryScan = {id:number;source_scan_id?:number|null;status:string;device_serial:string;screen_size:number[];captured_pages:number;candidate_count?:number;offset?:number;candidates:InventoryScanCandidate[];imported_player_ids:number[];imported_count:number;last_error:string|null;confirmation_phrase:string;archive_demo_phrase:string;images_saved:false;requires_review:true;created_at:string;imported_at:string|null;game_version?:GameVersion;is_active?:boolean;can_capture?:boolean;can_continue?:boolean}
export type DcpInspection = {raw_text:string;detected_requirements:Record<string,unknown>;warnings?:string[];review_warnings?:string[];requires_human_review?:boolean;screen_size:number[]|null;source:'ADB';saved:false;requires_confirmation:true}
export type ImportPreview = {total:number;preview:(PlayerInput & {validation_status?:string})[];preview_token:string;content_hash:string;requires_confirmation:true}
export type GalleryEntry = {id:number;item_key:string;game_version:GameVersion;player_id:number|null;name:string;rating:number;position:string;league:string;club:string;nationality:string;card_type:string;is_holographic:boolean;gallery_score:number|null;recorded_at:string;owned:boolean;current_player_ids:number[]}
export type GalleryEvaluation = {selected_entries:GalleryEntry[];eligible_count:number;filled_slots:number;required_slots:number;complete:boolean;known_score:number;unknown_score_count:number;score:number|null;grade:string|null;tags:{name:string;achieved:boolean;count:number;minimum:number;bonus:number}[];missing_slots:number;warnings:string[]}
export type GallerySetInput = {game_version?:GameVersion;slug?:string;name:string;description?:string;category?:string;rules:{size:number;min_rating:number;league?:string;club?:string;nationality?:string;card_type?:string;holographic_only?:boolean;unique_players?:boolean};tags:{name:string;field:string;value:string|boolean;minimum:number;bonus:number}[];grade_thresholds:Record<string,number>;reward?:string;source_url?:string|null;rules_reviewed:boolean}
export type GallerySet = GallerySetInput&{id:number;evaluation:GalleryEvaluation}
export type GallerySummary = {game_version:GameVersion;entries_count:number;eligible_owned_count:number;unrecorded_count:number;excluded_loans:number;unresolved_evolutions:number;sets:GallerySet[];message:string}
export type EvolutionPath = {id:string;name:string;upgrades:{rating?:number;attributes?:Partial<Record<AttributeKey,number>>;alternate_positions?:string[];playstyles?:string[];playstyles_plus?:string[];roles?:Record<string,string>;skill_moves?:number;weak_foot?:number}}
export type Evolution = {id:number;game_version:GameVersion;slug:string;name:string;description:string;requirements:Record<string,unknown>;paths:EvolutionPath[];expires_at:string|null;source_url:string|null;rules_reviewed:boolean}
export type EvolutionPreview = {simulation:true;game_version:GameVersion;eligible:boolean;original:Player;projected:Player;steps:{evolution_id:number;name:string;path_id:string;path_name:string;eligible:boolean;violations:string[];projected:Player}[];warnings:string[]}
export type ContentResponse = {game_version:GameVersion;verified_at:string|null;features:{id:string;title:string;description:string;source_url:string}[];articles:{title:string;url:string;published_at?:string}[];last_checked:string|null;refresh_error:string|null;pending_articles?:number;scoring_notice?:string;scoring?:null|{verified_at:string;source_url:string;base_scores:Record<string,number>;message:string}}
export type PracticeSource={title:string;url:string;published_on:string;kind:string}
export type PracticeDrill={title:string;principle:string;exercise:string;error:string;metric:string;references:string[]}
export type PracticeCatalog={game_version:string;notice:string;review_due:boolean;drills:Record<string,PracticeDrill>;sources:Record<string,PracticeSource>}
export type PracticeSession={id:number;game_version:string;status:string;agenda:PracticeCatalog&{title:string;focus:string;platform:string;minutes:number;control:string|null;metric:string;reference_ids:string[];steps:{minutes:number;task:string}[]};result:{attempts:number;successes:number;minutes:number;next_change:string}}
export type MatchRecord={id:number;game_version:string;played_at:string;tactic:string;minutes:number;chances:number;dangerous_losses:number;conceded:number;change_tested:string;practice_id:number|null}
export type MatchGroup={tactic:string;change_tested:string;sample_size:number;minutes:number;per_90:{chances:number;dangerous_losses:number;conceded:number}}
export type MatchHistory={items:MatchRecord[];game_version:string;sample_size:number;message:string;truncated:boolean;unverified_history_count:number;groups:MatchGroup[]}
export type MarketPoint={id:number;amount:number;observed_at:string;source_url:string;coverage:string;expired:boolean}
export type MarketSeries={points:MarketPoint[];message:string;truncated:boolean}
export type MarketAlert={id:number;variant_id:string;market:string;kind:string;direction:string;threshold:number;enabled:boolean;status:string;latest:MarketPoint|null}
export type PlanSummary={id:number;name:string;status:string;deadline:string;copy_ids:number[];consumed_copy_ids:number[];max_cost:number;reserve_coins:number;known_card_value:number;unknown_price_count:number;plan_hash:string}
export type PlanComparison={a:PlanSummary;b:PlanSummary;shared_copy_ids:number[];cost_delta_b_minus_a:number;message:string}
export type ClubAgenda={selected:(PlanSummary&{balance_after:number})[];pending:(PlanSummary&{reason:string})[];objectives:{id:number;name:string;expires_at:string|null;expired:boolean;progress:number;target:number}[];committed_coins:number;remaining_coins:number;reserve_coins:number;truncated:boolean;message:string}
