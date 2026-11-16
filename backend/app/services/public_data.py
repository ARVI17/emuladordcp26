"""Versioned public evidence. Reading never renews its review window."""
import json
from datetime import datetime, timezone
from pathlib import Path

DATA_ROOT = Path(__file__).resolve().parents[1] / 'data'


def read_public_data(name):
    return json.loads((DATA_ROOT / name).read_text(encoding='utf-8'))


def active_review(row, current=None):
    try:
        start = datetime.fromisoformat(row.get('observed_at') or row['verified_at'])
        end = datetime.fromisoformat(row['valid_until'])
        return (row.get('validation_status', row.get('status')) == 'documented'
                and start.tzinfo is not None and end.tzinfo is not None
                and start <= (current or datetime.now(timezone.utc)) < end)
    except (KeyError, TypeError, ValueError):
        return False
