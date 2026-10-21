"""Explicit sparse-data assumptions, parameter uncertainty, and sequential safety bounds."""
import math
import numpy as np
from scipy.stats import beta
from scipy.special import betaln, logsumexp
from scipy.optimize import brentq
from functools import lru_cache
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


def estimate(losses, seed=87, draws=16000, delta=0.05):
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
    sequence = loss_confidence_sequence(losses, delta)
    sensitivity = []
    for frequency_prior in [0.5, 1.0]:
        for severity_strength in [0.5, 1.0, 2.0]:
            q = counts + severity_strength / 4
            sensitivity.append((k+frequency_prior)/(n+2*frequency_prior) * (q @ SEVERITY_CENTS/q.sum())/100)
    return {
        "n": n, "failures": k,
        "frequency_mean": a / (a + b),
        "frequency_ci95": beta.ppf([0.025, 0.975], a, b).tolist(),
        "severity_mean_usd": float(concentration @ SEVERITY_CENTS / concentration.sum() / 100),
        "expected_loss_usd": float((a / (a + b)) * (concentration @ SEVERITY_CENTS / concentration.sum()) / 100),
        "expected_loss_ci95": np.quantile(expected, [0.025, 0.975]).tolist(),
        "observed_loss_usd": float(sum(losses) / 100),
        "empirical_mean_usd": float(sum(losses) / n / 100) if n else 0,
        "anytime_upper_usd": sequence["upper_usd"],
        "confidence_sequence": sequence,
        "hoeffding_upper_usd": anytime_upper(losses, delta=delta) / 100,
        "prior_sensitivity_usd": [float(min(sensitivity)), float(max(sensitivity))],
        "evidence_quality": "prior_only" if n == 0 else "severity_unobserved" if k == 0 else "sparse" if k < 5 else "observed",
        "severity_counts": counts.astype(int).tolist(),
        "prior": "Jeffreys Beta(0.5,0.5); Dirichlet(0.25,0.25,0.25,0.25)",
        "severity_band_upper_usd": (SEVERITY_CENTS / 100).tolist(),
        "interval_target": "95% posterior interval for mean binned loss; not a predictive interval",
        "bound_assumption": "Beta-mixture tail confidence sequences; fixed conditional tail probabilities, loss cap $1000; allocated per-stream error budget",
        "status": "prior_only" if n == 0 else ("sparse" if k < 5 else "observed"),
    }


def legacy_drift(failures, baseline=0.10, bet=3.0):
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


@lru_cache(maxsize=8192)
def bernoulli_sequence(successes, n, delta=0.05):
    """Invert a Jeffreys beta-mixture likelihood-ratio test martingale.

    E_n(p) = B(k+.5,n-k+.5)/B(.5,.5) / [p^k (1-p)^(n-k)].
    Ville's inequality gives simultaneous-in-time coverage for fixed conditional p.
    Boundary p=0/1 is retained whenever compatible with the observations.
    """
    if n < 0 or not 0 <= successes <= n or not 0 < delta < 1:
        raise ValueError("Invalid confidence sequence configuration")
    if n == 0:
        return (0.0, 1.0)
    k = successes
    log_mixture = betaln(k+.5, n-k+.5)-betaln(.5, .5)
    threshold = math.log(1/delta)
    if k == 0:
        return (0.0, float(-math.expm1((log_mixture-threshold)/n)))
    if k == n:
        return (float(math.exp((log_mixture-threshold)/n)), 1.0)
    def objective(p):
        return log_mixture-k*math.log(p)-(n-k)*math.log1p(-p)-threshold
    empirical = k/n
    # Rounding endpoints outward preserves conservative numerical inversion.
    lower = brentq(objective, 1e-300, empirical, xtol=1e-13)
    upper = brentq(objective, empirical, 1-1e-15, xtol=1e-13)
    return (max(0.0, lower-1e-12), min(1.0, upper+1e-12))


def loss_confidence_sequence(losses, delta=0.05):
    """Simultaneous tail-probability intervals and a conservative mean loss bound.

    E[rounded_loss] = sum_j (v_j-v_{j-1}) P(loss > v_{j-1}).
    Four beta-mixture CSs each receive delta/4. On their joint event, the
    weighted upper endpoints bound rounded and therefore exact mean loss.
    """
    if not 0 < delta < 1:
        raise ValueError("Invalid error budget")
    values = np.asarray(losses, dtype=float)
    if np.any(~np.isfinite(values)) or np.any(values < 0) or np.any(values > CAP):
        raise ValueError("Loss outside the prespecified bound")
    thresholds = np.array([0, 2500, 10000, 50000])
    intervals = [bernoulli_sequence(int(np.sum(values > x)), len(values), delta/4) for x in thresholds]
    # Nested tails obey p_0 >= ... >= p_3; tighten without extra error spending.
    upper = np.minimum.accumulate([v[1] for v in intervals])
    lower = np.maximum.accumulate([v[0] for v in intervals][::-1])[::-1]
    increments = np.diff(np.r_[0, SEVERITY_CENTS]) / 100
    return {"method": "beta_mixture_tail_cs_v2", "confidence": 1-delta,
            "upper_usd": float(increments @ upper),
            "binned_lower_usd": float(increments @ lower),
            "frequency_interval": [float(lower[0]), float(upper[0])],
            "tail_thresholds_usd": (thresholds/100).tolist(),
            "tail_intervals": [[float(lo), float(hi)] for lo,hi in zip(lower,upper)],
            "target": "Upper bound for exact and upward-binned mean loss; lower endpoint targets binned loss only",
            "assumption": "Fixed conditional probabilities for four loss thresholds; bounded losses; one evaluation"}


