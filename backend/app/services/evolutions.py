"""Conservative, read-only branching Evolution previews from reviewed inputs."""
from copy import deepcopy
from datetime import datetime, timezone
from pydantic import ValidationError
from app.schemas.api import PlayerCreate
from app.schemas.fc27 import EvolutionRequirements, EvolutionUpgrades
from app.services.gallery import snapshot_player


def definition_data(definition):
    from app.services.definition_validation import is_documented, pending_result
    if not is_documented(definition):
        return pending_result(definition)
    return {field: getattr(definition, field) for field in ("id", "game_version", "slug", "name", "description", "requirements", "paths", "expires_at", "source_url", "rules_reviewed")}


def preview_path(player, definition, path):
    card = deepcopy(player)
    requirements = EvolutionRequirements.model_validate(definition.requirements)
    upgrades = EvolutionUpgrades.model_validate(path["upgrades"])
    violations = []
    from app.services.definition_validation import is_documented
    if not is_documented(definition):
        violations.append('Pendiente de evidencia vigente de las reglas FC27.')
    if not definition.rules_reviewed:
        violations.append("Las reglas de esta evolución todavía no están revisadas.")
    if card.get("game_version") != definition.game_version:
        violations.append("La evolución y la carta pertenecen a ediciones distintas.")
    if definition.expires_at:
        expiry = definition.expires_at.replace(tzinfo=timezone.utc) if definition.expires_at.tzinfo is None else definition.expires_at
        if expiry <= datetime.now(timezone.utc): violations.append("Esta evolución ha vencido.")
    if card.get("is_loan"):
        violations.append("Una carta cedida no se propone para evolución.")
    if not card.get("data_reviewed"):
        violations.append("Revisa primero los datos de esta carta.")
    if not requirements.min_rating <= card["rating"] <= requirements.max_rating:
        violations.append(f"La media debe estar entre {requirements.min_rating} y {requirements.max_rating}.")
    positions = {card["position"], *card.get("alternate_positions", [])}
    if requirements.positions and not positions.intersection(requirements.positions):
        violations.append("La carta no tiene una posición admitida.")
    for field, maximum in requirements.max_attributes.items():
        value = card.get("attributes", {}).get(field)
        if value is None: violations.append(f"Falta el atributo {field} para verificar el límite {maximum}.")
        elif value > maximum: violations.append(f"{field} supera el límite {maximum}.")
    for field, maximum in (("playstyles", requirements.max_playstyles), ("playstyles_plus", requirements.max_playstyles_plus)):
        if maximum is not None and len(card.get(field, [])) > maximum:
            violations.append(f"La cantidad de {field} supera {maximum}.")
    for field, maximum in (("skill_moves", requirements.max_skill_moves), ("weak_foot", requirements.max_weak_foot)):
        if maximum is not None:
            if card.get(field) is None: violations.append(f"Falta {field} para verificar la evolución.")
            elif card[field] > maximum: violations.append(f"{field} supera {maximum}.")
    if requirements.exclude_special and card.get("special"):
        violations.append("Esta evolución excluye cartas especiales.")
    # An unknown starting stat cannot be filled with an invented numerical value.
    for field in upgrades.attributes:
        if field not in card.get("attributes", {}): violations.append(f"Falta {field} para proyectar su mejora.")
    for field in ("skill_moves", "weak_foot"):
        if getattr(upgrades, field) and card.get(field) is None:
            violations.append(f"Falta {field} para proyectar su mejora.")
    plus = list(dict.fromkeys([*card.get("playstyles_plus", []), *upgrades.playstyles_plus]))
    if card.get("game_version") == "FC27" and len(plus) > 3:
        violations.append("La proyección supera los tres PlayStyle+ de FC 27; revisa la definición.")
    if violations:
        return {"eligible": False, "violations": violations, "projected": card}
    card["rating"] = max(card["rating"], min(upgrades.rating_cap, card["rating"] + upgrades.rating))
    card["attributes"] = {**card.get("attributes", {})}
    for field, boost in upgrades.attributes.items():
        card["attributes"][field] = max(card["attributes"][field], min(upgrades.attribute_caps.get(field, 99), card["attributes"][field] + boost))
    card["alternate_positions"] = list(dict.fromkeys([*card.get("alternate_positions", []), *upgrades.alternate_positions]))
    card["playstyles"] = list(dict.fromkeys([*card.get("playstyles", []), *upgrades.playstyles]))
    card["playstyles_plus"] = plus
    roles = dict(card.get("roles", {}))
    def familiarity(value):
        text = str(value).strip()
        if text.endswith("++"): return 2
        if text.endswith("+"): return 1
        if text.casefold() in ("base", "normal", "0"): return 0
        return None
    for role, value in upgrades.roles.items():
        old_level, new_level = familiarity(roles.get(role)), familiarity(value)
        if old_level is None or new_level is None or new_level > old_level:
            roles[role] = value
    card["roles"] = roles
    for field in ("skill_moves", "weak_foot"):
        if card.get(field) is not None: card[field] = max(card[field], min(getattr(upgrades, field + "_cap"), card[field] + getattr(upgrades, field)))
    if not card.get("is_evolution"): card["base_card_id"] = card.get("card_id")
    card["is_evolution"] = True
    card["gallery_score"] = None  # evolved card points need their own reviewed value
    try:
        PlayerCreate.model_validate({key: card[key] for key in PlayerCreate.model_fields if key in card})
    except ValidationError as error:
        messages = ["Proyección no válida en " + ".".join(str(part) for part in item["loc"]) + ": " + item["msg"] for item in error.errors()]
        return {"eligible": False, "violations": messages, "projected": deepcopy(player)}
    return {"eligible": True, "violations": [], "projected": card}
