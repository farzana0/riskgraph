"""Independent-episode audit bounds: fixed quotas need not be IID Bernoulli."""
import math
from .travel_factorial import FAMILIES, MODES
from .travel_factorial_stats import METRICS, contrasts, event, key
from .providers import MODELS


def independent_bounds(study):
    records = {}
    for model in MODELS:
        for mode in MODES:
            for critic in (False, True):
                stage = 'corrected' if critic else 'initial'
                records[key(model, mode, critic)] = {r['case_id']: r[stage + '_outcome'] for r in study['cells']
                                                    if r['model'] == model and r['memory_mode'] == mode}
    cases = study['cases']
    complete = study['status'] == 'complete' and all(len(r) == len(cases) for r in records.values())
    # One common 5% error family: 32 arm frequencies + 48 paired effects + 8 arm dollars + 12 paired dollars.
    intervals = len(records) * (len(METRICS) + 1) + len(contrasts()) * (len(METRICS) + 1)
    alpha = .05 / intervals

    def bound(before, after=None, metric='harm'):
        lower = upper = squared_weights = 0.
        n = missing = 0
        monetary = metric == 'dollars'
        cap = 1000 if monetary else 1
        def value(o):
            if monetary:
                return o['proposed_loss_cents'] / 100 if o['resolved'] else None
            return event(o, metric)
        for f in FAMILIES:
            ids = [c['id'] for c in cases if c['family'] == f and c['id'] in before and (after is None or c['id'] in after)]
            if not ids:
                continue
            w = 1 / len(FAMILIES) / len(ids)
            for cid in ids:
                x = value(before[cid])
                y = value(after[cid]) if after is not None else 0
                lower += w * ((0 if x is None else x) - (cap if y is None else y))
                upper += w * ((cap if x is None else x) - (0 if y is None else y))
                squared_weights += w * w
                missing += x is None or y is None
                n += 1
        # Hoeffding permits different distributions for independent bounded episodes.
        # A pair is one observation of width 2*cap; dependence within the pair is retained.
        width = cap * (2 if after is not None else 1)
        radius = width * math.sqrt(math.log(2 / alpha) * squared_weights / 2)
        return {'processed_pairs' if after is not None else 'processed': n, 'unresolved': missing,
                'empirical_missing_range': [lower, upper],
                'simultaneous95': [max(-cap if after is not None else 0, lower - radius), min(cap, upper + radius)] if complete else None}

    arms = {arm: {metric: bound(rows, metric=metric) for metric in (*METRICS, 'dollars')} for arm, rows in records.items()}
    comparisons = [{'kind': kind, 'before': before, 'after': after,
                    'metrics': {metric: bound(records[before], records[after], metric) for metric in (*METRICS, 'dollars')}}
                   for kind, before, after in contrasts()]
    return {'method': 'Fixed-design weighted Hoeffding bounds with Bonferroni allocation',
            'intervals': intervals, 'joint_confidence': .95, 'arms': arms, 'comparisons': comparisons,
            'scope': 'One simultaneous 95% family covers 32 frequency estimates, 48 paired frequency reductions, eight mean-loss estimates and 12 paired mean-loss reductions. Requires independent episodes, a fixed workflow and the stated $1,000 loss cap; dependence across configurations within the same trip is allowed. Does not require identically distributed trips or IID outcomes within a family. Unknown financial losses retain their full range. Bounds appear only for the completed fixed batch. They describe the expected risk over this fixed 3:1 eligible/escalation challenge design, not production traffic. The preregistered Bayesian intervals remain separate working-model summaries. The preregistered exact binomial intervals need the stronger within-family IID assumption, which the fixed eligibility quota does not establish; they are not the primary frequentist bounds.'}
