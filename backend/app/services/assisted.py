"""Deliberate OCR and reviewed ownership. Visual evidence is never EA authentication."""
import hashlib
import io
import json
import re
from copy import deepcopy
from datetime import timedelta
from fastapi import HTTPException
from sqlalchemy import and_, exists, select
from app.models.assisted import CaptureSession, VisualReading, VisualCopy
from app.models.entities import Player, Objective, now
from app.services.contexts import utc
from app.services.import_export import _plain, extract_inventory_candidates, ocr_image, validate_image, review_dcp_requirements
from app.services.main_squad import fingerprint

IDENTITY = ('name', 'rating', 'position', 'card_type')
FACTS = ('name', 'rating', 'position', 'card_type', 'league', 'club', 'nationality', 'is_loan',
         'is_evolution', 'tradable', 'rare', 'special', 'alternate_positions', 'attributes',
         'is_holographic', 'gallery_score', 'skill_moves', 'weak_foot')
UNKNOWN = ('chemistry', 'playstyles', 'playstyles_plus', 'roles', 'base_card_id')
SENSITIVE = re.compile(r'password|contrase[nñ]a|iniciar sesi[oó]n|sign in|log in|verification code|c[oó]digo de (?:seguridad|verificaci[oó]n)|autenticaci[oó]n|@\w+[.]|access[_ -]?token|bearer\s', re.I)


def safe_text(value):
    if SENSITIVE.search(value):
        raise HTTPException(422, 'Contenido sensible detectado. Borra la captura y selecciona otra pantalla.')
    return value


def require_assisted(db):
    context, session = db.info['context'], db.info['local_session']
    if context.provider != 'visual_assisted' or context.verified or session.mode != 'assisted':
        raise HTTPException(409, 'Abre un contexto de lectura asistida para esta operación.')
    return context


def visual_copy_clause():
    evidence = Player.validation_evidence
    return and_(Player.validation_status == 'visual_reviewed', evidence['kind'].as_string() == 'visual_copy',
        exists(select(VisualCopy.id).join(VisualReading, VisualReading.id == VisualCopy.reading_id).where(
            VisualCopy.id == evidence['visual_copy_id'].as_integer(), VisualCopy.player_id == Player.id,
            VisualCopy.club_context_id == Player.club_context_id, VisualReading.club_context_id == Player.club_context_id,
            VisualReading.status == 'reviewed', VisualReading.reviewed['edition'].as_string() == 'FC27',
            VisualCopy.state.in_(['reviewed', 'ambiguous']),
            *(getattr(Player, key) == (VisualCopy.facts[key].as_integer() if key == 'rating' else VisualCopy.facts[key].as_string()) for key in IDENTITY))))


def identity_key(card):
    return fingerprint([_plain(str(card.get(key) or '')).strip() for key in IDENTITY])


def ambiguity_key(card):
    # Translated/unknown variant labels do not prove that two visual copies differ.
    return fingerprint([_plain(str(card.get(key) or '')).strip() for key in IDENTITY[:3]])


def capture_row(db, identifier, *, active=True):
    row = db.scalar(select(CaptureSession).where(CaptureSession.id == identifier))
    if not row:
        raise HTTPException(404, 'Sesión de captura no disponible')
    if active and (row.status != 'active' or utc(row.expires_at) <= now() or row.entry_id != db.info['local_session'].entry_id):
        raise HTTPException(409, 'La captura terminó, caducó o cambió la cuenta. Selecciona la pestaña otra vez.')
    return row


def reading_row(db, identifier):
    row = db.scalar(select(VisualReading).where(VisualReading.id == identifier))
    if not row:
        raise HTTPException(404, 'Lectura no disponible en este contexto')
    return row


def reading_data(row, *, detail=True):
    return dict(id=row.id, session_id=row.session_id, scope=row.scope, page=row.page, filters=row.filters,
        status=row.status, observed_at=row.observed_at, reviewed_at=row.reviewed_at,
        original=row.original if detail else None, reviewed=row.reviewed if detail else None,
        source='visual_assisted', provider_verified=False, image_retained=False)


def erase_draft(row):
    row.original, row.status = {}, 'erased'
    row.frame_hash = fingerprint(['erased', row.id, row.frame_hash])


