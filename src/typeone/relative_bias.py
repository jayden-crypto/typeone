"""Why relative-lift tests misbehave on noisy metrics, and how much data fixes it.

For conversion rates the delta-method z-statistic for the relative lift is,
to a close approximation at low rates (exactly as the rates go to zero),

    z_rel ≈ z_abs * sqrt(p_A_hat / p_B_hat)

so whenever the treatment *looks* better, z shrinks (real winners are missed),
and whenever it looks worse, z grows (false "losers" are declared). The same
coupling between the estimate and its plug-in variance appears for skewed
revenue metrics. This experiment splits errors by direction and sweeps the
sample size to show how slowly the problem fades.
"""

from __future__ import annotations

import multiprocessing as mp

import numpy as np
import pandas as pd

from .engines import BY_ID
from .scenarios import conversion, revenue

CELLS = (
    [("revenue", n) for n in (2_000, 5_000, 20_000, 50_000)]
    + [("conversion-0.5%", n) for n in (2_000, 10_000, 50_000, 200_000)]
)
LIFTS = {"revenue": 0.20, "conversion-0.5%": 0.30}


def _simulate(kind: str, n: int, rng, sims: int, lift: float):
    if kind == "revenue":
        return revenue(n)(rng, sims, lift)
    return conversion(n, 0.005)(rng, sims, lift)


def _cell(args) -> list[dict]:
    kind, n, sims, seed = args
    rng = np.random.default_rng(seed)
    rows = []
    for hypothesis, lift in (("null", 0.0), ("alt", LIFTS[kind])):
        batch = _simulate(kind, n, rng, sims, lift)
        for diff in ("absolute", "relative"):
            out = BY_ID[f"growthbook/ttest/{diff}"].run(batch, diff)
            sig = out["p"] < 0.05
            rows.append({
                "metric": kind, "n_per_arm": n, "hypothesis": hypothesis, "difference": diff,
                "lift": lift, "sims": sims,
                "reject": float(sig.mean()),
                "false_winners" if hypothesis == "null" else "detected_winners": float((sig & (out["est"] > 0)).mean()),
                "false_losers" if hypothesis == "null" else "wrong_sign": float((sig & (out["est"] < 0)).mean()),
            })
    print(f"  {kind} n={n:,}: done", flush=True)
    return rows


def run_relative_bias(sims: int = 6000, workers: int = 8, seed: int = 99) -> pd.DataFrame:
    cells = [(k, n, sims, seed + i) for i, (k, n) in enumerate(CELLS)]
    with mp.get_context("spawn").Pool(workers) as pool:
        results = pool.map(_cell, cells, chunksize=1)
    return pd.DataFrame([r for rs in results for r in rs])
