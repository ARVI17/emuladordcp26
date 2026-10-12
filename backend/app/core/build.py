"""Non-secret, immutable image provenance. Development never guesses a Git SHA."""
import json
from pathlib import Path


def build_info():
    path = Path(__file__).resolve().parents[2] / 'build.json'
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    return {'edition': 'FC27', 'revision': 'unknown', 'built_at': 'unknown',
            'environment': 'development', 'source_dirty': False}