def parse_screen(text, scope):
    """No raw login text reaches a response or persistent row, even on failure."""
    if SENSITIVE.search(text):
        return None
    plain = _plain(text)
    if re.search(r'\bfc\s*2[0-689]\b', plain):
        return None
    recognizable = re.search(r'\bfc\s*27\b|ultimate team|futb[.]? de mi club|\b(?:mi club|plantilla|objetivos|squad battles|rivals|monedas|sin asignar|dcp)\b', plain)
    if not recognizable:
        return None
    # OCR often confuses capital I and lowercase l. Keep the original and require review.
    uncertain_positions = {}
    def normalize_position(match):
        uncertain_positions[(int(match[1]), match[3].strip())] = match[2]
        return f'{match[1]} EI {match[3]}'
    normalized = re.sub(r'^([4-9][0-9])\s+(El|EL)\s+([^\n]+)$', normalize_position, text, flags=re.M)
    cards = extract_inventory_candidates(normalized)
    for card in cards:
        original = uncertain_positions.get((card['rating'], card['name']))
        if original and card['position'] == 'EI':
            card.update(original_position=original, warning='OCR leyó El/EL: comprueba si la posición visible es EI.')
            card['confidence']['position'] = 0.45
    for n, card in enumerate(cards):
        card.update(ordinal=n, card_type=None, league=None, club=None, nationality=None, is_loan=None,
                    is_evolution=None, tradable=None, rare=None, special=None, location='unknown', slot=None)
    def labeled(pattern):
        match = re.search(pattern, text, re.I | re.M)
        return match.group(1).strip() if match else None
    coin_text = labeled(r'(?:monedas|coins)\s*[:\s]\s*([\d., ]+)')
    coins = int(re.sub(r'\D', '', coin_text)) if coin_text and re.sub(r'\D', '', coin_text) else None
    if coins is not None and coins > 2_000_000_000:
        coins = None
    unassigned = {}
    if 'sin asignar' in plain:
        for kind,label in [('players','jugadores'),('packs','sobres'),('consumables','consumibles'),('other','otros')]:
            match = re.search(rf'\b{label}\s*:\s*(\d{{1,5}})\b', plain)
            if match:
                unassigned[kind] = int(match.group(1))
    if len(cards) == 1:
        attributes = {}
        for key,label in [('pace','rit'),('shooting','tir'),('passing','pas'),('dribbling','reg'),('defending','def'),('physical','fis')]:
            match = re.search(rf'\b{label}\s*:?\s*(\d{{1,2}})\b', plain)
            if match:
                attributes[key] = int(match.group(1))
        cards[0]['attributes'] = attributes or None
    return dict(cards=cards, edition='FC27' if re.search(r'\bfc\s*27\b', plain) else None,
        club_name=labeled(r'^(?:nombre del club|club name)\s*:\s*(.{1,100})$'), coins=coins,
        unassigned=unassigned or None, formation=labeled(r'(?:formacion|formación|formation)\s*:\s*([\d-]{3,20})'),
        objective_text=text[:5000] if scope in {'objective','dcp'} else None,
        dcp_draft=review_dcp_requirements(text) if scope == 'dcp' else None,
        confidence='requires_review', origin_authenticated=False)


def reusable_reading(db, row, session):
    if row and row.status == 'pending' and row.session_id != session.id:
        # Re-sharing grants a new deliberate reading; an unreviewable old draft must
        # not trap the same frame forever. Reviewed evidence keeps its original date.
        old = db.get(CaptureSession, row.session_id)
        if old.status != 'active' or utc(old.expires_at) <= now() or old.entry_id != session.entry_id:
            erase_draft(row)
            db.flush()
            return None
    return row


