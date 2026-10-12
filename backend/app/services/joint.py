"""Bounded enumeration + CP-SAT set packing, with independent final validation."""
import itertools
import time
from ortools.sat.python import cp_model
from app.optimizers.sbc import _cost, validate_solution


def joint_dcp(players, segments, protected, *, seconds=5, combination_limit=20000, max_total_value=None, priority_ids=(), allow_partial=False):
    started = time.monotonic()
    candidates = [p for p in players if p.game_version == 'FC27' and not p.deleted and p.id not in protected and not p.protected and not p.is_loan and not p.is_evolution and not p.starter and not p.favorite and p.data_reviewed and not p.unknown_fields and p.availability == "available" and (max_total_value is None or p.price is not None)]
    priorities = list(priority_ids)+[s['id'] for s in segments if s['id'] not in priority_ids]
    if len(candidates) > 24:
        return {"status": "data_missing", "reason": "Selecciona como máximo 24 cartas para esta búsqueda conjunta acotada", "solutions": [], "simulation": True}
    alternatives, examined, exhausted = [], 0, True
    for segment in segments:
        rules, progress = segment["requirements"], segment.get("current_score", 0)
        sizes = range(1, min(len(candidates), rules.get("max_items_per_submission", 23))+1) if rules.get("kind") == "score" else [rules.get("squad_size", 11)]
        options = []
        for size in sizes:
            for selected in itertools.combinations(candidates, size):
                examined += 1
                if examined > combination_limit or time.monotonic()-started > seconds:
                    exhausted = False
                    break
                if not validate_solution(list(selected), rules, current_score=progress, require_full_score=True):
                    if max_total_value is not None and sum(p.price for p in selected) > max_total_value:
                        continue
                    options.append((selected, sum(_cost(p, rules.get("min_rating", 0)) for p in selected)))
            if not exhausted:
                break
        alternatives.append(options)
        if not exhausted:
            break
    if len(alternatives) != len(segments) or (all(not options for options in alternatives) if allow_partial else any(not options for options in alternatives)):
        return {"status": "infeasible" if exhausted else "timeout", "solutions": [], "simulation": True, "examined": examined}
    model = cp_model.CpModel()
    choices = [[model.new_bool_var(f"s{i}_{j}") for j in range(len(options))] for i, options in enumerate(alternatives)]
    for options in choices:
        model.add(sum(options) <= 1 if allow_partial else sum(options) == 1)
    model.add(sum(v for options in choices for v in options) >= 1)
    for player in candidates:
        model.add(sum(choices[i][j] for i, options in enumerate(alternatives) for j, (cards, _) in enumerate(options) if player in cards) <= 1)
    cost = sum(choices[i][j]*value for i, options in enumerate(alternatives) for j, (_, value) in enumerate(options))
    if max_total_value is not None:
        model.add(sum(choices[i][j]*sum(p.price for p in cards) for i, options in enumerate(alternatives) for j, (cards, _) in enumerate(options)) <= max_total_value)
    if allow_partial:
        # Ordered priority is lexicographic. Completing a higher-priority segment
        # dominates every lower-priority one and the entire secondary fit cost.
        max_cost = sum(max((abs(value) for _, value in options), default=0) for options in alternatives)
        reward = sum(sum(choices[i])*(2**(len(priorities)-priorities.index(segment['id'])-1)) for i, segment in enumerate(segments))
        model.maximize(reward*(2*max_cost+1)-cost)
    else:
        model.minimize(cost)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max(.05, seconds-(time.monotonic()-started))
    solver.parameters.num_search_workers = 1
    status = solver.solve(model)
    result = []
    if status in {cp_model.OPTIMAL, cp_model.FEASIBLE}:
        used = set()
        for i, options in enumerate(alternatives):
            cards = next((cards for j, (cards, _) in enumerate(options) if solver.value(choices[i][j])), None)
            if cards is None:
                continue
            ids = {p.id for p in cards}
            assert not ids & used
            assert not validate_solution(list(cards), segments[i]["requirements"], current_score=segments[i].get("current_score", 0), require_full_score=True)
            used |= ids
            rules, progress = segments[i]['requirements'], segments[i].get('current_score', 0)
            score = sum(p.gallery_score for p in cards) if rules.get('kind') == 'score' else None
            result.append({"segment_id": segments[i]["id"], "player_ids": sorted(ids), "total_value": None if any(p.price is None for p in cards) else sum(p.price for p in cards),
                'unknown_price_count': sum(p.price is None for p in cards), 'additional_cost': 0,
                'score_contribution': score, 'current_score': progress,
                'remaining_score': max(0, rules['target_score']-progress-score) if score is not None else None,
                'score_surplus': max(0, progress+score-rules['target_score']) if score is not None else None})
        if max_total_value is not None:
            assert sum(row['total_value'] for row in result) <= max_total_value
    selected = {row['segment_id'] for row in result}
    return {"status": "optimal" if status == cp_model.OPTIMAL and exhausted else "feasible" if result else "infeasible" if status == cp_model.INFEASIBLE and exhausted else "timeout", "solutions": result, "examined": examined, "duration_ms": round((time.monotonic()-started)*1000), "simulation": True, "official_validation": False,
        'max_total_value': max_total_value, 'priority_ids': priorities, 'all_segments_covered': len(result)==len(segments),
        'pending_segment_ids': [s['id'] for s in segments if s['id'] not in selected],
        'total_value': None if any(row['total_value'] is None for row in result) else sum(row['total_value'] for row in result),
        'additional_cost': 0, 'unknown_price_count': sum(row['unknown_price_count'] for row in result)}
