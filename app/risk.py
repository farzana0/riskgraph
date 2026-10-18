"""Explicit sparse-data assumptions, parameter uncertainty, and sequential safety bounds."""
import math
import numpy as np
from scipy.stats import beta
from .domain import CAP

SEVERITY_CENTS = np.array([2500, 10000, 50000, CAP])


def anytime_upper(values, delta=0.05, cap=CAP):
    """One-sided Hoeffding + union bound over t, alpha_t=delta*6/(pi*t)^2.

    Valid across arbitrary repeated looks for independent bounded observations
    with a common mean (also constant conditional mean martingale setting).
    This is deliberately conservative; it is not a Bayesian credible bound.
    """
    if not 0 < delta < 1 or cap <= 0:
        raise ValueError("Invalid bound configuration")
    if any(not math.isfinite(x) or x < 0 or x > cap for x in values):
        raise ValueError("Loss outside the prespecified bound")
    n = len(values)
    if not n:
        return float(cap)
    alpha_t = delta * 6 / (math.pi ** 2 * n ** 2)
    radius = math.sqrt(math.log(1 / alpha_t) / (2 * n))
    return min(float(cap), float(np.mean(values)) + cap * radius)


def estimate(losses, seed=87, draws=16000):
    if any(not math.isfinite(x) or x < 0 or x > CAP for x in losses):
        raise ValueError("Loss exceeds synthetic exposure cap")
    n = len(losses)
    positive = [v for v in losses if v > 0]
    k = len(positive)
    a, b = 0.5 + k, 0.5 + n - k
    # Dirichlet-multinomial on positive-loss bands; upper endpoints conservatively
    # round each observed severity up. It is a model for binned, not exact, loss.
    counts = np.zeros(4)
    for value in positive:
        counts[np.searchsorted(SEVERITY_CENTS, value, side="left")] += 1
    concentration = counts + 0.25
    rng = np.random.default_rng(seed)
    frequency = rng.beta(a, b, draws)
    severity = rng.dirichlet(concentration, draws) @ SEVERITY_CENTS
    expected = frequency * severity / 100
    return {
        "n": n, "failures": k,
        "frequency_mean": a / (a + b),
        "frequency_ci95": beta.ppf([0.025, 0.975], a, b).tolist(),
        "severity_mean_usd": float(concentration @ SEVERITY_CENTS / concentration.sum() / 100),
        "expected_loss_usd": float((a / (a + b)) * (concentration @ SEVERITY_CENTS / concentration.sum()) / 100),
        "expected_loss_ci95": np.quantile(expected, [0.025, 0.975]).tolist(),
        "observed_loss_usd": float(sum(losses) / 100),
        "empirical_mean_usd": float(sum(losses) / n / 100) if n else 0,
        "anytime_upper_usd": anytime_upper(losses) / 100,
        "severity_counts": counts.astype(int).tolist(),
        "prior": "Jeffreys Beta(0.5,0.5); Dirichlet(0.25,0.25,0.25,0.25)",
        "severity_band_upper_usd": (SEVERITY_CENTS / 100).tolist(),
        "interval_target": "95% posterior interval for mean binned loss; not a predictive interval",
        "bound_assumption": "Independent bounded losses with common mean, cap $1000; per-stream 95% time-uniform upper bound",
        "status": "prior_only" if n == 0 else ("sparse" if k < 5 else "observed"),
    }


def drift(failures, baseline=0.10, bet=3.0):
    """Test supermartingale under P(failure_t | past) <= baseline.

    Ville's inequality: crossing e>=20 has <=5% probability under the null,
    per run. Running max latches the alert. No sliding/resetting without a new run.
    """
    total = peak = 0.0
    for failure in failures:
        total += math.log1p(bet * (int(failure) - baseline))
        peak = max(peak, total)
    return {"e_value": math.exp(min(total, 700)), "max_e_value": math.exp(min(peak, 700)),
            "alert": peak >= math.log(20), "threshold": 20,
            "baseline": baseline, "label": "Proposed-harm rate exceeds 10% reference"}
