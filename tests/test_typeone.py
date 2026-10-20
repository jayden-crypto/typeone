import numpy as np
import pytest
from scipy import stats

from typeone.audit import wilson
from typeone.engines import BY_ID, ref_ratio, ref_welch
from typeone.lift_sweep import fieller, predicted_divide_by_control
from typeone.scenarios import SCENARIOS, Batch


def batch_from(a: np.ndarray, b: np.ndarray, kind="mean") -> Batch:
    def arm(x):
        return {"n": np.array([len(x)], float), "sum": np.array([x.sum()]), "sum_sq": np.array([(x**2).sum()])}
    return Batch(kind, arm(a), arm(b), 0.0, 0.0)


@pytest.fixture
def data():
    rng = np.random.default_rng(0)
    return rng.normal(10, 3, 400), rng.normal(10.4, 3, 500)


def test_reference_matches_scipy_welch(data):
    a, b = data
    out = ref_welch(batch_from(a, b), "absolute").iloc[0]
    se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    assert out.est == pytest.approx(b.mean() - a.mean())
    assert out.hi - out.lo == pytest.approx(2 * stats.norm.ppf(0.975) * se)
    # z-test p-value is close to scipy's Welch t-test at this sample size
    assert out.p == pytest.approx(stats.ttest_ind(b, a, equal_var=False).pvalue, rel=0.02)


@pytest.mark.parametrize("method", ["growthbook/ttest/absolute", "spotify/ztest/absolute", "spotify/ttest/absolute"])
def test_engines_agree_with_reference_on_point_estimate_and_interval(method, data):
    a, b = data
    batch = batch_from(a, b)
    ref = ref_welch(batch, "absolute").iloc[0]
    out = BY_ID[method].run(batch, "absolute").iloc[0]
    assert out.est == pytest.approx(ref.est, rel=1e-9)
    assert out.hi - out.lo == pytest.approx(ref.hi - ref.lo, rel=0.01)  # t vs z quantiles differ slightly


def test_growthbook_relative_uses_delta_method(data):
    a, b = data
    batch = batch_from(a, b)
    ref = ref_welch(batch, "relative").iloc[0]
    gb = BY_ID["growthbook/ttest/relative"].run(batch, "relative").iloc[0]
    assert gb.est == pytest.approx(ref.est, rel=1e-9)
    assert gb.hi - gb.lo == pytest.approx(ref.hi - ref.lo, rel=0.01)


def test_spotify_relative_is_absolute_divided_by_control_mean(data):
    a, b = data
    batch = batch_from(a, b)
    absolute = BY_ID["spotify/ztest/absolute"].run(batch, "absolute").iloc[0]
    relative = BY_ID["spotify/ztest/relative"].run(batch, "relative").iloc[0]
    assert relative.lo == pytest.approx(absolute.lo / a.mean())
    assert relative.hi == pytest.approx(absolute.hi / a.mean())
    assert relative.p == pytest.approx(absolute.p)


def test_ratio_delta_method_matches_user_level_bootstrap():
    rng = np.random.default_rng(3)
    sessions = 1 + rng.poisson(2, 3000)
    clicks = rng.binomial(sessions, rng.beta(1, 4, 3000))
    arm = {"n": np.array([3000.0]), "m_sum": np.array([clicks.sum()], float),
           "m_sum_sq": np.array([(clicks**2).sum()], float), "d_sum": np.array([sessions.sum()], float),
           "d_sum_sq": np.array([(sessions**2).sum()], float), "md_sum": np.array([(clicks * sessions).sum()], float)}
    se = (ref_ratio(Batch("ratio", arm, arm, 0, 0), "absolute").iloc[0].hi
          - ref_ratio(Batch("ratio", arm, arm, 0, 0), "absolute").iloc[0].lo) / (2 * 1.96) / np.sqrt(2)
    idx = rng.integers(0, 3000, (2000, 3000))
    boot = clicks[idx].sum(1) / sessions[idx].sum(1)
    assert se == pytest.approx(boot.std(), rel=0.08)


def test_fieller_contains_delta_interval_centre(data):
    a, b = data
    batch = batch_from(a, b)
    lo, hi = fieller(batch)
    est = ref_welch(batch, "relative").iloc[0].est
    assert lo[0] < est < hi[0]


def test_predicted_coverage_formula():
    assert predicted_divide_by_control(0.0) == pytest.approx(0.95, abs=1e-6)
    assert predicted_divide_by_control(0.5) < 0.9 < predicted_divide_by_control(0.1)


def test_wilson_interval_contains_rate():
    lo, hi = wilson(500, 10_000)
    assert lo < 0.05 < hi and hi - lo < 0.012


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.name)
def test_scenario_truth_matches_simulation(scenario):
    """The estimated effect, averaged over many simulations, converges on the stated truth."""
    rng = np.random.default_rng(5)
    batch = scenario.simulate(rng, 400, scenario.lift)
    method = {"mean": "reference/delta-z/absolute", "proportion": "reference/delta-z/absolute",
              "ratio": "reference/ratio-delta/absolute", "cuped": "reference/cuped-ols/absolute"}[batch.kind]
    out = BY_ID[method].run(batch, "absolute")
    se_of_mean = out["est"].std() / np.sqrt(len(out))
    assert abs(out["est"].mean() - batch.true_abs) < 4 * se_of_mean


def test_fieller_rejects_exactly_when_absolute_z_test_rejects():
    """Whenever the Fieller set is a bounded interval, it excludes 'no effect' exactly when the
    unpooled absolute z-test rejects. (If the control mean is indistinguishable from zero the set
    is unbounded and Fieller honestly declines to bound the ratio.)"""
    from typeone.engines import ref_fieller
    from typeone.scenarios import BY_NAME
    rng = np.random.default_rng(11)
    for name in ("normal", "conversion-rare", "skewed-small"):
        batch = BY_NAME[name].simulate(rng, 2000, 0.0)
        f = ref_fieller(batch, "relative")
        z = ref_welch(batch, "absolute")
        bounded = np.isfinite(f["lo"]) & np.isfinite(f["hi"])
        excludes_zero = (f["lo"] > 0) | (f["hi"] < 0)
        assert (excludes_zero == (z["p"] < 0.05))[bounded].all()
        assert np.allclose(f["p"], z["p"])
