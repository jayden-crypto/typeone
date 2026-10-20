"""How do relative-lift confidence intervals behave as the true lift grows?

Three ways to build a 95% interval for r = mu_B / mu_A - 1:
  * spotify    - spotify-confidence: (absolute CI) / (control mean). Treats the
                 control mean as a known constant.
  * growthbook - gbstats: delta method, including the control mean's variance.
  * fieller    - Fieller's theorem: exact for normal data, the textbook gold standard.

Closed-form prediction for the "divide by the control mean" interval: the
coverage condition is |xbar_B - (1+r) xbar_A| <= z * sqrt(V_B + V_A), but the
left side has variance V_B + (1+r)^2 V_A, so with equal arm variances

    coverage(r) = 2 * Phi(z * sqrt(2 / (1 + (1+r)^2))) - 1

which does not depend on the sample size: more data does not fix it.
"""

from __future__ import annotations

import multiprocessing as mp

import numpy as np
import pandas as pd
from scipy import stats

from .engines import BY_ID, Z, _arm_moments
from .scenarios import normal

LIFTS = [-0.5, -0.25, -0.1, 0.0, 0.1, 0.25, 0.5, 0.75, 1.0]


def predicted_divide_by_control(r: float) -> float:
    return float(2 * stats.norm.cdf(Z * np.sqrt(2 / (1 + (1 + r) ** 2))) - 1)


def fieller(batch, z: float = Z) -> tuple[np.ndarray, np.ndarray]:
    """Fieller interval for mu_B/mu_A - 1 with independent arms."""
    na, ma, va = _arm_moments(batch.a, batch.kind)
    nb, mb, vb = _arm_moments(batch.b, batch.kind)
    sa2, sb2 = va / na, vb / nb
    # solve (mb - q ma)^2 = z^2 (sb2 + q^2 sa2) for q
    a = ma**2 - z**2 * sa2
    b = -2 * ma * mb
    c = mb**2 - z**2 * sb2
    disc = np.sqrt(np.maximum(b**2 - 4 * a * c, 0))
    lo, hi = (-b - disc) / (2 * a), (-b + disc) / (2 * a)
    return lo - 1, hi - 1


def _cell(args):
    lift, sims, n, seed = args
    rng = np.random.default_rng(seed)
    batch = normal(n=n, mu=10.0, sigma=4.0)(rng, sims, lift)
    truth = batch.true_rel
    out = {"lift": lift, "n_per_arm": n, "sims": sims,
           "predicted_spotify": predicted_divide_by_control(lift)}
    for label, method_id in (("spotify", "spotify/ztest/relative"), ("growthbook", "growthbook/ttest/relative")):
        r = BY_ID[method_id].run(batch, "relative")
        out[label] = float(((r["lo"] <= truth) & (truth <= r["hi"])).mean())
    lo, hi = fieller(batch)
    out["fieller"] = float(((lo <= truth) & (truth <= hi)).mean())
    print(f"  lift {lift:+.2f} n={n}: done", flush=True)
    return out


def run_lift_sweep(sims: int = 10_000, sizes=(200, 5000), workers: int = 8, seed: int = 11) -> pd.DataFrame:
    grid = [(lift, n) for n in sizes for lift in LIFTS]
    cells = [(lift, sims, n, seed + i) for i, (lift, n) in enumerate(grid)]
    with mp.get_context("spawn").Pool(workers) as pool:
        rows = pool.map(_cell, cells, chunksize=1)
    return pd.DataFrame(rows)
