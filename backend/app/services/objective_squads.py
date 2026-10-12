"""Non-consumptive objective composition: CP-SAT plus independent validation.

Unknown predicates use an interval of possible counts. A minimum needs enough
known matches; a maximum must include all possible matches. Participants remain
pending because a saved lineup cannot prove who actually played.
"""
from collections import defaultdict
from ortools.sat.python import cp_model
from app.services.gallery import folded
from app.services.remote_evidence import field_known
from app.services.squad_analysis import (
    formation_slots, player_positions, athlete_keys, normalized_position,
    serialize_player, _fit,
)
from app.services.rating import calculate_rating

DIFFICULTIES = ['beginner', 'amateur', 'semi_pro', 'professional', 'world_class', 'legendary', 'ultimate']


def conditions(goals):
    return [(goal['id'], condition) for goal in goals for condition in goal['rules'].conditions]


def interpretable(condition):
    return condition.reviewed and condition.field is not None and condition.value is not None and condition.scope in {'starters', 'bench', 'roster'}


def matches(player, condition, assigned_position=None):
    if not field_known(player, condition.field):
        return None
    actual, expected = getattr(player, condition.field), condition.value
    if condition.field == 'position':
        actual = assigned_position or normalized_position(actual)
        expected = normalized_position(expected)
    if actual is None:
        return None
    if condition.comparison == 'ge':
        return actual >= expected
    if condition.comparison == 'le':
        return actual <= expected
    return actual == expected if not isinstance(expected, str) else folded(actual) == folded(expected)


def loan_eligible(player, goals):
    if field_known(player, 'is_loan') and not player.is_loan:
        return True
    # Remaining loan games are not exposed by the current read contract.
    return bool(field_known(player, 'is_loan') and all(g['rules'].loans_allowed is True and g['rules'].minimum_loan_matches is None for g in goals))


def context_compatibility(goals):
    modes = {g['rules'].mode for g in goals} - {'unknown', 'any'}
    if len(modes) > 1:
        return dict(compatible=False, reason='Las modalidades son incompatibles; prepara sesiones separadas. No se suman progresos entre ellas.',
            sessions=[dict(mode=mode, objective_ids=[g['id'] for g in goals if g['rules'].mode in {mode, 'any'}]) for mode in sorted(modes)])
    difficulties = [g['rules'].min_difficulty for g in goals if g['rules'].min_difficulty in DIFFICULTIES]
    return dict(compatible=True, mode=next(iter(modes), 'unknown' if any(g['rules'].mode == 'unknown' for g in goals) else 'any'),
        min_difficulty=max(difficulties, key=DIFFICULTIES.index) if difficulties else 'unknown' if any(g['rules'].min_difficulty == 'unknown' for g in goals) else 'not_required',
        pending=[g['id'] for g in goals if g['rules'].mode == 'unknown' or g['rules'].min_difficulty == 'unknown'], sessions=[])


def validate_composition(players, lineup, bench_ids, goals, formation, bench_size, excluded=()):
    """Recompute eligibility, positions and counts without solver assignments."""
    by_id = {p.id: p for p in players}
    slots = {r['slot']: r['position'] for r in formation_slots(formation)}
    ids = [r['player_id'] for r in lineup]+list(bench_ids)
    errors, identities = [], set()
    if len(lineup) != 11 or {r['slot'] for r in lineup} != set(slots):
        errors.append('El once debe cubrir cada puesto de la formación exactamente una vez.')
    if len(bench_ids) != bench_size or len(ids) != len(set(ids)):
        errors.append('La convocatoria requiere copias únicas y el número elegido de suplentes.')
    for identifier in ids:
        player = by_id.get(identifier)
        if not player or player.deleted or player.game_version != 'FC27' or player.availability != 'available' or identifier in excluded or not loan_eligible(player, goals):
            errors.append('Hay una copia ausente, reservada, excluida o incompatible con las restricciones de cesión.')
            continue
        if athlete_keys(player) & identities:
            errors.append('Se repite el mismo futbolista entre once y banquillo.')
        identities.update(athlete_keys(player))
    for row in lineup:
        p = by_id.get(row['player_id'])
        if p and (row['slot'] not in slots or slots[row['slot']] not in player_positions(p)):
            errors.append('Una carta no es apta para el puesto asignado.')
    checklist = []
    for objective_id, condition in conditions(goals):
        row = dict(objective_id=objective_id, condition_id=condition.id, source_text=condition.source_text,
                   scope=condition.scope, quantity=condition.quantity, required=condition.count,
                   known_matches=None, possible_matches=None, status='pending')
        if not interpretable(condition):
            row['reason'] = 'Participación pendiente de jugar.' if condition.scope == 'participants' else 'Condición sin interpretación o revisión suficiente.'
        else:
            values = []
            if condition.scope in {'starters', 'roster'}:
                values += [matches(by_id[r['player_id']], condition, slots.get(r['slot'])) for r in lineup if r['player_id'] in by_id]
            if condition.scope in {'bench', 'roster'}:
                values += [matches(by_id[pid], condition) for pid in bench_ids if pid in by_id]
            lower, upper = sum(v is True for v in values), sum(v is not False for v in values)
            passed = (condition.quantity == 'min' and lower >= condition.count or
                      condition.quantity == 'max' and upper <= condition.count or
                      condition.quantity == 'exact' and lower == upper == condition.count)
            impossible = (condition.quantity == 'min' and upper < condition.count or
                          condition.quantity == 'max' and lower > condition.count or
                          condition.quantity == 'exact' and not lower <= condition.count <= upper)
            row.update(known_matches=lower, possible_matches=upper, status='met' if passed else 'failed' if impossible else 'pending',
                       reason=None if passed else 'Los datos conocidos incumplen la cantidad.' if impossible else 'Faltan metadatos de las copias para verificar la cantidad.')
        checklist.append(row)
    if any(not g['rules'].reviewed for g in goals):
        errors.append('Revisa las reglas auxiliares antes de preparar una plantilla.')
    return dict(valid=not errors, errors=sorted(set(errors)), checklist=checklist,
        composition_ready=not errors and all(r['status'] == 'met' for r in checklist))


