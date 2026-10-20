"""Turn audit outputs into REPORT.md and figures."""

from __future__ import annotations

import json
from importlib import metadata
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from .scenarios import BY_NAME  # noqa: E402

# Reference palette (validated: categorical slots 1-3, all pairs, light mode)
SURFACE, INK, INK_2, GRID, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1", "#8d8c86"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]


def _style(ax, ylabel: str, xlabel: str) -> None:
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_2, labelsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_ylabel(ylabel, color=INK_2, fontsize=10)
    ax.set_xlabel(xlabel, color=INK_2, fontsize=10)


def _line(ax, x, y, color, label, dashed=False, dy=0):
    ax.plot(x, y, color=color, linewidth=2, linestyle="--" if dashed else "-",
            marker=None if dashed else "o", markersize=5, markeredgecolor=SURFACE,
            markeredgewidth=1.5, label=label)
    if label:
        ax.annotate(label, (x[-1], y[-1]), xytext=(6, dy), textcoords="offset points",
                    va="center", fontsize=9, color=INK)


def lift_figure(df: pd.DataFrame, path: Path) -> None:
    sizes = sorted(df["n_per_arm"].unique())
    fig, axes = plt.subplots(1, len(sizes), figsize=(5.2 * len(sizes), 3.8), sharey=True,
                             facecolor=SURFACE)
    for ax, n in zip(axes, sizes):
        d = df[df["n_per_arm"] == n].sort_values("lift")
        x = (d["lift"] * 100).to_numpy()
        ax.axhline(95, color=INK_2, linewidth=1, linestyle=":")
        ax.text(x[0], 95.3, "nominal 95%", color=INK_2, fontsize=8)
        _line(ax, x, (d["predicted_spotify"] * 100).to_numpy(), MUTED, "", dashed=True)
        _line(ax, x, (d["spotify"] * 100).to_numpy(), SERIES[0], "Spotify")
        _line(ax, x, (d["growthbook"] * 100).to_numpy(), SERIES[1], "GrowthBook", dy=7)
        _line(ax, x, (d["fieller"] * 100).to_numpy(), SERIES[2], "Fieller", dy=-7)
        _style(ax, "Coverage of true relative lift (%)" if ax is axes[0] else "", "True relative lift (%)")
        ax.set_title(f"{n:,} users per arm", color=INK, fontsize=11, loc="left")
        ax.set_xlim(x[0] - 5, x[-1] + 30)
    axes[0].set_ylim(75, 100)
    handles, labels = axes[-1].get_legend_handles_labels()
    keep = [(h, lbl) for h, lbl in zip(handles, labels) if lbl]
    keep.append((plt.Line2D([], [], color=MUTED, linestyle="--", linewidth=2), "Spotify, predicted by formula"))
    fig.legend(*zip(*keep), loc="upper center", ncol=4, frameon=False, fontsize=9, labelcolor=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def peeking_figure(df: pd.DataFrame, path: Path) -> None:
    labels = {"growthbook/ttest/absolute": "Fixed-horizon t-test",
              "growthbook/bayesian/absolute": "Bayesian, chance to win > 95%",
              "growthbook/sequential/absolute": "Sequential (anytime-valid)"}
    fig, ax = plt.subplots(figsize=(7.5, 4), facecolor=SURFACE)
    ax.axhline(5, color=INK_2, linewidth=1, linestyle=":")
    ax.text(df["look"].max(), 5.6, "5% promised", color=INK_2, fontsize=8, ha="right")
    for color, (mid, label) in zip(SERIES, labels.items()):
        d = df[df["method"] == mid].sort_values("look")
        _line(ax, d["look"].to_numpy(), (d["ever_rejected"] * 100).to_numpy(), color, label)
    _style(ax, "Experiments ever declared a winner (%)", "Number of daily looks at an A/A test")
    ax.set_xlim(0.5, df["look"].max() + 8)
    ax.set_ylim(0, None)
    ax.legend(frameon=False, fontsize=9, labelcolor=INK, loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def _pct(x) -> str:
    return "–" if pd.isna(x) else f"{100 * x:.1f}%"


def _grid(df: pd.DataFrame, value: str, flag_word: str) -> str:
    """Markdown table: rows = scenarios, columns = methods. Flagged cells are bold with a warning sign."""
    methods = list(dict.fromkeys(df["method"]))
    header = "| Scenario | " + " | ".join(m.replace("/", " / ") for m in methods) + " |"
    lines = [header, "|" + "---|" * (len(methods) + 1)]
    for scen, g in df.groupby("scenario", sort=False):
        cells = []
        for m in methods:
            r = g[g["method"] == m]
            if r.empty:
                cells.append("")
                continue
            r = r.iloc[0]
            text = _pct(r[value])
            if flag_word in str(r["flag"]):
                text = f"**{text}** ⚠"
            cells.append(text)
        lines.append(f"| {scen} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_report(results_dir: Path, out: Path) -> None:
    results_dir = Path(results_dir)
    fig_dir = out.parent / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(results_dir / "results.csv", keep_default_na=False, na_values=[""])
    meta = json.loads((results_dir / "meta.json").read_text())
    versions = {lib: metadata.version(lib) for lib in ("gbstats", "spotify-confidence", "numpy", "scipy")}
    parts = [
        "# typeone report", "",
        f"{meta['sims']:,} simulated experiments per cell, seed {meta['seed']}. "
        + ", ".join(f"{k} {v}" for k, v in versions.items()) + ".", "",
        "Cells in **bold ⚠** are outside the 99% Monte Carlo interval *and* more than one percentage "
        "point from nominal.", "",
        "## Scenarios", "",
        "| Scenario | Data | Lift in the alternative |", "|---|---|---|",
    ]
    for name in meta["scenarios"]:
        s = BY_NAME[name]
        parts.append(f"| {name} | {s.description} | {s.lift:+.0%} |")

    fixed = df[~df["sequential"]]
    for diff in ("absolute", "relative"):
        null = fixed[(fixed["hypothesis"] == "null") & (fixed["difference"] == diff) & fixed["reject"].notna()]
        alt = fixed[(fixed["hypothesis"] == "alt") & (fixed["difference"] == diff)]
        parts += ["", f"## {diff.capitalize()} effects: false-positive rate (no true effect, nominal 5%)", "",
                  _grid(null[null["test"] != "bayesian"], "reject", "inflated"),
                  "", f"## {diff.capitalize()} effects: interval coverage under a true lift (nominal 95%)", "",
                  _grid(alt, "coverage", "under-coverage")]
    bayes = df[(df["test"] == "bayesian") & (df["hypothesis"] == "null")]
    parts += ["", "## Bayesian: false winners under no true effect (chance to win > 95%, nominal 5%)", "",
              _grid(bayes, "win95", "inflated false winners")]
    seq = df[df["sequential"] & (df["hypothesis"] == "null")]
    parts += ["", "## Sequential test, single look (anytime-valid intervals are conservative by design)", "",
              _grid(seq, "coverage", "under-coverage")]

    if (results_dir / "relative_bias.csv").exists():
        b = pd.read_csv(results_dir / "relative_bias.csv", keep_default_na=False, na_values=[""])
        parts += ["", "## Direction of errors: GrowthBook relative vs absolute test", "",
                  "| Metric | Users per arm | Test | A/A: false winners | A/A: false losers | "
                  "A/B: winner detected | A/B: wrong direction |", "|---|---|---|---|---|---|---|"]
        for (metric, n, diff), g in b.groupby(["metric", "n_per_arm", "difference"], sort=False):
            null, alt = g[g.hypothesis == "null"].iloc[0], g[g.hypothesis == "alt"].iloc[0]
            parts.append(f"| {metric} | {n:,} | {diff} | {_pct(null.false_winners)} | {_pct(null.false_losers)} "
                         f"| {_pct(alt.detected_winners)} | {_pct(alt.wrong_sign)} |")
    if (results_dir / "lift_sweep.csv").exists():
        lift = pd.read_csv(results_dir / "lift_sweep.csv")
        lift_figure(lift, fig_dir / "relative_lift_coverage.png")
        parts += ["", "## Relative-lift intervals vs. the true lift", "",
                  "![Coverage of relative-lift intervals](figures/relative_lift_coverage.png)", "",
                  "| n per arm | lift | Spotify | predicted | GrowthBook (delta) | Fieller |",
                  "|---|---|---|---|---|---|"]
        for _, r in lift.sort_values(["n_per_arm", "lift"]).iterrows():
            parts.append(f"| {int(r.n_per_arm):,} | {r.lift:+.0%} | {_pct(r.spotify)} | {_pct(r.predicted_spotify)} "
                         f"| {_pct(r.growthbook)} | {_pct(r.fieller)} |")
    if (results_dir / "peeking.csv").exists():
        peek = pd.read_csv(results_dir / "peeking.csv")
        peeking_figure(peek, fig_dir / "peeking.png")
        last = peek[peek["look"] == peek["look"].max()]
        parts += ["", "## Peeking: checking an A/A test every day", "",
                  "![Peeking](figures/peeking.png)", "",
                  "| Method | Ever declared a winner | Interval ever excluded the truth |", "|---|---|---|"]
        for _, r in last.iterrows():
            parts.append(f"| {r.method} | {_pct(r.ever_rejected)} | {_pct(r.ever_excluded_truth)} |")
    out.write_text("\n".join(parts) + "\n")
