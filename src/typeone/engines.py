"""Adapters that run each engine's public API on a batch of simulated experiments.

Every method returns a DataFrame with one row per simulation:
    est, lo, hi  - point estimate and 95% interval for the effect
    p            - two-sided p-value (NaN for Bayesian methods)
    ctw          - chance to win (Bayesian methods only)

Engines audited:
    growthbook  - gbstats, the stats engine behind GrowthBook (installed from main)
    spotify     - spotify-confidence, Spotify's experimentation statistics library
    reference   - textbook formulas written here, as a yardstick
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd
from scipy import stats

from .scenarios import Batch

Z = stats.norm.ppf(0.975)


@dataclass(frozen=True)
class Method:
    engine: str
    name: str            # e.g. "ttest"
    difference: str      # "absolute" | "relative"
    kinds: tuple[str, ...]
    run: Callable[[Batch, str], pd.DataFrame]
    sequential: bool = False

    @property
    def id(self) -> str:
        return f"{self.engine}/{self.name}/{self.difference}"


# ------------------------------------------------------------------ helpers
def _arm_moments(arm: dict, kind: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(n, mean, variance) per simulation for mean/proportion metrics."""
    n = arm["n"]
    if kind == "proportion":
        m = arm["sum"] / n
        return n, m, m * (1 - m) * n / (n - 1)
    m = arm["sum"] / n
    return n, m, (arm["sum_sq"] - arm["sum"] ** 2 / n) / (n - 1)


def _frame(est, se, p=None) -> pd.DataFrame:
    if p is None:
        p = 2 * stats.norm.sf(np.abs(est / se))
    return pd.DataFrame({"est": est, "lo": est - Z * se, "hi": est + Z * se, "p": p, "ctw": np.nan})


# --------------------------------------------------------------- reference
def ref_welch(batch: Batch, diff: str) -> pd.DataFrame:
    na, ma, va = _arm_moments(batch.a, batch.kind)
    nb, mb, vb = _arm_moments(batch.b, batch.kind)
    if diff == "absolute":
        est, se = mb - ma, np.sqrt(va / na + vb / nb)
    else:  # delta method for (mb / ma - 1), including the uncertainty of ma
        est = mb / ma - 1
        se = np.sqrt(vb / (nb * ma**2) + mb**2 * va / (na * ma**4))
    return _frame(est, se)


def _ratio_moments(arm: dict):
    n = arm["n"]
    mm, md = arm["m_sum"] / n, arm["d_sum"] / n
    vm = (arm["m_sum_sq"] - arm["m_sum"] ** 2 / n) / (n - 1)
    vd = (arm["d_sum_sq"] - arm["d_sum"] ** 2 / n) / (n - 1)
    c = (arm["md_sum"] - arm["m_sum"] * arm["d_sum"] / n) / (n - 1)
    r = mm / md
    var_r = (vm - 2 * r * c + r**2 * vd) / (n * md**2)  # delta method, per-user randomisation
    return r, var_r


def ref_fieller(batch: Batch, diff: str) -> pd.DataFrame:
    """Fieller interval for mu_B / mu_A - 1; p-value from the absolute z-test, which is the
    Fieller test of 'no effect' (the interval excludes 0 exactly when the z-test rejects)."""
    na, ma, va = _arm_moments(batch.a, batch.kind)
    nb, mb, vb = _arm_moments(batch.b, batch.kind)
    sa2, sb2 = va / na, vb / nb
    a = ma**2 - Z**2 * sa2
    b = -2 * ma * mb
    c = mb**2 - Z**2 * sb2
    disc = np.sqrt(np.maximum(b**2 - 4 * a * c, 0))
    bounded = a > 0   # otherwise the Fieller set is unbounded: report an infinite interval
    lo = np.where(bounded, (-b - disc) / (2 * a) - 1, -np.inf)
    hi = np.where(bounded, (-b + disc) / (2 * a) - 1, np.inf)
    p = 2 * stats.norm.sf(np.abs(mb - ma) / np.sqrt(sa2 + sb2))
    return pd.DataFrame({"est": mb / ma - 1, "lo": lo, "hi": hi, "p": p, "ctw": np.nan})


