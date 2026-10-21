# Monitoring under diverse failure patterns

A separate stress study evaluates the existing v2 frequency alarm under ten patterns. It uses **100,000 simulated trajectories**, each 500 observations, for **50 million simulated observations**. Each pattern has 10,000 fresh-seed trajectories. These are proposed-harm paths, not Claude decisions or payment executions. The study makes zero provider calls.

The seed is `20261022`. [Raw results](examples/monitoring-stress.json) record exact binomial 95% Monte Carlo intervals and source fingerprints. The alarm is unchanged from the mathematical framework comparison.

## Results

The alarm tests whether conditional harmful-proposal probability is at most 10%. It does not test every kind of loss or operational failure.

| Pattern | Alarm by observation 500 (95% MC interval) | Simulated mean proposed loss / decision | Conditional frequency null holds? |
| --- | ---: | ---: | --- |
| 10% conditional null | 3.01% (2.68–3.36%) | $2.50 | Yes |
| 0.5% rare $1,000 losses | 0.00% (0.00–0.04%) | $4.99 | Yes |
| 2% rare $1,000 losses | 0.00% (0.00–0.04%) | $19.96 | Yes |
| 10% harm, severity rises after case 100 | 3.03% (2.70–3.38%) | $80.68 | Yes |
| Gradual rise from 2% to 30% harm | 98.51% (98.25–98.74%) | $4.00 | No |
| 20-case burst at 80% harm | 99.97% (99.91–99.99%) | $1.28 | No |
| Two 25-case bursts at 50% harm | 90.79% (90.21–91.35%) | $1.70 | No |
| 50% harm after case 400 | 100.00% (99.96–100.00%) | $2.90 | No |
| Persistent Markov clusters | 38.14% (37.19–39.10%) | $1.55 | No |
| Service errors, no monetary harm | 0.00% (0.00–0.04%) | $0.00 | Yes |

The table's average dollar amounts are Monte Carlo averages over the specified 500-step workloads, not forecasts of business losses. The severity-only shift uses $25 losses before case 101 and $1,000 afterwards, while keeping harm frequency at 10%. Markov clusters use 70% next-case harm after a harmful case and 2% otherwise.

## Interpretation

**Rare, severe losses can evade a frequency alarm.** A 2% chance of a $1,000 error implies $20 mean loss per decision under that synthetic distribution, yet 2% stays below the alarm's 10% frequency reference. No alarm is therefore compatible with substantial dollar exposure. Conservative loss bounds and severity estimates must remain visible alongside the frequency alarm.

**A severity-only shift need not trigger.** The alarm observes binary harm indicators, so it has no mechanism for distinguishing a $25 harmful proposal from a $1,000 one. The approximately 3% crossing rate in the severity-shift scenario is within the frequency-null budget; it is not evidence of useful severity-shift detection. Changes in loss-tail probabilities invalidate the stationary loss-bound assumptions as well.

**Clusters change the meaning of a false alarm.** The Markov scenario can have low marginal harm frequency while the conditional probability after harm is 70%. Its crossings do not violate a guarantee requiring every next-case conditional probability to remain at or below 10%. This distinction motivates disabling stationary bounds for the correlated suite.

**Service quality needs a separate metric.** Unnecessary declines and referrals have zero unauthorized monetary loss under the current scoring rule. The review notes therefore expose unpaid fully eligible requests separately. The study's service-only stream intentionally has no scored monetary harm and never alerts on that harm stream.

These results support cautious interpretation, not universal detection. Risk appetite expressed in dollars would require an additional loss-targeted monitor with its own precommitted null and error allocation; the current application does not claim to provide that monitor. Source-system authenticity, real settlement, aggregate limits across orders, and nonmonetary harms remain outside this synthetic model.

## Reproduce

```sh
python scripts/stress_monitoring.py --seed 20261022 --trajectories 10000 --output evidence/monitoring-stress.json
```
