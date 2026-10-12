"""Presentation of observed account facts, independent of manual profile/catalog data."""
from app.models.planner import InventorySnapshot, SyncRun
from app.services.contexts import utc


def account_summary(db):
    context = db.info.get('context')
    snapshot = db.get(InventorySnapshot, context.snapshot_id) if context and context.verified and context.snapshot_id else None
    run = db.get(SyncRun, snapshot.run_id) if snapshot else None
    # Older snapshots did not capture the balance/name together. Never backfill
    # them from today's mutable Profile or from a different remote observation.
    account = (run.manifest or {}).get('account', {}) if run else {}
    coverage = snapshot.coverage if snapshot else {}
    return {
        'identity_verified': bool(context and context.verified),
        'provider': context.provider if context and context.verified else None,
        'name': account.get('name'), 'platform': context.platform if context and context.verified else None,
        'coins': account.get('coins') if coverage.get('coins', {}).get('complete') else None,
        'observed_copies': len(snapshot.items) if snapshot and 'inventory' in coverage else None,
        'inventory_complete': bool(coverage.get('inventory', {}).get('complete')),
        'snapshot_id': snapshot.id if snapshot else None,
        'observed_at': utc(snapshot.observed_at).isoformat() if snapshot else None,
        'coverage': coverage,
        # Inventory alone never certifies these domains.
        'progress': {key: 'unavailable' for key in ('squads', 'dcp', 'gallery', 'evolutions', 'objectives', 'history')},
    }
