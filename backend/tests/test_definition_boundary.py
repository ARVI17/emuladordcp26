from datetime import timedelta
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import aliased
from app.db.session import SessionLocal
from app.models.entities import AuditLog, Challenge, EvolutionDefinition, GallerySet, Objective, Profile, Segment, now
from app.services.definition_validation import MODELS

pytestmark = pytest.mark.catalog_boundary


def test_demo_rules_squads_and_balances_are_preserved_but_never_active(client):
    for route in ('/challenges','/objectives','/gallery/sets','/evolutions','/squads','/catalog/definitions','/catalog/private-definitions'):
        assert client.get(route).json() == [], route
    panel = client.get('/dashboard').json()
    assert panel['counts']['pending_challenges'] == 0 and panel['objectives'] == []
    assert panel['profile']['coins'] == 0
    counts = client.get('/catalog/pending').json()['counts']
    assert counts['dcp'] == 5 and counts['objective'] == 10
    with SessionLocal() as db:
        assert db.scalar(select(func.count(Challenge.id))) == 5
        assert db.scalar(select(Profile.coins).where(Profile.origin == 'unverified')) == 325000
        segment = db.scalar(select(Segment.id))
    assert client.post(f'/segments/{segment}/optimize',json={}).status_code == 404


@pytest.mark.parametrize('route,payload', [
    ('/challenges', {'name':'UNVERIFIED_RULE','segments':[{'name':'Draft','requirements':{'squad_size':1}}]}),
    ('/objectives', {'name':'UNVERIFIED_RULE'}),
    ('/gallery/sets', {'name':'UNVERIFIED_RULE','rules_reviewed':True,'source_url':'https://example.com/fc27'}),
    ('/evolutions', {'name':'UNVERIFIED_RULE','rules_reviewed':True,'requirements':{},'paths':[{'id':'draft','name':'Draft','upgrades':{'rating':1}}]})])
def test_manual_checkbox_and_url_cannot_certify_a_definition(client, route, payload):
    response = client.post(route,json={'game_version':'FC27',**payload})
    assert response.status_code == 201, response.text
    assert response.json()['validation_status'] == 'pending_verification'
    assert 'UNVERIFIED_RULE' not in client.get(route).text
    assert 'UNVERIFIED_RULE' not in client.get('/catalog/private-definitions').text


def test_documented_rules_expiry_alias_counts_and_mutation_invalidation(client):
    from catalog_fixture import witness_definition
    with SessionLocal() as db:
        row = GallerySet(game_version='FC27',slug='checked',name='Checked source',rules={},tags=[],grade_thresholds={},rules_reviewed=True)
        witness_definition(row)  # Explicit trusted synthetic publication, outside HTTP.
        db.add(row)
        db.commit()
        identifier = row.id
    assert len(client.get('/gallery/sets').json()) == 1
    edited = client.patch(f'/gallery/sets/{identifier}',json={'game_version':'FC27','name':'Changed','rules_reviewed':True})
    assert edited.status_code == 200 and edited.json()['validation_status'] == 'pending_verification'
    assert client.get('/gallery/sets').json() == []
    with SessionLocal() as db:
        row = db.get(GallerySet,identifier)
        witness_definition(row)
        row.validation_evidence = {**row.validation_evidence, 'valid_until': (now()-timedelta(seconds=1)).isoformat()}
        db.commit()
        db.info['club_context_id'] = 1
        alias = aliased(GallerySet)
        assert db.scalar(select(func.count(alias.id))) == 0
    assert client.get('/gallery/sets').json() == []


def test_legacy_audit_is_hidden_without_deleting_it(client):
    with SessionLocal() as db:
        db.add(AuditLog(action='old',entity_type='player',details={'name':'LEGACY_AUDIT_SENTINEL'}))
        db.commit()
    assert 'LEGACY_AUDIT_SENTINEL' not in client.get('/audit').text
    with SessionLocal() as db:
        assert db.scalar(select(func.count(AuditLog.id)).where(AuditLog.action=='old')) == 1


def test_agenda_does_not_summarize_plans_after_variant_evidence_expires(client):
    from test_variant_boundary import documented
    from app.models.catalog import CardVariant
    data = documented(client)
    copy = client.post('/players',json=data).json()
    created = client.post('/plans',json={'name':'Pending evidence sentinel','budget':0,'actions':[{'kind':'keep','player_ids':[copy['id']]}]})
    assert created.status_code == 201, created.text
    with SessionLocal() as db:
        row = db.scalar(select(CardVariant).where(CardVariant.variant_id == data['card_id']))
        row.valid_until = now()-timedelta(seconds=1)
        db.commit()
    result = client.post('/plans/agenda',json={'budget':0,'reserve_coins':0})
    assert result.status_code == 200, result.text
    assert 'Pending evidence sentinel' not in result.text
    assert result.json()['selected'] == [] and result.json()['pending'] == []
