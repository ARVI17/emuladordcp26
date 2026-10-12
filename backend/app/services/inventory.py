import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import InventoryScan, Player


def normalized_text(value: object) -> str:
    plain = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", " ", plain).strip()


def inventory_identity(name: object, rating: object, position: object) -> tuple[str, int | None, str]:
    try:
        parsed_rating = int(rating) if rating is not None else None
    except (TypeError, ValueError):
        parsed_rating = None
    return normalized_text(name), parsed_rating, normalized_text(position)


def candidate_identity(candidate: dict) -> tuple[str, int | None, str]:
    return inventory_identity(candidate.get("name"), candidate.get("rating"), candidate.get("position"))


def player_identity(player: Player) -> tuple[str, int | None, str]:
    return inventory_identity(player.name, player.rating, player.position)


def complete_candidate(candidate: dict) -> bool:
    name, rating, position = candidate_identity(candidate)
    return bool(name and position and rating is not None and 1 <= rating <= 99)


def all_player_identities(db: Session) -> set[tuple[str, int | None, str]]:
    # Incluye cartas eliminadas para que una lectura vieja no resucite una carta ya usada en un DCP.
    return {player_identity(player) for player in db.scalars(select(Player)).all()}


def open_inventory_scans(db: Session) -> list[InventoryScan]:
    return list(db.scalars(
        select(InventoryScan)
        .where(InventoryScan.status.in_(("scanning", "review")))
        .order_by(InventoryScan.id)
    ).all())


def pending_identities(db: Session, exclude_scan_id: int | None = None) -> set[tuple[str, int | None, str]]:
    identities: set[tuple[str, int | None, str]] = set()
    for scan in open_inventory_scans(db):
        if scan.id == exclude_scan_id:
            continue
        identities.update(candidate_identity(candidate) for candidate in (scan.candidates or []) if complete_candidate(candidate))
    return identities


def unique_new_candidates(db: Session, candidates: list[dict], scan_id: int) -> tuple[list[dict], int]:
    blocked = all_player_identities(db) | pending_identities(db, exclude_scan_id=scan_id)
    current_scan = db.get(InventoryScan, scan_id)
    if current_scan:
        blocked.update(candidate_identity(candidate) for candidate in (current_scan.candidates or []) if complete_candidate(candidate))
    accepted: list[dict] = []
    skipped = 0
    for candidate in candidates:
        identity = candidate_identity(candidate)
        if not complete_candidate(candidate) or identity in blocked:
            skipped += 1
            continue
        blocked.add(identity)
        accepted.append(candidate)
    return accepted, skipped


def remove_pending_identities(db: Session, identities: set[tuple[str, int | None, str]], exclude_scan_id: int | None = None) -> int:
    removed = 0
    if not identities:
        return removed
    for scan in open_inventory_scans(db):
        if scan.id == exclude_scan_id:
            continue
        current = list(scan.candidates or [])
        remaining = [candidate for candidate in current if candidate_identity(candidate) not in identities]
        if len(remaining) == len(current):
            continue
        removed += len(current) - len(remaining)
        scan.candidates = remaining
        scan.candidate_count = len(remaining)
        if not remaining and scan.imported_count:
            scan.status = "imported"
    return removed


def bulk_inventory_preview(db: Session) -> tuple[dict, list[tuple[InventoryScan, dict, tuple[str, int | None, str]]]]:
    scans = open_inventory_scans(db)
    existing = all_player_identities(db)
    seen: set[tuple[str, int | None, str]] = set()
    importable: list[tuple[InventoryScan, dict, tuple[str, int | None, str]]] = []
    total = duplicate = existing_match = incomplete = 0
    for scan in scans:
        for candidate in list(scan.candidates or []):
            total += 1
            identity = candidate_identity(candidate)
            if not complete_candidate(candidate):
                incomplete += 1
            elif identity in existing:
                existing_match += 1
            elif identity in seen:
                duplicate += 1
            else:
                seen.add(identity)
                importable.append((scan, candidate, identity))
    return {
        "scan_ids": [scan.id for scan in scans],
        "sessions": len(scans),
        "detected": total,
        "unique_new": len(importable),
        "duplicates": duplicate,
        "already_registered_or_used": existing_match,
        "incomplete": incomplete,
        "confirmation_phrase": "IMPORTAR TODO EL CLUB",
        "requires_review": True,
        "fields_from_companion": ["name", "rating", "position"],
    }, importable
