from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.entities import Player, now
from app.models.planner import MatchRecord, PracticeSession
from test_planner import fake_run


@pytest.fixture(autouse=True)
def practice_reference_clock(monkeypatch):
    from app.services import practice
    class ReviewedDate(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 20, tzinfo=timezone.utc)
    monkeypatch.setattr(practice, 'datetime', ReviewedDate)


def create(client, **extra):
    response = client.post('/practice/sessions', json={'focus': 'runs', 'minutes': 15, 'platform': 'Xbox', **extra})
    assert response.status_code == 201, response.text
    return response.json()


def finish(client, row, **extra):
    return client.post(f"/practice/sessions/{row['id']}/result", json={'status': 'completed', 'attempts': 10, 'successes': 6, 'minutes': 12, 'next_change': 'Activar mas tarde', **extra})


def match(client, **extra):
    return client.post('/matches', json={'played_at': now().isoformat(), 'tactic': '4-4-2', 'minutes': 90, 'chances': 4, 'dangerous_losses': 2, 'conceded': 1, 'change_tested': 'Cambio temprano', **extra})


def test_practice_agenda_bounds_controls_evidence_and_no_inventory_mutation(client):
    before = client.get('/players').json()
    catalog = client.get('/practice/catalog').json()
    assert len(catalog['drills']) == 6 and not catalog['patch_verified']
    for platform, control in [('Xbox', 'LB + RB'), ('PlayStation', 'L1 + R1'), ('PC', None), ('Switch', None)]:
        row = create(client, minutes=5, platform=platform)
        assert sum(s['minutes'] for s in row['agenda']['steps']) == 5
        assert (control in row['agenda']['control']) if control else row['agenda']['control'] is None
    assert client.post('/practice/sessions', json={'focus': 'runs', 'minutes': 4, 'platform': 'Xbox'}).status_code == 422
    assert client.get('/players').json() == before


def test_practice_completion_link_and_context_edition_isolation(client):
    row = create(client)
    assert match(client, practice_id=row['id']).status_code == 422
    assert finish(client, row, successes=11).status_code == 422
    assert finish(client, row).status_code == 200
    assert finish(client, row).status_code == 409
    assert match(client, practice_id=row['id']).status_code == 201
    assert client.patch('/profile', json={'game_version': 'FC26'}).status_code == 422
    assert client.get('/matches').json()['sample_size'] == 1
    fake_run(client)
    assert client.get('/practice/sessions').json() == []
    assert finish(client, row).status_code == 404
    assert match(client, practice_id=row['id']).status_code == 422
    assert client.get('/matches?edition=FC27').json()['sample_size'] == 0


def test_match_groups_use_minutes_keep_unknown_history_and_reject_future(client):
    assert match(client, minutes=30, chances=2, conceded=0).status_code == 201
    assert match(client, minutes=60, chances=4, conceded=1).status_code == 201
    assert match(client, change_tested='Sin cambio', minutes=90).status_code == 201
    assert match(client, played_at=(now()+timedelta(days=1)).isoformat()).status_code == 422
    with SessionLocal() as db:
        old = MatchRecord(played_at=now(), tactic='Historico', minutes=90, chances=1, dangerous_losses=1, conceded=1, change_tested='Desconocido')
        db.add(old)
        db.commit()
    result = client.get('/matches').json()
    assert result['sample_size'] == 3 and result['unverified_history_count'] == 0
    group = next(g for g in result['groups'] if g['change_tested'] == 'Cambio temprano')
    assert group['sample_size'] == 2 and group['minutes'] == 90
    assert group['per_90'] == {'chances': 6.0, 'dangerous_losses': 4.0, 'conceded': 1.0}
    assert client.get('/matches?edition=unverified').status_code == 422
    assert client.get('/matches?edition=FC26').status_code == 422
    with SessionLocal() as db:
        assert db.scalar(select(MatchRecord).where(MatchRecord.game_version == 'unverified')) is not None
    assert client.get('/matches?edition=FC27').json()['sample_size'] == 3


def test_practice_cancel_is_audited_and_cannot_be_recompleted(client):
    row = create(client)
    assert client.post(f"/practice/sessions/{row['id']}/result", json={'status': 'cancelled'}).status_code == 200
    assert finish(client, row).status_code == 409
    with SessionLocal() as db:
        assert db.get(PracticeSession, row['id']).result['attempts'] == 0
