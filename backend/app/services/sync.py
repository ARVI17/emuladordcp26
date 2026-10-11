"""Atomic reconciliation contract for a future authorized read adapter.

There is intentionally no network adapter or public snapshot-upload endpoint.
Only provider-verified IDs and a documented manifest may reach this function.
"""
from datetime import datetime
from pydantic import Field, model_validator
from sqlalchemy import select
from app.models.entities import Player, now
from app.models.planner import AppEntry, ClubContext, ExternalItemMapping, InventorySnapshot, LocalSession, SyncRun
from app.schemas.api import InputModel, PlayerCreate
from app.services.contexts import utc
from app.services.locks import resource_locks
from app.services.audit import record


class RemoteItem(InputModel):
    copy_id: str = Field(min_length=1, max_length=120)
    athlete_id: str = Field(min_length=1, max_length=120)
    variant_id: str = Field(min_length=1, max_length=80)
    location: str = Field(min_length=1, max_length=40)
    fields: dict


class RemoteRead(InputModel):
    provider: str
    subject: str
    club_key: str
    platform: str
    game_version: str
    revision: str = Field(min_length=1, max_length=120)
    end_revision: str
    observed_at: datetime
    coverage: dict
    pagination: dict
    items: list[RemoteItem] = Field(max_length=20000)
    coins: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def evidence(self):
        if self.observed_at.tzinfo is None or self.observed_at > now():
            raise ValueError("La observación remota exige fecha válida con zona horaria")
        if self.revision != self.end_revision:
            raise ValueError("La revisión cambió durante la lectura")
        if self.coverage.get("coins", {}).get("complete") and self.coins is None:
            raise ValueError("No hay saldo observado que respalde la cobertura de monedas")
        if self.coverage.get("inventory", {}).get("complete"):
            if not self.pagination.get("documented_end") or not self.pagination.get("all_locations"):
                raise ValueError("No hay prueba de fin de paginación y cobertura de ubicaciones")
            expected = self.pagination.get("expected_count")
            if expected is not None and expected != len({item.copy_id for item in self.items}):
                raise ValueError("El recuento remoto no coincide")
        return self


