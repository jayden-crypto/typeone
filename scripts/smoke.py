import sys

from typeone.audit import run_audit

if __name__ == "__main__":
    df = run_audit(sys.argv[1], sims=int(sys.argv[2]), workers=8)
    print(df[["scenario", "hypothesis", "method", "reject", "coverage", "flag"]].to_string())
