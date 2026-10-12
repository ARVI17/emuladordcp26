from datetime import timedelta
from sqlalchemy import select, func
from app.db.session import SessionLocal
from app.models.entities import Player, now
from app.models.planner import ClubPlan, Reservation, MarketQuote
from test_planner import card, plan, approve, fake_run, publish, remote


def quote(client, **extra):
    stamp = now()-timedelta(seconds=1)
    data = dict(variant_id='variant-test', market='Console', game_version='FC27', kind='listing', amount=100, source_url='https://example.com/synthetic', coverage='Synthetic manual observation', observed_at=stamp.isoformat(), expires_at=(stamp+timedelta(hours=1)).isoformat())
    response = client.post('/market/quotes', json={**data, **extra})
    assert response.status_code == 201, response.text
    return response.json()['id']


def alert(client, **extra):
    response = client.post('/market/alerts', json={'variant_id': 'variant-test', 'market': 'Console', 'direction': 'below', 'threshold': 100, **extra})
    assert response.status_code == 201, response.text
    return response.json()


def test_series_filters_identity_kind_edition_and_keeps_dated_sources(client):
    old = quote(client, amount=120, observed_at=(now()-timedelta(hours=26)).isoformat(), expires_at=(now()-timedelta(hours=25)).isoformat())
    newest = quote(client)
    for fields in ({'market': 'PC'}, {'kind': 'observed_sale'}, {'variant_id': 'different'}):
        quote(client, **fields)
    result = client.get('/market/series?variant_id=variant-test&market=Console&kind=listing').json()
    assert [r['id'] for r in result['points']] == [old, newest]
    assert result['points'][0]['expired'] and not result['points'][1]['expired']
    assert all(r['source_url'] == 'https://example.com/synthetic' for r in result['points'])
    assert result['sales_volume'] is None and result['prediction'] is None
    assert len(client.get('/market/series?variant_id=variant-test&kind=observed_sale').json()['points']) == 1


def test_alerts_no_data_trigger_stale_disabled_and_context_isolation(client):
    row = alert(client)
    assert row['status'] == 'no_data'
    identifier = quote(client)
    rows = client.get('/market/alerts').json()['items']
    assert rows[0]['status'] == 'triggered' and not rows[0]['remote_action']
    with SessionLocal() as db:
        db.get(MarketQuote, identifier).expires_at = now()-timedelta(seconds=1)
        db.commit()
    assert client.get('/market/alerts').json()['items'][0]['status'] == 'stale'
    assert client.patch(f"/market/alerts/{row['id']}", json={'enabled': False}).json()['status'] == 'disabled'
    assert client.patch('/profile', json={'game_version': 'FC26'}).status_code == 422
    fake_run(client)
    assert client.get('/market/alerts').json()['items'] == []
    assert client.get('/market/series?variant_id=variant-test').json()['points'] == []


def test_configured_commission_costs_and_adverse_scenario(client):
    result = client.post('/market/simulate', json={'purchase': 10000, 'sale': 11000, 'adverse_sale': 9500, 'tax_percent': 10, 'other_costs': 100, 'price_increment': 50}).json()
    assert result['estimated_profit'] == -200 and result['adverse_profit'] == -1550
    assert result['break_even'] == 11250 and result['decision'] == 'no_operar'
    assert result['tax_assumption']['percent'] == 10 and not result['tax_assumption']['official_fc27_confirmation']
    assert client.post('/market/simulate', json={'purchase': 0, 'sale': 0, 'adverse_sale': 0, 'tax_percent': 100}).status_code == 422


def test_agenda_shared_copies_priority_and_comparison_are_read_only(client):
    p = card(client, price=None)
    a = plan(client, [{'kind': 'keep', 'player_ids': [p['id']]}])
    b = plan(client, [{'kind': 'keep', 'player_ids': [p['id']]}])
    comparison = client.post('/plans/compare', json={'a_id': a['id'], 'b_id': b['id']})
    assert comparison.status_code == 200, comparison.text
    assert comparison.json()['shared_copy_ids'] == [p['id']]
    assert comparison.json()['a']['unknown_price_count'] == 1
    result = client.post('/plans/agenda', json={'budget': 10000, 'priority_ids': [b['id']]}).json()
    assert [r['id'] for r in result['selected']] == [b['id']]
    assert result['pending'][0]['id'] == a['id'] and 'comprometidas' in result['pending'][0]['reason']
    assert not result['resources_reserved']
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Reservation)) == 0
        assert db.scalar(select(func.count()).select_from(ClubPlan)) == 2
        assert not db.get(Player, p['id']).deleted


def test_agenda_deducts_coin_claims_does_not_reuse_budget_and_quotes_expire(client):
    q = quote(client, amount=700)
    rows = [plan(client, [{'kind': 'buy', 'quote_id': q, 'max_cost': 700}]) for _ in range(3)]
    approve(client, rows[0])
    result = client.post('/plans/agenda', json={'budget': 1500, 'reserve_coins': 100, 'priority_ids': [rows[1]['id']]}).json()
    assert result['committed_coins'] == 700 and result['remaining_coins'] == 800-700
    assert len(result['selected']) == 1 and len(result['pending']) == 1
    with SessionLocal() as db:
        db.get(MarketQuote, q).expires_at = now()-timedelta(seconds=1)
        db.commit()
    result = client.post('/plans/agenda', json={'budget': 10000}).json()
    assert not result['selected'] and len(result['pending']) == 2


def test_stale_inventory_pauses_agenda_refresh_makes_new_draft_without_approval(client):
    p = card(client)
    a = plan(client, [{'kind': 'keep', 'player_ids': [p['id']]}])
    b = plan(client, [{'kind': 'keep', 'player_ids': [p['id']]}])
    client.patch(f"/players/{p['id']}", json={'notes': 'Changed local evidence'})
    result = client.post('/plans/agenda', json={'budget': 10000}).json()
    assert not result['selected'] and len(result['pending']) == 2
    assert client.post('/plans/compare', json={'a_id': a['id'], 'b_id': b['id']}).status_code == 409
    refreshed = client.post(f"/plans/{a['id']}/refresh")
    assert refreshed.status_code == 201, refreshed.text
    assert refreshed.json()['id'] != a['id'] and refreshed.json()['status'] == 'draft'
    assert refreshed.json()['reserved'] == []
    with SessionLocal() as db:
        assert db.get(ClubPlan, a['id']).plan_hash == a['plan_hash']
    fake_run(client)
    assert client.post(f"/plans/{a['id']}/refresh").status_code == 404


def test_agenda_live_balance_coverage_and_foreign_priorities_blocked(client):
    context, run = fake_run(client)
    publish(run, remote())
    result = client.post('/plans/agenda', json={'budget': 999999})
    assert result.status_code == 200, result.text
    assert result.json()['remaining_coins'] == 10000
    assert client.post('/plans/agenda', json={'budget': 10, 'priority_ids': [999]}).status_code == 422
    assert client.post('/plans/agenda', json={'budget': 10, 'priority_ids': [1, 1]}).status_code == 422
    _, run = fake_run(client, context)
    publish(run, remote(coverage={'inventory': {'complete': True}}))
    assert client.post('/plans/agenda', json={'budget': 999999}).status_code == 409
