"""Fail closed on unknown editions/variants. HTTP review cannot certify a source."""
from datetime import timezone
from fastapi import HTTPException
from sqlalchemy import and_, exists, select
from app.models.catalog import CardVariant
from app.models.entities import Player, now

ACCEPTED = ('documented', 'provider_verified')


def variant_conditions():
    return (CardVariant.game_version == 'FC27', CardVariant.validation_status.in_(ACCEPTED),
            CardVariant.observed_at <= now(), CardVariant.valid_until > now())


def active_player_clause():
    # Correlation is explicit: joins/aliases and count queries must enforce this
    # before pagination, not remove rows after producing totals.
    return and_(Player.game_version == 'FC27', Player.validation_status.in_(ACCEPTED),
                Player.data_source != 'demo', exists(select(CardVariant.id).where(
                    *variant_conditions(), CardVariant.id == Player.catalog_variant_id,
                    CardVariant.variant_id == Player.card_id,
                    CardVariant.name == Player.name, CardVariant.rating == Player.rating,
                    CardVariant.position == Player.position, CardVariant.card_type == Player.card_type)))


def find_variant(db, variant_id):
    if not variant_id:
        return None
    return db.scalar(select(CardVariant).where(*variant_conditions(), CardVariant.variant_id == variant_id))


def active_gallery_clause():
    from app.models.entities import GalleryEntry
    snapshot = GalleryEntry.snapshot
    return and_(snapshot['game_version'].as_string() == 'FC27', snapshot['validation_status'].as_string().in_(ACCEPTED),
        exists(select(CardVariant.id).where(*variant_conditions(),
            CardVariant.variant_id == snapshot['card_id'].as_string(), CardVariant.name == snapshot['name'].as_string(),
            CardVariant.rating == snapshot['rating'].as_integer(), CardVariant.position == snapshot['position'].as_string(),
            CardVariant.card_type == snapshot['card_type'].as_string())))


def require_variant(db, variant_id):
    row = find_variant(db, variant_id)
    if row is None:
        raise HTTPException(409, 'Variante FC27 pendiente de verificación; no está disponible para cálculos u operaciones')
    return row


def check_fields(db, values, *, explicit_edition=True):
    if not explicit_edition or values.get('game_version') != 'FC27':
        return None, 'Falta una declaración explícita de edición FC27'
    if values.get('data_source') == 'demo':
        return None, 'Los datos demostrativos no pertenecen al catálogo activo'
    variant = find_variant(db, values.get('card_id'))
    if variant is None:
        return None, 'No hay evidencia vigente de esta variante exacta de FC27'
    if any(values.get(key) != getattr(variant, key) for key in ('name', 'rating', 'position', 'card_type')):
        return None, 'Nombre, media, posición o tipo no coinciden con la variante documentada'
    return variant, None


def validate_copy(db, player, *, explicit_edition=True):
    values = {key: getattr(player, key, None) for key in ('game_version', 'card_id', 'name', 'rating', 'position', 'card_type', 'data_source')}
    variant, reason = check_fields(db, values, explicit_edition=explicit_edition)
    player.validation_status = variant.validation_status if variant else 'pending_verification'
    player.catalog_variant_id = variant.id if variant else None
    player.validation_evidence = ({'source_url': variant.source_url, 'observed_at': variant.observed_at.isoformat(),
                                  'valid_until': variant.valid_until.isoformat(), 'official': variant.validation_status == 'provider_verified'}
                                 if variant else {'reason': reason, 'claimed_edition': values['game_version'] if explicit_edition else None})
    return variant is not None


def copy_result(player):
    return {'id': player.id, 'validation_status': player.validation_status,
            'quarantined': True, 'available': False, 'game_version': 'FC27',
            'message': 'Pendiente de verificación: guardada en cuarentena, fuera del club activo',
            'evidence': player.validation_evidence}


def load_documented_catalog(db):
    """Versioned, reviewed facts only. Never creates Player/Gallery/price rows."""
    import json
    from pathlib import Path
    from datetime import datetime
    root = Path(__file__).parents[1] / 'data'
    data = json.loads((root / 'fc27_variants.json').read_text(encoding='utf-8'))
    refs = {row['id']: row['url'] for row in json.loads((root / 'fc27_references.json').read_text(encoding='utf-8'))}
    for reference, variant, name, rating, position, card_type in data['items']:
        if db.scalar(select(CardVariant.id).where(CardVariant.game_version == 'FC27', CardVariant.variant_id == variant)):
            continue  # Never overwrite a later review or revocation on startup.
        db.add(CardVariant(game_version='FC27', variant_id=variant, name=name, rating=rating, position=position,
            card_type=card_type, source_url=refs[reference], observed_at=datetime.fromisoformat(data['observed_at']),
            valid_until=datetime.fromisoformat(data['valid_until']), validation_status='documented',
            evidence={'reference_id': reference, 'edition_and_item_checked': True, 'official': False, 'ownership': False}))
