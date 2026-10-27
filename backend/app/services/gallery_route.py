"""Finite shared acquisition baskets; estimates never become owned copies or cash."""
from itertools import combinations
from time import monotonic
from app.services.gallery_v2 import evaluate_v2, reward_accounting


def cash_flow(basket, *, fee_basis_points, available, reserve):
    # A conservative feasible sequence buys the basket, evaluates all sets, then sells.
    # Shared acquisitions occur once; no pending sale finances the initial basket.
    unique={c['key']:c for c in basket}
    gross=sum(c['buy'] for c in unique.values())
    projected=0
    for c in unique.values():
        if not c['keep']:
            if c['resale'] is None or fee_basis_points is None:raise ValueError('Precio de salida o comisión desconocidos')
            projected+=c['resale']*(10000-fee_basis_points)//10000
    return dict(gross_purchases=gross,maximum_capital=gross,estimated_net_spend=gross-projected,
        projected_sale_proceeds=projected,realized_profit_loss=None,available_balance=available,
        reserve_coins=reserve,initially_affordable=available-reserve>=gross,
        hypothetical_final_balance=available-gross+projected,
        retained_residual_value=sum(c.get('resale') or 0 for c in unique.values() if c['keep']),
        residual_value_complete=all(c.get('resale') is not None for c in unique.values() if c['keep']),
        fees_rounding='floor_proceeds_per_sale',pending_sales_are_available=False)


def plan_route(sets, history, acquisitions, progress, payload, *, seconds=8):
    started,best,checked,exhausted=monotonic(),None,0,True
    # Historical keys exclude repeat purchases before search.
    historical={e.item_key for e in history}
    acquisitions=[a for a in acquisitions if a['key'] not in historical]
    for size in range(len(acquisitions)+1):
        for basket in combinations(acquisitions,size):
            if monotonic()-started>=seconds:exhausted=False;break
            finance=cash_flow(basket,fee_basis_points=payload.fee_basis_points,available=payload.available_coins,reserve=payload.reserve_coins)
            if (not finance['initially_affordable'] or finance['maximum_capital']>payload.maximum_capital or
                finance['estimated_net_spend']>payload.maximum_loss):continue
            outcomes=[];tokens=0;unknown_rewards=0
            for definition in sets:
                if monotonic()-started>=seconds:exhausted=False;break
                evaluation=evaluate_v2(definition,[*history,*(a['entry'] for a in basket)],seconds=min(.25,max(.01,seconds-(monotonic()-started))))
                rules=definition.rules;p=progress.get(definition.id,{})
                rewards=reward_accounting(definition.grade_thresholds,rules.get('rewards',{}),rules.get('reward_mode','cumulative'),
                    evaluation['score'] if evaluation['complete'] else None,attained=p.get('attained_grade'),claimed=p.get('claimed_grade'))
                gain=rewards['additional_tokens']
                if gain is not None:tokens+=gain
                else:unknown_rewards+=1
                outcomes.append(dict(set_id=definition.id,name=definition.name,evaluation=evaluation,rewards=rewards,
                    progress_source=p.get('source','unknown'),current_grade=p.get('attained_grade')))
                if evaluation.get('search_status') not in {'optimal_relative_to_candidates','infeasible'}:exhausted=False
            if len(outcomes)!=len(sets):break
            checked+=1
            reaches=not unknown_rewards and payload.target_tokens is not None and tokens>=payload.target_tokens
            key=(reaches,-finance['maximum_capital'] if reaches else tokens,-finance['estimated_net_spend'],-len(basket))
            if best is None or key>best[0]:best=(key,basket,finance,outcomes,tokens,unknown_rewards)
        if monotonic()-started>=seconds:break
    if best is None:
        return dict(status='timeout' if not exhausted else 'no_feasible_known_basket',simulation=True,writes_performed=False,checked_baskets=checked)
    _,basket,finance,outcomes,tokens,unknown_rewards=best
    steps=['Revisar reglas, historia elegible, grados declarados y precios fechados.']
    if basket:steps.append('Adquirir manualmente la cesta y registrar evidencia; la simulación no acredita posesión.')
    steps.append('Evaluar cada conjunto manualmente en EA y observar su grado y recompensa.')
    if any(not a['keep'] for a in basket):steps.append('Solo después plantear la reventa manual indicada. Una venta pendiente no aumenta el saldo.')
    steps.append('Conciliar observaciones y declaraciones; no avanzar gastos dependientes de una venta sin evidencia.' if basket else 'Conciliar únicamente los grados y premios observados. Esta ruta no requiere compras.')
    return dict(status='provisional' if unknown_rewards else 'feasible',optimal_relative_to_candidates=exhausted and not unknown_rewards,simulation=True,writes_performed=False,
        additional_tokens=None if unknown_rewards else tokens,known_additional_tokens=tokens,unknown_rewards=unknown_rewards,
        target_reached=not unknown_rewards and payload.target_tokens is not None and tokens>=payload.target_tokens,
        finance=finance,sets=outcomes,acquisitions=[{k:v for k,v in a.items() if k!='entry'} for a in basket],
        checked_baskets=checked,elapsed_ms=round((monotonic()-started)*1000,2),
        coverage='known_history_and_explicit_candidates_only',
        steps=steps)
