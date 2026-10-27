"""All rule values in this module are SYNTHETIC, never production game constants."""
from types import SimpleNamespace as NS
import pytest
from app.schemas.fc27 import GallerySetInput
from app.services.gallery import evaluate_set, item_key
from app.services.gallery_v2 import validate_selection, reward_accounting


def definition(**changes):
    payload=dict(name='Conjunto SINTÉTICO',rules=dict(schema_version=2,size=4,multiplicity='variant',evidence_status='scenario'),
        tags=[dict(name='Solo bajas',field='card_type',value='baja',minimum=2,mode='percentage',tiers=[dict(minimum=2,percent_basis_points=1000)])],
        grade_thresholds={'D':0,'C':1000,'B':2000,'A':2500,'S':3000},rules_reviewed=True)
    payload.update(changes)
    data=GallerySetInput.model_validate(payload).model_dump(mode='json')
    return NS(**data)


def entries(scores=(1000,1000,100,100)):
    return [NS(id=i+1,item_key=str(i),player_id=i+1,game_version='FC27',recorded_at=None,
        snapshot=dict(card_id=f'synthetic-{i}',athlete_id=f'athlete-{i}',name=f'Sintético {i}',rating=80,
            position='MC',card_type='baja' if i>1 else 'alta',gallery_score=score,score_reviewed=True,
            is_loan=False,is_evolution=False,first_owner=None)) for i,score in enumerate(scores)]


def test_percentage_matches_subtotal_not_fixed_or_whole_set():
    rows=entries();definition_=definition()
    result=evaluate_set(definition_,rows)
    assert result['tags'][0]['bonus']==20
    assert result['tags'][0]['basis_score']==200
    assert result['score']==2220
    assert validate_selection(definition_,rows)['score']==result['score']
    legacy=definition(rules={'size':4},tags=[dict(name='Heredado',field='card_type',value='baja',minimum=2,bonus=10)])
    assert evaluate_set(legacy,rows)['score']==2210


def test_tiers_floor_unknown_owner_and_unknown_score():
    tag=dict(name='Propietario',field='first_owner',value=True,minimum=2,mode='percentage',tiers=[dict(minimum=2,percent_basis_points=3333),dict(minimum=3,percent_basis_points=5000)])
    rules=definition(tags=[tag]);rows=entries((1,2,3,4))
    assert evaluate_set(rules,rows)['score'] is None
    for row in rows:row.snapshot['first_owner']=False
    for row in rows[:2]:row.snapshot['first_owner']=True
    result=evaluate_set(rules,rows);assert result['tags'][0]['bonus']==0
    rows[2].snapshot['first_owner']=True
    result=evaluate_set(rules,rows);assert result['tags'][0]['bonus']==3
    assert result['tags'][0]['tier_minimum']==3
    rows[0].snapshot['gallery_score']=None
    assert evaluate_set(rules,rows)['grade'] is None


def test_reward_deltas_incremental_claimed_and_exhaustion():
    thresholds=dict(D=0,C=100,B=200,A=300,S=400)
    cumulative=dict(D=0,C=5,B=15,A=30,S=50)
    result=reward_accounting(thresholds,cumulative,'cumulative',400,attained='B',claimed='C')
    assert result['additional_tokens']==35 and result['pending_tokens']==10
    incremental=dict(D=0,C=5,B=10,A=15,S=20)
    assert reward_accounting(thresholds,incremental,'incremental',400,attained='B')['additional_tokens']==35
    assert reward_accounting(thresholds,cumulative,'cumulative',400,attained='S')['exhausted']
    assert reward_accounting(thresholds,cumulative,'cumulative',None,attained='B')['additional_tokens'] is None


def test_holographic_levels_multiplicity_and_group_rules():
    base=dict(card_id='SYNTHETIC-shared-id',is_holographic=True)
    assert item_key({**base,'holographic_level':1})!=item_key({**base,'holographic_level':2})
    rows=entries()
    for row in rows:row.snapshot.update(name='Mismo nombre',athlete_id='same',nationality='CO')
    assert evaluate_set(definition(tags=[]),rows)['complete']
    athlete=definition(rules=dict(schema_version=2,size=4,multiplicity='athlete',evidence_status='scenario'),tags=[])
    assert not evaluate_set(athlete,rows)['complete']
    grouped=definition(tags=[dict(name='Misma nación',field='nationality',aggregation='largest_group',minimum=2,mode='percentage',tiers=[dict(minimum=2,percent_basis_points=1000)])])
    assert evaluate_set(grouped,rows)['tags'][0]['bonus']==220
    rows[0].snapshot['is_evolution']=True
    assert evaluate_set(grouped,rows)['filled_slots']==3


def test_versions_do_not_silently_change_legacy_rules():
    with pytest.raises(ValueError):definition(rules=dict(schema_version=2,size=4))
    with pytest.raises(ValueError):definition(rules=dict(size=4))


def test_shared_basket_capital_and_net_cost_are_distinct():
    from app.services.gallery_route import cash_flow,plan_route
    from app.schemas.gallery_planning import GalleryRouteInput
    card=entries((1000,))[0]
    acquisition=dict(key=card.item_key,entry=card,buy=10000,resale=9800,keep=False)
    finance=cash_flow([acquisition,acquisition],fee_basis_points=500,available=10000,reserve=0)
    assert finance['gross_purchases']==10000
    assert finance['maximum_capital']==10000
    assert finance['projected_sale_proceeds']==9310
    assert finance['estimated_net_spend']==690
    assert finance['realized_profit_loss'] is None
    assert not cash_flow([acquisition],fee_basis_points=500,available=690,reserve=0)['initially_affordable']
    definition_=definition(rules=dict(schema_version=2,size=1,multiplicity='variant',evidence_status='scenario',rewards={'C':5}),tags=[],grade_thresholds={'C':1000})
    definition_.id=1
    second=definition(rules=definition_.rules,tags=[],grade_thresholds={'C':1000});second.id=2
    request=GalleryRouteInput(set_ids=[1,2],mode='token_target',target_tokens=10,available_coins=10000,maximum_capital=10000,maximum_loss=690,fee_basis_points=500)
    result=plan_route([definition_,second],[],[acquisition],{},request)
    assert result['additional_tokens']==10
    assert result['finance']['gross_purchases']==10000 and len(result['acquisitions'])==1
    # Eligible history can be reused without repurchasing or inventing ownership.
    result=plan_route([definition_,second],[card],[acquisition],{},request)
    assert result['additional_tokens']==10 and result['finance']['gross_purchases']==0


def test_minimum_target_score_and_independent_cp_validation():
    rows=entries((500,400,200,100))
    rules=definition(rules=dict(schema_version=2,size=2,multiplicity='variant',evidence_status='scenario'),tags=[],grade_thresholds={'C':300})
    from app.services.gallery_v2 import evaluate_v2
    result=evaluate_v2(rules,rows,target_score=300)
    assert result['score']==300
    assert result['objective']=='minimum_score_reaching_target'
