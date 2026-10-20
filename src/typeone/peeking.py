"""Peeking: what happens when you check an experiment every day?

Simulates experiments under the null that accumulate users over D daily looks.
At every look each method is evaluated on the cumulative data, and we record
whether it has *ever* declared a winner (or ever excluded the true effect from
its interval). A fixed-horizon test checked daily inflates false positives;
GrowthBook's sequential test is designed to stay below alpha at every look
("anytime-valid"). This module measures both.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .engines import METHODS
from .scenarios import Batch, _normal_stats

PEEK_METHODS = ["growthbook/ttest/absolute", "growthbook/sequential/absolute",
                "growthbook/bayesian/absolute", "spotify/ztest/absolute", "reference/delta-z/absolute"]


def cumulative_batches(rng, sims: int, looks: int, per_look: int, mu=10.0, sigma=4.0, lift=0.0):
    """Yield one Batch per look, with sufficient statistics accumulated over days."""
    acc = None
    for _ in range(looks):
        a = _normal_stats(rng, sims, per_look, mu, sigma)
        b = _normal_stats(rng, sims, per_look, mu * (1 + lift), sigma)
        if acc is None:
            acc = (a, b)
        else:
            acc = tuple({k: prev[k] + new[k] for k in prev} for prev, new in zip(acc, (a, b)))
        yield Batch("mean", acc[0], acc[1], mu * lift, lift)


def run_peeking(sims: int = 4000, looks: int = 20, per_look: int = 250, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    methods = [m for m in METHODS if m.id in PEEK_METHODS]
    ever_reject = {m.id: np.zeros(sims, bool) for m in methods}
    ever_miss = {m.id: np.zeros(sims, bool) for m in methods}
    rows = []
    for look, batch in enumerate(cumulative_batches(rng, sims, looks, per_look), start=1):
        for m in methods:
            out = m.run(batch, m.difference)
            if m.name == "bayesian":
                winner = out["ctw"].to_numpy() > 0.95
            else:
                winner = out["p"].to_numpy() < 0.05
            ever_reject[m.id] |= winner
            ever_miss[m.id] |= ~((out["lo"] <= 0) & (0 <= out["hi"])).to_numpy()
            rows.append({"look": look, "users_per_arm": look * per_look, "method": m.id,
                         "reject_this_look": winner.mean(),
                         "ever_rejected": ever_reject[m.id].mean(),
                         "ever_excluded_truth": ever_miss[m.id].mean()})
        print(f"  look {look}/{looks}", flush=True)
    return pd.DataFrame(rows)
