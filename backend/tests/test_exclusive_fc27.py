"""Mixed editions exist only in the disposable test database."""
import pytest
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.entities import Player, Profile, Challenge, Segment, Objective, GalleryEntry, Squad, SquadPlayer, now
from app.models.planner import ClubContext, PublicDefinition, MatchRecord
from app.services.sync import RemoteRead


def test_historical_rows_never_enter_public_lists_aggregates_or_relationships(client):
    with SessionLocal() as db:
        player = db.scalar(select(Player).order_by(Player.id))
        historical_id = player.id
        player.game_version = 'FC26'
        for row in db.scalars(select(GalleryEntry).where(GalleryEntry.player_id == historical_id)):
            row.game_version = 'FC26'
        old = Challenge(game_version='FC26', name='HISTORICAL_SENTINEL')
        db.add(old)
        db.flush()
        segment = Segment(challenge_id=old.id, name='HISTORICAL_SENTINEL', requirements={'squad_size': 1})
        db.add_all([segment, Objective(game_version='FC25', name='HISTORICAL_SENTINEL'),
                    PublicDefinition(kind='dcp', game_version='FC26', slug='old', revision=1, body={}, source_url='https://example.com/old', observed_at=now())])
        db.commit()
        segment_id = segment.id
    for url in ['/players?limit=500', '/gallery/entries', '/gallery', '/squads', '/challenges', '/objectives',
                '/club/analysis', '/catalog/definitions', '/catalog/private-definitions', '/dashboard', '/ai/history', '/matches']:
        response = client.get(url)
        assert response.status_code == 200, (url, response.text)
        assert 'HISTORICAL_SENTINEL' not in response.text and 'FC26' not in response.text and 'FC25' not in response.text, url
    assert historical_id not in [p['id'] for p in client.get('/players?limit=500').json()['items']]
    assert client.post(f'/segments/{segment_id}/optimize', json={}).status_code == 404
    assert client.patch(f'/players/{historical_id}', json={'notes':'overwrite'}).status_code == 404
    with SessionLocal() as db:
        assert db.get(Player, historical_id).game_version == 'FC26'
        assert db.get(Segment, segment_id).name == 'HISTORICAL_SENTINEL'


def test_historical_profile_and_context_cannot_select_the_active_edition(client):
    with SessionLocal() as db:
        profile = db.scalar(select(Profile))
        old_id = profile.id
        profile.game_version, profile.coins = 'FC26', 987654
        context = ClubContext(owner_id=1, game_version='FC26', name='Historical account')
        db.add(context)
        db.commit()
        context_id = context.id
    profile = client.get('/profile').json()
    assert profile['game_version'] == 'FC27' and profile['coins'] == 0 and profile['id'] != old_id
    assert context_id not in [c['id'] for c in client.get('/club-contexts').json()]
    assert client.post('/app/entries', json={'nonce':'historical-entry', 'mode':'local', 'context_id':context_id}).status_code == 404
    assert client.patch('/profile', json={'game_version':'FC26'}).status_code == 422
    with SessionLocal() as db:
        assert db.get(Profile, old_id).coins == 987654


@pytest.mark.parametrize('path', ['/players', '/dashboard', '/squads', '/gallery', '/evolutions', '/content', '/market/quotes'])
def test_other_editions_rejected_even_on_legacy_query_parameters(client, path):
    assert client.get(path+'?game_version=FC26').status_code == 422
