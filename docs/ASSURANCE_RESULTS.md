# Adaptive-loss simulation results

Seed 20261021; 50,000 trajectories × 500 episodes = 25,000,000 observations. No provider calls.

Each alarm has its own 5% anytime false-alert budget. Frequency reference: 10% harmful proposals. Monetary reference: $10 conditional mean proposed loss. The confidence sequence uses 2.5% error per stream, rho=6.25, and a $1,000 cap.

| Scenario | Frequency alarm | Monetary alarm | Mean observed loss / episode | Adaptive-CS anytime misses |
|---|---:|---:|---:|---:|
| bounded_mean_null | 0.00% | 2.07% | $9.92 | 0.00% |
| rare_catastrophe_02 | 0.00% | 28.38% | $20.08 | 0.00% |
| severity_shift | 2.66% | 100.00% | $80.27 | 0.00% |
| adaptive_feedback | 38.16% | 98.27% | $62.36 | 0.00% |
| common_cause_burst | 100.00% | 100.00% | $44.84 | 0.00% |

The monetary-null row observed 2.07% crossings (95% Monte Carlo interval 1.80%–2.37%). This supports the implementation check against the 5% upper guarantee. Zero confidence-sequence misses in these simulations does not imply exact coverage or useful tightness in every setting; the normal-mixture Hoeffding construction is conservative.

The rare-catastrophe row illustrates a remaining power limitation: the monetary alarm detects 28.38% by episode 500, even though its mean loss is about $20. No-alert must not be read as evidence of low risk. The severity-shift row retains a 10% harm rate but changes loss severity after episode 100.

Raw counts, Monte Carlo intervals, conditional-null labels, source fingerprints and interpretation are in [the machine-readable study](examples/assurance-study.json). These paths are generated financial outcomes, not measured Claude errors or independent production claims. The earlier frequency-only study remains a historical record.

Construction and research sources: [research specification](RESEARCH_DESIGN.md).
