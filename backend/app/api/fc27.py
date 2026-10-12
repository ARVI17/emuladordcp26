"""FC27 Gallery, evolving local content, and read-only Evolution planning."""
from datetime import datetime, timezone
import hashlib
import json
import re
import unicodedata
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.entities import AppSetting, EvolutionDefinition, GalleryEntry, GallerySet, Player
from app.schemas.api import GameVersion
from app.schemas.fc27 import (ContentImportRequest, EvolutionInput, EvolutionPreview, GalleryRecordRequest,
                             GalleryScoreUpdate, GallerySetInput)
from app.services.audit import record
from app.services.content import builtin_content, fetch_news, active_article
from app.services.editions import current_version
from app.services.evolutions import definition_data, preview_path
from app.services.gallery import (base_for_gallery, entry_data, item_key, owned_index, record_player,
                                  set_data, snapshot_player)
from app.services.locks import resource_locks

router = APIRouter(tags=["FC27 Club Lab"])


def version_of(db, requested=None):
    return requested or current_version(db)


def active_input_version(db, payload):
    version = payload.game_version if "game_version" in payload.model_fields_set else current_version(db)
    if version != current_version(db):
        raise HTTPException(409, "Cambia a la edición correspondiente antes de guardar datos.")
    return version


def require_gallery(version):
    if int(version[2:]) < 27:
        raise HTTPException(409, "La Galería pertenece a FC 27 y ediciones posteriores; tu historial FC 26 sigue separado.")


def slug_for(name):
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")[:80] or hashlib.sha256(name.encode()).hexdigest()[:20]


def gallery_rows(db, version):
    entries = list(db.scalars(select(GalleryEntry).where(GalleryEntry.game_version == version).order_by(GalleryEntry.id.desc())))
    players = list(db.scalars(select(Player).where(Player.game_version == version)))
    return entries, players, owned_index(players)


@router.get("/gallery")
def gallery_summary(game_version: GameVersion | None = None, db: Session = Depends(get_db)):
    version = version_of(db, game_version)
    entries, players, owned = gallery_rows(db, version)
    sets = list(db.scalars(select(GallerySet).where(GallerySet.game_version == version).order_by(GallerySet.name)))
    recorded = {key for entry in entries for key in [entry.item_key, *entry.snapshot.get("identity_keys", [])]}
    eligible = [player for player in players if not player.deleted and base_for_gallery(db, player) is player]
    missing_evos = [player for player in players if not player.deleted and player.is_evolution and not player.is_loan
                    and base_for_gallery(db, player) is None and not any(entry.snapshot.get("card_id") == player.base_card_id for entry in entries if player.base_card_id)]
    return {"game_version": version, "entries_count": len(entries), "eligible_owned_count": len(eligible),
            "unrecorded_count": sum(item_key(player) not in recorded for player in eligible),
            "excluded_loans": sum(player.is_loan and not player.deleted for player in players),
            "unresolved_evolutions": len(missing_evos),
            "sets": [set_data(gallery_set, entries, owned) for gallery_set in sets],
            "message": "Historial local: las cartas registradas permanecen aunque ya no estén disponibles. No modifica tu Galería en EA." if int(version[2:]) >= 27 else "FC 26 se conserva como archivo separado. La Galería se incorpora en FC 27."}


@router.get("/gallery/entries")
def gallery_entries(game_version: GameVersion | None = None, search: str = Query(default="", max_length=100),
                    limit: int = Query(default=60, ge=1, le=200), offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)):
    entries, _, owned = gallery_rows(db, version_of(db, game_version))
    if search:
        entries = [entry for entry in entries if search.casefold() in " ".join(str(entry.snapshot.get(field, "")) for field in ("name", "club", "league", "card_type")).casefold()]
    return {"items": [entry_data(entry, owned) for entry in entries[offset:offset + limit]], "total": len(entries), "limit": limit, "offset": offset}


