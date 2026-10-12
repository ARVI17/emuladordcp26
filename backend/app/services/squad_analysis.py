"""Read-only, position-aware analysis of owned cards.

Fit scores are transparent local heuristics, not gameplay or chemistry formulas.
Protection is derived here so a squad never overwrites a manual player flag.
"""

from collections import Counter, defaultdict
from datetime import date, datetime, timezone
import unicodedata

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.entities import Player, Squad, SquadPlayer
from app.services.editions import current_version
from app.services.rating import calculate_rating

FORMATIONS = {
    "4-2-1-3": ["POR", "LD", "DFC", "DFC", "LI", "MCD", "MCD", "MCO", "ED", "DC", "EI"],
    "4-2-3-1 abierta": ["POR", "LD", "DFC", "DFC", "LI", "MCD", "MCD", "MD", "MCO", "MI", "DC"],
    "4-4-1-1 mediocampo": ["POR", "LD", "DFC", "DFC", "LI", "MD", "MC", "MC", "MI", "MCO", "DC"],
    "4-3-1-2": ["POR", "LD", "DFC", "DFC", "LI", "MC", "MC", "MC", "MCO", "DC", "DC"],
    "4-1-2-1-2 estrecha": ["POR", "LD", "DFC", "DFC", "LI", "MCD", "MC", "MC", "MCO", "DC", "DC"],
    "4-3-3": ["POR", "LD", "DFC", "DFC", "LI", "MC", "MC", "MC", "ED", "DC", "EI"],
    "4-3-3 Holding": ["POR", "LD", "DFC", "DFC", "LI", "MCD", "MC", "MC", "ED", "DC", "EI"],
    "4-4-2": ["POR", "LD", "DFC", "DFC", "LI", "MD", "MC", "MC", "MI", "DC", "DC"],
    "4-2-3-1": ["POR", "LD", "DFC", "DFC", "LI", "MCD", "MCD", "MCO", "MCO", "MCO", "DC"],
    "4-1-2-1-2": ["POR", "LD", "DFC", "DFC", "LI", "MCD", "MC", "MC", "MCO", "DC", "DC"],
    "3-5-2": ["POR", "DFC", "DFC", "DFC", "MD", "MCD", "MCD", "MCO", "MI", "DC", "DC"],
}
POSITION_ALIASES = {"GK": "POR", "RB": "LD", "CB": "DFC", "LB": "LI", "RWB": "CAD", "LWB": "CAI", "CDM": "MCD", "CM": "MC", "CAM": "MCO", "RM": "MD", "LM": "MI", "RW": "ED", "LW": "EI", "CF": "SD", "ST": "DC"}
ATTRIBUTE_WEIGHTS = {
    "POR": {"diving": 25, "handling": 20, "reflexes": 25, "positioning": 20, "kicking": 5, "speed": 5},
    "DFC": {"defending": 45, "physical": 30, "pace": 15, "passing": 10},
    "LD": {"defending": 30, "pace": 30, "physical": 15, "passing": 15, "dribbling": 10},
    "LI": {"defending": 30, "pace": 30, "physical": 15, "passing": 15, "dribbling": 10},
    "CAD": {"defending": 25, "pace": 30, "physical": 15, "passing": 20, "dribbling": 10},
    "CAI": {"defending": 25, "pace": 30, "physical": 15, "passing": 20, "dribbling": 10},
    "MCD": {"defending": 35, "passing": 25, "physical": 25, "dribbling": 10, "pace": 5},
    "MC": {"passing": 35, "dribbling": 25, "physical": 15, "defending": 15, "pace": 10},
    "MCO": {"passing": 35, "dribbling": 30, "shooting": 20, "pace": 15},
    "MD": {"pace": 30, "passing": 30, "dribbling": 25, "defending": 10, "shooting": 5},
    "MI": {"pace": 30, "passing": 30, "dribbling": 25, "defending": 10, "shooting": 5},
    "ED": {"pace": 35, "dribbling": 30, "shooting": 25, "passing": 10},
    "EI": {"pace": 35, "dribbling": 30, "shooting": 25, "passing": 10},
    "DC": {"shooting": 40, "pace": 25, "physical": 20, "dribbling": 15},
    "SD": {"shooting": 30, "passing": 25, "dribbling": 30, "pace": 15},
}
ATTRIBUTE_LABELS = {"pace": "ritmo", "shooting": "tiro", "passing": "pase", "dribbling": "regate", "defending": "defensa", "physical": "físico", "diving": "estirada", "handling": "paradas", "reflexes": "reflejos", "positioning": "colocación", "kicking": "saque", "speed": "velocidad"}
PLAYER_FIELDS = (
    "id", "game_version", "name", "rating", "position", "league", "club", "nationality", "card_type", "rare", "special", "tradable", "price", "chemistry", "protected", "starter", "squad_role", "usefulness", "duplicate_untradeable", "deleted", "created_at", "updated_at", "card_id", "base_card_id", "alternate_positions", "attributes", "playstyles", "playstyles_plus", "roles", "skill_moves", "weak_foot", "is_loan", "is_evolution", "is_holographic", "gallery_score", "data_source", "data_reviewed", "athlete_id", "favorite", "notes", "availability",
)


