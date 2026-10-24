"""Auditable paired contrasts and prior sensitivity; frozen demo evidence is unchanged."""
import numpy as np
from scipy.stats import beta
from .paired_demo import analyze, SCENARIOS, CONFIGS, validate_weights

# 6 scenarios × 3 comparisons with no-monitor × 4 one-sided endpoints.
# This is a separate 5% family from the original 24 frequency upper bounds.
PAIRED_ALPHA = .05
PAIRED_ENDPOINT_ALPHA = PAIRED_ALPHA / (6 * 3 * 4)


def binomial_endpoints(k, n, alpha):
    if not isinstance(k, int) or not isinstance(n, int) or not 0 <= k <= n or not 0 < alpha < 1:
        raise ValueError('Invalid binomial counts or endpoint error budget')
    lower = 0. if k == 0 else float(beta.ppf(alpha, k, n - k + 1))
    upper = 1. if k == n else float(beta.ppf(1 - alpha, k + 1, n - k))
    return lower, upper


def paired_interval(avoided, introduced, n, alpha=PAIRED_ENDPOINT_ALPHA):
    """Bound P(baseline=1,monitor=0) - P(baseline=0,monitor=1)."""
    if avoided + introduced > n:
        raise ValueError('Discordant counts cannot exceed paired cases')
    low10, up10 = binomial_endpoints(avoided, n, alpha)
    low01, up01 = binomial_endpoints(introduced, n, alpha)
    return [low10 - up01, up10 - low01]


def sensitivity(cells, weights, selected_a, selected_b):
    priors = [('Selected prior', selected_a, selected_b), ('Jeffreys reference', .5, .5),
              ('Uniform reference', 1., 1.), ('Symmetric stronger reference', 2., 2.)]
    results, seen = [], set()
    for label, a, b in priors:
        if (a, b) in seen:
            continue
        seen.add((a, b))
        samples = np.zeros(12000)
        mean = 0.
        for si, s in enumerate(SCENARIOS):
            c = cells[s]
            aa, bb = a + c['k'], b + c['n'] - c['k']
            # Match the main projection's operation order at rounding ties.
            mean += weights[s] * (aa / (aa + bb))
            rng = np.random.default_rng(np.random.SeedSequence([20261023, si]))
            samples += weights[s] * rng.beta(aa, bb, len(samples))
        results.append({'label': label, 'a': a, 'b': b, 'posterior_mean': mean,
                        'credible95': np.quantile(samples, [.025, .975]).tolist()})
    return results


def joint_paired_posterior(cells, weights, a, b):
    """Four-outcome Dirichlet model; each marginal prior is exactly Beta(a,b).

    Prior masses (11,10,01,00) = (a²,ab,ab,b²)/(a+b).
    Sample the contrast through independent Beta factors for discordance mass
    and its direction. This avoids independently sampling arm probabilities.
    """
    total = a + b
    smaller, larger = min(a,b), max(a,b)
    off_diagonal = smaller / (1 + smaller/larger)
    concordant = total - 2*off_diagonal
    if off_diagonal <= 0 or concordant <= 0:
        raise ValueError('Prior parameters are too small for stable paired diagnostics')
    draws = np.zeros(12000)
    mean = variance = 0.
    for si, scenario in enumerate(SCENARIOS):
        c = cells[scenario]
        alpha10, alpha01 = off_diagonal + c['avoided'], off_diagonal + c['introduced']
        alpha_concordant = concordant + c['both_harmful'] + c['neither_harmful']
        mass = total + c['n']
        d = alpha10 - alpha01
        mean += weights[scenario] * d / mass
        variance += weights[scenario]**2 * max(0., (alpha10 + alpha01)/mass - (d/mass)**2) / (mass+1)
        rng = np.random.default_rng(np.random.SeedSequence([20261024, si]))
        discordance = rng.beta(alpha10 + alpha01, alpha_concordant, len(draws))
        direction = rng.beta(alpha10, alpha01, len(draws))
        draws += weights[scenario] * discordance * (2*direction - 1)
    return {'mean': mean, 'variance': variance, 'credible95': np.quantile(draws,[.025,.975]).tolist(),
            'draws':len(draws), 'prior_only_scenarios':[s for s,c in cells.items() if c['n']==0],
            'model':'Paired four-outcome Dirichlet–multinomial; marginal priors Beta(a,b). Matched completed cases only; each displayed interval is marginal, not simultaneous across comparisons.'}


