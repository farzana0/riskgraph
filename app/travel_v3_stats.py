"""Matched old/new workflow effects and one simultaneous independent-episode family."""
import math
import numpy as np
from .travel_factorial_stats import analyze as analyze_one, METRICS, key, event
from .travel_v3 import FAMILIES, WORKFLOWS
from .providers import MODELS


def analyze(study):
    analyses = {w: analyze_one({**study, 'cells': [r for r in study['cells'] if r['workflow'] == w]}) for w in WORKFLOWS}
    records = {}
    for w in WORKFLOWS:
        for model in MODELS:
            for mem in ('none', 'selected'):
                for critic in (False, True):
                    stage = 'corrected' if critic else 'initial'
                    records[w + ':' + key(model, mem, critic)] = {r['case_id']: r[stage + '_outcome'] for r in study['cells']
                        if r['workflow'] == w and r['model'] == model and r['memory_mode'] == mem}
    comparisons = []
    for model in MODELS:
        for mem in ('none', 'selected'):
            for critic in (False, True):
                k = key(model, mem, critic); before, after = 'legacy:' + k, 'grounded:' + k
                metrics = {}
                for mi, metric in enumerate(METRICS):
                    draws = np.zeros(24000); mean = 0.; avoided = introduced = paired = missing = 0
                    for fi, f in enumerate(FAMILIES):
                        counts = [0, 0, 0, 0]
                        for c in study['cases']:
                            if c['family'] != f or c['id'] not in records[before] or c['id'] not in records[after]: continue
                            x, y = event(records[before][c['id']], metric), event(records[after][c['id']], metric)
                            if x is None or y is None: missing += 1; continue
                            counts[0 if x and y else 1 if x else 2 if y else 3] += 1
                        params = np.array(counts) + .25
                        q = np.random.default_rng(np.random.SeedSequence([20261024163, fi, mi])).dirichlet(params, 24000)
                        draws += (q[:, 1] - q[:, 2]) / len(FAMILIES)
                        mean += (params[1] - params[2]) / params.sum() / len(FAMILIES)
                        avoided += counts[1]; introduced += counts[2]; paired += sum(counts)
                    metrics[metric] = {'posterior_reduction': mean, 'credible95': np.quantile(draws, [.025, .975]).tolist(),
                                       'avoided': avoided, 'introduced': introduced, 'resolved_pairs': paired, 'unresolved_pairs': missing}
                comparisons.append({'kind': 'workflow', 'before': before, 'after': after, 'metrics': metrics})
    definitions = []
    for w in WORKFLOWS:
        definitions.extend((r['kind'], w + ':' + r['before'], w + ':' + r['after']) for r in analyses[w]['comparisons'])
    definitions.extend((r['kind'], r['before'], r['after']) for r in comparisons)
    count = (len(records) + len(definitions)) * 5
    alpha = .05 / count
    final = study['status'] == 'complete' and all(len(v) == len(study['cases']) for v in records.values())
    def bounds(a, b=None, metric='harm'):
        cap = 1000 if metric == 'dollars' else 1; lower = upper = variance = 0.; n = unknown = 0
        def value(o): return (o['proposed_loss_cents'] / 100 if o['resolved'] else None) if metric == 'dollars' else event(o, metric)
        for f in FAMILIES:
            ids = [c['id'] for c in study['cases'] if c['family'] == f and c['id'] in a and (b is None or c['id'] in b)]
            if not ids: continue
            weight = 1 / len(FAMILIES) / len(ids)
            for cid in ids:
                x, y = value(a[cid]), value(b[cid]) if b is not None else 0
                lower += weight * ((0 if x is None else x) - (cap if y is None else y))
                upper += weight * ((cap if x is None else x) - (0 if y is None else y))
                variance += weight * weight; n += 1; unknown += x is None or y is None
        radius = cap * (2 if b is not None else 1) * math.sqrt(math.log(2 / alpha) * variance / 2)
        return {'processed': n, 'unresolved': unknown, 'empirical_missing_range': [lower, upper],
                'simultaneous95': [max(-cap if b is not None else 0, lower - radius), min(cap, upper + radius)] if final else None}
    audit = {'intervals': count, 'joint_confidence': .95,
             'arms': {k: {m: bounds(r, metric=m) for m in (*METRICS, 'dollars')} for k, r in records.items()},
             'comparisons': [{'kind': kind, 'before': a, 'after': b,
                             'metrics': {m: bounds(records[a], records[b], m) for m in (*METRICS, 'dollars')}} for kind, a, b in definitions],
             'scope': 'One simultaneous 95% weighted-Hoeffding family across all 240 old/new workflow frequency, paired-effect and dollar intervals. Independent episodes, a fixed workflow and the $1,000 loss cap are assumptions. Trips may have different distributions; configurations within a trip may be dependent. Fixed-batch intervals are suppressed until the full batch completes. Bayesian intervals are separate marginal working-model summaries; the original IID binomial reference intervals are not the primary frequentist bounds.'}
    return {'analysis': analyses['grounded'], 'legacy_analysis': analyses['legacy'], 'workflow_comparisons': comparisons, 'robust_analysis': audit}
