"""Known-truth non-IID, paired, missing-outcome audit; no provider requests."""
import json
import math
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.providers import MODELS
from app.travel_factorial_stats import contrasts, key
from app.research_stats import interval


def run(repetitions=5000):
    arms = [w + ':' + key(m, memory, critic) for w in ('legacy', 'grounded') for m in MODELS
            for memory in ('none', 'selected') for critic in (False, True)]
    definitions = [(w + ':' + a, w + ':' + b) for w in ('legacy', 'grounded') for _, a, b in contrasts()]
    definitions += [('legacy:' + k.split(':')[1], k) for k in arms if k.startswith('grounded:')]
    ai = {k: i for i, k in enumerate(arms)}
    before = np.array([ai[a] for a, b in definitions]); after = np.array([ai[b] for a, b in definitions])
    # Trip-specific probabilities intentionally violate identical distribution within a family.
    trip = np.arange(32)[:, None]; arm = np.arange(16)[None, :]
    p = .02 + .025 * (trip % 8) + .04 * (trip // 8) + .012 * (arm % 4)
    p = np.clip(p + np.where(arm >= 8, -.035, .025) + .015 * ((arm // 4) % 2), .005, .7)
    missing = np.broadcast_to(.01 + .01 * (arm % 3), p.shape)
    refusal = np.broadcast_to(.06 + .025 * (arm % 4), p.shape)
    truth = np.stack([p, .5 * p, p + (1 - p) * missing,
                      p + (1 - p) * (missing + (1 - missing) * refusal), 260 * p], axis=-1).mean(axis=0)
    true_pairs = truth[before] - truth[after]
    caps = np.array([1, 1, 1, 1, 1000.])
    radius = caps * math.sqrt(math.log(2 * 240 / .05) / (2 * 32))
    rng = np.random.default_rng(20261024211); misses = point_misses = 0
    for start in range(0, repetitions, 100):
        count = min(100, repetitions - start)
        # Shared uniforms create strong within-trip dependence across all configurations.
        harm = rng.random((count, 32, 1)) < p
        severity_u = rng.random((count, 32, 1))
        severity = np.where(severity_u < .5, 75., np.where(severity_u < .85, 250., 900.))
        loss = harm * severity
        unknown = rng.random((count, 32, 1)) < missing
        reject = rng.random((count, 32, 1)) < refusal
        full = np.stack([harm, loss > 100, harm | unknown, harm | unknown | reject, loss], axis=-1).astype(float)
        financial_unknown = np.stack([unknown, unknown, np.zeros_like(unknown), np.zeros_like(unknown), unknown], axis=-1)
        lo = np.where(financial_unknown, 0., full).mean(axis=1)
        hi = np.where(financial_unknown, caps, full).mean(axis=1)
        pair_lo, pair_hi = lo[:, before] - hi[:, after], hi[:, before] - lo[:, after]
        arm_miss = (truth < lo - radius) | (truth > hi + radius)
        pair_miss = (true_pairs < pair_lo - 2 * radius) | (true_pairs > pair_hi + 2 * radius)
        misses += int(np.sum(np.any(arm_miss, axis=(1, 2)) | np.any(pair_miss, axis=(1, 2))))
        # A deliberately invalid zero-width plug-in interval is a negative control.
        point_misses += int(np.sum(np.any(np.abs(truth - (lo + hi) / 2) > 1e-12, axis=(1, 2))))
    return {'repetitions': repetitions, 'episodes_per_replication': 32, 'arms': 16, 'paired_contrasts': 32,
            'simultaneous_intervals': 240, 'joint_misses': misses, 'observed_joint_coverage': 1 - misses / repetitions,
            'monte_carlo_95_coverage_interval': interval(repetitions - misses, repetitions, .05),
            'zero_width_negative_control_misses': point_misses,
            'probability_radius': float(radius[0]), 'paired_probability_radius': float(2 * radius[0]),
            'dollar_radius': float(radius[-1]), 'seed': 20261024211,
            'scope': 'Offline known-truth implementation audit with independent heterogeneous trips, strongly dependent configurations, and unresolved financial labels. All 240 intervals must cover together. This is not measured model performance, a proof, or production calibration. Wide Hoeffding bounds can be very conservative; zero observed misses does not establish exact 100% coverage.'}


if __name__ == '__main__':
    out = run(); Path('docs/examples/travel-v3-calibration.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps(out, indent=2))
