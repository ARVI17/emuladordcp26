"""Synthetic text only; personal acceptance is recorded separately."""
import pytest
from app.services.assisted import parse_screen
from app.services.import_export import POSITION_ALIASES, extract_inventory_candidates
from test_assisted import enter

pytestmark = pytest.mark.catalog_boundary


def preview(client, page='Primera página', text=None):
    response = client.post('/assisted/text-preview', json={'page':page, 'text':text or '\n'.join(f'85 CB Futbolista {i}' for i in range(20))})
    assert response.status_code == 200, response.text
    return response.json()


def body(reading, ids=None):
    return {'ownership_confirmed':True, 'review':{'phrase':'GUARDAR OBSERVACION','edition':'FC27',
        'cards':[{**c, 'existing_player_id':ids[i] if ids else None} for i,c in enumerate(reading['original']['cards'])]}}


def save(client, reading, payload=None):
    response = client.post(f'/assisted/text-readings/{reading["id"]}/review',json=payload or body(reading))
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize('position,expected', POSITION_ALIASES.items())
def test_bilingual_positions(position, expected):
    for text in (f'85 {position} Futbolista', f'85\n{position}\nFutbolista'):
        assert extract_inventory_candidates(text)[0]['position'] == expected
    assert parse_screen(f'My Club Players\n85 {position} Futbolista','inventory')['cards'][0]['position'] == expected
    assert parse_screen(f'Jugadores de mi club\n85 {position} Futbolista','inventory')['cards'][0]['position'] == expected
    assert parse_screen(f'FC26 My Club Players\n85 {position} Futbolista','inventory') is None


def test_twenty_review_corrections_two_fresh_repeats(client):
    enter(client)
    first=preview(client)
    assert client.get('/players').json()['total'] == 0
    request=body(first)
    request['review']['cards'][0]['name']='Futbolista corregido'
    request['review']['cards'][0]['position']='LD'
    initial=save(client,first,request)
    ids=initial['reviewed']['copy_ids']
    assert len(set(ids)) == 20
    assert save(client,first,request)['reviewed']['copy_ids'] == ids
    assert client.post(f'/players/{ids[0]}/protect').status_code == 200
    corrected='85 RB Futbolista corregido\n'+'\n'.join(f'85 CB Futbolista {i}' for i in range(1,20))
    for n in range(2):
        reading=preview(client,page=f'Nueva lectura {n}',text=corrected)
        assert reading['id'] != first['id']
        assert client.post(f'/assisted/text-readings/{reading["id"]}/review',json=body(reading)).status_code == 409
        assert save(client,reading,body(reading,ids))['reviewed']['copy_ids'] == ids
        players=client.get('/players?limit=100').json()
        assert players['total'] == 20
        assert {p['id'] for p in players['items']} == set(ids)
        assert all(p['ownership_source']=='user_reviewed_text' and p['tradable'] is None for p in players['items'])
        assert next(p for p in players['items'] if p['id']==ids[0])['effective_protected'] is True
        assert client.delete(f'/players/{ids[0]}').status_code == 409
    repeated=preview(client,page='Nueva lectura 1',text=corrected.replace('RB','LD').replace('CB','DFC'))
    assert repeated['repeated'] and repeated['reviewed']['copy_ids'] == ids
    assert client.get('/squads/main').json()['identified'] is False


def test_text_review_requires_ownership_and_bound_candidates(client):
    enter(client)
    reading=preview(client,text='85 GK Portero | DIV 81 HAN 82 KIC 70 REF 85 SPD 50 POS 80')
    assert reading['original']['cards'][0]['attributes']['diving'] == 81
    payload=body(reading)
    assert client.post(f'/assisted/readings/{reading["id"]}/review',json=payload['review']).status_code == 422
    assert client.post(f'/assisted/text-readings/{reading["id"]}/review',json={**payload,'ownership_confirmed':False}).status_code == 422
    payload['review']['cards'][0]['ordinal']=1
    assert client.post(f'/assisted/text-readings/{reading["id"]}/review',json=payload).status_code == 422
    assert client.get('/players').json()['total'] == 0
    enter(client,'Otro contexto sintético')
    assert client.post(f'/assisted/text-readings/{reading["id"]}/review',json=body(reading)).status_code == 404


@pytest.mark.parametrize('text', ['password secreto','85 CB Test\ntexto ilegible','85 GK Test | PAC 90','85 CB Test | PAC 99 PAC 98','85 CB Test | DEF 100', '85 GK '+'A'*101, '\n'.join('85 CB Test' for _ in range(31))])
def test_invalid_or_sensitive_text_stores_no_draft(client,text):
    enter(client)
    assert client.post('/assisted/text-preview',json={'page':'Prueba','text':text}).status_code == 422
    assert client.get('/assisted/readings').json()['items'] == []


def test_indistinguishable_rows_do_not_silently_merge(client):
    enter(client)
    reading=preview(client,text='85 CB Igual\n85 DFC Igual')
    assert client.post(f'/assisted/text-readings/{reading["id"]}/review',json=body(reading)).status_code == 409
    assert client.get('/players').json()['total'] == 0


def test_retired_copy_cannot_be_recreated(client):
    enter(client)
    reading=preview(client,text='85 CB Futbolista retirado')
    identifier=save(client,reading)['reviewed']['copy_ids'][0]
    assert client.delete(f'/players/{identifier}').status_code == 200
    reread=preview(client,page='Nueva observación',text='85 DFC Futbolista retirado')
    for ids in (None,[identifier]):
        assert client.post(f'/assisted/text-readings/{reread["id"]}/review',json=body(reread,ids)).status_code == 409
    assert client.get('/players').json()['total'] == 0
