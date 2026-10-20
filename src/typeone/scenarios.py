"""Data-generating processes with a known ground truth.

Each scenario simulates S independent experiments and returns, per arm, the
sufficient statistics that experimentation engines consume (counts, sums, sums
of squares, cross-products), plus the *true* absolute and relative effect.
Where an exact shortcut exists (normal and Bernoulli data) we draw the
sufficient statistics directly; otherwise we simulate users in chunks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np

Arm = dict[str, np.ndarray]


@dataclass
class Batch:
    kind: str                 # "mean" | "proportion" | "ratio" | "cuped"
    a: Arm                    # control sufficient statistics, arrays of shape (S,)
    b: Arm                    # treatment
    true_abs: float
    true_rel: float

    @property
    def size(self) -> int:
        return len(self.a["n"])


@dataclass
class Scenario:
    name: str
    kind: str
    description: str
    n_a: int
    n_b: int
    lift: float               # relative lift used for the "alternative" runs
    simulate: Callable[[np.random.Generator, int, float], Batch] = field(repr=False)


# ------------------------------------------------------------------ helpers
def _normal_stats(rng, S: int, n: int, mu: float, sigma: float) -> Arm:
    """Exact joint draw of (sum, sum of squares) for n iid normal values."""
    mean = rng.normal(mu, sigma / np.sqrt(n), S)
    ss_within = sigma**2 * rng.chisquare(n - 1, S)
    return {"n": np.full(S, n, float), "sum": n * mean, "sum_sq": ss_within + n * mean**2}


def _raw_stats(values: np.ndarray) -> Arm:
    """values: (S, n) matrix of user-level outcomes."""
    return {"n": np.full(values.shape[0], values.shape[1], float),
            "sum": values.sum(1), "sum_sq": (values**2).sum(1)}


def _chunked(rng, S: int, make: Callable[[np.random.Generator, int], Arm], chunk_elems: int, n: int) -> Arm:
    step = max(1, chunk_elems // n)
    parts = [make(rng, min(step, S - i)) for i in range(0, S, step)]
    return {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}


# ---------------------------------------------------------------- scenarios
def normal(n=1000, mu=10.0, sigma=4.0, n_b=None):
    n_b = n_b or n

    def sim(rng, S, lift):
        mu_b = mu * (1 + lift)
        return Batch("mean", _normal_stats(rng, S, n, mu, sigma),
                     _normal_stats(rng, S, n_b, mu_b, sigma), mu_b - mu, lift)
    return sim


def conversion(n, p):
    def sim(rng, S, lift):
        p_b = p * (1 + lift)
        sa, sb = rng.binomial(n, p, S).astype(float), rng.binomial(n, p_b, S).astype(float)
        mk = lambda s: {"n": np.full(S, n, float), "sum": s, "sum_sq": s}  # noqa: E731
        return Batch("proportion", mk(sa), mk(sb), p_b - p, lift)
    return sim


def revenue(n, buy_p=0.05, log_mu=3.0, log_sigma=1.5):
    """Zero-inflated, heavy-tailed revenue per user."""
    spend_mean = np.exp(log_mu + log_sigma**2 / 2)

    def arm(rng, S, scale):
        def make(rng, s):
            buys = rng.random((s, n)) < buy_p
            v = np.where(buys, rng.lognormal(log_mu, log_sigma, (s, n)) * scale, 0.0)
            return _raw_stats(v)
        return _chunked(rng, S, make, 4_000_000, n)

    def sim(rng, S, lift):
        mu_a = buy_p * spend_mean
        return Batch("mean", arm(rng, S, 1.0), arm(rng, S, 1 + lift), mu_a * lift, lift)
    return sim


def skewed_small(n=40):
    """Small sample of lognormal values: the t-test's worst case."""
    mu_a = np.exp(0.5)

    def arm(rng, S, scale):
        return _raw_stats(rng.lognormal(0, 1, (S, n)) * scale)

    def sim(rng, S, lift):
        return Batch("mean", arm(rng, S, 1.0), arm(rng, S, 1 + lift), mu_a * lift, lift)
    return sim


def ratio(n=2000, sessions_mean=3.0, ctr=0.2, ctr_concentration=4.0):
    """Clicks per session. Users differ in activity and CTR, so sessions within a user
    are correlated and a naive per-session variance is wrong (needs the delta method)."""
    def arm(rng, S, lift):
        def make(rng, s):
            sessions = 1 + rng.poisson(rng.gamma(2.0, (sessions_mean - 1) / 2.0, (s, n)))
            p_user = rng.beta(ctr * ctr_concentration, (1 - ctr) * ctr_concentration, (s, n))
            clicks = rng.binomial(sessions, np.clip(p_user * (1 + lift), 0, 1)).astype(float)
            d = sessions.astype(float)
            return {"n": np.full(s, n, float), "m_sum": clicks.sum(1), "m_sum_sq": (clicks**2).sum(1),
                    "d_sum": d.sum(1), "d_sum_sq": (d**2).sum(1), "md_sum": (clicks * d).sum(1)}
        return _chunked(rng, S, make, 3_000_000, n)

    def sim(rng, S, lift):
        # E[clicks]/E[sessions] = E[p * sessions]/E[sessions] = ctr (p independent of sessions)
        return Batch("ratio", arm(rng, S, 0.0), arm(rng, S, lift), ctr * lift, lift)
    return sim


def cuped(n=1000, mu=10.0, sigma=4.0, rho=0.7):
    """Post-period metric correlated with a pre-period covariate (variance reduction)."""
    def arm(rng, S, lift):
        def make(rng, s):
            x = rng.normal(mu, sigma, (s, n))
            y = mu + rho * (x - mu) + rng.normal(0, sigma * np.sqrt(1 - rho**2), (s, n))
            y = y * (1 + lift)
            return {"n": np.full(s, n, float), "y_sum": y.sum(1), "y_sum_sq": (y**2).sum(1),
                    "x_sum": x.sum(1), "x_sum_sq": (x**2).sum(1), "xy_sum": (x * y).sum(1)}
        return _chunked(rng, S, make, 4_000_000, n)

    def sim(rng, S, lift):
        return Batch("cuped", arm(rng, S, 0.0), arm(rng, S, lift), mu * lift, lift)
    return sim


SCENARIOS: list[Scenario] = [
    Scenario("normal", "mean", "Normal(10, 4), 1,000 users per arm", 1000, 1000, 0.05, normal()),
    Scenario("unequal-split", "mean", "Normal(10, 4), 9,000 vs 1,000 users", 9000, 1000, 0.05,
             normal(n=9000, n_b=1000)),
    Scenario("conversion-5%", "proportion", "Bernoulli(5%), 10,000 users per arm", 10000, 10000, 0.10,
             conversion(10000, 0.05)),
    Scenario("conversion-rare", "proportion", "Bernoulli(0.5%), 2,000 users per arm (~10 conversions)",
             2000, 2000, 0.50, conversion(2000, 0.005)),
    Scenario("revenue", "mean", "Zero-inflated lognormal revenue (5% buyers), 5,000 users per arm",
             5000, 5000, 0.20, revenue(5000)),
    Scenario("skewed-small", "mean", "Lognormal(0, 1), 40 users per arm", 40, 40, 0.30, skewed_small(40)),
    Scenario("ratio", "ratio", "Clicks per session with user-level correlation, 2,000 users", 2000, 2000,
             0.05, ratio()),
    Scenario("cuped", "cuped", "Post metric with pre-period covariate (rho=0.7), 1,000 users", 1000, 1000,
             0.03, cuped()),
]

BY_NAME = {s.name: s for s in SCENARIOS}
