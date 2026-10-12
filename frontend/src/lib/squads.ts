import type {SquadBinding,SquadRecommendation,TacticNotes} from '../types'

export function squadRequest(name:string, squad:SquadRecommendation, binding?:SquadBinding, tactic?:TacticNotes){
  const expected=binding?{entry_id:binding.entry_id,club_context_id:binding.club_context_id,revision:binding.revision,snapshot_id:binding.snapshot_id,game_version:binding.game_version}:undefined
  return {game_version:squad.game_version,name,formation:squad.formation,
    player_ids:[...squad.lineup.map(row=>row.player.id),...squad.bench.map(player=>player.id)],
    slots:[...squad.lineup.map(row=>row.slot),...squad.bench.map((_,index)=>`BENCH-${index+1}`)],
    expected_binding:expected,tactic}
}
