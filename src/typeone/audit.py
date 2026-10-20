"""Run the conformance grid: scenarios x {null, alternative} x methods.

For every cell we measure, over S simulated experiments with a known truth:
  reject   - share of experiments declared significant (p < 0.05). Under the
             null this is the false-positive rate (nominal 5%); under the
             alternative it is power.
  coverage - share of 95% intervals containing the true effect (nominal 95%).
  win95    - Bayesian only: share with chance-to-win > 95% (GrowthBook's
             "winner" threshold). Under the null, a calibrated posterior gives 5%.
Every rate comes with a Wilson interval, so a flag means "outside Monte Carlo
noise", not "a bit off".
"""

from __future__ import annotations

import json
import multiprocessing as mp
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .engines import METHODS
from .scenarios import BY_NAME, SCENARIOS

ALPHA = 0.05


def wilson(k: float, n: int, z: float = 2.576) -> tuple[float, float]:
    """99% Wilson score interval for a binomial proportion."""
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return centre - half, centre + half


def _rate(mask: np.ndarray) -> dict:
    mask = mask[~np.isnan(mask)] if mask.dtype.kind == "f" else mask
    k, n = int(mask.sum()), int(mask.size)
    lo, hi = wilson(k, n)
    return {"rate": k / n if n else np.nan, "lo": lo, "hi": hi, "n": n}


def run_cell(args: tuple) -> tuple[list[dict], dict]:
    scenario_name, hypothesis, sims, seed, only = args
    sc = BY_NAME[scenario_name]
    rng = np.random.default_rng(seed)
    lift = 0.0 if hypothesis == "null" else sc.lift
    t0 = time.time()
    batch = sc.simulate(rng, sims, lift)
    rows, pvalues = [], {}
    for m in METHODS:
        if batch.kind not in m.kinds or (only and m.id not in only):
            continue
        t = time.time()
        out = m.run(batch, m.difference)
        truth = 0.0 if hypothesis == "null" else (batch.true_abs if m.difference == "absolute" else batch.true_rel)
        valid = np.isfinite(out["lo"]) & np.isfinite(out["hi"])
        covered = ((out["lo"] <= truth) & (truth <= out["hi"]))[valid].to_numpy()
        row = {
            "scenario": scenario_name, "hypothesis": hypothesis, "method": m.id, "engine": m.engine,
            "test": m.name, "difference": m.difference, "sequential": m.sequential,
            "truth": truth, "sims": sims, "invalid": int((~valid).sum()),
            "mean_est": float(out["est"].mean()), "bias": float(out["est"].mean() - truth),
            "median_width": float((out["hi"] - out["lo"]).median()),
            "seconds": round(time.time() - t, 2),
        }
        cov = _rate(covered)
        row.update(coverage=cov["rate"], coverage_lo=cov["lo"], coverage_hi=cov["hi"])
        if out["p"].notna().any():
            rej = _rate((out["p"] < ALPHA).to_numpy()[out["p"].notna().to_numpy()])
            row.update(reject=rej["rate"], reject_lo=rej["lo"], reject_hi=rej["hi"])
            if hypothesis == "null":
                pvalues[m.id] = out["p"].to_numpy()
        if out["ctw"].notna().any():
            ctw = out["ctw"].to_numpy()
            w = _rate(ctw > 0.95)
            row.update(win95=w["rate"], win95_lo=w["lo"], win95_hi=w["hi"],
                       reject=float(((ctw > 0.975) | (ctw < 0.025)).mean()))
            if hypothesis == "null":
                pvalues[m.id] = 2 * np.minimum(ctw, 1 - ctw)  # posterior "two-sided p"
        rows.append(row)
    print(f"  {scenario_name:16} {hypothesis:5} done in {time.time() - t0:5.0f}s", flush=True)
    return rows, pvalues


def flag(row: pd.Series) -> str:
    """Name the deviation, if any, that is beyond Monte Carlo noise and material (>1 point)."""
    flags = []
    if row["hypothesis"] == "null" and pd.notna(row.get("reject")) and pd.notna(row.get("reject_lo")):
        if row["reject_lo"] > ALPHA and row["reject"] > ALPHA + 0.01:
            flags.append("inflated false positives")
    if pd.notna(row.get("win95_lo")) and row["hypothesis"] == "null":
        if row["win95_lo"] > ALPHA and row["win95"] > ALPHA + 0.01:
            flags.append("inflated false winners")
    if row["coverage_hi"] < 0.95 and row["coverage"] < 0.94:
        flags.append("under-coverage")
    return "; ".join(flags)


def run_audit(out_dir: str | Path, sims: int = 10_000, workers: int = 8, seed: int = 2026,
              scenarios: list[str] | None = None, methods: list[str] | None = None) -> pd.DataFrame:
    """Run the grid. With `methods`, only those methods are computed and merged into an
    existing results.csv; seeds are per cell, so they see exactly the same simulated data."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    names = scenarios or [s.name for s in SCENARIOS]
    all_names = [s.name for s in SCENARIOS]
    cells = [(n, h, sims, seed + 1000 * all_names.index(n) + (0 if h == "null" else 1), methods)
             for n in names for h in ("null", "alt")]
    # slow (Spotify-heavy, mean-metric) cells first for better packing
    cells.sort(key=lambda c: BY_NAME[c[0]].kind not in ("mean", "proportion"))
    print(f"running {len(cells)} cells x {sims} simulations on {workers} workers", flush=True)
    with mp.get_context("spawn").Pool(workers) as pool:
        results = pool.map(run_cell, cells, chunksize=1)
    rows = [r for rs, _ in results for r in rs]
    df = pd.DataFrame(rows)
    df["flag"] = df.apply(flag, axis=1)
    if methods and (out_dir / "results.csv").exists():
        old = pd.read_csv(out_dir / "results.csv", keep_default_na=False, na_values=[""])
        df = pd.concat([old[~old["method"].isin(methods)], df], ignore_index=True)
        df["flag"] = df["flag"].fillna("")
        df.to_csv(out_dir / "results.csv", index=False)
        return df
    df.to_csv(out_dir / "results.csv", index=False)
    pvals = {f"{c[0]}|{k}": v for (rs, pv), c in zip(results, cells) for k, v in pv.items()}
    np.savez_compressed(out_dir / "null_pvalues.npz", **pvals)
    meta = {"sims": sims, "seed": seed, "scenarios": names}
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=1))
    return df
