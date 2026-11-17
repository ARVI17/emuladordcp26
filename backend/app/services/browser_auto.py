"""User-authorized, partial visible DOM observations. Never provider authentication."""
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy import select
from app.models.assisted import CaptureSession, VisualReading
from app.models.entities import Player, Squad, SquadPlayer, now
from app.models.reader import BrowserAutoLink
from app.schemas.assisted import ReadingReview, ReviewedCard
from app.services.assisted import ambiguity_key, save_reading, safe_text, FACTS
from app.services.contexts import utc
from app.services.main_squad import fingerprint, main_status, select_main, state_row

MESSAGES = {
    'disabled': 'Actualización automática desactivada.',
    'ready': 'Se actualizará al abrir Club Lab.',
    'reading': 'Leyendo el club y la plantilla activa en Chrome…',
    'updated': 'Lectura actualizada; principal y suplentes protegidos.',
    'partial': 'Lectura parcial conservada. Hay datos o copias pendientes.',
    'login_required': 'Entra de nuevo en EA. Se conserva la última lectura.',
    'permission_required': 'La extensión necesita permiso para la pestaña oficial de EA.',
    'page_changed': 'La vista cambió o contiene datos ambiguos. Se conserva la última lectura.',
    'cancelled': 'Lectura detenida; datos y protecciones conservados.',
    'reader_unavailable': 'La extensión local no está disponible en este Chrome.',
    'timeout': 'La lectura no terminó a tiempo. Se conserva la última lectura.',
}


def link_row(db):
    return db.scalar(select(BrowserAutoLink))


def status(row):
    if not row:
        return dict(enabled=False, status='disabled', message=MESSAGES['disabled'], result={}, extension_id=None)
    current = row.status
    if current == 'reading' and now()-utc(row.requested_at) > timedelta(minutes=5):
        current = 'timeout'
    return dict(enabled=row.enabled, status=current, message=MESSAGES[current], result=row.result,
        extension_id=row.extension_id, request_id=row.request_id, provider_verified=False,
        inventory_complete=False, protect_main=row.protect_main)


def require_run(db, grant, request_id):
    row = link_row(db)
    if (not row or not row.enabled or row.grant_id != grant.id or row.extension_id != grant.extension_id
            or row.request_id != str(request_id) or not row.requested_at
            or now()-utc(row.requested_at) > timedelta(minutes=5)):
        raise HTTPException(409, 'Lectura detenida, sustituida o caducada; abre la aplicación de nuevo.')
    return row


