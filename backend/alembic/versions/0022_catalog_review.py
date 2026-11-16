"""Revisión pública acotada; conserva revisiones locales y todas las copias."""
import json
from datetime import datetime, timezone
from pathlib import Path
from alembic import op
import sqlalchemy as sa

revision = '0022'
down_revision = '0021'
branch_labels = None
depends_on = None


def review_catalog(bind):
    data = json.loads((Path(__file__).parents[1] / 'data' / '0022_catalog_review.json').read_text(encoding='utf-8'))
    table = sa.Table('card_variants', sa.MetaData(), autoload_with=bind)
    previous_start = datetime.fromisoformat(data['previous_observed_at'])
    previous_end = datetime.fromisoformat(data['previous_valid_until'])
    changed = 0
    for item in data['items']:
        identity = {k: v for k, v in item.items() if k != 'reference_id'}
        conditions = [table.c[k] == v for k, v in identity.items()]
        conditions += [table.c.game_version == 'FC27', table.c.validation_status == 'documented',
                       table.c.observed_at == previous_start, table.c.valid_until == previous_end]
        row = bind.execute(sa.select(table).where(*conditions).with_for_update()).mappings().first()
        if row is None:
            continue
        old = row['evidence']
        # An edited provenance is a local review, even if its dates were retained.
        expected = {'reference_id': item['reference_id'], 'edition_and_item_checked': True,
                    'official': False, 'ownership': False,
                    'card_type_scope': 'Etiqueta del catálogo de origen; Rare no acredita clasificación oficial EA'}
        if old != expected:
            continue
        pending = item['reference_id'] in {'R33', 'R49'}
        evidence = {**old, 'review_id': data['review_id'], 'review_history': [{
            'observed_at': data['previous_observed_at'], 'valid_until': data['previous_valid_until'],
            'validation_status': row['validation_status'], 'evidence': old}]}
        if pending:
            evidence['reason'] = data['pending_reason']
        bind.execute(table.update().where(table.c.id == row['id'], *conditions).values(
            observed_at=datetime.fromisoformat(data['observed_at']),
            valid_until=datetime.fromisoformat(data['valid_until']),
            validation_status='pending_verification' if pending else 'documented', evidence=evidence))
        changed += 1
    return changed


def upgrade():
    # Alembic provides the transaction; each evidence row keeps its prior receipt.
    review_catalog(op.get_bind())


def downgrade():
    raise RuntimeError('Restaurar un respaldo probado; no sobrescribir revisiones posteriores del catálogo')
