<!-- draft — file at https://github.com/spotify/confidence/issues/new. Status: not yet filed. -->
# Relative-difference confidence intervals under-cover when the true lift is non-zero

## Summary

With `absolute=False`, `difference()` returns `(absolute CI) / (control point estimate)` (`_adjust_if_absolute` in `confidence_computer.py`). This treats the control mean as a known constant. When there is a real effect, the interval misses the true relative lift more often than advertised, and **the shortfall does not shrink with sample size**:

| true lift | coverage (n=200/arm) | coverage (n=5,000/arm) | predicted |
|---|---|---|---|
| +10% | 93.6% | 93.7% | 93.8% |
| +25% | 91.7% | 91.5% | 91.7% |
| +50% | 87.2% | 87.8% | 87.6% |
| +100% | 78.6% | 78.8% | 78.5% |

10,000 simulated experiments per cell, normal metric, nominal 95%.

## Why

The interval covers r iff `|x̄_B − (1+r)·x̄_A| ≤ z·sqrt(V_B + V_A)`. But the left-hand side has variance `V_B + (1+r)²·V_A`, so with equal arm variances `coverage(r) = 2Φ(z·sqrt(2/(1+(1+r)²))) − 1`, independent of n. Negative lifts over-cover.

## Suggested fix

Use a Fieller interval for the ratio of means, which keeps the current calibrated p-value (the Fieller test of r=0 equals the absolute z-test), or the delta-method variance including the control mean's uncertainty.

## Reproduce

https://github.com/jayden-crypto/typeone — `uv run typeone lifts`. spotify-confidence 4.1.0.
