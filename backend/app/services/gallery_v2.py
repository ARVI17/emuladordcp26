"""Versioned scenario calculator. Exact integer arithmetic, no executable rules."""
from collections import defaultdict
from itertools import combinations
from time import monotonic
from app.schemas.fc27 import GalleryRules, GalleryTag


def known(card, field):
    if field in card.get('unknown_fields', []): return None
    return card.get(field)


def normalized(value):
    return value.strip().casefold() if isinstance(value,str) else value


def matches(card, tag):
    value = known(card,tag.field)
    return value is not None and type(value) == type(tag.value) and normalized(value) == normalized(tag.value)


def tag_breakdown(cards, tag):
    """Independent evaluator: select one tier; floor the matched subtotal once."""
    from app.services.gallery import reviewed_score
    unknown = sum(known(c,tag.field) is None for c in cards)
    if tag.aggregation == 'matched':
        matched = [c for c in cards if matches(c,tag)]
        count = len(matched)
    else:
        groups = defaultdict(list)
        for c in cards:
            value = known(c,tag.field)
            if value is not None: groups[normalized(value)].append(c)
        if tag.aggregation == 'distinct':
            count = len(groups)
            matched = [c for group in groups.values() for c in group]
        else:
            # Explicit semantics: largest group, then largest known subtotal, then key.
            matched = max(sorted(groups.items(),key=lambda x:str(x[0])),
                key=lambda x:(len(x[1]),sum(reviewed_score(c) or 0 for c in x[1])), default=(None,[]))[1]
            count = len(matched)
    scores = [reviewed_score(c) for c in matched]
    base = None if any(s is None for s in scores) else sum(scores)
    if tag.mode == 'fixed_legacy':
        bonus = tag.bonus if count >= tag.minimum else 0
        tier, rate = tag.minimum, None
    else:
        reached = [t for t in tag.tiers if count >= t.minimum]
        tier = reached[-1].minimum if reached else None
        rate = reached[-1].percent_basis_points if reached else 0
        bonus = (base*rate)//10000 if base is not None else None
    return dict(name=tag.name, count=count, minimum=tag.minimum, tier_minimum=tier,
        mode=tag.mode, aggregation=tag.aggregation, basis_score=base, percent_basis_points=rate,
        bonus=bonus, achieved=count >= tag.minimum, unknown_field_count=unknown,
        rounding='floor_per_tag', provisional=bool(unknown) or base is None)


def reward_accounting(thresholds, rewards, mode, score, *, attained=None, claimed=None):
    order = sorted(thresholds, key=lambda name: (thresholds[name],name))
    if len(set(thresholds.values())) != len(order):
        raise ValueError('Los grados necesitan umbrales distintos')
    if any(g is not None and g not in order for g in (attained,claimed)):
        raise ValueError('Grado actual o reclamado desconocido')
    if claimed is not None and (attained is None or order.index(claimed)>order.index(attained)):
        raise ValueError('Lo reclamado supera el grado obtenido')
    if set(rewards) != set(order):
        return dict(status='unknown_rewards', reached=None, additional_tokens=None, pending_tokens=None)
    totals, total = {}, 0
    for grade in order:
        total = total+rewards[grade] if mode == 'incremental' else rewards[grade]
        if totals and total < list(totals.values())[-1]:
            raise ValueError('Las recompensas acumuladas no pueden decrecer')
        totals[grade] = total
    earned = totals[attained] if attained else 0
    received = totals[claimed] if claimed else 0
    if received > earned: raise ValueError('Lo reclamado supera el grado obtenido')
    reached = [g for g in order if score is not None and score >= thresholds[g]]
    target = reached[-1] if reached else None
    return dict(status='known' if score is not None else 'pending_score', reached=target,
        cumulative_rewards=totals, earned_tokens=earned, claimed_tokens=received,
        pending_tokens=earned-received, additional_tokens=max(0,totals.get(target,0)-earned) if score is not None else None,
        exhausted=bool(order and earned == totals[order[-1]]), available_balance=None)


