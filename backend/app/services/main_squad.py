"""Copy-level consumption locks; playing in an alternative never consumes a copy."""
import hashlib
import json
from fastapi import HTTPException
from sqlalchemy import select
from app.models.entities import Player, Squad, SquadPlayer, now
from app.models.squad_safety import MainSquadState


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(',', ':')).encode()).hexdigest()


def state_row(db):
    return db.scalar(select(MainSquadState))


def main_ids(db):
    row = state_row(db)
    return set(row.locked_copy_ids) if row else set()


def main_status(db):
    row = state_row(db)
    if not row:
        return dict(identified=False, complete=False, squad_id=None, revision=0, snapshot=None,
                    protected_copy_ids=[], retained_copy_ids=[], state_hash=fingerprint(None),
                    reason='Identifica y revisa tu plantilla principal antes de consumir cartas.')
    snapshot = row.snapshot
    ids = {r['player_id'] for r in snapshot['members']}
    available = {p.id: p for p in db.scalars(select(Player).where(Player.id.in_(ids), Player.deleted.is_(False), Player.availability == 'available'))}
    from app.services.squad_analysis import player_positions
    valid_positions = all(m['slot'].startswith(('BENCH-', 'RESERVE-')) or
        (m['player_id'] in available and m['slot'].rsplit('-', 1)[0] in player_positions(available[m['player_id']])) for m in snapshot['members'])
    complete = bool(snapshot.get('complete') and not snapshot.get('needs_review') and ids == available.keys() and valid_positions)
    return dict(identified=True, complete=complete, squad_id=row.squad_id, revision=row.revision,
                snapshot=snapshot, protected_copy_ids=sorted(row.locked_copy_ids),
                retained_copy_ids=sorted(set(row.locked_copy_ids)-ids),
                state_hash=fingerprint([row.squad_id, row.revision, snapshot, sorted(row.locked_copy_ids)]),
                reason=None if complete else 'La principal tiene copias ausentes o pendientes. Sus protecciones se conservan; revisa su estado.')


def require_main_ready(db):
    status = main_status(db)
    if not status['complete']:
        raise HTTPException(409, status['reason'])
    return status


def select_main(db, squad, *, expected_hash, complete):
    from app.services.squad_analysis import formation_slots, player_positions, athlete_keys
    before = main_status(db)
    if before['state_hash'] != expected_hash:
        raise HTTPException(409, 'La principal cambió. Vuelve a revisar la selección.')
    members = list(db.scalars(select(SquadPlayer).where(SquadPlayer.squad_id == squad.id)))
    allowed = {r['slot']: r['position'] for r in formation_slots(squad.formation)}
    starters = [m for m in members if not m.slot.startswith(('BENCH-', 'RESERVE-'))]
    if not complete or {m.slot for m in starters} != set(allowed) or len(starters) != 11:
        raise HTTPException(422, 'Revisa el once completo y declara que incluiste todo su banquillo y reservas.')
    identities, ids = set(), set()
    for m in members:
        p = db.get(Player, m.player_id)
        if not p or p.deleted or p.availability != 'available' or p.id in ids:
            raise HTTPException(409, 'La plantilla contiene copias no disponibles o repetidas.')
        if m.slot in allowed and allowed[m.slot] not in player_positions(p):
            raise HTTPException(422, 'Una posición de la principal requiere revisión.')
        if athlete_keys(p) & identities:
            raise HTTPException(422, 'No se pueden alinear dos copias del mismo futbolista.')
        identities.update(athlete_keys(p))
        ids.add(p.id)
    snapshot = dict(name=squad.name, formation=squad.formation, tactic=dict(squad.tactic or {}), manager=None,
                    source='user_selection', observed_at=now().isoformat(), complete=True,
                    members=[dict(player_id=m.player_id, slot=m.slot) for m in members],
                    ea_active_squad=False)
    row = state_row(db)
    if row:
        row.history = [*row.history[-19:], dict(squad_id=row.squad_id, snapshot=row.snapshot, revision=row.revision)]
        row.locked_copy_ids = sorted(set(row.locked_copy_ids) | ids)
        row.squad_id, row.snapshot, row.revision = squad.id, snapshot, row.revision+1
    else:
        row = MainSquadState(squad_id=squad.id, snapshot=snapshot, locked_copy_ids=sorted(ids), history=[])
        db.add(row)
    db.info['selecting_main'] = True
    for old in db.scalars(select(Squad).execution_options(include_historical_squads=True)):
        old.primary = old.id == squad.id
    squad.primary = True
    # Individual and optional squad locks remain separate; selection never clears them.
    db.info['context'].revision += 1
    db.flush()
    return main_status(db)
