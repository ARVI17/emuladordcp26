from collections import Counter
from dataclasses import dataclass
from app.models.entities import Player
from app.services.rating import calculate_rating, minimum_rating_sum

@dataclass
class Solution:
    player_ids: list[int]
    total_cost: int
    rating: int
    chemistry: int
    valid: bool
    violations: list[str]

def _cost(player: Player, minimum_rating: int) -> int:
    value = player.price
    value += 1500 if player.tradable else 0
    value += max(0, player.rating - minimum_rating) * 650
    value += player.usefulness * 120
    value += 50_000 if player.special else 0
    value += 200_000 if player.starter else 0
    value -= 8_000 if player.duplicate_untradeable else 0
    value -= 1_000 if player.usefulness < 15 else 0
    return max(1, value)

def validate_solution(players: list[Player], requirements: dict) -> list[str]:
    errors: list[str] = []
    size = int(requirements.get("squad_size", 11))
    if len(players) != size: errors.append(f"Se requieren {size} jugadores")
    minimum = int(requirements.get("min_rating", 0))
    strategy = requirements.get("rating_strategy", "floor_average")
    if calculate_rating([p.rating for p in players], strategy) < minimum: errors.append(f"Media inferior a {minimum}")
    if sum(p.chemistry for p in players) < int(requirements.get("min_chemistry", 0)): errors.append("Química insuficiente")
    checks = [("rare", "min_rare", "raros"), ("special", "min_special", "especiales")]
    for attr, key, label in checks:
        if sum(bool(getattr(p, attr)) for p in players) < int(requirements.get(key, 0)): errors.append(f"Faltan jugadores {label}")
    for attr, prefix, label in [("league", "leagues", "ligas"), ("club", "clubs", "clubes"), ("nationality", "nations", "nacionalidades")]:
        count = len({getattr(p, attr) for p in players})
        if requirements.get(f"min_{prefix}") is not None and count < int(requirements[f"min_{prefix}"]): errors.append(f"Mínimo de {label} incumplido")
        if requirements.get(f"max_{prefix}") is not None and count > int(requirements[f"max_{prefix}"]): errors.append(f"Máximo de {label} incumplido")
    mapping = [("league", "required_league", "min_from_league"), ("club", "required_club", "min_from_club"), ("nationality", "required_nation", "min_from_nation"), ("card_type", "required_card_type", "min_card_type")]
    for attr, value_key, min_key in mapping:
        value = requirements.get(value_key)
        if value and sum(getattr(p, attr) == value for p in players) < int(requirements.get(min_key, 1)): errors.append(f"Requisito {value} incumplido")
    required_positions = requirements.get("required_positions", {})
    positions = Counter(p.position for p in players)
    for pos, amount in required_positions.items():
        if positions[pos] < int(amount): errors.append(f"Faltan {amount} {pos}")
    required_ids = set(requirements.get("required_player_ids", []))
    if not required_ids.issubset({p.id for p in players}): errors.append("Faltan jugadores obligatorios")
    if set(requirements.get("excluded_player_ids", [])) & {p.id for p in players}: errors.append("Incluye jugadores excluidos")
    max_value = requirements.get("max_total_value")
    if max_value is not None and sum(p.price for p in players) > int(max_value): errors.append("Valor máximo excedido")
    return errors

def solve(players: list[Player], requirements: dict, allow_protected_ids: set[int] | None = None, exclude_ids: set[int] | None = None, max_solutions: int = 3) -> list[Solution]:
    from ortools.sat.python import cp_model

    allow_protected_ids = allow_protected_ids or set()
    excluded = set(requirements.get("excluded_player_ids", [])) | (exclude_ids or set())
    candidates = [p for p in players if not p.deleted and p.id not in excluded and (not p.protected or p.id in allow_protected_ids)]
    size, minimum = int(requirements.get("squad_size", 11)), int(requirements.get("min_rating", 0))
    if len(candidates) < size: return []
    found: list[Solution] = []
    blocked: list[list[int]] = []
    for _ in range(max_solutions):
        model = cp_model.CpModel()
        x = [model.new_bool_var(f"p_{p.id}") for p in candidates]
        model.add(sum(x) == size)
        model.add(sum(x[i] * candidates[i].rating for i in range(len(x))) >= minimum_rating_sum(size, minimum, requirements.get("rating_strategy", "floor_average")))
        model.add(sum(x[i] * candidates[i].chemistry for i in range(len(x))) >= int(requirements.get("min_chemistry", 0)))
        model.add(sum(x[i] * int(candidates[i].rare) for i in range(len(x))) >= int(requirements.get("min_rare", 0)))
        model.add(sum(x[i] * int(candidates[i].special) for i in range(len(x))) >= int(requirements.get("min_special", 0)))
        if requirements.get("max_total_value") is not None:
            model.add(sum(x[i] * candidates[i].price for i in range(len(x))) <= int(requirements["max_total_value"]))
        for attr, min_key, max_key in [("league", "min_leagues", "max_leagues"), ("club", "min_clubs", "max_clubs"), ("nationality", "min_nations", "max_nations")]:
            values = sorted({getattr(p, attr) for p in candidates})
            used = []
            for value in values:
                indexes = [i for i, p in enumerate(candidates) if getattr(p, attr) == value]
                flag = model.new_bool_var(f"{attr}_{len(used)}")
                model.add(sum(x[i] for i in indexes) >= flag)
                for i in indexes: model.add(x[i] <= flag)
                used.append(flag)
            if requirements.get(min_key) is not None: model.add(sum(used) >= int(requirements[min_key]))
            if requirements.get(max_key) is not None: model.add(sum(used) <= int(requirements[max_key]))
        mappings = [("league", "required_league", "min_from_league"), ("club", "required_club", "min_from_club"), ("nationality", "required_nation", "min_from_nation"), ("card_type", "required_card_type", "min_card_type")]
        for attr, value_key, count_key in mappings:
            value = requirements.get(value_key)
            if value: model.add(sum(x[i] for i,p in enumerate(candidates) if getattr(p, attr) == value) >= int(requirements.get(count_key, 1)))
        for pos, amount in requirements.get("required_positions", {}).items():
            model.add(sum(x[i] for i,p in enumerate(candidates) if p.position == pos) >= int(amount))
        for required_id in requirements.get("required_player_ids", []):
            indexes = [i for i,p in enumerate(candidates) if p.id == int(required_id)]
            if not indexes: return []
            model.add(x[indexes[0]] == 1)
        for prior in blocked:
            indexes = [i for i,p in enumerate(candidates) if p.id in prior]
            model.add(sum(x[i] for i in indexes) <= size - 1)
        model.minimize(sum(x[i] * _cost(candidates[i], minimum) for i in range(len(x))))
        solver = cp_model.CpSolver(); solver.parameters.max_time_in_seconds = 8.0; solver.parameters.num_search_workers = 4
        if solver.solve(model) not in (cp_model.OPTIMAL, cp_model.FEASIBLE): break
        chosen = [p for i,p in enumerate(candidates) if solver.value(x[i])]
        violations = validate_solution(chosen, requirements)
        ids = [p.id for p in chosen]; blocked.append(ids)
        if not violations:
            found.append(Solution(ids, sum(_cost(p, minimum) for p in chosen), calculate_rating([p.rating for p in chosen], requirements.get("rating_strategy", "floor_average")), sum(p.chemistry for p in chosen), True, []))
    return found
