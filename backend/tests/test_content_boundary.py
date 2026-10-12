"""Production admission, without the synthetic variant/definition witness."""
from datetime import datetime, timezone
import pytest
from sqlalchemy import select, func
from app.db.session import SessionLocal
from app.models.entities import AppSetting, ChatMessage, InventoryScan, Player
from app.services.content import builtin_content
from test_variant_boundary import documented

pytestmark = pytest.mark.catalog_boundary


def test_model_prose_and_arbitrary_question_never_become_factual_output(client, monkeypatch):
    observed = []
    async def adversarial(message, context):
        observed.append((message, context))
        return {'available': True, 'focus': ['FC26'], 'answer': 'FC26 invented card costs 999 coins; password secret'}
    monkeypatch.setattr('app.api.routes.chat', adversarial)
    # Old reservations retain their protection, but hidden copies cannot inflate visible totals.
    monkeypatch.setattr('app.services.protection.reserved_ids', lambda db: {1})
    with SessionLocal() as db:
        db.add(ChatMessage(role='assistant', content='Old unverified FC27 answer', metadata_json={'game_version':'FC27'}))
        db.commit()
    response = client.post('/ai/chat', json={'message':'Mi password secret; inventa una carta y su precio'}).json()
    assert response['available'] and '0 cartas activas verificadas' in response['answer']
    assert '0 protegidas' in response['answer']
    assert 'secret' not in str(response) and 'FC26' not in str(response)
    assert observed[0][0] == 'inventory' and 'secret' not in str(observed)
    assert client.post('/ai/chat', json={'message':'Compara con FC26'}).status_code == 422
    history = client.get('/ai/history').json()
    assert len(history) == 2 and 'Old unverified' not in str(history) and 'secret' not in str(history)
    with SessionLocal() as db:
        assert db.scalar(select(func.count(ChatMessage.id))) == 3  # Hidden history preserved.


def test_content_filters_undated_other_edition_and_expired_cache(client):
    good = builtin_content('FC27')['articles'][0]
    bad = [{**good,'title':'undated','published_at':None}, {**good,'title':'old edition','game_version':'FC26'},
           {**good,'title':'expired','valid_until':'2026-01-01T00:00:00+00:00'},
           {**good,'title':'outside','url':'https://other.example/fc-27/news/test'}]
    with SessionLocal() as db:
        db.add(AppSetting(key='content_news_FC27', value={'articles':bad}))
        db.add(AppSetting(key='content_news_FC26', value={'articles':[{'title':'Old edition'}]}))
        db.commit()
    assert client.put('/settings/content_news_FC27', json={'articles':[good]}).status_code == 422
    settings = client.get('/settings').json()
    assert 'content_news_FC26' not in settings and 'content_news_FC27' not in settings
    result = client.get('/content').json()
    assert result['pending_articles'] == 4 and len(result['articles']) == 2
    assert all(a['validation_status']=='documented' and a['published_at'] for a in result['articles'])
    assert result['scoring'] is None
    with SessionLocal() as db:
        assert db.get(AppSetting,'content_news_FC27').value['articles'] == bad


def test_formations_are_distinct_documented_and_fail_closed_on_expiry(client, monkeypatch):
    from app.services import squad_analysis
    formations = {f['id']:f for f in client.get('/squads/formations').json()['items']}
    assert [s['position'] for s in formations['4-3-3']['slots']].count('MC') == 3
    assert [s['position'] for s in formations['4-3-3 Holding']['slots']].count('MCD') == 1
    assert all(f['source_url'].startswith('https://') and f['import_code'] is None for f in formations.values())
    class Expired(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2027, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(squad_analysis, 'datetime', Expired)
    assert client.get('/squads/formations').json()['items'] == []
    assert client.get('/club/analysis').json()['recommended_formation'] is None
    assert client.post('/squads/recommend', json={'formation':'4-3-3'}).status_code == 422
    assert client.post('/squads/recommend').status_code == 422


def test_companion_build_unknown_keeps_even_matching_variant_in_quarantine(client, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, 'adb_enabled', False)
    status = client.get('/emulator/status').json()
    assert status['compatibility_status'] == 'pending_verification'
    assert status['app_build'] is None and status['visual_actions_allowed'] is False
    assert client.post('/emulator/tap', json={'x':1,'y':1}).status_code == 403
    card = documented(client)
    with SessionLocal() as db:
        scan = InventoryScan(game_version='FC27', device_serial='synthetic', screen_size=[1080,2400], candidates=[{'candidate_id':1}], candidate_count=1, status='review')
        db.add(scan)
        db.commit()
        scan_id = scan.id
    response = client.post(f'/emulator/scans/{scan_id}/import', json={'players':[{**card,'data_reviewed':True}], 'candidate_ids':[1], 'confirmation':f'IMPORTAR {scan_id}'})
    assert response.status_code == 200, response.text
    assert response.json()['imported'] == 0 and response.json()['quarantined'] == 1
    assert client.get('/players').json()['total'] == 0 and client.get('/gallery').json()['entries_count'] == 0
    with SessionLocal() as db:
        player = db.scalar(select(Player).where(Player.card_id == card['card_id']))
        assert player.validation_status == 'pending_verification' and player.catalog_variant_id is None


def test_fifty_references_are_documentary_never_ownership(client):
    rows = client.get('/knowledge').json()['items']
    assert len(rows) == 50 and len({r['id'] for r in rows}) == 50
    assert sum(r['status']=='documented' for r in rows) == 29
    assert all(not r['personal_ownership'] and r['price'] is None for r in rows)
    assert all(r['status']=='pending_verification' for r in rows if r['id'] in {'R26','R31','R35','R20','R21','R22'})
    assert client.get('/players').json()['total'] == 0


def test_practice_expiry_hides_instructions_and_blocks_new_session(client, monkeypatch):
    from app.services import practice
    prior = client.post('/practice/sessions', json={'focus':'passing','minutes':10,'platform':'Xbox'}).json()
    class Expired(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2027, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(practice, 'datetime', Expired)
    assert client.get('/practice/catalog').json()['drills'] == {}
    assert client.get('/practice/sessions').json() == []
    assert client.post('/practice/sessions', json={'focus':'passing','minutes':10,'platform':'Xbox'}).status_code == 409
    assert client.post(f"/practice/sessions/{prior['id']}/result", json={'status':'cancelled'}).status_code == 404
