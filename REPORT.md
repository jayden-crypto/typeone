# typeone report

10,000 simulated experiments per cell, seed 2026. gbstats 0.8.0, spotify-confidence 4.1.0, numpy 1.26.4, scipy 1.17.1.

Cells in **bold ⚠** are outside the 99% Monte Carlo interval *and* more than one percentage point from nominal.

## Scenarios

| Scenario | Data | Lift in the alternative |
|---|---|---|
| normal | Normal(10, 4), 1,000 users per arm | +5% |
| unequal-split | Normal(10, 4), 9,000 vs 1,000 users | +5% |
| conversion-5% | Bernoulli(5%), 10,000 users per arm | +10% |
| conversion-rare | Bernoulli(0.5%), 2,000 users per arm (~10 conversions) | +50% |
| revenue | Zero-inflated lognormal revenue (5% buyers), 5,000 users per arm | +20% |
| skewed-small | Lognormal(0, 1), 40 users per arm | +30% |
| ratio | Clicks per session with user-level correlation, 2,000 users | +5% |
| cuped | Post metric with pre-period covariate (rho=0.7), 1,000 users | +3% |

## Absolute effects: false-positive rate (no true effect, nominal 5%)

| Scenario | reference / delta-z / absolute | growthbook / ttest / absolute | spotify / ztest / absolute | spotify / ttest / absolute | reference / ratio-delta / absolute | reference / ratio-naive / absolute | reference / cuped-ols / absolute |
|---|---|---|---|---|---|---|---|
| normal | 4.9% | 4.8% | 4.9% | 4.8% |  |  |  |
| unequal-split | 4.9% | 4.8% | 4.9% | 4.8% |  |  |  |
| conversion-5% | 5.4% | 5.4% | 5.4% |  |  |  |  |
| conversion-rare | 5.0% | 4.9% | 5.0% |  |  |  |  |
| revenue | 4.3% | 4.3% | 4.3% | 4.3% |  |  |  |
| skewed-small | 4.5% | 4.0% | 4.5% | 4.0% |  |  |  |
| ratio |  | 4.9% |  |  | 4.9% | **13.0%** ⚠ |  |
| cuped |  | 5.0% |  |  |  |  | 5.0% |

## Absolute effects: interval coverage under a true lift (nominal 95%)

| Scenario | reference / delta-z / absolute | growthbook / ttest / absolute | growthbook / bayesian / absolute | spotify / ztest / absolute | spotify / ttest / absolute | reference / ratio-delta / absolute | reference / ratio-naive / absolute | reference / cuped-ols / absolute |
|---|---|---|---|---|---|---|---|---|
| normal | 94.9% | 94.9% | 94.9% | 94.9% | 94.9% |  |  |  |
| unequal-split | 95.0% | 95.0% | 95.0% | 95.0% | 95.0% |  |  |  |
| conversion-5% | 95.1% | 95.1% | 95.1% | 95.1% |  |  |  |  |
| conversion-rare | 95.2% | 95.2% | 95.2% | 95.2% |  |  |  |  |
| revenue | 95.4% | 95.4% | 95.4% | 95.4% | 95.4% |  |  |  |
| skewed-small | 95.2% | 95.7% | 95.2% | 95.2% | 95.7% |  |  |  |
| ratio |  | 95.0% | 94.9% |  |  | 94.9% | **86.7%** ⚠ |  |
| cuped |  | 94.9% | 94.9% |  |  |  |  | 94.9% |

## Relative effects: false-positive rate (no true effect, nominal 5%)

