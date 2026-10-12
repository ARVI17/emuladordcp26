from copy import deepcopy
import pytest
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.entities import AppSetting, GalleryEntry, Player
from app.services.content import NewsLinks
from app.services.gallery import record_player


def player(client, **overrides):
    payload = {"name":"Lucía Prueba", "rating":82, "position":"DC", "league":"Liga de prueba", "club":"Club A", "nationality":"Colombia", "card_type":"Oro", "price":1200, "attributes":{"pace":85,"shooting":84,"passing":75,"dribbling":81,"defending":35,"physical":70}, "data_reviewed":True, **overrides}
    result = client.post('/players', json=payload)
    assert result.status_code == 201, result.text
    created = result.json()
    # Backfill is a public user action and also exercises idempotent acquisition.
    assert client.post('/gallery/record-inventory', json={"player_ids":[created['id']]}).status_code == 200
    return created


def set_payload(**overrides):
    return {"name":"Conjunto de prueba", "rules":{"size":2}, "rules_reviewed":True, **overrides}


def evo_payload(**overrides):
    return {"name":"Camino de prueba", "requirements":{"max_rating":85,"positions":["DC"]}, "paths":[
        {"id":"ataque", "name":"Finalización", "upgrades":{"rating":2,"attributes":{"shooting":8},"attribute_caps":{"shooting":88}}},
        {"id":"movilidad", "name":"Movilidad", "upgrades":{"rating":1,"attributes":{"pace":5}}}
    ], "rules_reviewed":True, **overrides}


def test_gallery_survives_removal_and_deduplicates_item_copies(client):
    first = player(client, card_id='test-card-82', gallery_score=340)
    second = player(client, name='Lucía Prueba', card_id='test-card-82', gallery_score=340)
    entries = client.get('/gallery/entries?search=Lucía').json()['items']
    assert len(entries) == 1 and set(entries[0]['current_player_ids']) == {first['id'], second['id']}
    client.delete(f"/players/{first['id']}")
    client.delete(f"/players/{second['id']}")
    history = client.get('/gallery/entries?search=Lucía').json()['items']
    assert len(history) == 1 and history[0]['owned'] is False and history[0]['gallery_score'] == 340


def test_gallery_rejects_loans_and_evolved_stats_as_base(client):
    loan = player(client, name='Préstamo de prueba', is_loan=True)
    evolved = player(client, name='Evo sin base', is_evolution=True, base_card_id='missing-base', rating=89)
    entries = client.get('/gallery/entries?search=Préstamo').json()['items']
    assert entries == []
    assert client.get('/gallery/entries?search=Evo sin base').json()['items'] == []
    base = player(client, name='Base real', card_id='missing-base', rating=80)
    result = client.post('/gallery/record-inventory', json={"player_ids":[evolved['id']]}).json()
    assert result['unresolved_evolutions'] == 0
    history = client.get('/gallery/entries?search=Base real').json()['items']
    assert len(history) == 1 and history[0]['rating'] == 80


def test_gallery_correction_without_card_id_does_not_duplicate_acquisition(client):
    card = player(client, name='OCR erróneo')
    response = client.patch(f"/players/{card['id']}", json={"name":"OCR corregido", "rating":83})
    assert response.status_code == 200
    client.post('/gallery/record-inventory', json={"player_ids":[card['id']]})
    with SessionLocal() as db:
        history = list(db.scalars(select(GalleryEntry).where(GalleryEntry.player_id == card['id'])))
        assert len(history) == 2 and any(h.snapshot['name'] == 'OCR corregido' for h in history)


def test_gallery_suggests_tag_combination_and_one_version_per_athlete(client):
    player(client, name='Prueba A', gallery_score=100, card_id='a1', club='Otro')
    player(client, name='Prueba B', gallery_score=60, card_id='b1', club='Unión')
    player(client, name='Prueba C', gallery_score=60, card_id='c1', club='Unión')
    player(client, name='Prueba B', gallery_score=65, card_id='b2', club='Unión', card_type='Especial', special=True)
    result = client.post('/gallery/sets', json=set_payload(tags=[{"name":"Pareja de club","field":"club","value":"Unión","minimum":2,"bonus":200}], grade_thresholds={"A":300})).json()['evaluation']
    assert result['complete'] and result['score'] == 325 and result['grade'] == 'A'
    assert {card['name'] for card in result['selected_entries']} == {'Prueba B', 'Prueba C'}


