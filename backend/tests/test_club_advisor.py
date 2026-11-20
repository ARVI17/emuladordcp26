"""The dashboard may recommend a playing XI before it can safely suggest disposals."""
from datetime import timedelta

import pytest

from app.models.entities import now
from test_assisted import capture, enter, frame, review
from test_browser_auto import post, setup, snapshot, start

pytestmark = pytest.mark.catalog_boundary


def observed_dcp(client, monkeypatch, session, name, expiry):
    row = frame(client, monkeypatch, session, text='FC27 DCP ' + name, scope='dcp', page=name)
    review(client, row, dict(phrase='GUARDAR OBSERVACION', edition='FC27', dcp=dict(name=name, reviewed=True,
        requirements={'squad_size': 1, 'min_rating': 80}, source_text=name, expires_at=expiry)))


def test_home_connects_two_new_reads_to_squad_dcp_and_grounded_explanation(client, monkeypatch):
    setup(client, monkeypatch)
    session = capture(client)
    observed_dcp(client, monkeypatch, session, 'Activo', (now()+timedelta(days=2)).isoformat())
    observed_dcp(client, monkeypatch, session, 'Vencido', (now()-timedelta(days=1)).isoformat())
    observed_dcp(client, monkeypatch, session, 'Fecha pendiente', None)
    before = client.get('/club/opportunities').json()
    assert [(d['name'], d['status']) for d in before['dcp']] == [('Activo', 'protection_pending')]
    assert not before['dcp'][0]['players'] and not before['sales']['items']
    stable = None
    for _ in range(2):
        ticket, headers = start(client)
        result = post(client, headers, snapshot(ticket))['result']
        plan = client.get('/club/match-plan').json()
        assert plan['reviewed'] == 20 and plan['latest_card_observation']
        assert plan['protection'] == dict(ready=True, starters=11, bench=7, reserves=0)
        team = plan['squad']
        ids = [p['id'] for p in team['lineup']+team['bench']]
        assert len(set(ids)) == len(ids) == 18 and len(team['lineup']) == 11
        signature = (set(result['inventory_ids']), ids, team['formation'])
        if stable is not None:
            assert signature == stable
        stable = signature
        options = client.get('/club/opportunities').json()
        assert len(options['dcp']) == 1 and options['dcp'][0]['status'] == 'covered'
        assert set(options['dcp'][0]['players']) <= {'Auto sintético 18', 'Auto sintético 19'}
        assert options['dcp'][0]['card_value'] is None
        assert options['sales']['items'] == [] and client.get('/players').json()['total'] == 20
        assert client.get('/squads/main').json()['protected_copy_ids'] == result['protected_copy_ids']

    assert 'Activo' in client.post('/ai/chat', json={'message':'Qué DCP puedo cubrir'}).json()['answer']
    assert 'mercado de consola' in client.post('/ai/chat', json={'message':'Qué cartas puedo vender'}).json()['answer']
    assert 'Galería' in client.post('/ai/chat', json={'message':'Cómo avanzo en Galería'}).json()['answer']
    calls = []
    async def local_model(intent, context):
        calls.append((intent, context))
        return dict(available=True, focus='bench', answer='precio inventado')
    monkeypatch.setattr('app.api.routes.chat', local_model)
    reply = client.post('/ai/chat', json={'message':'Explica mi equipo', 'squad_style':'wide'}).json()
    assert reply['available'] and 'de 7 plazas' in reply['answer'] and 'precio inventado' not in reply['answer']
    assert calls[0][0] == 'squad' and 'wide' in calls[0][1] and 'sintético' not in calls[0][1]
    async def offline(*_):
        return dict(available=False)
    monkeypatch.setattr('app.api.routes.chat', offline)
    fallback = client.post('/ai/chat', json={'message':'Explícame este equipo'}).json()
    assert not fallback['available'] and team['formation'] in fallback['answer'] and '20 cartas' in fallback['answer']
    enter(client, 'Otro club')
    assert client.get('/club/match-plan').json()['squad'] is None
    assert client.get('/club/opportunities').json()['dcp'] == []


def test_unconnected_live_session_cannot_compute_a_personal_plan(client):
    result = client.post('/app/entries', json={'nonce':'home-live-no-proof','mode':'live','context_id':1})
    client.headers['X-App-Entry'] = str(result.json()['entry_id'])
    assert client.get('/club/match-plan').status_code == 409
    assert client.get('/club/opportunities').status_code == 409


def test_sale_candidates_need_exact_current_console_listing_and_spare_copy(client):
    from app.db.session import SessionLocal
    from app.models.planner import ClubContext, MarketQuote
    from test_main_squad import choose_main
    from test_planner import fake_run, publish
    from test_remote_admission import item, reading

    context, run = fake_run(client)
    with SessionLocal() as db:
        db.get(ClubContext, context).platform = 'Console'
        db.commit()
    inventory = reading([item(i, tradable=True) for i in range(20)])
    inventory.platform, inventory.coins = 'Console', 500
    inventory.coverage['coins'] = {'complete': True}
    publish(run, inventory)
    main, _ = choose_main(client)
    cards = client.get('/players').json()['items']
    spare = next(p for p in cards if p['id'] not in main['protected_copy_ids'])
    locked = next(p for p in cards if p['id'] in main['protected_copy_ids'])
    at = now()
    with SessionLocal() as db:
        def quote(card, amount, age=1, **changes):
            fields = dict(club_context_id=context, game_version='FC27', variant_id=card['card_id'],
                          market='Console', kind='listing', currency='coins', amount=amount,
                          observed_at=at-timedelta(minutes=age), expires_at=at+timedelta(hours=1),
                          source_url='https://example.test/observation', coverage='Anuncio sintético')
            db.add(MarketQuote(**(fields | changes)))
        quote(locked, 10000)
        quote(spare, 800, age=4)
        quote(spare, 700)
        quote(spare, 4000, age=0, market='PC')
        quote(spare, 3200, age=0, kind='bid')
        quote(spare, 4500, age=0, expires_at=at)
        quote(spare, 8000, age=1500)
        quote(spare, 1000, age=-60)
        db.commit()
    assert not client.get('/club/opportunities').json()['sales']['items']  # undocumented variant
    from catalog_fixture import witness
    for p in (spare, locked):
        witness({k:p[k] for k in ('name','rating','position','card_type','card_id','league','club','nationality')})
    sales = client.get('/club/opportunities').json()['sales']
    assert [(p['id'], p['amount']) for p in sales['items']] == [(spare['id'], 700)]
    assert client.get('/squads/main').json()['protected_copy_ids'] == main['protected_copy_ids']