def publish_read(db, run_id: int, read: RemoteRead):
    """Caller fetched into memory outside a transaction; commit all or nothing."""
    run = db.get(SyncRun, run_id)
    if run is None:
        raise ValueError("Lectura desconocida")
    with resource_locks(db, "inventory", f"sync:{run.club_context_id}"):
        db.expire_all()
        run = db.get(SyncRun, run_id)
        context = db.get(ClubContext, run.club_context_id)
        entry = db.get(AppEntry, run.entry_id)
        session = db.get(LocalSession, entry.session_id)
        if not context.verified or run.status != "syncing" or run.generation != context.generation:
            raise ValueError("La lectura fue sustituida o carece de identidad verificada")
        if not session or utc(session.expires_at) <= now() or session.context_id != context.id or session.entry_id != entry.id:
            raise ValueError("La sesión o el contexto cambió durante la lectura")
        if (read.provider, read.subject, read.club_key, read.platform, read.game_version) != (context.provider, context.subject, context.club_key, context.platform, context.game_version):
            raise ValueError("La identidad remota no coincide")
        db.info["club_context_id"] = context.id
        db.info["remote_reconciliation"] = True
        previous = db.get(InventorySnapshot, context.snapshot_id) if context.snapshot_id else None
        if previous and read.observed_at < utc(previous.observed_at):
            raise ValueError("La observación remota es anterior a la publicada")
        unique = {}
        for item in read.items:
            old = unique.get(item.copy_id)
            if old and old != item:
                raise ValueError("Movimiento o datos ambiguos para la misma copia")
            unique[item.copy_id] = item
        # Validate everything before any mutation. Preferences never come from a provider.
        protected_fields = {"athlete_id", "notes", "favorite", "price", "protected", "starter", "usefulness", "squad_role", "duplicate_untradeable", "data_source", "data_reviewed"}
        mappings = {row.external_copy_id: row for row in db.scalars(select(ExternalItemMapping).where(ExternalItemMapping.provider == read.provider))}
        prepared = []
        for item in unique.values():
            if set(item.fields) - (set(PlayerCreate.model_fields) - protected_fields):
                raise ValueError("El proveedor incluyó campos no admitidos")
            if not {"name", "rating", "position"}.issubset(item.fields):
                raise ValueError("Cada copia requiere identidad deportiva actual; no se infiere de una lectura antigua")
            mapping = mappings.get(item.copy_id)
            player = db.get(Player, mapping.player_id) if mapping else None
            fields = {key: getattr(player, key) for key in PlayerCreate.model_fields} if player else {"league": "No disponible", "club": "No disponible", "nationality": "No disponible"}
            fields.update(item.fields)
            # An observation is not an undocumented delta. Old details remain in the
            # historical snapshot, never masquerade as newly observed current facts.
            missing_details = {"attributes": {}, "alternate_positions": [], "playstyles": [],
                               "playstyles_plus": [], "roles": {}, "skill_moves": None,
                               "weak_foot": None, "gallery_score": None}
            for key, empty in missing_details.items():
                if key not in item.fields:
                    fields[key] = empty
            fields.update(game_version=context.game_version, card_id=item.variant_id, data_source=read.provider, data_reviewed=True)
            # Omitted remote facts are unknown in this snapshot, even if history has a value.
            missing = {"tradable", "is_loan", "is_evolution"} - set(item.fields)
            fields["data_reviewed"] = not missing
            validated = PlayerCreate.model_validate(fields).model_dump()
            validated["unknown_fields"] = sorted(missing)
            prepared.append((item, mapping, player, validated))
        snapshot = InventorySnapshot(run_id=run.id, revision=read.revision, observed_at=read.observed_at,
                                     coverage=read.coverage, items=[item.model_dump(mode="json") for item in unique.values()])
        db.add(snapshot)
        db.flush()
        conflicts = []
        for item, mapping, player, fields in prepared:
            if player is None:
                player = Player(**{**fields, "athlete_id": item.athlete_id})
                db.add(player)
                db.flush()
                mapping = ExternalItemMapping(provider=read.provider, external_copy_id=item.copy_id, player_id=player.id,
                                              location=item.location, last_snapshot_id=snapshot.id)
                db.add(mapping)
            else:
                if player.athlete_id != item.athlete_id or player.consumed_by_submission_id is not None:
                    conflicts.append(player.id)
                    player.availability = "review_required"
                    continue
                # Omitted fields are preserved; new copies never inherit old preferences.
                for key in item.fields:
                    setattr(player, key, fields[key])
                for key in missing_details:
                    if key not in item.fields:
                        setattr(player, key, fields[key])
                player.card_id = item.variant_id
                player.unknown_fields = fields["unknown_fields"]
                player.data_reviewed = fields["data_reviewed"]
            mapping.location = item.location
            mapping.last_snapshot_id = snapshot.id
            mapping.available = True
            player.deleted = False
            player.availability = "available" if item.location in {"club", "sbc_storage"} else "unavailable"
        if read.coverage.get("inventory", {}).get("complete"):
            for copy_id, mapping in mappings.items():
                if copy_id not in unique:
                    player = db.get(Player, mapping.player_id)
                    mapping.available = False
                    player.availability = "absent"
                    # Absence does not invent a sale, submission, or discard.
                    if player.protected or player.starter or player.favorite or player.is_evolution:
                        conflicts.append(player.id)
        if read.coverage.get("coins", {}).get("complete") and read.coins is not None:
            context.coins = read.coins
        context.snapshot_id = snapshot.id
        entry.snapshot_id = snapshot.id
        entry.status = "review_required" if conflicts else "ready" if read.coverage.get("inventory", {}).get("complete") else "partial"
        run.status = entry.status
        run.finished_at = now()
        run.manifest = {"pagination": read.pagination, "coverage": read.coverage, "conflicts": conflicts, "revision": read.revision, "count": len(unique)}
        record(db, "publish_snapshot", "inventory_snapshot", snapshot.id, {"count": len(unique), "conflicts": len(conflicts)})
        db.commit()
        return snapshot