def serialize_player(player: Player, protected_ids: set[int] | None = None) -> dict:
    result = {key: getattr(player, key, None) for key in PLAYER_FIELDS}
    result.update(validation_status=player.validation_status, variant_evidence=player.validation_evidence)
    from app.services.remote_evidence import field_known
    evidence = player.validation_evidence or {}
    result['ownership_source'] = 'observed' if evidence.get('kind') == 'observed_copy' else 'manual'
    result['observed_at'] = evidence.get('observed_at') if evidence.get('kind') == 'observed_copy' else None
    result['metadata_pending'] = [key for key in ('league', 'club', 'nationality', 'card_type', 'rare', 'special', 'chemistry', 'alternate_positions', 'attributes', 'playstyles', 'roles', 'is_loan', 'is_evolution', 'tradable', 'is_holographic') if not field_known(player, key)]
    for key in ('rare', 'special', 'chemistry', 'is_holographic', 'tradable', 'is_loan', 'is_evolution'):
        if not field_known(player, key):
            result[key] = None
    for key in (getattr(player, "unknown_fields", None) or []):
        if key in result:
            result[key] = None
    result["unknown_fields"] = getattr(player, "unknown_fields", None) or []
    result["effective_protected"] = bool(player.protected or player.id in (protected_ids or set()))
    return result


def effective_protected_ids(db: Session, game_version: str | None = None) -> set[int]:
    version = game_version or current_version(db)
    manual = db.scalars(select(Player.id).where(Player.game_version == version, Player.deleted.is_(False), or_(Player.protected.is_(True), Player.starter.is_(True), Player.is_evolution.is_(True), Player.favorite.is_(True))).execution_options(include_quarantine=True)).all()
    inherited = db.scalars(
        select(SquadPlayer.player_id).join(Squad, Squad.id == SquadPlayer.squad_id).join(Player, Player.id == SquadPlayer.player_id)
        .where(Squad.game_version == version, Squad.protected.is_(True), Player.game_version == version, Player.deleted.is_(False))
        .execution_options(include_historical_squads=True, include_quarantine=True)
    ).all()
    from app.services.protection import reserved_ids
    reserved = db.scalars(select(Player.id).where(Player.id.in_(reserved_ids(db)), Player.game_version == version, Player.deleted.is_(False))).all()
    from app.services.main_squad import main_ids
    return set(manual) | set(inherited) | set(reserved) | main_ids(db)