| Scenario | reference / delta-z / relative | growthbook / ttest / relative | spotify / ztest / relative | spotify / ttest / relative | reference / ratio-delta / relative | reference / ratio-naive / relative | reference / cuped-ols / relative | reference / fieller / relative |
|---|---|---|---|---|---|---|---|---|
| normal | 4.8% | 4.8% | 4.9% | 4.8% |  |  |  | 4.9% |
| unequal-split | 4.8% | 4.8% | 4.9% | 4.8% |  |  |  | 4.9% |
| conversion-5% | 5.4% | 5.4% | 5.4% |  |  |  |  | 5.4% |
| conversion-rare | **8.2%** ⚠ | **8.2%** ⚠ | 5.0% |  |  |  |  | 5.0% |
| revenue | **8.0%** ⚠ | **7.9%** ⚠ | 4.3% | 4.3% |  |  |  | 4.3% |
| skewed-small | **8.7%** ⚠ | **8.1%** ⚠ | 4.5% | 4.0% |  |  |  | 4.5% |
| ratio |  | 5.1% |  |  | 5.1% | **13.1%** ⚠ |  |  |
| cuped |  | 5.0% |  |  |  |  | 5.0% |  |

## Relative effects: interval coverage under a true lift (nominal 95%)

| Scenario | reference / delta-z / relative | growthbook / ttest / relative | growthbook / bayesian / relative | spotify / ztest / relative | spotify / ttest / relative | reference / ratio-delta / relative | reference / ratio-naive / relative | reference / cuped-ols / relative | reference / fieller / relative |
|---|---|---|---|---|---|---|---|---|---|
| normal | 94.9% | 95.0% | 94.9% | 94.4% | 94.4% |  |  |  | 95.0% |
| unequal-split | 95.0% | 95.1% | 95.0% | 94.9% | 94.9% |  |  |  | 95.0% |
| conversion-5% | 95.1% | 95.1% | 95.1% | **93.7%** ⚠ |  |  |  |  | 95.0% |
| conversion-rare | **93.4%** ⚠ | **93.4%** ⚠ | **93.4%** ⚠ | **88.5%** ⚠ |  |  |  |  | 96.1% |
| revenue | **92.3%** ⚠ | **92.3%** ⚠ | **92.3%** ⚠ | **93.2%** ⚠ | **93.2%** ⚠ |  |  |  | 95.7% |
| skewed-small | **91.9%** ⚠ | **92.3%** ⚠ | **91.9%** ⚠ | **91.9%** ⚠ | **92.8%** ⚠ |  |  |  | 95.7% |
| ratio |  | 94.9% | 94.9% |  |  | 94.9% | **86.6%** ⚠ |  |  |
| cuped |  | 94.8% | 94.8% |  |  |  |  | 94.5% |  |

## Bayesian: false winners under no true effect (chance to win > 95%, nominal 5%)

| Scenario | growthbook / bayesian / absolute | growthbook / bayesian / relative |
|---|---|---|
| normal | 5.0% | 4.8% |
| unequal-split | 4.9% | 4.9% |
| conversion-5% | 5.4% | 4.4% |
| conversion-rare | 5.0% | 0.0% |
| revenue | 4.8% | 2.6% |
| skewed-small | 4.9% | 2.7% |
| ratio | 4.8% | 4.1% |
| cuped | 5.0% | 4.8% |

## Sequential test, single look (anytime-valid intervals are conservative by design)

| Scenario | growthbook / sequential / absolute | growthbook / sequential / relative |
|---|---|---|
| normal | 99.8% | 99.8% |
| unequal-split | 99.8% | 99.8% |
| conversion-5% | 99.8% | 99.7% |
| conversion-rare | 99.9% | 97.3% |
| revenue | 99.9% | 98.4% |
| skewed-small | 100.0% | 100.0% |
| ratio | 99.8% | 99.7% |
| cuped | 99.9% | 99.8% |

## Direction of errors: GrowthBook relative vs absolute test

