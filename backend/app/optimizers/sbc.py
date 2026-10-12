from collections import Counter
from dataclasses import dataclass

from app.models.entities import Player
from app.schemas.requirements import normalize_requirements
from app.services.rating import calculate_rating, minimum_rating_sum
from app.services.remote_evidence import missing_for_dcp


@dataclass
class Solution:
    player_ids: list[int]
    total_cost: int | None
    rating: int
    chemistry: int
    valid: bool
    violations: list[str]
    optimization_score: int = 0
    score_contribution: int = 0
    current_score: int = 0
    projected_score: int = 0
    remaining_score: int = 0
    partial: bool = False
    will_complete: bool = True


def _cost(player: Player, minimum_rating: int) -> int:
    """Local preservation score, deliberately separate from monetary value."""
    value = player.price if player.price is not None else 1_000_000
    value += 1500 if player.tradable else 0
    value += max(0, player.rating - minimum_rating) * 650
    value += player.usefulness * 120
    value += 50_000 if player.special else 0
    value += 200_000 if player.starter else 0
    value -= 8_000 if player.duplicate_untradeable else 0
    value -= 1_000 if player.usefulness < 15 else 0
    return max(1, value)


def validate_solution(players: list[Player], requirements: dict, *, current_score: int = 0, require_full_score: bool = False) -> list[str]:
    """Validate current cards; a score batch may legitimately be partial."""
    try:
        requirements = normalize_requirements(requirements)
    except ValueError as exc:
        return [f"Requisitos inválidos: {exc}"]
    errors: list[str] = []
    if any(missing_for_dcp(p, requirements) for p in players):
        errors.append('Faltan datos observados para verificar estos requisitos')
    if any(p.game_version != 'FC27' or p.validation_status not in ('documented', 'provider_verified', 'visual_reviewed') for p in players):
        errors.append('Solo se admiten variantes FC27 documentadas')
    if any(p.protected or p.starter or getattr(p, "is_evolution", False) or getattr(p, "favorite", False) for p in players):
        errors.append("Titulares, favoritos, Evos y cartas protegidas no se pueden consumir")
    if any(getattr(p, "availability", "available") not in {None, "available"} for p in players):
        errors.append("Hay cartas ausentes o comprometidas")
    ids = [p.id for p in players]
    if len(ids) != len(set(ids)):
        errors.append("No se permiten jugadores repetidos")
    if any(p.deleted for p in players):
        errors.append("Incluye jugadores no disponibles")
    if any(getattr(p, "is_loan", False) for p in players):
        errors.append("No se pueden consumir jugadores cedidos")
    if any(getattr(p, "data_reviewed", True) is False for p in players):
        errors.append("Hay cartas pendientes de revisión")
    if len({getattr(p, "game_version", "FC27") for p in players}) > 1:
        errors.append("No se pueden mezclar ediciones del juego")
    required_ids = set(requirements.get("required_player_ids", []))
    if not required_ids.issubset(set(ids)):
        errors.append("Faltan jugadores obligatorios")
    if set(requirements.get("excluded_player_ids", [])) & set(ids):
        errors.append("Incluye jugadores excluidos")
    max_value = requirements.get("max_total_value")
    if max_value is not None and (any(p.price is None for p in players) or sum(p.price or 0 for p in players) > max_value):
        errors.append("Valor máximo excedido")
    if requirements["kind"] == "score":
        limit = requirements.get("max_items_per_submission", 23)
        if not 1 <= len(players) <= limit:
            errors.append(f"La entrega requiere entre 1 y {limit} cartas")
        if any(p.rating < requirements.get("min_item_rating", 1) for p in players):
            errors.append("Hay cartas por debajo de la media mínima individual")
        if any(getattr(p, "gallery_score", None) is None or p.gallery_score <= 0 for p in players):
            errors.append("Todas las cartas requieren una puntuación positiva registrada y revisada")
        contribution = sum(max(0, getattr(p, "gallery_score", 0) or 0) for p in players)
        target = requirements["target_score"]
        if current_score >= target:
            errors.append("La puntuación objetivo ya se alcanzó")
        if require_full_score and current_score + contribution < target:
            errors.append("La entrega todavía no alcanza la puntuación objetivo")
        return errors

    size = requirements.get("squad_size", 11)
    if len(players) != size:
        errors.append(f"Se requieren {size} jugadores")
    minimum = requirements.get("min_rating", 0)
    strategy = requirements.get("rating_strategy", "floor_average")
    if calculate_rating([p.rating for p in players], strategy) < minimum:
        errors.append(f"Media inferior a {minimum}")
    if sum(p.chemistry for p in players) < requirements.get("min_chemistry", 0):
        errors.append("Química registrada insuficiente")
    for attr, key, label in (("rare", "min_rare", "raros"), ("special", "min_special", "especiales")):
        if sum(bool(getattr(p, attr)) for p in players) < requirements.get(key, 0):
            errors.append(f"Faltan jugadores {label}")
    for attr, prefix, label in (("league", "leagues", "ligas"), ("club", "clubs", "clubes"), ("nationality", "nations", "nacionalidades")):
        count = len({getattr(p, attr) for p in players})
        if requirements.get(f"min_{prefix}") is not None and count < requirements[f"min_{prefix}"]:
            errors.append(f"Mínimo de {label} incumplido")
        if requirements.get(f"max_{prefix}") is not None and count > requirements[f"max_{prefix}"]:
            errors.append(f"Máximo de {label} incumplido")
    for attr, value_key, min_key in (("league", "required_league", "min_from_league"), ("club", "required_club", "min_from_club"), ("nationality", "required_nation", "min_from_nation"), ("card_type", "required_card_type", "min_card_type")):
        value = requirements.get(value_key)
        if value and sum(getattr(p, attr) == value for p in players) < requirements.get(min_key, 1):
            errors.append(f"Requisito {value} incumplido")
    positions = Counter(p.position for p in players)
    for position, amount in requirements.get("required_positions", {}).items():
        if positions[position] < amount:
            errors.append(f"Faltan {amount} {position}")
    return errors


