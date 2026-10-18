"""Persistent, local acquisition history and user-reviewed Gallery planning."""
from collections import defaultdict
import hashlib
import json
import unicodedata
from datetime import timezone
from ortools.sat.python import cp_model
from sqlalchemy import select
from app.models.entities import GalleryEntry, Player
from app.schemas.api import PlayerCreate
from app.schemas.fc27 import GalleryRules, GalleryTag


def folded(value):
    return " ".join(unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().casefold().split())


def item_key(player):
    """Copies share an item key; distinct versions never share acquisition slots."""
    get = player.get if isinstance(player, dict) else lambda key, default=None: getattr(player, key, default)
    identity = ["card", get("card_id"), bool(get("is_holographic"))] if get("card_id") else [
        "local", folded(get("name")), get("rating"), folded(get("card_type")),
        folded(get("league")), folded(get("club")), folded(get("nationality")), bool(get("is_holographic")),
    ]
    evidence = get('validation_evidence', {}) or {}
    level = get('holographic_level', evidence.get('additional_facts',{}).get('holographic_level'))
    if level is not None:
        identity.extend(['holographic_level', level])
    return hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode()).hexdigest()


def snapshot_player(player):
    if (player.validation_evidence or {}).get('kind') == 'visual_copy':
        from app.services.squad_analysis import serialize_player
        values = serialize_player(player)
        return {key:values.get(key) for key in PlayerCreate.model_fields} | player.validation_evidence.get('additional_facts',{}) | {
            'validation_status':player.validation_status,'variant_evidence':player.validation_evidence,
            'unknown_fields':player.unknown_fields,'ownership_source':'user_reviewed_visual'}
    return {key: getattr(player, key, None) for key in PlayerCreate.model_fields} | {'validation_status': player.validation_status, 'variant_evidence': player.validation_evidence}


def base_for_gallery(db, player):
    from app.services.remote_evidence import field_known
    if player.is_loan or not field_known(player, 'is_loan') or not field_known(player, 'is_evolution'):
        return None
    if not player.is_evolution:
        return player
    if not player.base_card_id or not field_known(player, 'base_card_id'):
        return None
    return db.scalar(select(Player).where(
        Player.game_version == player.game_version, Player.card_id == player.base_card_id,
        Player.is_evolution.is_(False), Player.is_loan.is_(False),
    ).order_by(Player.id))


def reviewed_score(snapshot):
    return snapshot.get("gallery_score") if snapshot.get("score_reviewed", snapshot.get("data_reviewed", False)) else None