BET_GRID = np.array([0.25, 0.5, 1.0, 2.0, 3.0, 5.0])


def alarm_starts(n):
    """Countable, precommitted start-time prior: .5 at zero, geometric thereafter."""
    yield 0, 0.5
    start, weight = 25, 0.25
    while start < n:
        yield start, weight
        start *= 2
        weight /= 2


def mixture_log_path(failures, baseline=0.10):
    if not 0 < baseline < 1 or BET_GRID[-1]*baseline >= 1:
        raise ValueError("Baseline incompatible with the nonnegative betting grid")
    x = np.asarray(failures, dtype=float)
    if np.any((x != 0) & (x != 1)):
        raise ValueError("Alarm observations must be binary")
    n = len(x)
    if not n:
        return np.array([])
    prefixes = np.vstack([np.zeros(len(BET_GRID)), np.cumsum(np.log1p((x[:,None]-baseline)*BET_GRID), axis=0)])
    terms, used = [], 0.0
    for start, weight in alarm_starts(n):
        component = np.zeros(n)
        component[start:] = logsumexp(prefixes[start+1:]-prefixes[start], axis=1)-math.log(len(BET_GRID))
        terms.append(math.log(weight)+component)
        used += weight
    # All future, unstarted components equal one, retaining initial capital.
    terms.append(np.full(n, math.log(max(1-used, 1e-300))))
    return logsumexp(np.array(terms), axis=0)


def drift(failures, baseline=0.10):
    """A single valid e-process mixing bets and precommitted restart times.

    Each component has conditional expected factor <=1 under the null. Their
    fixed weighted sum (including unstarted mass) is a supermartingale. No
    post-hoc reset or multiplicity-free scanning is used. Alert at e>=20.
    """
    path = mixture_log_path(failures, baseline)
    total = float(path[-1]) if len(path) else 0.0
    peak = max(0.0, float(np.max(path))) if len(path) else 0.0
    return {"e_value": math.exp(min(total, 700)), "max_e_value": math.exp(min(peak, 700)),
            "alert": peak >= math.log(20), "threshold": 20, "baseline": baseline,
            "method": "multi_bet_restart_mixture_v2", "false_alarm_budget": .05,
            "label": "Sequential evidence against the 10% conditional harm reference"}


def conditional_mean_sequence(losses, cap=CAP, delta=.025, rho=6.25):
    """Normal-mixture Hoeffding CS for average predictable conditional means.

    For X_t=L_t/cap and m_t=E[X_t|F_(t-1)], Hoeffding's lemma gives
    exp(lambda sum(X-m)-lambda^2*n/8) a supermartingale. Mixing lambda
    ~N(0,1/rho) yields sqrt(rho/(rho+n/4))*exp(S^2/(2*(rho+n/4))).
    Ville inversion bounds |S| at all n. m_t may vary and agents may depend
    on history. rho is fixed in advance. Never intersect different n targets.
    """
    if cap <= 0 or not math.isfinite(cap) or not 0 < delta < 1 or rho <= 0:
        raise ValueError("Invalid conditional-mean bound configuration")
    if any(not math.isfinite(v) or v < 0 or v > cap for v in losses):
        raise ValueError("Loss outside prespecified bound")
    n = len(losses)
    mean = sum(losses) / n / cap if n else 0
    variance = rho + n / 4
    width = math.sqrt(variance * math.log(variance / (rho * delta**2))) / n if n else 1
    return {"lower_usd": max(0, mean-width)*cap/100,
            "upper_usd": min(1, mean+width)*cap/100,
            "confidence": 1-delta, "rho": rho, "method": "normal_mixture_hoeffding_v1",
            "target": "Running average of conditional expected loss over the observed episodes",
            "assumption": "Adapted bounded outcomes; cap and rho fixed before observation; all completed episodes included",
            "future_guarantee": False}


def severity_alarm(losses, reference_cents=1000, cap=CAP, delta=.05):
    """Anytime mean-loss e-process, valid under E[L_t|past] <= reference.

    Normalize by the cap and mix fixed nonnegative linear bets and start times.
    This complements, rather than silently replaces, the binary harm alarm.
    """
    if not 0 < reference_cents < cap or not 0 < delta < 1:
        raise ValueError("Invalid severity reference")
    x = np.asarray(losses, dtype=float) / cap
    if np.any(~np.isfinite(x)) or np.any((x < 0) | (x > 1)):
        raise ValueError("Loss outside prespecified bound")
    n, baseline = len(x), reference_cents / cap
    bets = BET_GRID * .1 / baseline
    terms, used = [], 0.0
    if n:
        prefixes = np.vstack([np.zeros(len(bets)), np.cumsum(np.log1p((x[:,None]-baseline)*bets), axis=0)])
        for start, weight in alarm_starts(n):
            component = np.zeros(n)
            component[start:] = logsumexp(prefixes[start+1:]-prefixes[start], axis=1)-math.log(len(bets))
            terms.append(math.log(weight)+component)
            used += weight
        terms.append(np.full(n, math.log(max(1-used, 1e-300))))
        path = logsumexp(np.array(terms), axis=0)
        total, peak = float(path[-1]), max(0, float(np.max(path)))
    else:
        total = peak = 0.0
    return {"e_value": math.exp(min(total,700)), "max_e_value": math.exp(min(peak,700)),
            "alert": peak >= math.log(1/delta), "threshold": 1/delta,
            "reference_usd": reference_cents/100, "false_alarm_budget": delta,
            "method": "bounded_loss_restart_mixture_v1",
            "null": "Every conditional mean proposed loss is at or below the reference"}
