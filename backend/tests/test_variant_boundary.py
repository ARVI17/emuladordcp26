"""Real admission policy, without the synthetic catalog witness harness."""
from datetime import timedelta
import pytest
from sqlalchemy import func, select
from app.db.session import SessionLocal
from app.models.entities import Player, now
from app.models.catalog import CardVariant
from app.services.catalog_validation import load_documented_catalog

pytestmark = pytest.mark.catalog_boundary


def documented(client):
    with SessionLocal() as db:
        load_documented_catalog(db)
        db.commit()
    row = next(r for r in client.get('/catalog/variants').json()['items'] if r['variant_id'] == '245956')
    return {'game_version':'FC27', 'card_id':row['variant_id'], **{k:row[k] for k in ('name','rating','position','card_type')},
            'league':'Revisión manual', 'club':'Revisión manual', 'nationality':'Revisión manual'}


def test_seed_and_references_cannot_create_active_inventory(client, monkeypatch):
    before = client.get('/players').json()
    assert before['total'] == 0
    assert client.get('/dashboard').json()['counts']['players'] == 0
    assert client.get('/gallery').json()['entries_count'] == 0
    assert client.get('/duplicates').json() == []
    assert client.get('/club/analysis').json()['top_players'] == []
    assert client.get('/knowledge').json()['count'] == 50
    documented(client)
    assert client.get('/players').json() == before
    assert b'demo-FC27' not in client.get('/players/export').content
    with SessionLocal() as db:
        assert db.scalar(select(func.count(Player.id))) == 132
    observed = []
    async def fake_chat(message, context):
        observed.append(context)
        return {'available':False, 'answer':'Sin datos certificados', 'sections':{}}
    monkeypatch.setattr('app.api.routes.chat', fake_chat)
    assert client.post('/ai/chat', json={'message':'Resume mis cartas'}).status_code == 200
    assert observed and 'demo-FC27' not in str(observed) and 'FC26' not in str(observed)


def test_unknown_edition_variant_and_false_identity_go_to_quarantine(client):
    known = documented(client)
    for data in ({k:v for k,v in known.items() if k != 'game_version'}, {**known,'card_id':'nonexistent'}, {**known,'rating':99}):
        response = client.post('/players', json=data)
        assert response.status_code == 202, response.text
        assert response.json()['quarantined'] and not response.json()['available']
    assert client.get('/players').json()['total'] == 0
    assert client.get('/inventory/quarantine').json()['total'] == 3
    assert client.post('/players', json={**known,'game_version':'FC26'}).status_code == 422
    assert client.post('/players', json={**known,'validation_status':'documented'}).status_code == 422


def test_import_rejects_other_editions_by_row_and_quarantines_unknown_idempotently(client):
    header = 'name,rating,position,league,club,nationality,game_version\n'
    bad = (header+'A,80,MC,L,C,N,FC26\nB,80,MC,L,C,N,FC25\n').encode()
    response = client.post('/players/import', files={'file':('mixed.csv', bad, 'text/csv')})
    assert response.status_code == 422 and 'Fila 2' in response.text and 'Fila 3' in response.text
    data = b'name,rating,position,league,club,nationality\nUnknown,80,MC,L,C,N\n'
    files = {'file':('unknown.csv', data, 'text/csv')}
    preview = client.post('/players/import', files=files).json()
    assert preview['preview'][0]['validation_status'] == 'pending_verification'
    confirm = {'confirm':'true', 'preview_token':preview['preview_token']}
    result = client.post('/players/import', files=files, data=confirm).json()
    assert result['imported'] == 0 and result['quarantined'] == 1
    assert client.post('/players/import', files=files, data=confirm).json()['already_imported']
    assert client.get('/inventory/quarantine').json()['total'] == 1
    assert client.get('/players?search=Unknown').json()['total'] == 0


def test_documented_copy_expiry_hides_every_active_use_and_keeps_history(client):
    known = documented(client)
    created = client.post('/players', json=known)
    assert created.status_code == 201, created.text
    identifier = created.json()['id']
    assert created.json()['validation_status'] == 'documented'
    assert created.json()['variant_evidence']['official'] is False
    assert client.get('/players').json()['total'] == 1
    assert client.get('/gallery').json()['entries_count'] == 1
    with SessionLocal() as db:
        row = db.scalar(select(CardVariant).where(CardVariant.variant_id == known['card_id']))
        row.valid_until = now()-timedelta(seconds=1)
        db.commit()
    for route in ['/players','/dashboard','/gallery/entries','/gallery','/club/analysis','/duplicates','/squads']:
        response = client.get(route)
        assert response.status_code == 200, response.text
        assert known['name'] not in response.text
    assert client.post('/evolutions/preview', json={'player_id':identifier,'steps':[]}).status_code in (404,422)
    assert client.patch(f'/players/{identifier}', json={'data_reviewed':True}).status_code == 404
    with SessionLocal() as db:
        assert not db.get(Player, identifier).deleted


def test_review_requires_real_catalog_match_and_cannot_self_certify(client):
    known = documented(client)
    unknown = {**known, 'card_id':'unknown'}
    identifier = client.post('/players', json=unknown).json()['id']
    request = {'player':unknown, 'source_url':'https://www.fut.gg/players/', 'confirmation':f'REVISAR FC27 {identifier}'}
    result = client.post(f'/inventory/quarantine/{identifier}/review', json=request)
    assert result.status_code == 200 and result.json()['quarantined']
    result = client.post(f'/inventory/quarantine/{identifier}/review', json={**request,'player':known})
    assert result.status_code == 200 and result.json()['validation_status'] == 'documented'
    assert client.get('/inventory/quarantine').json()['total'] == 0
    assert client.get('/players').json()['total'] == 1


def test_unverified_market_variant_cannot_be_quoted_traded_or_planned(client):
    stamp = now()-timedelta(seconds=1)
    result = client.post('/market/quotes', json={'variant_id':'invented','market':'Console','game_version':'FC27','amount':100,'kind':'listing','source_url':'https://www.fut.gg/','observed_at':stamp.isoformat(),'expires_at':(stamp+timedelta(hours=1)).isoformat(),'coverage':'manual'})
    assert result.status_code == 409
    assert client.post('/market/alerts', json={'variant_id':'invented','market':'Console','direction':'below','threshold':100}).status_code == 409
    assert client.get('/market/quotes').json() == []
    assert client.get('/market/journal').json()['items'] == []