def read_frame(db, session, content, scope, page, filters, region=None):
    validate_image(content)
    safe_text(page + ' ' + filters)
    digest = hashlib.sha256(content + (region or '').encode()).hexdigest()
    previous = db.scalar(select(VisualReading).where(VisualReading.frame_hash == digest, VisualReading.scope == scope, VisualReading.page == page))
    previous = reusable_reading(db, previous, session)
    if previous:
        return dict(**reading_data(previous), repeated=True)
    count = len(list(db.scalars(select(VisualReading.id).where(VisualReading.session_id == session.id))))
    if count >= 50:
        raise HTTPException(409, 'Esta sesión alcanzó 50 páginas. Revisa las lecturas y comienza otra sesión.')
    result = parse_screen(ocr_image(content)['raw_text'], scope)
    browser_session = db.info['local_session']
    db.refresh(browser_session)
    if browser_session.context_id != session.club_context_id or browser_session.entry_id != session.entry_id:
        raise HTTPException(409, 'La cuenta o entrada cambió durante la lectura; se descartó el fotograma.')
    if result is None:
        session.status = 'blocked'
        db.commit()  # Do not store pixels, OCR text or candidate facts from this frame.
        return dict(blocked=True, stop_capture=True, reason='Pantalla ajena, sensible, de otra edición o ilegible. Selecciona otra pantalla.', image_retained=False)
    if region:
        # Safety detection examines the full image first; cropping cannot bypass it.
        from PIL import Image
        try:
            rect = json.loads(region)
            if len(rect) != 4 or any(type(v) not in (int,float) for v in rect):
                raise ValueError()
            x,y,w,h = rect
            if not (0 <= x < 100 and 0 <= y < 100 and 1 <= w <= 100-x and 1 <= h <= 100-y):
                raise ValueError()
            with Image.open(io.BytesIO(content)) as image:
                width,height = image.size
                cropped = image.crop((int(width*x/100),int(height*y/100),int(width*(x+w)/100),int(height*(y+h)/100)))
                temporary = io.BytesIO()
                cropped.save(temporary,format='PNG')
            region_text = ocr_image(temporary.getvalue())['raw_text']
            if SENSITIVE.search(region_text):
                session.status = 'blocked'
                db.commit()
                return dict(blocked=True,stop_capture=True,reason='Pantalla sensible detectada. Selecciona otra pestaña.',image_retained=False)
            region_result = parse_screen('FC27 Mi club\n'+region_text, 'inventory')
            if region_result is None:
                raise ValueError('Region is not an FC27 inventory view')
            result['cards'] = region_result['cards']
            result['region_percent'] = rect
        except (ValueError, TypeError, KeyError, OSError):
            raise HTTPException(422, 'Revisa la región: izquierda, arriba, ancho y alto entre 0 y 100 %.') from None
    # Duplicate normalized pages are also detected when the clock/cursor changes pixels.
    semantic = fingerprint(dict(cards=result['cards'], scope=scope, page=page, filters=filters,
        objective=result['objective_text'], coins=result['coins'], club_name=result['club_name'], formation=result['formation']))
    previous = db.scalar(select(VisualReading).where(VisualReading.original['semantic_hash'].as_string() == semantic))
    previous = reusable_reading(db, previous, session)
    if previous:
        return dict(**reading_data(previous), repeated=True)
    result['semantic_hash'] = semantic
    row = VisualReading(session_id=session.id, frame_hash=digest, scope=scope, page=page, filters=filters, original=result)
    db.add(row)
    db.flush()
    return dict(**reading_data(row), repeated=False)


