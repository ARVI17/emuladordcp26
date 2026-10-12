from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.entities import Player
from app.services.joint import joint_dcp
from test_main_squad import card, segment


def test_joint_budget_and_priority_choose_whole_segments_without_unknown_prices(client):
    cheap=card(client,price=10)
    expensive=card(client,price=30)
    unknown=card(client,price=None)
    rules=[{'id':11,'requirements':{'squad_size':1}},{'id':12,'requirements':{'squad_size':1}}]
    with SessionLocal() as db:
        players=list(db.scalars(select(Player).where(Player.id.in_([cheap['id'],expensive['id'],unknown['id']]))))
        all_required=joint_dcp(players,rules,set(),max_total_value=10)
        assert all_required['status']=='infeasible'
        chosen=joint_dcp(players,rules,set(),max_total_value=10,priority_ids=[12,11],allow_partial=True)
        assert chosen['status']=='optimal' and chosen['solutions'][0]['segment_id']==12
        assert chosen['solutions'][0]['player_ids']==[cheap['id']]
        assert chosen['total_value']==10 and chosen['unknown_price_count']==0
        assert chosen['pending_segment_ids']==[11] and not chosen['all_segments_covered']
        assert all(not p.deleted for p in players)


def test_joint_budget_cannot_buy_eligibility_or_override_protection(client):
    protected=card(client,price=1,protected=True)
    unknown=card(client,price=None)
    rule=[{'id':1,'requirements':{'squad_size':1}}]
    with SessionLocal() as db:
        players=[db.get(Player,p['id']) for p in (protected,unknown)]
        assert joint_dcp(players,rule,set(),max_total_value=100000)['status']=='infeasible'
        no_limit=joint_dcp(players,rule,set())
        assert no_limit['solutions'][0]['player_ids']==[unknown['id']]
        assert no_limit['total_value'] is None and no_limit['unknown_price_count']==1


def test_joint_api_validates_priorities_and_preserves_inventory(client):
    p=card(client,price=50)
    ids=[segment(client),segment(client)]
    payload={'player_ids':[p['id']],'segment_ids':ids,'max_total_value':50,'allow_partial':True,'priority_ids':ids[::-1]}
    result=client.post('/dcp/joint-preview',json=payload)
    assert result.status_code==200,result.text
    assert result.json()['solutions'][0]['segment_id']==ids[-1]
    assert result.json()['additional_cost']==0
    assert client.post('/dcp/joint-preview',json={**payload,'priority_ids':[999999]}).status_code==422
    assert client.post('/dcp/joint-preview',json={**payload,'allow_protected':True}).status_code==422
    assert client.get(f"/players?search={p['name']}").json()['total']>=1