def ref_ratio(batch: Batch, diff: str) -> pd.DataFrame:
    ra, va = _ratio_moments(batch.a)
    rb, vb = _ratio_moments(batch.b)
    if diff == "absolute":
        return _frame(rb - ra, np.sqrt(va + vb))
    return _frame(rb / ra - 1, np.sqrt(vb / ra**2 + rb**2 * va / ra**4))


def ref_ratio_naive(batch: Batch, diff: str) -> pd.DataFrame:
    """The classic mistake: treat each session as independent (binomial variance)."""
    def arm(a):
        r = a["m_sum"] / a["d_sum"]
        return r, r * (1 - r) / a["d_sum"]
    ra, va = arm(batch.a)
    rb, vb = arm(batch.b)
    if diff == "absolute":
        return _frame(rb - ra, np.sqrt(va + vb))
    return _frame(rb / ra - 1, np.sqrt(vb / ra**2 + rb**2 * va / ra**4))


def ref_cuped(batch: Batch, diff: str) -> pd.DataFrame:
    a, b = batch.a, batch.b

    def var(s, ss, n):
        return (ss - s**2 / n) / (n - 1)

    def cov(sx, sy, sxy, n):
        return (sxy - sx * sy / n) / (n - 1)

    n = a["n"] + b["n"]
    theta = cov(a["x_sum"] + b["x_sum"], a["y_sum"] + b["y_sum"], a["xy_sum"] + b["xy_sum"], n) / var(
        a["x_sum"] + b["x_sum"], a["x_sum_sq"] + b["x_sum_sq"], n)
    out = []
    for arm in (a, b):
        na = arm["n"]
        my, mx = arm["y_sum"] / na, arm["x_sum"] / na
        vy, vx = var(arm["y_sum"], arm["y_sum_sq"], na), var(arm["x_sum"], arm["x_sum_sq"], na)
        cxy = cov(arm["x_sum"], arm["y_sum"], arm["xy_sum"], na)
        out.append((na, my - theta * mx, (vy + theta**2 * vx - 2 * theta * cxy) / na))
    (_, adj_a, va), (_, adj_b, vb) = out
    if diff == "absolute":
        return _frame(adj_b - adj_a, np.sqrt(va + vb))
    ma = a["y_sum"] / a["n"]
    return _frame((adj_b - adj_a) / ma, np.sqrt(va + vb) / ma)  # approximate; reference only


# --------------------------------------------------------------- GrowthBook
def _gb_stats(batch: Batch, i: int):
    from gbstats.models.statistics import (
        ProportionStatistic,
        RatioStatistic,
        RegressionAdjustedStatistic,
        SampleMeanStatistic,
    )

    def one(arm):
        n = int(arm["n"][i])
        if batch.kind == "proportion":
            return ProportionStatistic(n=n, sum=float(arm["sum"][i]))
        if batch.kind == "mean":
            return SampleMeanStatistic(n=n, sum=float(arm["sum"][i]), sum_squares=float(arm["sum_sq"][i]))
        if batch.kind == "ratio":
            return RatioStatistic(
                n=n,
                m_statistic=SampleMeanStatistic(n=n, sum=float(arm["m_sum"][i]), sum_squares=float(arm["m_sum_sq"][i])),
                d_statistic=SampleMeanStatistic(n=n, sum=float(arm["d_sum"][i]), sum_squares=float(arm["d_sum_sq"][i])),
                m_d_sum_of_products=float(arm["md_sum"][i]))
        return RegressionAdjustedStatistic(
            n=n,
            post_statistic=SampleMeanStatistic(n=n, sum=float(arm["y_sum"][i]), sum_squares=float(arm["y_sum_sq"][i])),
            pre_statistic=SampleMeanStatistic(n=n, sum=float(arm["x_sum"][i]), sum_squares=float(arm["x_sum_sq"][i])),
            post_pre_sum_of_products=float(arm["xy_sum"][i]), theta=None)
    return one(batch.a), one(batch.b)