@router.post("/gallery/record-inventory")
def register_inventory(payload: GalleryRecordRequest = GalleryRecordRequest(), db: Session = Depends(get_db)):
    with resource_locks(db, "inventory"):
        db.expire_all()
        version = current_version(db)
        require_gallery(version)
        query = select(Player).where(Player.game_version == version).order_by(Player.is_evolution, Player.id)
        if payload.player_ids is not None: query = query.where(Player.id.in_(payload.player_ids))
        players = list(db.scalars(query))
        if payload.player_ids is not None and {player.id for player in players} != set(payload.player_ids):
            raise HTTPException(409, "Hay cartas ajenas a la edición activa o que no existen.")
        before = {entry.item_key for entry in db.scalars(select(GalleryEntry).where(GalleryEntry.game_version == version))}
        updated = set()
        created = set()
        loans = unresolved = 0
        for player in players:
            if player.is_loan:
                loans += 1
                continue
            entry = record_player(db, player)
            if entry is None:
                unresolved += int(player.is_evolution)
                continue
            (updated if entry.item_key in before else created).add(entry.item_key)
        record(db, "register_inventory", "gallery", None, {"game_version": version, "created": len(created), "updated": len(updated), "excluded_loans": loans, "unresolved_evolutions": unresolved})
        db.commit()
        return {"created": len(created), "updated": len(updated), "excluded_loans": loans, "unresolved_evolutions": unresolved,
                "message": "Historial local actualizado. Las evoluciones sin carta base identificada quedan pendientes de revisión."}


@router.patch("/gallery/entries/{entry_id}")
def update_gallery_score(entry_id: int, payload: GalleryScoreUpdate, db: Session = Depends(get_db)):
    with resource_locks(db, "inventory"):
        db.expire_all()
        entry = db.get(GalleryEntry, entry_id)
        if entry is None or entry.game_version != current_version(db): raise HTTPException(404, "Carta de Galería no encontrada en esta edición")
        snapshot = dict(entry.snapshot)
        snapshot["gallery_score"] = payload.gallery_score
        snapshot["score_reviewed"] = payload.gallery_score is not None
        entry.snapshot = snapshot
        # The same reviewed item score applies to each physical copy of that version.
        copies = list(db.scalars(select(Player).where(Player.game_version == entry.game_version, Player.is_evolution.is_(False))))
        for player in copies:
            if item_key(player) in {entry.item_key, *entry.snapshot.get("identity_keys", [])}: player.gallery_score = payload.gallery_score
        record(db, "update_score", "gallery", entry.id, {"gallery_score": payload.gallery_score})
        db.commit()
        return entry_data(entry, owned_index(copies))


@router.get("/gallery/sets")
def gallery_sets(game_version: GameVersion | None = None, db: Session = Depends(get_db)):
    version = version_of(db, game_version)
    entries, _, owned = gallery_rows(db, version)
    return [set_data(gallery_set, entries, owned) for gallery_set in db.scalars(select(GallerySet).where(GallerySet.game_version == version).order_by(GallerySet.name))]


def store_set(db, payload, version, existing=None):
    values = payload.model_dump(exclude={"game_version", "slug"})
    slug = payload.slug or (existing.slug if existing else slug_for(payload.name))
    conflict = db.scalar(select(GallerySet).where(GallerySet.game_version == version, GallerySet.slug == slug).execution_options(include_pending_definitions=True))
    if conflict is not None and (existing is None or conflict.id != existing.id): raise HTTPException(409, "Ya existe un conjunto con este identificador")
    if existing is None:
        existing = GallerySet(game_version=version, slug=slug, **values)
        db.add(existing)
    else:
        existing.slug = slug
        for key, value in values.items(): setattr(existing, key, value)
    db.flush()
    return existing


@router.post("/gallery/sets", status_code=201)
def create_gallery_set(payload: GallerySetInput, db: Session = Depends(get_db)):
    with resource_locks(db, "inventory"):
        version = active_input_version(db, payload)
        require_gallery(version)
        item = store_set(db, payload, version)
        record(db, "create", "gallery_set", item.id, {"game_version": version, "rules_reviewed": item.rules_reviewed})
        db.commit()
        entries, _, owned = gallery_rows(db, version)
        return set_data(item, entries, owned)


@router.patch("/gallery/sets/{set_id}")
def edit_gallery_set(set_id: int, payload: GallerySetInput, db: Session = Depends(get_db)):
    with resource_locks(db, "inventory"):
        db.expire_all()
        item = db.get(GallerySet, set_id)
        if item is None or item.game_version != current_version(db): raise HTTPException(404, "Conjunto no encontrado")
        version = active_input_version(db, payload)
        store_set(db, payload, version, item)
        record(db, "update", "gallery_set", item.id, {"rules_reviewed": item.rules_reviewed})
        db.commit()
        entries, _, owned = gallery_rows(db, version)
        return set_data(item, entries, owned)


@router.delete("/gallery/sets/{set_id}")
def delete_gallery_set(set_id: int, db: Session = Depends(get_db)):
    with resource_locks(db, "inventory"):
        item = db.get(GallerySet, set_id)
        if item is None or item.game_version != current_version(db): raise HTTPException(404, "Conjunto no encontrado")
        db.delete(item)
        record(db, "delete", "gallery_set", set_id, {"history_preserved": True})
        db.commit()
        return {"deleted": True}


