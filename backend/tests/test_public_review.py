"""Actual release evidence and migration invariants, without rebased fixtures."""
import importlib.util
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
import sqlalchemy as sa
from app.services.public_data import active_review, read_public_data
from app.services import squad_analysis, practice, content

pytestmark = pytest.mark.bundled_evidence


def test_review_window_future_expired_missing_timezone_and_revoked():
    row = next(iter(read_public_data('fc27_formations.json')['items'].values()))
    start, end = (datetime.fromisoformat(row[k]) for k in ('observed_at', 'valid_until'))
    assert active_review(row, start)
    assert active_review(row, end - timedelta(microseconds=1))
    assert not active_review(row, start - timedelta(microseconds=1))
    assert not active_review(row, end)
    assert not active_review({**row, 'validation_status': 'revoked'}, start)
    assert not active_review({**row, 'observed_at': '2026-11-16'}, start)
    assert not active_review({}, start)


@pytest.mark.parametrize('phase', ['before', 'active', 'expired'])
def test_actual_bundle_forms_practice_and_content_use_review_dates(monkeypatch, phase):
    data = read_public_data('fc27_content.json')
    start, end = (datetime.fromisoformat(data[k]) for k in ('observed_at', 'valid_until'))
    instant = {'before': start-timedelta(seconds=1), 'active': start, 'expired': end}[phase]
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant
    for module in (squad_analysis, practice, content):
        monkeypatch.setattr(module, 'datetime', Clock)
    assert len(squad_analysis.verified_formations()) == (11 if phase == 'active' else 0)
    assert practice.catalog()['review_due'] is (phase != 'active')
    assert len(content.builtin_content('FC27')['articles']) == (2 if phase == 'active' else 0)


def test_formation_review_is_per_item_and_alias_retains_narrow_slots(monkeypatch):
    bundle = read_public_data('fc27_formations.json')
    instant = datetime.fromisoformat(bundle['items']['4-3-3']['observed_at'])
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant
    bundle['items']['4-3-3']['validation_status'] = 'revoked'
    monkeypatch.setattr(squad_analysis, 'datetime', Clock)
    monkeypatch.setattr(squad_analysis, 'read_public_data', lambda _: deepcopy(bundle))
    assert '4-3-3' not in squad_analysis.verified_formations()
    assert '4-3-3 Holding' in squad_analysis.verified_formations()
    assert squad_analysis.FORMATIONS['4-1-2-1-2'] == squad_analysis.FORMATIONS['4-1-2-1-2 estrecha']


def test_catalog_update_is_exact_idempotent_and_preserves_local_evidence():
    from app.models.catalog import CardVariant
    file = Path(__file__).parents[1] / 'alembic' / 'versions' / '0022_catalog_review.py'
    spec = importlib.util.spec_from_file_location('catalog_review_0022', file)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    import json
    data = json.loads((file.parents[1] / 'data' / '0022_catalog_review.json').read_text(encoding='utf-8'))
    engine = sa.create_engine('sqlite:///:memory:')
    table = CardVariant.__table__
    table.create(engine)
    start, end = (datetime.fromisoformat(data[k]) for k in ('previous_observed_at', 'previous_valid_until'))
    with engine.begin() as conn:
        for item in data['items']:
            evidence = {'reference_id': item['reference_id'], 'edition_and_item_checked': True,
                        'official': False, 'ownership': False,
                        'card_type_scope': 'Etiqueta del catálogo de origen; Rare no acredita clasificación oficial EA'}
            values = {k: v for k, v in item.items() if k != 'reference_id'}
            conn.execute(table.insert().values(**values, game_version='FC27', observed_at=start,
                valid_until=end, validation_status='documented', evidence=evidence))
        # Same old dates are insufficient to override a revocation or local edit.
        conn.execute(table.update().where(table.c.variant_id == '245956').values(validation_status='revoked'))
        conn.execute(table.update().where(table.c.variant_id == '203376').values(observed_at=start+timedelta(days=1)))
        conn.execute(table.update().where(table.c.variant_id == '236479').values(evidence={'manual': True}))
        before = {r.variant_id: dict(r._mapping) for r in conn.execute(sa.select(table))}
        assert migration.review_catalog(conn) == 19
        assert migration.review_catalog(conn) == 0
        after = {r.variant_id: dict(r._mapping) for r in conn.execute(sa.select(table))}
        for key in ('245956', '203376', '236479'):
            assert before[key] == after[key]
        for key in ('67361009', '67372876'):
            assert after[key]['validation_status'] == 'pending_verification'
        assert len(after) == 22
        updated = after['243715']
        assert updated['evidence']['review_history'][0]['evidence'] == before['243715']['evidence']
        assert updated['validation_status'] == 'documented'
    engine.dispose()
