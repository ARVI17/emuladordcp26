"""Synthetic rules test composition, never current EA objectives or progress."""
from app.models.entities import Player, now
from app.schemas.api import PlayerCreate
from app.schemas.objective_planning import ObjectiveRules
from app.services.objective_squads import solve_objective_squad, validate_composition, context_compatibility
from app.services.squad_analysis import formation_slots


def cards(count=22):
    positions = [s['position'] for s in formation_slots('4-3-3')]
    return [Player(**PlayerCreate(name=f'Futbolista sintético {i}', rating=70+i%20, position=positions[i%11],
        league='Liga A' if i<8 else 'Liga B', club='Club sintético', nationality='Colombia' if i<8 else 'Chile',
        data_reviewed=True, athlete_id=f'athlete-{i}', attributes={'pace': 70+i%20}).model_dump(),
        id=i+1, deleted=False, availability='available', validation_status='documented', unknown_fields=[])
        for i in range(count)]


def goal(identifier=1, conditions=(), **overrides):
    return dict(id=identifier, rules=ObjectiveRules(source_reference='Prueba sintética',
        source_text='Condiciones inventadas únicamente para probar el motor', observed_at=now(),
        reviewed=True, mode=overrides.pop('mode','squad_battles'), min_difficulty=overrides.pop('min_difficulty','professional'),
        loans_allowed=overrides.pop('loans_allowed',False), conditions=list(conditions), **overrides))


def condition(identifier, quantity='min', count=1, scope='starters', **extra):
    return dict(id=identifier, source_text='Condición sintética', field='league', value='Liga A',
        quantity=quantity, count=count, scope=scope, reviewed=True, **extra)


def raw_lineup(result):
    return [dict(player_id=r['player']['id'],slot=r['slot']) for r in result['lineup']]


def test_min_max_exact_and_starter_bench_scopes_are_independently_validated():
    players=cards()
    goals=[goal(conditions=[condition('min',count=6),condition('max','max',0,'bench'),condition('exact','exact',8,'roster')])]
    result=solve_objective_squad(players,goals,bench_size=7)
    assert result['composition_ready'] and {r['status'] for r in result['checklist']}=={'met'}
    lineup, bench=raw_lineup(result),[p['id'] for p in result['bench']]
    independent=validate_composition(players,lineup,bench,goals,'4-3-3',7)
    assert independent['composition_ready']
    # Same total across the roster does not excuse putting required starters on the bench.
    starter=next(row for row in lineup if row['player_id']<=8 and row['player_id']+11 in bench)
    old=starter['player_id'];starter['player_id']=old+11
    bench[bench.index(old+11)]=old
    wrong=validate_composition(players,lineup,bench,goals,'4-3-3',7)
    assert not wrong['composition_ready'] and any(c['condition_id']=='max' and c['status']=='failed' for c in wrong['checklist'])


def test_unknown_metadata_never_proves_exact_or_maximum_and_unparsed_text_stays_pending():
    players=cards()
    for p in players:
        p.validation_evidence={'kind':'observed_copy','observed_fields':['name','rating','position','is_loan']}
    for quantity in ('max','exact'):
        result=solve_objective_squad(players,[goal(conditions=[condition('unknown',quantity,0)])],bench_size=0)
        assert result['status']=='infeasible'  # Cannot verify zero without league metadata.
    goals=[goal(conditions=[dict(id='text',source_text='Texto ambiguo sin regla normalizada',field=None),
        condition('participate',scope='participants')])]
    result=solve_objective_squad(players,goals,bench_size=0)
    assert result['valid'] and not result['composition_ready']
    assert all(c['status']=='pending' for c in result['checklist'])


def test_mode_conflicts_require_separate_sessions_and_difficulty_uses_stricter_rule():
    conflict=context_compatibility([goal(1,mode='rivals'),goal(2,mode='squad_battles'),goal(3,mode='any')])
    assert not conflict['compatible'] and len(conflict['sessions'])==2
    assert all(3 in session['objective_ids'] for session in conflict['sessions'])
    together=context_compatibility([goal(1,min_difficulty='amateur'),goal(2,min_difficulty='world_class')])
    assert together['compatible'] and together['min_difficulty']=='world_class'


def test_loans_and_exclusions_apply_without_consuming_protected_players():
    players=cards()
    for p in players[:11]:
        p.protected=True
    result=solve_objective_squad(players,[goal()],bench_size=0)
    assert result['valid']  # Protected copies can play.
    avoided=solve_objective_squad(players,[goal()],bench_size=0,excluded=set(range(1,12)))
    assert avoided['valid'] and all(r['player']['id']>11 for r in avoided['lineup'])
    for p in players:
        p.is_loan=True
    assert solve_objective_squad(players,[goal()],bench_size=0)['status']=='infeasible'
    assert solve_objective_squad(players,[goal(loans_allowed=True)],bench_size=0)['valid']
    assert solve_objective_squad(players,[goal(loans_allowed=True,minimum_loan_matches=2)],bench_size=0)['status']=='infeasible'
    assert all(p.protected and not p.deleted for p in players[:11])


def test_rating_booleans_and_positions_use_typed_predicates():
    players=cards()
    goals=[goal(conditions=[
        dict(id='rating',source_text='Al menos una media 85 o superior',field='rating',comparison='ge',value=85,count=1,reviewed=True),
        dict(id='keeper',source_text='Exactamente un portero en el once',field='position',value='POR',quantity='exact',count=1,reviewed=True),
        dict(id='special',source_text='Ninguna especial en convocatoria',field='special',value=True,quantity='max',count=0,scope='roster',reviewed=True),
    ])]
    result=solve_objective_squad(players,goals,bench_size=0)
    assert result['composition_ready'] and len(result['checklist'])==3