def formation_slots(formation: str) -> list[dict]:
    if formation not in verified_formations():
        raise ValueError("Formación no disponible")
    counts: Counter = Counter()
    result = []
    for position in FORMATIONS[formation]:
        counts[position] += 1
        result.append({"slot": f"{position}-{counts[position]}", "position": position})
    return result


def formations_data() -> dict:
    return {"game_version": "FC27", "items": [{"id": key, "name": key, "slots": formation_slots(key),
        "source_url": formation_source(key), "reviewed_on": "2026-10-12", "valid_until": "2026-11-10",
        "validation_status": "documented", "tactic_status": "local_hypothesis", "import_code": None} for key in verified_formations()]}


def verified_formations():
    return FORMATIONS if date(2026, 10, 12) <= datetime.now(timezone.utc).date() <= date(2026, 11, 10) else {}


def formation_source(key):
    if key in {'4-3-3', '4-3-3 Holding', '3-5-2'}:
        return 'https://www.fut.gg/tactics/' + key.lower().replace(' ', '-') + '/'
    if key == '4-3-1-2':
        return 'https://note.com/yuyugamesyoutube/n/nf627565b75df'
    return 'https://nealguides.com/best-fc-27-formations/'


def normalized_position(position: str) -> str:
    key = (position or "").strip().upper()
    return POSITION_ALIASES.get(key, key)


def player_positions(player: Player, use_alternate_positions: bool = True) -> set[str]:
    positions = {normalized_position(player.position)}
    if use_alternate_positions:
        positions.update(normalized_position(position) for position in (player.alternate_positions or []))
    return positions & ATTRIBUTE_WEIGHTS.keys()


def athlete_keys(player: Player) -> set[str]:
    """A duplicate name OR base identity OR card identity cannot play twice."""
    if getattr(player, "athlete_id", None):
        return {f"athlete:{player.athlete_id}"}
    name = " ".join(unicodedata.normalize("NFKD", player.name).encode("ascii", "ignore").decode("ascii").casefold().split())
    keys = {f"name:{name}"} if name else {f"row:{player.id}"}
    if player.base_card_id:
        keys.add(f"athlete:{player.base_card_id}")
    if player.card_id:
        keys.add(f"card:{player.card_id}")
    return keys


def _fit(player: Player, position: str, style: str = "balanced") -> tuple[float, str]:
    weights = dict(ATTRIBUTE_WEIGHTS[position])
    if position != "POR":
        for attribute in weights:
            if style == "attacking" and attribute in {"pace", "shooting", "dribbling"}:
                weights[attribute] *= 1.25
            if style == "possession" and attribute in {"passing", "dribbling"}:
                weights[attribute] *= 1.4
            if style == "defensive" and attribute in {"defending", "physical"}:
                weights[attribute] *= 1.4
            if style == "wide" and position in {"MD", "MI", "ED", "EI", "LD", "LI"} and attribute in {"pace", "passing", "dribbling"}:
                weights[attribute] *= 1.4
    attributes = player.attributes or {}
    observed = {key: float(attributes[key]) for key in weights if key in attributes and isinstance(attributes[key], (int, float)) and 0 <= attributes[key] <= 99}
    if observed:
        weighted = sum(observed[key] * weights[key] for key in observed) / sum(weights.values())
        score = 0.70 * player.rating + 0.30 * weighted
        strongest = sorted(observed, key=lambda key: weights[key] * observed[key], reverse=True)[:2]
        explanation = f"Media {player.rating}; " + ", ".join(f"{ATTRIBUTE_LABELS[key]} {observed[key]:g}" for key in strongest)
    else:
        score = 0.70 * float(player.rating)
        explanation = f"Media {player.rating}; sin atributos detallados, se usa la media registrada"
    role = (player.roles or {}).get(position)
    bonus = 2 if role == "++" else 1 if role == "+" else 0
    if bonus:
        score += bonus
        explanation += f"; rol {position}{role} registrado"
    explanation += f"; cobertura de atributos {round(100 * sum(weights[k] for k in observed) / sum(weights.values()))}%"
    if player.playstyles_plus:
        explanation += "; PlayStyles registrados sin bonificación numérica no verificada"
    if normalized_position(player.position) != position:
        explanation += "; posición alternativa registrada"
    return round(min(100, max(0, score)), 2), explanation


