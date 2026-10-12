"""Presentation of observed account facts, independent of manual profile/catalog data."""
from collections import Counter
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
    values = {'name': account.get('name'),
              'platform': context.platform if context and context.verified else None,
              'coins': account.get('coins') if coverage.get('coins', {}).get('complete') else None,
              'fc_points': account.get('fc_points') if coverage.get('fc_points', {}).get('complete') else None,
              'unassigned_count': len(account['unassigned_items']) if coverage.get('unassigned', {}).get('complete') and account.get('unassigned_items') is not None else None}
    observed_at = utc(snapshot.observed_at).isoformat() if snapshot else None
    return {
        **values,
        'unassigned_types': dict(Counter(item['kind'] for item in account['unassigned_items'])) if values['unassigned_count'] is not None else None,
        'identity_verified': bool(context and context.verified),
        'provider': context.provider if context and context.verified else None,
        'observed_copies': len(snapshot.items) if snapshot and 'inventory' in coverage else None,
        'inventory_complete': bool(coverage.get('inventory', {}).get('complete')),
        'snapshot_id': snapshot.id if snapshot else None,
        'observed_at': observed_at,
        'facts': {key: {'value': value, 'status': 'observed' if value is not None else 'unknown',
                        'source': context.provider if value is not None and context else None,
                        'snapshot_id': snapshot.id if value is not None and snapshot else None,
                        'observed_at': observed_at if value is not None else None,
                        'coverage': coverage.get('unassigned' if key == 'unassigned_count' else key, {})}
                  for key, value in values.items()},
        'coverage': coverage,
        # Inventory alone never certifies these domains.
        'progress': {key: 'unavailable' for key in ('squads', 'dcp', 'gallery', 'evolutions', 'objectives', 'history')},
    }