def validate_selection(gallery_set, selected):
    from app.services.gallery import reviewed_score, item_key, folded
    rules = GalleryRules.model_validate(gallery_set.rules)
    cards = [e.snapshot for e in selected]
    if len(selected) > rules.size or len({e.id for e in selected}) != len(selected):
        raise ValueError('Selección con entradas repetidas o demasiadas cartas')
    if any(known(c,'is_loan') is not False or known(c,'is_evolution') is not False for c in cards):
        raise ValueError('La selección requiere historia elegible de la variante base')
    if rules.multiplicity == 'athlete':
        keys = [known(c,'athlete_id') for c in cards]
        if any(k is None for k in keys): raise ValueError('Falta identidad de deportista para esta regla')
    elif rules.multiplicity == 'variant':
        keys = [item_key(c) for c in cards]
    else: keys = [e.id for e in selected]
    if len(set(keys)) != len(keys): raise ValueError('La selección incumple multiplicidad')
    for c in cards:
        if (c.get('rating') is None or c['rating'] < rules.min_rating or
            (rules.holographic_only and known(c,'is_holographic') is not True) or
            any(getattr(rules,k) and folded(known(c,k)) != folded(getattr(rules,k)) for k in ('league','club','nationality','card_type'))):
            raise ValueError('Entrada fuera de los requisitos del conjunto')
    scores = [reviewed_score(c) for c in cards]
    tags = [tag_breakdown(cards, GalleryTag.model_validate(t)) for t in gallery_set.tags]
    unknown_scores = sum(s is None for s in scores)
    pending = unknown_scores or any(t['provisional'] for t in tags) or not gallery_set.rules_reviewed
    score = None if pending or not cards else sum(scores)+sum(t['bonus'] for t in tags)
    complete = len(cards) == rules.size
    grade = reward_accounting(gallery_set.grade_thresholds, rules.rewards, rules.reward_mode,
        score if complete else None)
    reached = [(v,k) for k,v in gallery_set.grade_thresholds.items() if complete and score is not None and score >= v]
    return dict(known_score=sum(s or 0 for s in scores), unknown_score_count=unknown_scores,
        score=score, score_lower_bound=sum(s or 0 for s in scores)+sum(t['bonus'] or 0 for t in tags),
        grade=max(reached)[1] if reached else None, tags=tags, complete=complete, rewards=grade)


def evaluate_v2(gallery_set, entries, owned=None, *, target_score=None, seconds=1.5, limit=20000):
    from app.services.gallery import entry_data
    rules = GalleryRules.model_validate(gallery_set.rules)
    eligible = []
    for entry in entries:
        try: validate_selection(gallery_set,[entry])
        except ValueError: continue
        eligible.append(entry)
    # Deterministic bounded search: reports exactly when optimality is not proven.
    eligible.sort(key=lambda e: (-(e.snapshot.get('gallery_score') or 0),e.id))
    modeled = solve_known(gallery_set, eligible, target_score, seconds)
    if modeled is not None:
        selected, search_status, bound, model_score = modeled
        evaluation = validate_selection(gallery_set, selected)
        if selected and evaluation['score'] != model_score:
            raise ValueError('El validador independiente no coincide con el modelo de Galería')
        return dict(selected_entries=[entry_data(e,owned) for e in selected], eligible_count=len(eligible),
            filled_slots=len(selected), required_slots=rules.size, missing_slots=rules.size-len(selected),
            **evaluation, warnings=['Escenario local; fórmula oficial y progreso EA sin verificar.']+
                (['Selección factible; óptimo no demostrado.'] if search_status=='feasible' else []),
            schema_version=2,evidence_status=rules.evidence_status,search_status=search_status,
            objective='minimum_score_reaching_target' if target_score is not None else 'score',
            objective_bound=bound, verified_official_formula=False)
    started, explored, exhausted, best = monotonic(), 0, True, None
    maximum = min(rules.size,len(eligible))
    for size in range(maximum, -1, -1):
        found = False
        for selected in combinations(eligible,size):
            if explored >= limit or monotonic()-started >= seconds:
                exhausted = False
                break
            explored += 1
            try: evaluation = validate_selection(gallery_set,selected)
            except ValueError: continue
            found = True
            meets = evaluation['complete'] and evaluation['score'] is not None and (target_score is None or evaluation['score'] >= target_score)
            # History is already eligible: no acquisition/ownership is inferred.
            objective = -evaluation['score'] if target_score is not None and meets else evaluation['score_lower_bound']
            key = (size, meets, objective, tuple(-e.id for e in selected))
            if best is None or key > best[0]: best = (key,selected,evaluation)
        if found or not exhausted: break
    selected, evaluation = (best[1], best[2]) if best else ([],validate_selection(gallery_set,[]))
    warnings = ['Escenario local sobre historia elegible conocida; no acredita una fórmula oficial ni cobra premios en EA.']
    if evaluation['score'] is None: warnings.append('Faltan puntos o atributos determinantes; grado pendiente.')
    if not exhausted: warnings.append('Búsqueda limitada: selección factible, óptimo no demostrado.')
    return dict(selected_entries=[entry_data(e,owned) for e in selected], eligible_count=len(eligible),
        filled_slots=len(selected), required_slots=rules.size, missing_slots=rules.size-len(selected),
        **evaluation, warnings=warnings, schema_version=2, evidence_status=rules.evidence_status,
        search_status='provisional' if evaluation['score'] is None else 'feasible',
        explored=explored, elapsed_ms=round((monotonic()-started)*1000,2),
        objective='minimum_score_reaching_target' if target_score is not None else 'score',
        verified_official_formula=False)