| Metric | Users per arm | Test | A/A: false winners | A/A: false losers | A/B: winner detected | A/B: wrong direction |
|---|---|---|---|---|---|---|
| revenue | 2,000 | absolute | 2.0% | 2.1% | 6.6% | 0.3% |
| revenue | 2,000 | relative | 0.4% | 9.7% | 1.8% | 3.1% |
| revenue | 5,000 | absolute | 1.9% | 1.8% | 10.7% | 0.3% |
| revenue | 5,000 | relative | 0.7% | 6.1% | 4.9% | 1.4% |
| revenue | 20,000 | absolute | 2.4% | 2.3% | 29.8% | 0.0% |
| revenue | 20,000 | relative | 1.4% | 4.6% | 22.7% | 0.1% |
| revenue | 50,000 | absolute | 2.5% | 2.5% | 58.8% | 0.0% |
| revenue | 50,000 | relative | 1.8% | 3.7% | 52.6% | 0.0% |
| conversion-0.5% | 2,000 | absolute | 2.6% | 2.6% | 9.4% | 0.6% |
| conversion-0.5% | 2,000 | relative | 0.0% | 8.8% | 0.0% | 2.1% |
| conversion-0.5% | 10,000 | absolute | 2.7% | 2.6% | 29.7% | 0.0% |
| conversion-0.5% | 10,000 | relative | 0.5% | 5.0% | 14.5% | 0.1% |
| conversion-0.5% | 50,000 | absolute | 2.1% | 2.5% | 88.4% | 0.0% |
| conversion-0.5% | 50,000 | relative | 1.2% | 3.5% | 84.4% | 0.0% |
| conversion-0.5% | 200,000 | absolute | 2.7% | 2.6% | 100.0% | 0.0% |
| conversion-0.5% | 200,000 | relative | 1.9% | 3.0% | 100.0% | 0.0% |

## Relative-lift intervals vs. the true lift

![Coverage of relative-lift intervals](figures/relative_lift_coverage.png)

| n per arm | lift | Spotify | predicted | GrowthBook (delta) | Fieller |
|---|---|---|---|---|---|
| 200 | -50% | 98.7% | 98.7% | 95.1% | 95.0% |
| 200 | -25% | 97.4% | 97.3% | 95.1% | 95.1% |
| 200 | -10% | 96.0% | 96.1% | 95.0% | 94.9% |
| 200 | +0% | 95.0% | 95.0% | 95.1% | 95.0% |
| 200 | +10% | 93.6% | 93.8% | 95.0% | 94.8% |
| 200 | +25% | 91.7% | 91.7% | 95.2% | 95.0% |
| 200 | +50% | 87.2% | 87.6% | 95.1% | 95.0% |
| 200 | +75% | 82.7% | 83.1% | 94.7% | 94.8% |
| 200 | +100% | 78.5% | 78.5% | 94.9% | 94.7% |
| 5,000 | -50% | 98.5% | 98.7% | 95.0% | 95.0% |
| 5,000 | -25% | 97.5% | 97.3% | 95.3% | 95.2% |
| 5,000 | -10% | 96.4% | 96.1% | 95.1% | 95.2% |
| 5,000 | +0% | 95.1% | 95.0% | 95.0% | 95.1% |
| 5,000 | +10% | 93.7% | 93.8% | 95.0% | 95.0% |
| 5,000 | +25% | 91.5% | 91.7% | 94.8% | 94.8% |
| 5,000 | +50% | 87.8% | 87.6% | 94.8% | 94.8% |
| 5,000 | +75% | 83.2% | 83.1% | 94.9% | 94.9% |
| 5,000 | +100% | 78.8% | 78.5% | 95.2% | 95.3% |

## Peeking: checking an A/A test every day

![Peeking](figures/peeking.png)

| Method | Ever declared a winner | Interval ever excluded the truth |
|---|---|---|
| reference/delta-z/absolute | 25.4% | 25.4% |
| growthbook/ttest/absolute | 25.2% | 25.2% |
| growthbook/bayesian/absolute | 21.9% | 25.4% |
| growthbook/sequential/absolute | 1.3% | 1.3% |
| spotify/ztest/absolute | 25.4% | 25.4% |