@router.get("/evolutions")
def evolutions(game_version: GameVersion | None = None, db: Session = Depends(get_db)):
    return [definition_data(item) for item in db.scalars(select(EvolutionDefinition).where(EvolutionDefinition.game_version == version_of(db, game_version)).order_by(EvolutionDefinition.name))]


def store_evolution(db, payload, version, existing=None):
    values = payload.model_dump(exclude={"game_version", "slug"})
    slug = payload.slug or (existing.slug if existing else slug_for(payload.name))
    conflict = db.scalar(select(EvolutionDefinition).where(EvolutionDefinition.game_version == version, EvolutionDefinition.slug == slug).execution_options(include_pending_definitions=True))
    if conflict is not None and (existing is None or conflict.id != existing.id): raise HTTPException(409, "Ya existe una evolución con este identificador")
    if existing is None:
        existing = EvolutionDefinition(game_version=version, slug=slug, **values)
        db.add(existing)
    else:
        existing.slug = slug
        for key, value in values.items(): setattr(existing, key, value)
    db.flush()
    return existing


@router.post("/evolutions", status_code=201)
def create_evolution(payload: EvolutionInput, db: Session = Depends(get_db)):
    with resource_locks(db, "inventory"):
        version = active_input_version(db, payload)
        item = store_evolution(db, payload, version)
        record(db, "create", "evolution", item.id, {"rules_reviewed": item.rules_reviewed})
        db.commit()
        return definition_data(item)


@router.patch("/evolutions/{evolution_id}")
def edit_evolution(evolution_id: int, payload: EvolutionInput, db: Session = Depends(get_db)):
    with resource_locks(db, "inventory"):
        db.expire_all()
        item = db.get(EvolutionDefinition, evolution_id)
        if item is None or item.game_version != current_version(db): raise HTTPException(404, "Evolución no encontrada")
        store_evolution(db, payload, active_input_version(db, payload), item)
        record(db, "update", "evolution", item.id, {"rules_reviewed": item.rules_reviewed})
        db.commit()
        return definition_data(item)


@router.delete("/evolutions/{evolution_id}")
def delete_evolution(evolution_id: int, db: Session = Depends(get_db)):
    with resource_locks(db, "inventory"):
        item = db.get(EvolutionDefinition, evolution_id)
        if item is None or item.game_version != current_version(db): raise HTTPException(404, "Evolución no encontrada")
        db.delete(item)
        record(db, "delete", "evolution", evolution_id, {})
        db.commit()
        return {"deleted": True}


@router.post("/evolutions/preview")
def preview_evolutions(payload: EvolutionPreview, db: Session = Depends(get_db)):
    version = current_version(db)
    player = db.get(Player, payload.player_id)
    if player is None or player.deleted or player.game_version != version: raise HTTPException(404, "Jugador no disponible en esta edición")
    original = {**snapshot_player(player), "id": player.id, "deleted": player.deleted, "created_at": player.created_at}
    projected = dict(original)
    steps = []
    eligible = True
    for step in payload.steps:
        definition = db.get(EvolutionDefinition, step.evolution_id)
        if definition is None or definition.game_version != version: raise HTTPException(404, "Evolución no encontrada en esta edición")
        path = next((path for path in definition.paths if path["id"] == step.path_id), None)
        if path is None: raise HTTPException(422, "El camino no existe en esta evolución")
        result = preview_path(projected, definition, path)
        steps.append({"evolution_id": definition.id, "name": definition.name, "path_id": path["id"], "path_name": path["name"], **result})
        if not result["eligible"]:
            eligible = False
            break
        projected = result["projected"]
    return {"simulation": True, "game_version": version, "eligible": eligible, "original": original,
            "projected": projected, "steps": steps,
            "warnings": ["Proyección local a partir de reglas introducidas y revisadas. No activa evoluciones ni cambia tus jugadores.",
                         "Comprueba en el juego los requisitos adicionales, costes, topes y plazos antes de elegir."]}


