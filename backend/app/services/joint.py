"""Bounded enumeration + CP-SAT set packing, with independent final validation."""
import itertools
import time
from ortools.sat.python import cp_model
from app.optimizers.sbc import _cost, validate_solution


def joint_dcp(players, segments, protected, *, seconds=5, combination_limit=20000):
    started = time.monotonic()
    candidates = [p for p in players if not p.deleted and p.id not in protected and not p.is_loan and not p.is_evolution and not p.starter and not p.favorite and p.data_reviewed and p.availability == "available"]
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
                    options.append((selected, sum(_cost(p, rules.get("min_rating", 0)) for p in selected)))
            if not exhausted:
                break
        alternatives.append(options)
        if not exhausted:
            break
    if len(alternatives) != len(segments) or any(not options for options in alternatives):
        return {"status": "infeasible" if exhausted else "timeout", "solutions": [], "simulation": True, "examined": examined}
    model = cp_model.CpModel()
    choices = [[model.new_bool_var(f"s{i}_{j}") for j in range(len(options))] for i, options in enumerate(alternatives)]
    for options in choices:
        model.add(sum(options) == 1)
    for player in candidates:
        model.add(sum(choices[i][j] for i, options in enumerate(alternatives) for j, (cards, _) in enumerate(options) if player in cards) <= 1)
    model.minimize(sum(choices[i][j]*cost for i, options in enumerate(alternatives) for j, (_, cost) in enumerate(options)))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max(.05, seconds-(time.monotonic()-started))
    solver.parameters.num_search_workers = 1
    status = solver.solve(model)
    result = []
    if status in {cp_model.OPTIMAL, cp_model.FEASIBLE}:
        used = set()
        for i, options in enumerate(alternatives):
            cards = next(cards for j, (cards, _) in enumerate(options) if solver.value(choices[i][j]))
            ids = {p.id for p in cards}
            assert not ids & used
            assert not validate_solution(list(cards), segments[i]["requirements"], current_score=segments[i].get("current_score", 0), require_full_score=True)
            used |= ids
            result.append({"segment_id": segments[i]["id"], "player_ids": sorted(ids), "total_value": None if any(p.price is None for p in cards) else sum(p.price for p in cards)})
    return {"status": "optimal" if status == cp_model.OPTIMAL and exhausted else "feasible" if result else "infeasible" if status == cp_model.INFEASIBLE and exhausted else "timeout", "solutions": result, "examined": examined, "duration_ms": round((time.monotonic()-started)*1000), "simulation": True, "official_validation": False}