def test_gallery_unknown_points_and_unreviewed_rules_do_not_invent_grades(client):
    player(client, name='Desconocida')
    result = client.post('/gallery/sets', json=set_payload(rules={"size":1}, rules_reviewed=False, grade_thresholds={"S":1})).json()['evaluation']
    assert result['score'] is None and result['grade'] is None and result['unknown_score_count'] == 1


def test_gallery_score_edit_updates_copies_but_not_other_versions(client):
    first = player(client, card_id='same-version', name='Puntos')
    second = player(client, card_id='same-version', name='Puntos')
    other = player(client, card_id='other-version', name='Puntos', rating=90, special=True)
    entries = client.get('/gallery/entries?search=Puntos').json()['items']
    entry = next(item for item in entries if item['card_id'] == 'same-version')
    assert client.patch(f"/gallery/entries/{entry['id']}", json={"gallery_score":340}).status_code == 200
    with SessionLocal() as db:
        assert db.get(Player, first['id']).gallery_score == 340
        assert db.get(Player, second['id']).gallery_score == 340
        assert db.get(Player, other['id']).gallery_score is None


def test_evolution_branches_caps_and_chain_never_mutate_player(client):
    original = player(client, card_id='evo-base')
    first = client.post('/evolutions', json=evo_payload()).json()
    second = client.post('/evolutions', json=evo_payload(name='Segundo paso', requirements={"min_rating":84,"max_rating":90}, paths=[{"id":"final", "name":"Último paso", "upgrades":{"rating":3,"rating_cap":86}}])).json()
    attack = client.post('/evolutions/preview', json={"player_id":original['id'],"steps":[{"evolution_id":first['id'],"path_id":"ataque"},{"evolution_id":second['id'],"path_id":"final"}]}).json()
    assert attack['simulation'] and attack['eligible']
    assert attack['projected']['rating'] == 86
    assert attack['projected']['attributes']['shooting'] == 88
    assert attack['projected']['base_card_id'] == 'evo-base'
    mobility = client.post('/evolutions/preview', json={"player_id":original['id'],"steps":[{"evolution_id":first['id'],"path_id":"movilidad"}]}).json()
    assert mobility['projected']['attributes']['pace'] == 90
    with SessionLocal() as db:
        persisted = db.get(Player, original['id'])
        assert persisted.rating == 82 and persisted.attributes['shooting'] == 84 and not persisted.is_evolution


@pytest.mark.parametrize('overrides,expected', [
    ({'requirements':{'max_attributes':{'reflexes':80}}}, 'Falta el atributo'),
    ({'rules_reviewed':False}, 'todavía no están revisadas'),
    ({'expires_at':'2020-01-01T00:00:00Z'}, 'ha vencido'),
    ({'requirements':{'max_rating':80}}, 'media debe'),
])
def test_evolution_fails_closed_for_unverified_or_ineligible_inputs(client, overrides, expected):
    original = player(client)
    definition = client.post('/evolutions', json=evo_payload(**overrides)).json()
    result = client.post('/evolutions/preview', json={"player_id":original['id'],"steps":[{"evolution_id":definition['id'],"path_id":"ataque"}]})
    if 'expires_at' in overrides:
        assert result.status_code == 404
        assert definition['id'] not in [row['id'] for row in client.get('/evolutions').json()]
        return
    response = result.json()
    assert not response['eligible']
    assert any(expected in message for message in response['steps'][0]['violations'])
    assert response['projected']['rating'] == original['rating']


def test_evolution_chain_does_not_repeat_same_definition(client):
    original = player(client)
    definition = client.post('/evolutions', json=evo_payload()).json()
    response = client.post('/evolutions/preview', json={"player_id":original['id'],"steps":[{"evolution_id":definition['id'],"path_id":"ataque"},{"evolution_id":definition['id'],"path_id":"movilidad"}]})
    assert response.status_code == 422


