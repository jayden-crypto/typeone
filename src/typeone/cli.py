"""typeone: an independent audit of A/B-testing statistics engines.

    typeone audit  --sims 10000 --workers 8     scenarios x engines grid -> results/
    typeone lifts  --sims 10000                 relative-lift coverage sweep -> results/lift_sweep.csv
    typeone peek   --sims 4000 --looks 20       daily-peeking simulation -> results/peeking.csv
    typeone bias   --sims 6000                  relative-test error direction + sample-size sweep
    typeone report                              results/ -> REPORT.md + figures/
"""

from __future__ import annotations

import argparse
import warnings
from pathlib import Path


def main(argv: list[str] | None = None) -> None:
    warnings.filterwarnings("ignore")
    p = argparse.ArgumentParser(prog="typeone", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--results", default="results")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("audit")
    a.add_argument("--sims", type=int, default=10_000)
    a.add_argument("--workers", type=int, default=8)
    a.add_argument("--seed", type=int, default=2026)
    a.add_argument("--scenarios", nargs="*")
    a.add_argument("--methods", nargs="*", help="only compute these methods and merge into results.csv")
    lifts = sub.add_parser("lifts")
    lifts.add_argument("--sims", type=int, default=10_000)
    lifts.add_argument("--workers", type=int, default=8)
    k = sub.add_parser("peek")
    k.add_argument("--sims", type=int, default=4000)
    k.add_argument("--looks", type=int, default=20)
    k.add_argument("--per-look", type=int, default=250)
    rb = sub.add_parser("bias")
    rb.add_argument("--sims", type=int, default=6000)
    rb.add_argument("--workers", type=int, default=8)
    sub.add_parser("report")
    args = p.parse_args(argv)
    results = Path(args.results)
    results.mkdir(parents=True, exist_ok=True)

    if args.cmd == "audit":
        from .audit import run_audit
        df = run_audit(results, sims=args.sims, workers=args.workers, seed=args.seed,
                       scenarios=args.scenarios, methods=args.methods)
        flagged = df[df["flag"] != ""]
        print(flagged[["scenario", "hypothesis", "method", "reject", "coverage", "flag"]].to_string())
    elif args.cmd == "lifts":
        from .lift_sweep import run_lift_sweep
        run_lift_sweep(sims=args.sims, workers=args.workers).to_csv(results / "lift_sweep.csv", index=False)
    elif args.cmd == "peek":
        from .peeking import run_peeking
        run_peeking(sims=args.sims, looks=args.looks, per_look=args.per_look).to_csv(
            results / "peeking.csv", index=False)
    elif args.cmd == "bias":
        from .relative_bias import run_relative_bias
        run_relative_bias(sims=args.sims, workers=args.workers).to_csv(results / "relative_bias.csv", index=False)
    else:
        from .report import write_report
        write_report(results, Path("REPORT.md"))
        print("wrote REPORT.md")


if __name__ == "__main__":
    main()