def solve_known(gallery_set, entries, target_score, seconds):
    """CP-SAT encoding, separately checked by validate_selection after solving."""
    from ortools.sat.python import cp_model
    from app.services.gallery import reviewed_score, item_key
    rules = GalleryRules.model_validate(gallery_set.rules)
    tags = [GalleryTag.model_validate(t) for t in gallery_set.tags]
    cards = [e.snapshot for e in entries]
    scores = [reviewed_score(c) for c in cards]
    if not entries or not gallery_set.rules_reviewed or any(s is None for s in scores) or any(known(c,t.field) is None for c in cards for t in tags):
        return None
    model = cp_model.CpModel()
    chosen = [model.NewBoolVar(f'entry_{i}') for i in range(len(entries))]
    model.Add(sum(chosen) <= rules.size)
    groups = defaultdict(list)
    for i,c in enumerate(cards):
        key = known(c,'athlete_id') if rules.multiplicity=='athlete' else item_key(c) if rules.multiplicity=='variant' else entries[i].id
        groups[key].append(i)
    for indices in groups.values():model.Add(sum(chosen[i] for i in indices)<=1)
    cap = sum(sorted(scores,reverse=True)[:rules.size])
    bonuses,bonus_cap = [],0
    for n,t in enumerate(tags):
        if t.aggregation=='matched':
            indices=[i for i,c in enumerate(cards) if type(known(c,t.field))==type(t.value) and normalized(known(c,t.field))==normalized(t.value)]
            count=sum(chosen[i] for i in indices)
            subtotal=sum(chosen[i]*scores[i] for i in indices)
        else:
            groups=defaultdict(list)
            for i,c in enumerate(cards):groups[normalized(known(c,t.field))].append(i)
            counts=[sum(chosen[i] for i in ids) for ids in groups.values()]
            subtotals=[sum(chosen[i]*scores[i] for i in ids) for ids in groups.values()]
            if t.aggregation=='distinct':
                present=[]
                for k,cnt in enumerate(counts):
                    b=model.NewBoolVar(f'present_{n}_{k}')
                    model.Add(cnt>=1).OnlyEnforceIf(b);model.Add(cnt==0).OnlyEnforceIf(b.Not());present.append(b)
                count=sum(present);subtotal=sum(subtotals)
            else:
                maximum=model.NewIntVar(0,rules.size*(cap+1)+cap,f'largest_{n}')
                model.AddMaxEquality(maximum,[cnt*(cap+1)+s for cnt,s in zip(counts,subtotals)])
                flags=[model.NewBoolVar(f'largest_choice_{n}_{k}') for k in range(len(counts))]
                count=model.NewIntVar(0,rules.size,f'count_{n}');subtotal=model.NewIntVar(0,cap,f'subtotal_{n}')
                model.Add(sum(flags)==1)
                for flag,cnt,s in zip(flags,counts,subtotals):
                    model.Add(maximum==cnt*(cap+1)+s).OnlyEnforceIf(flag)
                    model.Add(count==cnt).OnlyEnforceIf(flag);model.Add(subtotal==s).OnlyEnforceIf(flag)
        if t.mode=='fixed_legacy':
            active=model.NewBoolVar(f'active_{n}')
            model.Add(count>=t.minimum).OnlyEnforceIf(active);model.Add(count<t.minimum).OnlyEnforceIf(active.Not())
            bonuses.append(active*t.bonus);bonus_cap+=t.bonus
        else:
            # Explicit tier selection uses the LAST reached minimum (rates need not grow).
            rates=[next((tier.percent_basis_points for tier in reversed(t.tiers) if tier.minimum<=i),0) for i in range(rules.size+1)]
            count_var=model.NewIntVar(0,rules.size,f'items_{n}');model.Add(count_var==count)
            rate=model.NewIntVar(0,max(rates),f'rate_{n}');model.AddElement(count_var,rates,rate)
            sub=model.NewIntVar(0,cap,f'base_{n}');model.Add(sub==subtotal)
            product=model.NewIntVar(0,cap*max(rates),f'product_{n}');model.AddMultiplicationEquality(product,[sub,rate])
            bonus=model.NewIntVar(0,cap*max(rates)//10000,f'bonus_{n}');model.AddDivisionEquality(bonus,product,10000)
            bonuses.append(bonus);bonus_cap+=cap*max(rates)//10000
    total=sum(chosen[i]*scores[i] for i in range(len(entries)))+sum(bonuses)
    if target_score is None:model.Maximize(sum(chosen)*(cap+bonus_cap+1)+total)
    else:
        model.Add(sum(chosen)==rules.size);model.Add(total>=target_score);model.Minimize(total)
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=seconds;solver.parameters.num_search_workers=1;solver.parameters.random_seed=0
    status=solver.Solve(model)
    if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE):
        return [],'infeasible' if status==cp_model.INFEASIBLE else 'timeout',None,None
    selected=[e for i,e in enumerate(entries) if solver.Value(chosen[i])]
    return selected,'optimal_relative_to_candidates' if status==cp_model.OPTIMAL else 'feasible',solver.BestObjectiveBound(),solver.Value(total)