def _group(position: str) -> str:
    if position == "POR":
        return "portero"
    if position in {"LD", "DFC", "LI", "CAD", "CAI"}:
        return "defensa"
    if position in {"MCD", "MC", "MCO", "MD", "MI"}:
        return "medio"
    return "ataque"


def recommend_owned_squad(players: list[Player], *, game_version: str, formation: str = "4-3-3", style: str = "balanced", locked_player_ids: list[int] | None = None, excluded_player_ids: list[int] | None = None, bench_size: int = 7, include_loans: bool = True, include_unreviewed: bool = False, use_alternate_positions: bool = True, protected_ids: set[int] | None = None) -> dict:
    if game_version != 'FC27':
        raise ValueError('Solo se admite FC27')
    players = [p for p in players if p.validation_status in ('documented', 'provider_verified')]
    from ortools.sat.python import cp_model

    slots = formation_slots(formation)
    locked, excluded = set(locked_player_ids or []), set(excluded_player_ids or [])
    if locked & excluded:
        raise ValueError("Una carta no puede estar fijada y excluida a la vez")
    from app.services.remote_evidence import field_known
    candidates = sorted((p for p in players if not p.deleted and getattr(p, "availability", "available") in {None, "available"} and p.game_version == game_version and p.id not in excluded and (include_loans or field_known(p, 'is_loan') and not p.is_loan) and (include_unreviewed or p.data_reviewed or (p.validation_evidence or {}).get('kind') == 'observed_copy')), key=lambda p: (-p.rating, p.id))
    by_id = {p.id: p for p in candidates}
    if not locked.issubset(by_id):
        raise ValueError("Una carta fijada no está disponible en esta edición o está pendiente de revisión")
    model = cp_model.CpModel()
    assignments, scores, descriptions = {}, {}, {}
    per_player, per_slot, per_identity = defaultdict(list), defaultdict(list), defaultdict(list)
    for player in candidates:
        for slot_index, slot in enumerate(slots):
            if slot["position"] not in player_positions(player, use_alternate_positions):
                continue
            variable = model.new_bool_var(f"p{player.id}_s{slot_index}")
            key = (player.id, slot_index)
            assignments[key] = variable
            scores[key], descriptions[key] = _fit(player, slot["position"], style)
            per_player[player.id].append(variable)
            per_slot[slot_index].append(variable)
            for identity in athlete_keys(player):
                per_identity[identity].append(variable)
    for player in candidates:
        variables = per_player[player.id]
        model.add(sum(variables) == 1 if player.id in locked else sum(variables) <= 1)
    for variables in per_slot.values():
        model.add(sum(variables) <= 1)
    for variables in per_identity.values():
        model.add(sum(variables) <= 1)
    # Filling a legitimate position dominates any fit-score improvement.
    model.maximize(sum(variable * (1_000_000 + round(scores[key] * 100)) for key, variable in assignments.items()))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 4.0
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    status = solver.solve(model)
    if status == cp_model.INFEASIBLE and locked:
        raise ValueError("Las cartas fijadas no caben en los puestos de esta formación o son versiones del mismo futbolista")
    chosen = {}
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        chosen = {slot_index: by_id[player_id] for (player_id, slot_index), variable in assignments.items() if solver.value(variable)}
    elif locked:
        raise ValueError("No se pudo verificar la asignación de las cartas fijadas dentro del tiempo disponible")
    lineup, gaps, chosen_identities = [], [], set()
    for slot_index, slot in enumerate(slots):
        player = chosen.get(slot_index)
        if not player:
            gaps.append({**slot, "reason": "Falta otra carta elegible para este puesto respetando posiciones, exclusiones e identidad del futbolista"})
            continue
        chosen_identities.update(athlete_keys(player))
        lineup.append({**slot, "player": serialize_player(player, protected_ids), "fit_score": scores[player.id, slot_index], "used_alternate_position": normalized_position(player.position) != slot["position"], "explanation": descriptions[player.id, slot_index]})
    reserve = [p for p in candidates if not (athlete_keys(p) & chosen_identities)]
    bench, bench_groups = [], Counter()
    while reserve and len(bench) < bench_size:
        def reserve_priority(player):
            positions = player_positions(player, use_alternate_positions)
            groups = {_group(position) for position in positions}
            uncovered = any(bench_groups[group] == 0 for group in groups)
            return (10 if uncovered else 0) + max((_fit(player, position, style)[0] for position in positions), default=player.rating), -player.id
        player = max(reserve, key=reserve_priority)
        bench.append(player)
        keys = athlete_keys(player)
        chosen_identities.update(keys)
        for position in player_positions(player, use_alternate_positions):
            bench_groups[_group(position)] += 1
        reserve = [p for p in reserve if not (athlete_keys(p) & keys)]
    warnings = ["La química es la suma 0–3 registrada en las cartas; no reproduce ni garantiza la química oficial de esta formación."]
    if gaps:
        warnings.append("Plantilla incompleta: se muestran los puestos vacantes sin colocar cartas fuera de posición.")
    if any(not (p.attributes or {}) for p in chosen.values()):
        warnings.append("Algunas cartas no tienen atributos detallados; su encaje utiliza la media registrada.")
    if any(not p.data_reviewed for p in chosen.values()):
        warnings.append("Incluiste datos pendientes de revisión; confirma esos valores antes de usar esta recomendación.")
    if any(not p.base_card_id and not p.athlete_id for p in candidates):
        warnings.append("Sin identificador base, las versiones del mismo futbolista se agrupan por nombre; revisa homónimos y nombres abreviados.")
    if status == cp_model.FEASIBLE:
        warnings.append("Se encontró una asignación válida dentro del límite de tiempo; no se ha probado que sea la mejor posible.")
    elif status not in (cp_model.OPTIMAL, cp_model.INFEASIBLE):
        warnings.append("El cálculo no produjo una asignación dentro del límite de tiempo; los puestos vacantes no prueban que falten cartas elegibles.")
    return {
        "game_version": game_version, "formation": formation, "style": style, "recommendation": True, "simulation": True,
        "complete": len(lineup) == 11, "players": [row["player"] for row in lineup], "lineup": lineup,
        "bench": [serialize_player(p, protected_ids) for p in bench], "gaps": gaps, "warnings": warnings,
        "rating": calculate_rating([p.rating for p in chosen.values()]), "chemistry": sum(p.chemistry for p in chosen.values()) if all(field_known(p, "chemistry") for p in chosen.values()) else None,
        "chemistry_approximate": True, "chemistry_status": "unavailable", "rating_status": "estimated", "solver_status": "optimal" if status == cp_model.OPTIMAL else "feasible" if status == cp_model.FEASIBLE else "infeasible" if status == cp_model.INFEASIBLE else "timeout", "objective_bound": solver.best_objective_bound, "eligible_count": len(candidates),
        "explanations": ["Se prioriza cubrir los once puestos con cartas propias de la edición activa.", "Encaje local: 70 % media y 30 % atributos disponibles ponderados por puesto; ajuste por rol registrado; PlayStyles sin bonificación numérica.", "Las cartas protegidas sí pueden jugar; su protección únicamente impide consumirlas en DCP.", "No se repite la misma carta, identificador base o nombre de futbolista entre titulares y suplentes."],
    }