@router.get("/content")
def content(game_version: GameVersion | None = None, db: Session = Depends(get_db)):
    version = version_of(db, game_version)
    result = builtin_content(version)
    news = db.get(AppSetting, f"content_news_{version}")
    manifest = db.get(AppSetting, f"content_manifest_{db.info.get('club_context_id', 1)}_{version}")
    result.update(last_checked=None, refresh_error=None, last_import=manifest.value if manifest else None, pending_articles=0)
    if news:
        result.update(last_checked=news.value.get("last_checked"), refresh_error=news.value.get("refresh_error"))
        candidates = news.value.get('articles', [])
        articles = [a for a in candidates if active_article(a)]
        result['pending_articles'] = len(candidates)-len(articles)
        seen = {article['url'] for article in articles}
        result['articles'] = [*articles, *[a for a in result['articles'] if a['url'] not in seen]]
    return result


@router.post("/content/refresh")
def refresh_content(db: Session = Depends(get_db)):
    version = current_version(db)
    try:
        refreshed = fetch_news(version)
    except Exception:
        # Keep the last successful list; exceptions cannot expose proxy or host data.
        refreshed = {"last_checked": datetime.now(timezone.utc).isoformat(), "refresh_error": "No se pudo leer la fuente pública de EA. Se conserva el contenido disponible; puedes abrir las fuentes e importar reglas revisadas."}
    with resource_locks(db, f"content:{version}"):
        db.expire_all()
        setting = db.get(AppSetting, f"content_news_{version}")
        value = {**(setting.value if setting else {}), **refreshed}
        if setting is None: db.add(AppSetting(key=f"content_news_{version}", value=value))
        else: setting.value = value
        record(db, "refresh_public_news", "content", None, {"game_version": version, "success": not bool(value.get("refresh_error"))})
        db.commit()
    return content(version, db)


@router.post("/content/import")
def import_content(payload: ContentImportRequest, db: Session = Depends(get_db)):
    manifest = payload.manifest
    if manifest.game_version != current_version(db): raise HTTPException(409, "El paquete pertenece a otra edición")
    serialized = json.dumps(manifest.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if len(serialized.encode()) > 2_000_000: raise HTTPException(413, "El paquete supera 2 MB")
    from app.api.routes import _import_secret
    import hmac
    digest = hmac.new(_import_secret(db), f"{db.info.get('club_context_id', 1)}:{serialized}".encode(), "sha256").hexdigest()
    for collection in (manifest.sets, manifest.evolutions):
        slugs = [item.slug or slug_for(item.name) for item in collection]
        if len(slugs) != len(set(slugs)): raise HTTPException(422, "El paquete contiene identificadores repetidos")
    version = manifest.game_version
    if manifest.sets: require_gallery(version)
    summary = {"game_version": version, "sets": len(manifest.sets), "evolutions": len(manifest.evolutions),
               "preview_hash": digest, "published_at": manifest.published_at,
               "warnings": ["Reemplaza las definiciones con el mismo identificador; conserva jugadores e historial de Galería.",
                            "Los datos proceden del paquete importado. Su fuente no implica verificación automática de las reglas."]}
    if not payload.confirm: return {"preview": True, **summary}
    if payload.preview_hash != digest: raise HTTPException(409, "El paquete cambió después de la vista previa; revísalo de nuevo")
    with resource_locks(db, "inventory"):
        db.expire_all()
        if version != current_version(db): raise HTTPException(409, "La edición activa cambió después de la vista previa")
        setting = db.get(AppSetting, f"content_manifest_{db.info.get('club_context_id', 1)}_{version}")
        receipt_key = "_content_" + digest
        if db.get(AppSetting, receipt_key) is not None:
            return {"preview": False, "already_imported": True, **summary}
        for item in manifest.sets:
            existing = db.scalar(select(GallerySet).where(GallerySet.game_version == version, GallerySet.slug == (item.slug or slug_for(item.name))).execution_options(include_pending_definitions=True))
            store_set(db, item, version, existing)
        for item in manifest.evolutions:
            existing = db.scalar(select(EvolutionDefinition).where(EvolutionDefinition.game_version == version, EvolutionDefinition.slug == (item.slug or slug_for(item.name))).execution_options(include_pending_definitions=True))
            store_evolution(db, item, version, existing)
        value = {"preview_hash": digest, "published_at": manifest.published_at.isoformat(), "source_url": manifest.source_url,
                 "imported_at": datetime.now(timezone.utc).isoformat(), "sets": len(manifest.sets), "evolutions": len(manifest.evolutions)}
        if setting: setting.value = value
        else: db.add(AppSetting(key=f"content_manifest_{db.info.get('club_context_id', 1)}_{version}", value=value))
        db.add(AppSetting(key=receipt_key, value={"game_version": version, "imported_at": value["imported_at"]}))
        record(db, "import_reviewed_content", "content", None, value)
        db.commit()
        return {"preview": False, "already_imported": False, **summary}
