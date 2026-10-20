<!-- draft — file at https://github.com/growthbook/growthbook/issues/new (stats engine). Status: not yet filed. -->
# Relative-lift frequentist test is direction-biased for skewed / low-count metrics

## Summary

On simulated experiments with a known truth, `TwoSidedTTest` with `difference_type="relative"` (the delta-method relative test) is miscalibrated in a *directional* way for metrics with noisy control means. The same data analysed with `difference_type="absolute"` is calibrated.

| Metric (users per arm) | A/A false-positive rate | false "losers" | false "winners" | real lift: detected | real lift: wrong direction |
|---|---|---|---|---|---|
| Revenue, 5% buyers, lognormal spend (2,000) | 10.1% (abs 4.1%) | 9.7% | 0.4% | 1.8% (abs 6.6%) | 3.1% |
| Revenue (5,000) | 6.9% (abs 3.8%) | 6.1% | 0.7% | 4.9% (abs 10.7%) | 1.4% |
| Conversion 0.5% (2,000) | 8.8% (abs 5.2%) | 8.8% | 0.0% | 0.0% (abs 9.4%) | 2.1% |

6,000 simulated experiments per cell; real-lift runs use +20% (revenue) and +30% (conversion).

## Why

For proportions, the delta-method statistic is approximately `z_rel ≈ z_abs * sqrt(p_A_hat / p_B_hat)`, exactly so as the rates go to zero (0.8163 vs 0.8165 at 0.5%). When the treatment looks better, z shrinks; when it looks worse, z grows. The plug-in variance is correlated with the estimate, so the test favours "loser" calls and suppresses "winner" calls. The Bayesian engine in relative mode shows the same pattern: under a true +50% lift on a 0.5% conversion rate, chance-to-win > 95% occurs in 0.7% of experiments vs 26% in absolute mode.

## Suggested fix

Decide significance with the absolute-difference test, which is calibrated here, and report the relative lift with a Fieller interval. Fieller's test of "no effect" is identical to the absolute z-test (4.3–5.4% false positives), and its interval covered the true lift 95.0–96.1% of the time in every mean/proportion scenario tested, including the ones above. Alternatively, a log-ratio interval.

## Reproduce

https://github.com/jayden-crypto/typeone — `uv run typeone bias` (≈3 min). gbstats from `main` @ 19d66a7.