def compare_main(db: Session, proposal: dict) -> dict:
    """Read-only local fit comparison; it neither changes nor activates a squad."""
    from app.services.main_squad import main_status
    main = main_status(db)
    result = dict(available=False, squad_id=main['squad_id'], additional_cost=0, rows=[],
                  reason=main['reason'], official_performance=False)
    if not main['complete']:
        return result
    members = {m['slot']: m['player_id'] for m in main['snapshot']['members']}
    players = {p.id: p for p in db.scalars(select(Player).where(Player.id.in_(members.values())))}
    rows = []
    for row in proposal['lineup']:
        previous = players.get(members.get(row['slot']))
        score = _fit(previous, row['position'], proposal['style'])[0] if previous else None
        rows.append(dict(slot=row['slot'], position=row['position'], proposed_id=row['player']['id'],
            proposed_name=row['player']['name'], main_id=previous.id if previous else None,
            main_name=previous.name if previous else None, main_fit=score, proposed_fit=row['fit_score'],
            delta=round(row['fit_score']-score, 2) if score is not None else None))
    result.update(available=True, rows=rows, reason='Comparación del encaje local en puestos equivalentes; usa la media cuando faltan atributos. No predice resultados ni química oficial.',
        main_formation=main['snapshot']['formation'], proposed_formation=proposal['formation'])
    return result