def record_player(db, player, *, score_changed=False):
    """Part of the caller's transaction. Never records an action in EA's service."""
    db.flush()
    from app.services.remote_evidence import field_known
    if (player.validation_evidence or {}).get('kind') == 'visual_copy' and not field_known(player, 'card_type'):
        return None
    if player.game_version != 'FC27' or player.is_loan or player.validation_status not in ('documented', 'provider_verified', 'visual_reviewed'):
        return None
    base = base_for_gallery(db, player)
    if base is None:
        # A previously recorded base can still represent a now-evolved card.
        if player.is_evolution and player.base_card_id:
            entries = db.scalars(select(GalleryEntry).where(GalleryEntry.game_version == player.game_version))
            return next((entry for entry in entries if entry.snapshot.get("card_id") == player.base_card_id), None)
        return None
    key = item_key(base)
    entry = db.scalar(select(GalleryEntry).where(GalleryEntry.game_version == base.game_version, GalleryEntry.item_key == key))
    matched_alias = False
    if entry is None and not base.card_id:
        entry = next((candidate for candidate in db.scalars(select(GalleryEntry).where(GalleryEntry.game_version == base.game_version))
                      if key in candidate.snapshot.get("identity_keys", [])), None)
        matched_alias = entry is not None
    old_entry = db.scalar(select(GalleryEntry).where(GalleryEntry.game_version == base.game_version, GalleryEntry.player_id == base.id))
    if old_entry and base.card_id and old_entry.snapshot.get('card_id') != base.card_id:
        old_entry = None  # Different documented variants keep independent history.
    level = (base.validation_evidence or {}).get('additional_facts',{}).get('holographic_level')
    if old_entry and old_entry.snapshot.get('holographic_level') != level and (level is not None or old_entry.snapshot.get('holographic_level') is not None):
        old_entry = None  # Never rewrite a previous holographic level's history.
    if entry is None:
        entry = old_entry
    aliases = set(entry.snapshot.get("identity_keys", [])) if entry else set()
    if entry is not None:
        aliases.add(entry.item_key)
    if old_entry is not None and entry is not old_entry:
        # A corrected canonical ID can identify an item already recorded by
        # another copy. Merge those records and preserve the earliest history.
        aliases.update([old_entry.item_key, *old_entry.snapshot.get("identity_keys", [])])
        if old_entry.recorded_at.replace(tzinfo=timezone.utc) < entry.recorded_at.replace(tzinfo=timezone.utc):
            entry.recorded_at = old_entry.recorded_at
        db.delete(old_entry)
    snapshot = snapshot_player(base)
    if matched_alias and not base.card_id:
        aliases.add(key)
        key = entry.item_key
        snapshot["card_id"] = entry.snapshot.get("card_id")
    snapshot["score_reviewed"] = bool(base.data_reviewed and base.gallery_score is not None and field_known(base,'gallery_score'))
    snapshot["identity_keys"] = sorted(aliases - {key})
    if entry is not None and not score_changed and not snapshot["score_reviewed"] and reviewed_score(entry.snapshot) is not None and (base.validation_evidence or {}).get('kind') != 'visual_copy':
        snapshot["gallery_score"] = reviewed_score(entry.snapshot)
        snapshot["score_reviewed"] = True
    if entry is None:
        entry = GalleryEntry(game_version=base.game_version, item_key=key, player_id=base.id, snapshot=snapshot)
        db.add(entry)
    else:
        entry.item_key = key
        entry.snapshot = snapshot
    # One reviewed item value belongs to its version, including duplicate copies.
    # An explicit null patch clears the score instead of reviving an older value.
    if snapshot["score_reviewed"] or score_changed:
        keys = {key, *snapshot["identity_keys"]}
        for copy in db.scalars(select(Player).where(Player.game_version == base.game_version, Player.is_evolution.is_(False))):
            if item_key(copy) in keys and (copy.validation_evidence or {}).get('kind') not in {'observed_copy', 'visual_copy'}:
                copy.gallery_score = snapshot.get("gallery_score")
    db.flush()
    return entry


def owned_index(players):
    from app.services.remote_evidence import field_known
    result = defaultdict(list)
    for player in players:
        if not player.deleted and not player.is_loan and not player.is_evolution and field_known(player, 'is_loan') and field_known(player, 'is_evolution') and getattr(player, "availability", "available") in {None, "available", "unavailable"}:
            result[item_key(player)].append(player.id)
    return result


def entry_data(entry, owned=None):
    item = dict(entry.snapshot)
    keys = {entry.item_key, *entry.snapshot.get("identity_keys", [])}
    current_ids = sorted({player_id for key in keys for player_id in (owned or {}).get(key, [])})
    item["gallery_score"] = reviewed_score(entry.snapshot)
    item.update(id=entry.id, item_key=entry.item_key, game_version=entry.game_version,
                player_id=entry.player_id, recorded_at=entry.recorded_at,
                owned=bool(current_ids), current_player_ids=current_ids)
    return item


def tag_match(snapshot, tag):
    value = snapshot.get(tag.field)
    return value is tag.value if isinstance(tag.value, bool) else folded(value) == folded(tag.value)