def save_reading(db, row, payload):
    if row.status == 'reviewed':
        if row.reviewed.get('request_hash') != fingerprint(payload.model_dump(mode='json')):
            raise HTTPException(409, 'La lectura ya fue revisada. Crea otra observación para registrar cambios.')
        return reading_data(row)
    if row.status != 'pending':
        raise HTTPException(409, 'Esta lectura fue borrada. Lee otra vez la pantalla.')
    capture_row(db, row.session_id)
    if now()-utc(row.observed_at) > timedelta(minutes=30):
        raise HTTPException(409, 'La lectura caducó para revisión. Lee otra vez la pantalla.')
    safe_text(str(payload.model_dump()))
    original = row.original
    original_cards = {c['ordinal']: c for c in original.get('cards', [])}
    if any(c.ordinal not in original_cards for c in payload.cards):
        raise HTTPException(422, 'Solo se revisan candidatas extraídas de esta imagen; lee una región más clara.')
    if payload.objective and (row.scope != 'objective' or not original.get('objective_text')):
        raise HTTPException(422, 'Se necesita una lectura de objetivo para revisar sus reglas.')
    if payload.dcp and (row.scope != 'dcp' or not original.get('objective_text')):
        raise HTTPException(422, 'Se necesita una lectura de DCP para revisar sus reglas.')
    # Explicit account label changes require another isolated context; no mixed club.
    previous_name = db.scalar(select(VisualReading).where(VisualReading.status == 'reviewed', VisualReading.reviewed['club_name'].as_string().is_not(None)).order_by(VisualReading.id.desc()))
    if payload.club_name and previous_name and _plain(payload.club_name) != _plain(previous_name.reviewed['club_name']):
        raise HTTPException(409, 'Cambió el nombre del club observado. Abre otro contexto antes de guardar; no se mezclaron datos.')
    reviewed = payload.model_dump(mode='json')
    reviewed.update(request_hash=fingerprint(reviewed), copy_ids=[], objective_id=None, source='user_reviewed_visual', provider_verified=False)
    row.status, row.reviewed_at, row.reviewed = 'reviewed', now(), deepcopy(reviewed)
    if row.scope == 'result':
        # Result checks compare evidence. They do not replace inventory or infer consumption.
        return reading_data(row)
    db.info['visual_reconciliation'] = True
    for card in payload.cards:
        facts = {key: getattr(card, key) for key in FACTS}
        key = ambiguity_key(facts)
        if card.existing_player_id:
            p = db.scalar(select(Player).where(Player.id == card.existing_player_id).execution_options(include_quarantine=True))
            if not p or p.deleted or p.validation_evidence.get('kind') != 'visual_copy' or ambiguity_key(p.validation_evidence['identity']) != key:
                raise HTTPException(409, 'La copia seleccionada cambió, está consumida o no coincide. No se resucitó ninguna carta.')
            if p.card_type and card.card_type and _plain(p.card_type) != _plain(card.card_type):
                raise HTTPException(409, 'La variante cambió. Guarda una candidata pendiente y revisa la distinción de copias.')
            # Reobservations may enrich known metadata but never silently resolve duplicate identity.
        else:
            p = Player(game_version='FC27', data_source='visual_assisted', data_reviewed=True,
                name=card.name, rating=card.rating, position=card.position, league='', club='', nationality='',
                card_type=card.card_type or '', card_id=None, athlete_id=None)
            db.add(p)
        for field, value in facts.items():
            if value is not None:
                setattr(p, field, value)
        p.validation_status = 'visual_reviewed'
        p.unknown_fields = sorted([field for field, value in facts.items() if value is None] + list(UNKNOWN) + ['card_id', 'athlete_id'])
        db.flush()
        copy = VisualCopy(reading_id=row.id, ordinal=card.ordinal, player_id=p.id, identity_key=key,
            facts={**facts, 'card_type': p.card_type}, resolution={})
        db.add(copy)
        db.flush()
        p.validation_evidence = dict(kind='visual_copy', visual_copy_id=copy.id, reading_id=row.id,
            session_id=row.session_id, observed_at=utc(row.observed_at).isoformat(), reviewed_at=now().isoformat(),
            identity={k: getattr(p, k) for k in IDENTITY}, observed_fields=[k for k,v in facts.items() if v is not None],
            location=card.location, ea_copy_id=None, provider_verified=False)
        reviewed['copy_ids'].append(p.id)
        others = list(db.scalars(select(VisualCopy).where(VisualCopy.identity_key == key, VisualCopy.player_id != p.id, VisualCopy.state != 'merged')))
        if others:
            copy.state = 'ambiguous'
            p.availability = 'review_required'
            for other in others:
                other.state = 'ambiguous'
                old = db.scalar(select(Player).where(Player.id == other.player_id).execution_options(include_quarantine=True))
                if old and not old.deleted:
                    # A newly ambiguous protected copy retains its lock and triggers a review warning.
                    old.availability = 'review_required'
        db.flush()
    if payload.objective:
        from app.api.objective_planning import apply_rules
        goal = Objective(game_version='FC27', progress=0, progress_evidence={})
        apply_rules(db, goal, payload.objective)
        db.add(goal)
        db.flush()
        goal.validation_evidence = dict(kind='visual_rule_draft', reading_id=row.id, reviewed_at=now().isoformat(), official=False)
        reviewed['objective_id'] = goal.id
    row.reviewed = dict(reviewed)
    if row.scope == 'squad':
        from app.services.main_squad import state_row
        main = state_row(db)
        if main:
            expected = {m['player_id']:m['slot'] for m in main.snapshot['members']}
            changed = any(c.slot and pid in expected and c.slot != expected[pid] for c,pid in zip(payload.cards,reviewed['copy_ids']))
            changed = changed or bool(payload.formation and payload.formation != main.snapshot['formation'])
            if changed:
                main.history = [*main.history[-19:],dict(snapshot=main.snapshot,revision=main.revision,reading_id=row.id)]
                main.snapshot = {**main.snapshot,'needs_review':True,'discrepancy_reading_id':row.id}
                main.revision += 1
    db.info['context'].revision += 1
    return reading_data(row)