def _formation_coverage(players: list[Player], formation: str) -> int:
    """Small augmenting-path match for a formation hint, not a lineup result."""
    groups: dict[str, set[str]] = defaultdict(set)
    for player in players:
        key = sorted(athlete_keys(player))[0]
        groups[key].update(player_positions(player))
    taken: dict[str, int] = {}
    slots = FORMATIONS[formation]
    def assign(slot: int, seen: set[str]) -> bool:
        for athlete, positions in groups.items():
            if slots[slot] not in positions or athlete in seen:
                continue
            seen.add(athlete)
            if athlete not in taken or assign(taken[athlete], seen):
                taken[athlete] = slot
                return True
        return False
    return sum(assign(index, set()) for index in range(len(slots)))


def analyze_club(db: Session) -> dict:
    version = current_version(db)
    players = db.scalars(select(Player).where(Player.game_version == version, Player.deleted.is_(False), Player.availability == "available").order_by(Player.rating.desc(), Player.id)).all()
    protected = effective_protected_ids(db, version) & {p.id for p in players}
    reviewed = [p for p in players if p.data_reviewed or (p.validation_evidence or {}).get("kind") == "observed_copy"]
    alternatives = [recommend_owned_squad(players, game_version=version, formation=formation, bench_size=0, protected_ids=protected) for formation in verified_formations()]
    recommendation = max(alternatives, key=lambda result: (len(result["lineup"]), sum(row["fit_score"] for row in result["lineup"])), default={"formation": None, "gaps": [], "warnings": ["Formaciones pendientes de una nueva revisión documental FC27"]})
    recommended = recommendation["formation"]
    positions = []
    for position in ATTRIBUTE_WEIGHTS:
        suitable = [p for p in reviewed if position in player_positions(p)]
        best = max(suitable, key=lambda p: (_fit(p, position)[0], p.rating, -p.id), default=None)
        positions.append({"position": position, "count": len(suitable), "best_rating": best.rating if best else None, "best_player_id": best.id if best else None})
    return {
        "game_version": version, "simulation": True,
        "counts": {"players": len(players), "reviewed": len(reviewed), "unreviewed": len(players) - len(reviewed), "protected": len(protected), "loans": sum(p.is_loan for p in players), "evolutions": sum(p.is_evolution for p in players), "holographic": sum(p.is_holographic for p in players), "duplicates": sum(p.duplicate_untradeable for p in players)},
        "average_rating": round(sum(p.rating for p in players) / len(players), 2) if players else 0,
        "positions": positions, "top_players": [serialize_player(p, protected) for p in reviewed[:10]],
        "gaps": recommendation["gaps"], "warnings": recommendation["warnings"], "recommended_formation": recommended,
    }