def evaluate_set(gallery_set, entries, owned=None):
    rules = GalleryRules.model_validate(gallery_set.rules)
    if rules.schema_version == 2:
        from app.services.gallery_v2 import evaluate_v2
        return evaluate_v2(gallery_set, entries, owned)
    tags = [GalleryTag.model_validate(tag) for tag in gallery_set.tags]
    eligible = []
    for entry in entries:
        card = entry.snapshot
        if card.get("rating", 0) < rules.min_rating or (rules.holographic_only and not card.get("is_holographic")):
            continue
        if any(getattr(rules, field) and folded(card.get(field)) != folded(getattr(rules, field)) for field in ("league", "club", "nationality", "card_type")):
            continue
        eligible.append(entry)
    model = cp_model.CpModel()
    chosen = [model.NewBoolVar(f"entry_{entry.id}") for entry in eligible]
    model.Add(sum(chosen) <= rules.size)
    if rules.unique_players:
        names = defaultdict(list)
        for index, entry in enumerate(eligible):
            # Conservative athlete identity when no canonical athlete ID exists.
            names[folded(entry.snapshot.get("name"))].append(index)
        for indices in names.values():
            model.Add(sum(chosen[index] for index in indices) <= 1)
    max_score = max((reviewed_score(entry.snapshot) or entry.snapshot.get("rating", 0) for entry in eligible), default=0)
    # Cardinality is the first priority; then reviewed item points and tag bonuses.
    cardinality_weight = rules.size * max_score + sum(tag.bonus for tag in tags) + 1
    scores = [reviewed_score(entry.snapshot) if reviewed_score(entry.snapshot) is not None else entry.snapshot.get("rating", 0) for entry in eligible]
    objective = sum(chosen[index] * (cardinality_weight + scores[index]) for index in range(len(eligible)))
    for index, tag in enumerate(tags):
        count = sum(chosen[i] for i, entry in enumerate(eligible) if tag_match(entry.snapshot, tag))
        active = model.NewBoolVar(f"tag_{index}")
        model.Add(count >= tag.minimum).OnlyEnforceIf(active)
        model.Add(count < tag.minimum).OnlyEnforceIf(active.Not())
        objective += active * tag.bonus
    model.Maximize(objective)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 1.5
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    status = solver.Solve(model)
    selected = [entry for i, entry in enumerate(eligible) if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) and solver.Value(chosen[i])]
    selected.sort(key=lambda entry: (-(reviewed_score(entry.snapshot) or 0), -entry.snapshot.get("rating", 0), entry.id))
    tag_results = []
    for tag in tags:
        count = sum(tag_match(entry.snapshot, tag) for entry in selected)
        tag_results.append({"name": tag.name, "achieved": count >= tag.minimum, "count": count,
                            "minimum": tag.minimum, "bonus": tag.bonus if count >= tag.minimum else 0})
    unknown = sum(reviewed_score(entry.snapshot) is None for entry in selected)
    known_score = sum(reviewed_score(entry.snapshot) or 0 for entry in selected)
    score = known_score + sum(tag["bonus"] for tag in tag_results) if unknown == 0 and selected and gallery_set.rules_reviewed else None
    complete = len(selected) == rules.size
    grade = None
    if complete and score is not None:
        reached = [(threshold, name) for name, threshold in gallery_set.grade_thresholds.items() if score >= threshold]
        grade = max(reached)[1] if reached else None
    warnings = ["Plan local: no registra ni cobra recompensas en EA."]
    if not gallery_set.rules_reviewed:
        warnings.append("Revisa las reglas, etiquetas y umbrales antes de usar esta propuesta.")
    if unknown:
        warnings.append(f"Falta la puntuación revisada de {unknown} cartas; la media solo orienta la selección.")
    if not gallery_set.grade_thresholds:
        warnings.append("No se calculará un grado hasta introducir sus umbrales reales.")
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        warnings.append("No se pudo calcular una selección dentro del tiempo disponible.")
    elif status != cp_model.OPTIMAL:
        warnings.append("Se muestra una selección válida; no se garantiza la puntuación máxima.")
    return {"selected_entries": [entry_data(entry, owned) for entry in selected], "eligible_count": len(eligible),
            "filled_slots": len(selected), "required_slots": rules.size, "complete": complete,
            "known_score": known_score, "unknown_score_count": unknown, "score": score, "grade": grade,
            "tags": tag_results, "missing_slots": rules.size - len(selected), "warnings": warnings}


def set_data(gallery_set, entries=None, owned=None):
    from app.services.definition_validation import is_documented, pending_result
    if not is_documented(gallery_set):
        return pending_result(gallery_set)
    result = {field: getattr(gallery_set, field) for field in ("id", "game_version", "slug", "name", "description", "category", "rules", "tags", "grade_thresholds", "reward", "source_url", "rules_reviewed")}
    if entries is not None:
        result["evaluation"] = evaluate_set(gallery_set, entries, owned)
    return result