def test_edition_boundaries_reject_cross_version_definitions(client):
    assert client.post('/gallery/sets', json=set_payload(game_version='FC26')).status_code == 422
    assert client.post('/evolutions', json=evo_payload(game_version='FC26')).status_code == 422
    assert client.patch('/profile', json={'game_version':'FC26'}).status_code == 422
    assert client.get('/evolutions?game_version=FC26').status_code == 422
    assert client.get('/gallery?game_version=FC26').status_code == 422


def test_content_pack_preview_integrity_and_idempotent_confirm(client):
    manifest = {'schema_version':1, 'game_version':'FC27','published_at':'2026-10-09T12:00:00Z','sets':[set_payload(slug='pack-set')],'evolutions':[evo_payload(slug='pack-evo')]}
    before = client.get('/gallery/sets').json()
    preview = client.post('/content/import', json={'manifest':manifest}).json()
    assert preview['preview'] and client.get('/gallery/sets').json() == before
    altered = deepcopy(manifest)
    altered['sets'][0]['name'] = 'Otra definición'
    assert client.post('/content/import', json={'manifest':altered,'confirm':True,'preview_hash':preview['preview_hash']}).status_code == 409
    confirmed = client.post('/content/import', json={'manifest':manifest,'confirm':True,'preview_hash':preview['preview_hash']}).json()
    assert not confirmed['already_imported']
    repeated = client.post('/content/import', json={'manifest':manifest,'confirm':True,'preview_hash':preview['preview_hash']}).json()
    assert repeated['already_imported']
    assert len(client.get('/gallery/sets').json()) == 1 and len(client.get('/evolutions').json()) == 1


def test_content_pack_validation_is_atomic(client):
    manifest = {'schema_version':1, 'game_version':'FC27','published_at':'2026-10-09T12:00:00Z','sets':[set_payload()],'evolutions':[evo_payload(requirements={'invented_requirement':True})]}
    assert client.post('/content/import', json={'manifest':manifest,'confirm':True}).status_code == 422
    assert client.get('/gallery/sets').json() == []
    assert client.get('/evolutions').json() == []


def test_failed_news_refresh_preserves_last_success(client, monkeypatch):
    monkeypatch.setattr('app.api.fc27.fetch_news', lambda version: {'articles':[{'title':'EA test','url':'https://www.ea.com/games/ea-sports-fc/fc-27/news/test','published_at':None}],'last_checked':'2026-10-09T12:00:00Z','refresh_error':None})
    assert client.post('/content/refresh').json()['articles'][0]['title'] == 'EA test'
    def failed(_): raise RuntimeError('sensitive internal value')
    monkeypatch.setattr('app.api.fc27.fetch_news', failed)
    response = client.post('/content/refresh').json()
    assert response['articles'][0]['title'] == 'EA test'
    assert response['refresh_error'] and 'sensitive' not in str(response)


def test_public_news_parser_rejects_non_ea_and_account_links():
    parser = NewsLinks('FC27')
    parser.feed('<a href="https://evil.example/games/ea-sports-fc/fc-27/news/fake">Fake</a><a href="https://accounts.ea.com/login">Login</a><a href="/games/ea-sports-fc/fc-27/news/update?tracking=x">Update</a>')
    assert parser.links == [{'title':'Update','url':'https://www.ea.com/games/ea-sports-fc/fc-27/news/update','published_at':None}]
    parser.feed('<a href=" /games/ea-sports-fc/fc-27/news/new-campaign " >Learn More</a>')
    assert parser.links[-1]['title'] == 'New campaign'
    assert parser.links[-1]['url'].endswith('/news/new-campaign')


def test_content_reference_never_applies_scores_or_imports_game_data(client):
    with SessionLocal() as db:
        before = [(player.id, player.gallery_score) for player in db.scalars(select(Player))]
    response = client.get('/content').json()
    assert response['game_version'] == 'FC27' and response['scoring']['base_scores']['84'] == 830
    with SessionLocal() as db:
        assert [(player.id, player.gallery_score) for player in db.scalars(select(Player))] == before