def resolve_copies(db, payload):
    ids = set(payload.player_ids)
    if len(ids) != len(payload.player_ids):
        raise HTTPException(422, 'No repitas copias')
    copies = list(db.scalars(select(VisualCopy).where(VisualCopy.player_id.in_(ids), VisualCopy.state != 'merged')))
    if {c.player_id for c in copies} != ids or len({c.identity_key for c in copies}) != 1:
        raise HTTPException(409, 'Selecciona copias visualmente ambiguas del mismo grupo')
    group = list(db.scalars(select(VisualCopy).where(VisualCopy.identity_key == copies[0].identity_key, VisualCopy.state != 'merged')))
    if {c.player_id for c in group} != ids:
        raise HTTPException(409, 'Revisa todas las copias de este grupo ambiguo')
    from app.services.squad_analysis import effective_protected_ids
    from app.services.protection import reserved_ids
    if ids & reserved_ids(db):
        raise HTTPException(409, 'Una copia está reservada; revisa el plan antes de resolver el grupo')
    protected = effective_protected_ids(db)
    if payload.decision == 'same_copy' and (payload.keep_player_id not in ids or (ids - {payload.keep_player_id}) & protected):
        raise HTTPException(409, 'Conserva la copia protegida; no se pueden fusionar varias copias protegidas')
    db.info['visual_reconciliation'] = True
    for copy in group:
        p = db.scalar(select(Player).where(Player.id == copy.player_id).execution_options(include_quarantine=True))
        if p.deleted:
            raise HTTPException(409, 'El grupo incluye una copia retirada; no se puede reactivar desde una lectura anterior')
        keep = payload.decision == 'distinct_copies' or copy.player_id == payload.keep_player_id
        copy.state = 'reviewed' if keep else 'merged'
        copy.resolution = dict(decision=payload.decision, note=safe_text(payload.note), at=now().isoformat(), user_declared=True)
        p.availability = 'available' if keep else 'review_required'
    db.info['context'].revision += 1
    return dict(resolved=True, provider_verified=False)


def ambiguous_protections(db, ids):
    # Even an unresolved duplicate of a favorite/main/reserved copy inherits consumption exclusion.
    keys = select(VisualCopy.identity_key).where(VisualCopy.player_id.in_(ids), VisualCopy.state == 'ambiguous')
    return set(db.scalars(select(VisualCopy.player_id).where(VisualCopy.identity_key.in_(keys), VisualCopy.state == 'ambiguous')))


def coverage(db):
    rows = list(db.scalars(select(VisualReading).order_by(VisualReading.id.desc()).limit(1000)))
    conflicts = list(db.scalars(select(VisualCopy).where(VisualCopy.state == 'ambiguous')))
    return dict(pages_observed=len(rows), pages_reviewed=sum(r.status == 'reviewed' for r in rows),
        complete=False, pending_locations=['club', 'unassigned', 'sbc_storage', 'transfer_list'],
        filters=sorted({r.filters for r in rows if r.filters}),
        conflicts=[dict(player_id=c.player_id, group=c.identity_key, reading_id=c.reading_id) for c in conflicts],
        message='Cobertura parcial de las pantallas compartidas. Terminar una sesión no demuestra inventario completo.')
