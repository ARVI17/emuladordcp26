"""Bounded transcription of visible cards, never an authenticated EA extractor."""
import re
from datetime import timedelta
from fastapi import HTTPException
from sqlalchemy import select
from app.models.assisted import CaptureSession, VisualReading
from app.models.entities import now
from app.services.assisted import safe_text, reading_data, erase_draft
from app.services.contexts import utc
from app.services.import_export import extract_inventory_candidates
from app.services.main_squad import fingerprint

STATS = dict(zip('PAC SHO PAS DRI DEF PHY DIV HAN KIC REF SPD POS'.split(),
    'pace shooting passing dribbling defending physical diving handling kicking reflexes speed positioning'.split()))
STATS.update(dict(zip('RIT TIR REG FIS FÍS SAL PAR SAQ VEL'.split(),
    'pace shooting dribbling physical physical diving handling kicking speed'.split())))


def parse_card_text(text):
    safe_text(text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not 1 <= len(lines) <= 30:
        raise HTTPException(422, 'Introduce entre 1 y 30 cartas, una por línea.')
    cards = []
    for ordinal, line in enumerate(lines):
        parts = line.split('|')
        values = extract_inventory_candidates(parts[0])
        name = re.split(r'\s+', parts[0].strip(), maxsplit=2)[-1]
        if len(parts) > 2 or len(values) != 1 or len(name) > 100:
            raise HTTPException(422, f'Revisa la línea {ordinal+1}: usa MEDIA POSICIÓN NOMBRE.')
        card = values[0]
        card.pop('source_page')
        card.pop('confidence')
        attributes = None
        if len(parts) == 2:
            tokens = parts[1].upper().split()
            if not tokens or len(tokens) % 2 or any(k not in STATS or not re.fullmatch(r'\d{1,2}', v) for k,v in zip(tokens[::2], tokens[1::2])):
                raise HTTPException(422, f'Revisa los atributos de la línea {ordinal+1}.')
            attributes = {STATS[k]: int(v) for k,v in zip(tokens[::2], tokens[1::2])}
            allowed = {'diving','handling','kicking','reflexes','speed','positioning'} if card['position'] == 'POR' else {'pace','shooting','passing','dribbling','defending','physical'}
            if len(attributes) != len(tokens)//2 or not attributes.keys() <= allowed:
                raise HTTPException(422, f'Los atributos de la línea {ordinal+1} están repetidos o no corresponden a su posición.')
        card.update(ordinal=ordinal, attributes=attributes, card_type=None, league=None, club=None,
            nationality=None, is_loan=None, is_evolution=None, tradable=None, rare=None, special=None,
            location='unknown', slot=None)
        cards.append(card)
    return cards


def preview_text(db, payload):
    cards = parse_card_text(payload.text)
    safe_text(payload.page)
    digest = fingerprint(['browser_text', cards, payload.page])
    previous = db.scalar(select(VisualReading).where(VisualReading.frame_hash == digest,
        VisualReading.scope == 'inventory', VisualReading.page == payload.page))
    if previous and previous.status == 'pending':
        session = db.get(CaptureSession, previous.session_id)
        if session.entry_id != db.info['local_session'].entry_id or session.status != 'active' or utc(session.expires_at) <= now():
            erase_draft(previous)
            db.flush()
            previous = None
    if previous:
        return dict(**reading_data(previous), repeated=True)
    from app.core.config import settings
    threshold = now()-timedelta(minutes=settings.assisted_draft_retention_minutes)
    pending = list(db.scalars(select(VisualReading).where(VisualReading.status == 'pending')))
    for draft in pending:
        if utc(draft.observed_at) < threshold:
            erase_draft(draft)
    if sum(d.status == 'pending' for d in pending) >= 50:
        raise HTTPException(409, 'Revisa o borra los borradores pendientes antes de continuar.')
    session = CaptureSession(entry_id=db.info['local_session'].entry_id, source='browser_text', expires_at=now()+timedelta(minutes=30))
    db.add(session)
    db.flush()
    row = VisualReading(session_id=session.id, frame_hash=digest, scope='inventory', page=payload.page,
        filters='', original=dict(cards=cards, source_kind='browser_text', edition=None,
        origin_authenticated=False, requires_review=True), reviewed={})
    db.add(row)
    db.flush()
    return dict(**reading_data(row), repeated=False)
