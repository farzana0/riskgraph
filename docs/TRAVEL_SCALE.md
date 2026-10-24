# Large fresh Haiku travel campaign

This separately registered campaign targets 5,504 fresh cases: 688 per travel family, seed 2026102481. No earlier response is reused. The booking policy and generator are unchanged, but the caller now forces the `propose_booking` tool with a 512-token response limit. This reduces format overhead and gives a clearly specified proposal interface. It is a distinct format-controlled Haiku workflow, not a pooled extension of the earlier automatic-tool Haiku/Sonnet experiment or evidence for a model ranking. The prompts, source, cases and response controls are fingerprinted before calls.

The fresh API allowance is US$2, reserved persistently before each request, at most 5,504 requests and eight starts per second. Invalid/failed/uncertain requests are never retried automatically. Total newly authorized experiment caps are US$8: refund replication $4.80, matched travel and live demo $1.20, scale campaign $2.00. Application reservations enforce these limits independently of provider billing settings.

Tail estimates apply the law of total probability across eight fixed equal scenario weights. Each threshold has marginal family Jeffreys Beta posteriors; no simultaneous Bayesian band is claimed. A separate 5% frequentist family covers 32 exact family/threshold bounds, under complete fixed-batch, within-family IID and fixed-policy assumptions. A separate 5% conditional-dollar sequence covers bounded completed losses; the two frequentist families have a union guarantee of at least 90% under their assumptions.

Financial posteriors condition on resolved proposals. An additional fully observed adverse endpoint counts a harmful **or unresolved** proposal as adverse. Its exact upper bound is available after the fixed batch even when a proposal cannot be adjudicated. It does not turn an unknown financial loss into an observed dollar value. Missing-dollar sensitivity assigns each unknown any value in $0–$1,000. These endpoints remain distinct in the graph labels.

Balanced prefixes at 4, 16, 64, 256 and 688 cases per family illustrate how uncertainty changes as samples accumulate; these are not independent replications or stopping criteria. Example navigation shows the first resolved harmful and harmless case in each family under frozen case order. The aggregate retains every processed result. The complete response archive and generator allow offline reconstruction of every original request hash, source record, model identity, token cost, score and tail estimate.

The matched 32-case Haiku/Sonnet/critic report remains the source of model and critic comparisons. This campaign evaluates Haiku without memory or a critic. Live discretionary cases and deliberately injected stress fixtures are excluded.


## Recorded results

All 5,504 fresh requests completed collection for **US$1.9442618**. The response archive records 5,504 unique provider response identities. Of these proposals, 4,783 have adjudicated financial outcomes and 721 remain unresolved; 2,247 adjudicated proposals have nonzero potential loss. There are 5,318 service/task errors in total. All synthetic executed residual losses are zero because the independent gate stops the unsafe or unusable proposals. These results describe the deliberately constrained workflow, not default Haiku performance.

The scenario-standardized posterior probability of positive proposed loss, conditioning on usable proposals within each family, is **46.67% [95% credible: 45.48%–47.86%]**. The positive-loss interval narrows from **24.25 percentage points** at the balanced 32-case prefix to **2.39 pp** at 5,504 cases, about **90% narrower**. This is within-batch evidence accumulation, not independent replications or a simultaneous confidence guarantee.

The complete-batch conservative exact upper bound for the fully observed **harmful-or-unresolved** endpoint is **58.88%**. At thresholds $25, $100 and $500 the conditional posterior exceedance means are 31.69%, 17.99% and 0.084%, respectively. Their marginal intervals and separate adverse-or-unresolved upper bounds are retained in the report. High-threshold financial risk cannot be declared small by discarding the 721 unknown proposals.

The sum of assumed proposed exposure over adjudicated proposals is $258,768.56 in synthetic dollars. It is not money spent or a vendor-loss measurement. No proposal loss is fabricated for missing responses. [Independent verification](examples/travel-scale-verification.json) reconstructs every original input and request fingerprint, model identity, token cost, outcome, tail interval and balanced prefix from the [compressed responses](examples/travel-scale-responses.jsonl.gz) and deterministic generator.

A separate [40,000-dataset calibration audit](TAIL_CALIBRATION.md) documents prior sensitivity and poor rare-event frequentist coverage of central Bayesian intervals at low sample sizes. Exact confidence endpoints and model-based intervals remain distinct; no prior is retuned after these results.


The source generator's eligible-offer role suffix is not counterbalanced. This shortcut limitation carries over from the matched v1 generator and prevents a broad benchmark-generalization claim. The observed exposure is heavily influenced by quote-total and other record-application errors in this constrained condition. New opaque-ID live cases are separate; registered inputs and scores are never rewritten after collection.