def _make_solution(chosen: list[Player], requirements: dict, current_score: int) -> Solution:
    score_mode = requirements["kind"] == "score"
    minimum = requirements.get("min_item_rating", 1) if score_mode else requirements.get("min_rating", 0)
    contribution = sum(p.gallery_score for p in chosen) if score_mode else 0
    projected = current_score + contribution
    remaining = max(0, requirements.get("target_score", 0) - projected) if score_mode else 0
    return Solution(
        player_ids=[p.id for p in chosen], total_cost=None if any(p.price is None for p in chosen) else sum(p.price for p in chosen),
        rating=calculate_rating([p.rating for p in chosen], requirements.get("rating_strategy", "floor_average")),
        chemistry=sum(p.chemistry for p in chosen), valid=True, violations=[],
        optimization_score=sum(_cost(p, minimum) for p in chosen),
        score_contribution=contribution, current_score=current_score, projected_score=projected,
        remaining_score=remaining, partial=score_mode and remaining > 0, will_complete=remaining == 0,
    )


def solve(players: list[Player], requirements: dict, allow_protected_ids: set[int] | None = None, exclude_ids: set[int] | None = None, max_solutions: int = 3, *, effective_protected_ids: set[int] | None = None, current_score: int = 0) -> list[Solution]:
    from ortools.sat.python import cp_model

    requirements = normalize_requirements(requirements)
    allowed = set()  # Exceptions require exact reviewed actions, never a solver switch.
    excluded = set(requirements.get("excluded_player_ids", [])) | (exclude_ids or set())
    protected = effective_protected_ids or set()
    candidates = [
        p for p in players
        if not p.deleted and not p.starter and not getattr(p, "is_evolution", False) and not getattr(p, "favorite", False) and getattr(p, "availability", "available") in {None, "available"} and p.id not in excluded and not getattr(p, "is_loan", False)
        and getattr(p, "data_reviewed", True) is not False
        and not missing_for_dcp(p, requirements)
        and p.game_version == 'FC27' and p.validation_status in ('documented', 'provider_verified', 'visual_reviewed')
        and (not (p.protected or p.id in protected) or p.id in allowed)
    ]
    if requirements.get("max_total_value") is not None:
        candidates = [p for p in candidates if p.price is not None]
    score_mode = requirements["kind"] == "score"
    if score_mode:
        if current_score >= requirements["target_score"]:
            return []
        candidates = [p for p in candidates if p.rating >= requirements.get("min_item_rating", 1) and (getattr(p, "gallery_score", None) or 0) > 0]
    size = requirements.get("squad_size", 11)
    if not candidates or (not score_mode and len(candidates) < size):
        return []
    required_ids = set(requirements.get("required_player_ids", []))
    if not required_ids.issubset({p.id for p in candidates}):
        return []
    if len({getattr(p, "game_version", "FC27") for p in candidates}) > 1:
        raise ValueError("El optimizador requiere cartas de una sola edición")
    found: list[Solution] = []
    blocked: list[set[int]] = []
    minimum = requirements.get("min_item_rating", 1) if score_mode else requirements.get("min_rating", 0)
    for _ in range(max_solutions):
        model = cp_model.CpModel()
        x = [model.new_bool_var(f"p_{p.id}") for p in candidates]
        if score_mode:
            model.add(sum(x) >= 1)
            model.add(sum(x) <= requirements.get("max_items_per_submission", 23))
        else:
            model.add(sum(x) == size)
            model.add(sum(x[i] * p.rating for i, p in enumerate(candidates)) >= minimum_rating_sum(size, minimum, requirements.get("rating_strategy", "floor_average")))
            for attr, key in (("chemistry", "min_chemistry"), ("rare", "min_rare"), ("special", "min_special")):
                model.add(sum(x[i] * int(getattr(p, attr)) for i, p in enumerate(candidates)) >= requirements.get(key, 0))
            for attr, min_key, max_key in (("league", "min_leagues", "max_leagues"), ("club", "min_clubs", "max_clubs"), ("nationality", "min_nations", "max_nations")):
                if min_key not in requirements and max_key not in requirements:
                    continue
                used = []
                for value in sorted({getattr(p, attr) for p in candidates}):
                    indexes = [i for i, p in enumerate(candidates) if getattr(p, attr) == value]
                    flag = model.new_bool_var(f"{attr}_{len(used)}")
                    model.add(sum(x[i] for i in indexes) >= flag)
                    for index in indexes:
                        model.add(x[index] <= flag)
                    used.append(flag)
                if min_key in requirements:
                    model.add(sum(used) >= requirements[min_key])
                if max_key in requirements:
                    model.add(sum(used) <= requirements[max_key])
            for attr, value_key, count_key in (("league", "required_league", "min_from_league"), ("club", "required_club", "min_from_club"), ("nationality", "required_nation", "min_from_nation"), ("card_type", "required_card_type", "min_card_type")):
                if value := requirements.get(value_key):
                    model.add(sum(x[i] for i, p in enumerate(candidates) if getattr(p, attr) == value) >= requirements.get(count_key, 1))
            for position, amount in requirements.get("required_positions", {}).items():
                model.add(sum(x[i] for i, p in enumerate(candidates) if p.position == position) >= amount)
        if requirements.get("max_total_value") is not None:
            model.add(sum(x[i] * p.price for i, p in enumerate(candidates)) <= requirements["max_total_value"])
        for index, player in enumerate(candidates):
            if player.id in required_ids:
                model.add(x[index] == 1)
        # Block exactly the previous set, including variable-size score batches.
        for prior in blocked:
            model.add(sum((1 - x[i]) if p.id in prior else x[i] for i, p in enumerate(candidates)) >= 1)
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 5.0
        solver.parameters.num_search_workers = 4
        if score_mode:
            contribution = sum(x[i] * p.gallery_score for i, p in enumerate(candidates))
            model.maximize(contribution)
            if solver.solve(model) not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                break
            reachable_score = int(solver.value(contribution))
            # A partial batch records real progress; it does not invent a score.
            model.add(contribution >= min(requirements["target_score"] - current_score, reachable_score))
        model.minimize(sum(x[i] * _cost(p, minimum) for i, p in enumerate(candidates)))
        if solver.solve(model) not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            break
        chosen = [p for i, p in enumerate(candidates) if solver.value(x[i])]
        blocked.append({p.id for p in chosen})
        if not validate_solution(chosen, requirements, current_score=current_score):
            found.append(_make_solution(chosen, requirements, current_score))
    return found