def solve_objective_squad(players, goals, *, formation='4-3-3', bench_size=7, excluded=(), protected=(), competitive=True, seconds=4):
    candidates = sorted((p for p in players if not p.deleted and p.game_version == 'FC27'
        and p.validation_status in {'documented', 'provider_verified'} and p.availability == 'available'
        and p.id not in excluded and loan_eligible(p, goals)
        and (p.data_reviewed or (p.validation_evidence or {}).get('kind') == 'observed_copy')), key=lambda p:p.id)
    slots = formation_slots(formation)
    model = cp_model.CpModel()
    assignment, bench, by_player, by_slot, by_athlete = {}, {}, defaultdict(list), defaultdict(list), defaultdict(list)
    scored = []
    for rank, player in enumerate(candidates):
        bench[player.id] = model.new_bool_var(f'b{player.id}')
        by_player[player.id].append(bench[player.id])
        scored.append(bench[player.id]*(round(_fit(player, normalized_position(player.position))[0]*10) if competitive else -(rank+1)))
        for index, slot in enumerate(slots):
            if slot['position'] not in player_positions(player):
                continue
            variable = model.new_bool_var(f'p{player.id}s{index}')
            assignment[player.id, index] = variable
            by_player[player.id].append(variable)
            by_slot[index].append(variable)
            scored.append(variable*(round(_fit(player, slot['position'])[0]*100) if competitive else -(rank+1)))
        for key in athlete_keys(player):
            by_athlete[key].extend(by_player[player.id])
    for index in range(11):
        model.add(sum(by_slot[index]) == 1)
    model.add(sum(bench.values()) == bench_size)
    for variables in by_player.values():
        model.add(sum(variables) <= 1)
    for variables in by_athlete.values():
        model.add(sum(variables) <= 1)
    for _, condition in conditions(goals):
        if not interpretable(condition):
            continue
        lower, upper = [], []
        for player in candidates:
            choices = []
            if condition.scope in {'starters', 'roster'}:
                choices += [(assignment[player.id, i], matches(player, condition, slot['position'])) for i, slot in enumerate(slots) if (player.id, i) in assignment]
            if condition.scope in {'bench', 'roster'}:
                choices.append((bench[player.id], matches(player, condition)))
            lower.extend(v for v, match in choices if match is True)
            upper.extend(v for v, match in choices if match is not False)
        if condition.quantity in {'min', 'exact'}:
            model.add(sum(lower) >= condition.count)
        if condition.quantity in {'max', 'exact'}:
            model.add(sum(upper) <= condition.count)
    model.maximize(sum(scored))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = seconds
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    status = solver.solve(model)
    if status not in {cp_model.OPTIMAL, cp_model.FEASIBLE}:
        return dict(status='infeasible' if status == cp_model.INFEASIBLE else 'timeout',
                    reason='No hay una convocatoria verificable con estas condiciones y copias elegibles.' if status == cp_model.INFEASIBLE else 'El límite de tiempo no demuestra inviabilidad.', eligible_count=len(candidates))
    by_id = {p.id:p for p in candidates}
    lineup = [dict(slot=slot['slot'], player_id=pid) for i, slot in enumerate(slots) for pid in by_id if (pid,i) in assignment and solver.value(assignment[pid,i])]
    bench_ids = [pid for pid,v in bench.items() if solver.value(v)]
    checked = validate_composition(candidates, lineup, bench_ids, goals, formation, bench_size, excluded)
    if not checked['valid'] or any(row['status'] == 'failed' for row in checked['checklist']):
        raise RuntimeError('Objective solver result failed independent validation')
    rows = []
    for row in lineup:
        p, position = by_id[row['player_id']], row['slot'].rsplit('-',1)[0]
        score, why = _fit(p, position)
        rows.append(dict(slot=row['slot'], position=position, player=serialize_player(p, set(protected)),
                         fit_score=score, explanation=why, used_alternate_position=normalized_position(p.position) != position))
    return dict(status='optimal' if status == cp_model.OPTIMAL else 'feasible', formation=formation,
        style='balanced', lineup=rows, bench=[serialize_player(by_id[pid], set(protected)) for pid in bench_ids],
        players=[r['player'] for r in rows], rating=calculate_rating([r['player']['rating'] for r in rows]),
        chemistry=None, chemistry_status='unavailable', additional_cost=0, simulation=True,
        eligible_count=len(candidates), **checked)