def test_assigning_canonical_card_id_reconciles_historical_identity(client):
    card = player(client, name='Identidad revisada')
    assert client.patch(f"/players/{card['id']}", json={'card_id':'reviewed-id'}).status_code == 200
    client.post('/gallery/record-inventory', json={'player_ids':[card['id']]})
    entries = client.get('/gallery/entries?search=Identidad revisada').json()['items']
    assert len(entries) == 2 and sum(e['owned'] for e in entries) == 1


def test_unreviewed_points_cannot_produce_a_gallery_grade(client):
    card = player(client, name='Puntos por revisar', gallery_score=9999, data_reviewed=False)
    result = client.post('/gallery/sets', json=set_payload(rules={'size':1},grade_thresholds={'S':1})).json()['evaluation']
    assert result['score'] is None and result['grade'] is None and result['unknown_score_count'] == 1


def test_editing_one_copy_keeps_version_scores_consistent(client):
    first = player(client, card_id='shared-points', gallery_score=200)
    second = player(client, card_id='shared-points', gallery_score=200)
    assert client.patch(f"/players/{first['id']}", json={'gallery_score':123}).status_code == 200
    client.post('/gallery/record-inventory', json={'player_ids':[first['id']]})
    with SessionLocal() as db:
        assert db.get(Player, first['id']).gallery_score == db.get(Player, second['id']).gallery_score == 123


def test_gallery_different_documented_variants_never_merge_by_name(client):
    first = player(client, name='Dos copias')
    second = player(client, name='Dos copias')
    assert client.patch(f"/players/{first['id']}", json={'card_id':'canonical-after-ocr'}).status_code == 200
    client.post('/gallery/record-inventory', json={'player_ids':[first['id'],second['id']]})
    entries = client.get('/gallery/entries?search=Dos copias').json()['items']
    assert len(entries) == 2
    assert {e['card_id'] for e in entries} == {'canonical-after-ocr', second['card_id']}
    assert {pid for e in entries for pid in e['current_player_ids']} == {first['id'],second['id']}


def test_evolution_cannot_overflow_card_limits_or_downgrade_role(client):
    original = player(client, playstyles=[f'Estilo {i}' for i in range(30)], roles={'MC':'++'})
    invalid = client.post('/evolutions', json=evo_payload(paths=[{'id':'extra','name':'Extra','upgrades':{'playstyles':['Estilo adicional']}}])).json()
    result = client.post('/evolutions/preview', json={'player_id':original['id'],'steps':[{'evolution_id':invalid['id'],'path_id':'extra'}]}).json()
    assert not result['eligible'] and len(result['projected']['playstyles']) == 30
    valid = client.post('/evolutions', json=evo_payload(name='No reducir rol', paths=[{'id':'role','name':'Role','upgrades':{'roles':{'MC':'+'}}}])).json()
    result = client.post('/evolutions/preview', json={'player_id':original['id'],'steps':[{'evolution_id':valid['id'],'path_id':'role'}]}).json()
    assert result['eligible'] and result['projected']['roles']['MC'] == '++'


def test_retrying_older_content_pack_cannot_revert_newer_revision(client):
    def prepare(name, date):
        manifest = {'schema_version':1, 'game_version':'FC27','published_at':date,'sets':[set_payload(name=name,slug='stable-set')]}
        preview = client.post('/content/import', json={'manifest':manifest}).json()
        return {'manifest':manifest,'confirm':True,'preview_hash':preview['preview_hash']}
    old = prepare('Revisión A','2026-10-08T12:00:00Z')
    assert client.post('/content/import', json=old).status_code == 200
    latest = prepare('Revisión B','2026-10-09T12:00:00Z')
    assert client.post('/content/import', json=latest).status_code == 200
    assert client.post('/content/import', json=old).json()['already_imported'] is True
    assert client.get('/gallery/sets').json()[0]['name'] == 'Revisión B'
