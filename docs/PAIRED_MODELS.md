# Matched-case model comparison

Generation revision: `e69e110`. Four fixed seeds, 40 cases per seed and model, randomized 28-category synthetic workload, memory off. Haiku 5.5 and Sonnet 5.5 use the same cases, proposer prompt and strict action schema. Supported reasoning settings differ and are recorded in the manifest.

| Model | Episodes | Scenario types | Harmful proposals | Executed loss | Fully eligible requests unpaid | Estimated token cost |
|---|---:|---:|---:|---:|---:|---:|
| claude-haiku-5-5 | 160 | 28 | 0 | $0.00 | 0 | $0.0405 |
| claude-sonnet-5-5 | 160 | 28 | 0 | $0.00 | 0 | $0.7148 |

All 320 recorded reviews and handoff receipts recompute successfully. Each model encountered all 28 category types across its 160 episodes. The observed proposed-loss difference is zero; the exact paired discordance test has no discordant cases. This does not establish equivalence or a larger-model advantage. The benchmark may be too easy to discriminate model behavior.

## Risk remains uncertain

Under the stated Beta frequency/Dirichlet severity prior, each model has $1.2616 posterior mean binned loss per episode, with a 95% credible interval of approximately $0.0006–$8.0722. The identical numbers follow from identical zero-loss observations and the same prior; they are not an empirical estimate of unseen production failure frequency. Prior sensitivity of the mean spans approximately $1.2616–$2.5077.

A separate 95% time-uniform bound for the average conditional Haiku-minus-Sonnet proposed-loss difference is approximately −$240.34 to $240.34 per episode. It targets the preordered matched-episode reveal sequence, not a causal architecture effect or future workload superiority. The four model/stream mean-risk intervals use another shared 5% error budget; they are not jointly combined with the difference interval into a single 95% claim.

A conventional empirical bootstrap degenerates to [0,0] when every observed paired loss difference is zero. That interval cannot rule out unseen differences. The derived analysis explicitly marks this degeneracy and retains a nonzero bounded uncertainty interval. The normal-mixture Hoeffding bound is conservative; sharper variance-adaptive bounds are a further research opportunity.

## Reproduction and provenance

The [generation manifest](examples/paired-models.json) records seeds, settings, token totals, case fingerprints, run IDs, price assumptions, and generation-source hashes. The eight `paired-claude-*.json` exports preserve episode-level cases, proposals, policy reviews and handoffs. [Derived analysis](examples/paired-model-analysis.json) has separate source fingerprints and a digest of the unchanged campaign manifest.

Run `scripts/compare_models.py` on a configured service to generate a new budgeted campaign. Run `scripts/analyze_paired.py` to archive and analyze the completed hosted campaign without making model calls. Results are synthetic, task-specific and not calibrated production premiums. Token-based costs are estimates, not invoices or account balances.

Future evaluation should add independently authored tasks, held-out attack families, real audited episodes, stronger arithmetic/state-coordination challenges, and a matched critic ablation. These results alone do not justify spending more on a larger model for monetary-risk reduction.