def _gb_run(make_test) -> Callable[[Batch, str], pd.DataFrame]:
    def run(batch: Batch, diff: str) -> pd.DataFrame:
        rows = []
        for i in range(batch.size):
            sa, sb = _gb_stats(batch, i)
            r = make_test([(sa, sb)], diff).compute_result()
            p = getattr(r, "pValue", None)
            rows.append((r.expected, r.ci[0], r.ci[1], np.nan if p is None else p,
                         getattr(r, "chanceToWin", np.nan)))
        return pd.DataFrame(rows, columns=["est", "lo", "hi", "p", "ctw"])
    return run


def _gb_ttest(stats_, diff):
    from gbstats.frequentist.tests import FrequentistConfig, TwoSidedTTest
    return TwoSidedTTest(stats_, FrequentistConfig(difference_type=diff))


def _gb_sequential(stats_, diff):
    from gbstats.frequentist.tests import SequentialConfig, SequentialTwoSidedTTest
    return SequentialTwoSidedTTest(stats_, SequentialConfig(difference_type=diff))


def _gb_bayes(stats_, diff):
    from gbstats.bayesian.tests import EffectBayesianABTest, EffectBayesianConfig
    return EffectBayesianABTest(stats_, EffectBayesianConfig(difference_type=diff))


# ------------------------------------------------------------------ Spotify
def _spotify_run(cls_name: str) -> Callable[[Batch, str], pd.DataFrame]:
    def run(batch: Batch, diff: str) -> pd.DataFrame:
        import spotify_confidence as sc
        S = batch.size
        df = pd.DataFrame({
            "sim": np.repeat(np.arange(S), 2),
            "group": np.tile(["control", "treatment"], S),
            "sum": np.column_stack([batch.a["sum"], batch.b["sum"]]).ravel(),
            "sum_sq": np.column_stack([batch.a["sum_sq"], batch.b["sum_sq"]]).ravel(),
            "n": np.column_stack([batch.a["n"], batch.b["n"]]).ravel(),
        })
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            test = getattr(sc, cls_name)(
                df, numerator_column="sum", numerator_sum_squares_column="sum_sq",
                denominator_column="n", categorical_group_columns=["group", "sim"])
            d = test.difference(level_1="control", level_2="treatment", groupby="sim",
                                absolute=diff == "absolute").reset_index()
        d = d.sort_values("sim")
        return pd.DataFrame({"est": d["difference"].to_numpy(), "lo": d["ci_lower"].to_numpy(),
                             "hi": d["ci_upper"].to_numpy(), "p": d["p-value"].to_numpy(),
                             "ctw": np.nan})
    return run


# ----------------------------------------------------------------- registry
MEAN_LIKE = ("mean", "proportion")
METHODS: list[Method] = []
METHODS.append(Method("reference", "fieller", "relative", MEAN_LIKE, ref_fieller))
for diff in ("absolute", "relative"):
    METHODS += [
        Method("reference", "delta-z", diff, MEAN_LIKE, ref_welch),
        Method("reference", "ratio-delta", diff, ("ratio",), ref_ratio),
        Method("reference", "ratio-naive", diff, ("ratio",), ref_ratio_naive),
        Method("reference", "cuped-ols", diff, ("cuped",), ref_cuped),
        Method("growthbook", "ttest", diff, ("mean", "proportion", "ratio", "cuped"), _gb_run(_gb_ttest)),
        Method("growthbook", "bayesian", diff, ("mean", "proportion", "ratio", "cuped"), _gb_run(_gb_bayes)),
        Method("growthbook", "sequential", diff, ("mean", "proportion", "ratio", "cuped"),
               _gb_run(_gb_sequential), sequential=True),
        Method("spotify", "ztest", diff, MEAN_LIKE, _spotify_run("ZTest")),
        Method("spotify", "ttest", diff, ("mean",), _spotify_run("StudentsTTest")),
    ]

BY_ID = {m.id: m for m in METHODS}