def publish(db, link, payload):
    digest = fingerprint(payload.model_dump(mode='json'))
    if link.result.get('request_id') == str(payload.request_id):
        if link.result.get('payload_hash') != digest:
            raise HTTPException(409, 'El recibo de lectura no puede cambiar.')
        return status(link)
    if link.status != 'reading':
        raise HTTPException(409, 'La lectura ya terminó o fue cancelada.')
    if not -timedelta(seconds=30) <= now()-utc(payload.observed_at) <= timedelta(minutes=5):
        raise HTTPException(409, 'Fecha de lectura no vigente.')
    if link.club_fingerprint and link.club_fingerprint != payload.club_fingerprint:
        raise HTTPException(409, 'Cambió el club en EA. No se mezclaron cuentas; utiliza otro contexto.')
    safe_text(str(payload.model_dump()))
    existing = defaultdict(list)
    for player in db.scalars(select(Player).execution_options(include_quarantine=True)):
        existing[ambiguity_key(dict(name=player.name, rating=player.rating, position=player.position))].append(player)
    session = CaptureSession(entry_id=db.info['local_session'].entry_id, source='browser_auto',
        expires_at=now()+timedelta(minutes=10))
    db.add(session)
    db.flush()
    readings, ids_by_scope, pending = [], {}, []
    for scope, records in [('inventory', payload.inventory), ('squad', payload.squad)]:
        counts = Counter(ambiguity_key(c.model_dump()) for c in records)
        accepted = []
        for card in records:
            facts = card.model_dump()
            key, matches = ambiguity_key(facts), existing[ambiguity_key(facts)]
            reason = None
            if counts[key] != 1 or len(matches) > 1:
                reason = 'indistinguishable_copies'
            elif not all(facts.get(f) for f in ('card_type','league','club','nationality','attributes')):
                reason = 'identity_fields_missing'
            elif matches:
                player = matches[0]
                evidence = player.validation_evidence or {}
                if player.deleted or player.availability != 'available' or evidence.get('kind') != 'visual_copy':
                    reason = 'copy_unavailable'
                elif any(facts.get(k) is not None and k in evidence.get('observed_fields', [])
                         and getattr(player, k) not in (None, '', [], {}) and getattr(player, k) != facts[k]
                         for k in FACTS):
                    reason = 'known_facts_changed'
                elif evidence.get('source_kind') in {'synthetic_dom','user_export_dom'}:
                    reason = 'source_mismatch'
                elif utc(payload.observed_at) < utc(datetime.fromisoformat(evidence['observed_at'])):
                    reason = 'older_observation'
                else:
                    facts['existing_player_id'] = player.id
            if reason:
                pending.append(dict(scope=scope, ordinal=card.ordinal, reason=reason))
                continue
            accepted.append(ReviewedCard.model_validate(facts))
        reading = VisualReading(session_id=session.id, frame_hash=fingerprint([str(payload.request_id),scope]),
            scope=scope, page='browser-auto-'+scope, filters='Primeras veinte; cobertura parcial',
            original=dict(cards=[c.model_dump() for c in accepted], source_kind='browser_auto',
                reader_version='ea-visible-1', request_id=str(payload.request_id), automatic_consent=True),
            observed_at=payload.observed_at)
        db.add(reading)
        db.flush()
        save_reading(db, reading, ReadingReview(phrase='GUARDAR OBSERVACION', edition='FC27', cards=accepted,
            club_name=payload.club_name, formation=payload.formation if scope == 'squad' else None))
        reading.reviewed = {**reading.reviewed, 'source':'user_authorized_browser', 'ownership_confirmed':True}
        readings.append(reading.id)
        ids_by_scope[scope] = reading.reviewed['copy_ids']
        for identifier, card in zip(reading.reviewed['copy_ids'], accepted):
            player = db.get(Player, identifier)
            player.validation_evidence = {**player.validation_evidence, 'source_kind':'browser_auto',
                'review_method':'owner_authorized_auto', 'identity_method':'unique_visible_signature',
                'automatic_link_id':link.id, 'request_id':str(payload.request_id)}
            key = ambiguity_key(card.model_dump())
            if not existing[key]: existing[key].append(player)
        db.flush()
    main = main_status(db)
    main_current = False
    squad_reading = db.get(VisualReading, readings[-1])
    members = [dict(player_id=i, slot=c['slot']) for i,c in zip(ids_by_scope['squad'], squad_reading.reviewed['cards'])]
    starters = [m for m in members if not m['slot'].startswith(('BENCH-','RESERVE-'))]
    bench = [m for m in members if m['slot'].startswith('BENCH-')]
    if link.protect_main and payload.active_squad_observed and len(starters)==11 and len(bench)==7 and not any(p['scope']=='squad' for p in pending):
        same = main['snapshot'] and main['snapshot']['formation']==payload.formation and sorted(main['snapshot']['members'],key=lambda m:m['slot'])==sorted(members,key=lambda m:m['slot'])
        if not same:
            squad = Squad(name='Principal observada en Chrome', formation=payload.formation, game_version='FC27', origin='manual')
            db.add(squad)
            db.flush()
            for member in members: db.add(SquadPlayer(squad_id=squad.id, **member))
            db.flush()
            main = select_main(db, squad, expected_hash=main['state_hash'], complete=True)
        row = state_row(db)
        row.snapshot = {**row.snapshot, 'source':'user_authorized_browser', 'reading_ids':[readings[-1]],
            'active_view_observed':True, 'ea_active_squad':None, 'local_lock_only':True, 'needs_review':False}
        main = main_status(db)
        main_current = main['complete']
    link.club_fingerprint = payload.club_fingerprint
    link.status = 'updated' if len(ids_by_scope['inventory'])==20 and main_current and not pending else 'partial'
    link.updated_at = now()
    link.result = dict(request_id=str(payload.request_id), payload_hash=digest,
        observed_at=payload.observed_at.isoformat(), received_at=now().isoformat(), reading_ids=readings,
        inventory_ids=ids_by_scope['inventory'], squad_ids=ids_by_scope['squad'], pending=pending,
        main_complete=main_current, protected_copy_ids=main['protected_copy_ids'],
        source='user_authorized_browser', provider_verified=False, inventory_complete=False)
    return status(link)