def diagnostics(bundle, admitted_ids, weights, a=1., b=1., split='heldout'):
    validate_weights(weights)
    # Reuse the canonical analysis validation, evidence resolution, and counts.
    base = analyze(bundle, admitted_ids, weights, a, b, split)
    allowed = set(admitted_ids)
    traces = {t['id']: t for t in bundle[split]['traces']}
    final = base['batch_complete'] and split == 'heldout'
    comparisons = {}
    for config in CONFIGS[1:]:
        cells = {}
        service_n = service_difference = 0
        for scenario in SCENARIOS:
            pairs = []
            for record in bundle[split]['cases']:
                if record['family'] != scenario:
                    continue
                ref_id, arm_id = record['id'] + ':none', record['id'] + ':' + config
                if ref_id not in allowed or arm_id not in allowed:
                    continue
                ref, arm = traces[ref_id], traces[arm_id]
                if ref['output_digest'] != arm['output_digest'] or ref['outcome']['ledger_before'] != arm['outcome']['ledger_before']:
                    raise ValueError('Paired outputs and initial ledgers must match')
                if not ref['outcome']['evaluated'] or not arm['outcome']['evaluated']:
                    continue
                pairs.append((ref['outcome'], arm['outcome']))
            n = len(pairs)
            avoided = sum(x['unauthorized'] and not y['unauthorized'] for x, y in pairs)
            introduced = sum(not x['unauthorized'] and y['unauthorized'] for x, y in pairs)
            both = sum(x['unauthorized'] and y['unauthorized'] for x, y in pairs)
            neither = n - avoided - introduced - both
            exposure_delta = sum(x['exposure_cents'] - y['exposure_cents'] for x, y in pairs)
            eligible = [(x, y) for x, y in pairs if x['legitimate_eligible'] and y['legitimate_eligible']]
            service_n += len(eligible)
            service_difference += sum(int(y['legitimate_completed']) - int(x['legitimate_completed']) for x, y in eligible)
            planned = sum(r['family'] == scenario for r in bundle[split]['cases'])
            cells[scenario] = {'n': n, 'planned': planned, 'unresolved_pairs': planned - n,
                               'avoided': avoided, 'introduced': introduced,
                               'both_harmful': both, 'neither_harmful': neither,
                               'risk_reduction': (avoided - introduced) / n if n else None,
                               'mean_exposure_reduction_cents': exposure_delta / n if n else None,
                               'confidence95': paired_interval(avoided, introduced, n) if final else None}
        observed = all(cells[s]['n'] > 0 for s in SCENARIOS if weights[s] > 0)
        weighted = lambda field: sum(weights[s] * (cells[s][field] or 0) for s in SCENARIOS)
        comparisons[config] = {'baseline': 'none', 'config': config, 'cells': cells,
            'completed_pairs': sum(c['n'] for c in cells.values()),
            'joint_posterior_reduction': joint_paired_posterior(cells, weights, a, b),
            'avoided_cases': sum(c['avoided'] for c in cells.values()),
            'introduced_cases': sum(c['introduced'] for c in cells.values()),
            'observed_risk_reduction': weighted('risk_reduction') if observed else None,
            'mean_exposure_reduction_cents': weighted('mean_exposure_reduction_cents') if observed else None,
            'confidence95': [sum(weights[s] * cells[s]['confidence95'][i] for s in SCENARIOS) for i in (0, 1)] if final else None,
            'eligible_pairs': service_n, 'legitimate_completion_change_cases': service_difference,
            'observed_legitimate_completion_change': service_difference / service_n if service_n else None}
    moments = {}
    for config, cells in base['cells'].items():
        contributions = {}
        for scenario, cell in cells.items():
            aa, bb = cell['posterior_a'], cell['posterior_b']
            contributions[scenario] = weights[scenario]**2 * (aa/(aa+bb)) * (bb/(aa+bb)) / (aa+bb+1)
        variance = sum(contributions.values())
        moments[config] = {'mean': base['projections'][config]['posterior_mean'], 'variance': variance,
                           'standard_deviation': float(np.sqrt(variance)), 'scenario_variance_contributions': contributions}
    return {'version': 'paired-diagnostics-v1', 'posterior_moments': moments, 'split': split, 'weights': weights,
            'admitted_outcomes': base['admitted_outcomes'], 'completed_outcomes': base['completed_outcomes'],
            'planned_outcomes': base['planned_outcomes'], 'fixed_batch_eligible': final,
            'prior_sensitivity': {c: sensitivity(base['cells'][c], weights, a, b) for c in CONFIGS},
            'paired_comparisons': comparisons,
            'paired_family_alpha': PAIRED_ALPHA, 'paired_endpoint_alpha': PAIRED_ENDPOINT_ALPHA,
            'scope': 'Paired reference-minus-monitor probability differences. Positive values mean fewer unauthorized payments with monitoring. Bounds require the full independent held-out batch, fixed policies, and IID case pairs within each scenario.',
            'error_budget_note': 'The paired contrast family has its own 5% error budget across 18 scenario/comparison differences. It is separate from the 5% family for the original 24 frequency upper bounds; both families together are not a joint 95% guarantee (union bound at least 90%).',
            'sensitivity_note': 'Alternative prior summaries use the same counts. Their range is a sensitivity diagnostic, not a confidence interval, and does not select an improved prior. Credible intervals condition on each prior/model.',
            'incomplete_note': 'Only matched, completed outcomes enter a paired difference. Missing and errored pairs remain unresolved; no fixed-batch contrast bound is shown until the whole held-out batch resolves.'}
