"""Parallel-run validation: compare legacy (SAS) output with new (Python) output.

Checks
  1. Row counts and loan IDs (missing / extra / duplicate keys)
  2. Every column, loan by loan: exact match for categories and integers,
     tolerance match for amounts and probabilities
  3. Portfolio totals and the segment x stage summary

Writes a markdown reconciliation report and a CSV of every mismatch.
Exit code 0 = PASS, 1 = FAIL, so it can run in CI.

Usage:
    python validate.py --legacy output/sas_ecl_loan_level.csv \
                       --new    output/python_ecl_loan_level.csv \
                       --legacy-summary output/sas_ecl_summary.csv \
                       --new-summary    output/python_ecl_summary.csv
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

KEY = "loan_id"

# column -> tolerance (None = must match exactly)
LOAN_CHECKS = {
    "segment": None,
    "stage": None,
    "pd_source": None,
    "term_months": None,
    "ead": 0.005,          # half a cent
    "pd_curr": 1e-8,
    "pd_lifetime": 1e-8,
    "pd_used": 1e-8,
    "lgd": 1e-6,
    "ecl": 0.005,
}
SUMMARY_KEYS = ["segment", "stage"]
SUMMARY_CHECKS = {"n_loans": None, "total_ead": 0.01, "total_ecl": 0.01, "coverage": 1e-8}
TEXT_COLS = {"loan_id", "segment", "pd_source"}


def load(path: str) -> pd.DataFrame:
    """Read everything as text first so SAS formatting quirks don't break parsing:
    upper/lower-case headers, padded values, '.' for missing numbers."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df.columns = [c.strip().lower() for c in df.columns]
    for c in df.columns:
        df[c] = df[c].str.strip()
        if c not in TEXT_COLS:
            df[c] = pd.to_numeric(df[c].replace({".": None, "": None}), errors="coerce")
    return df


def compare(legacy: pd.DataFrame, new: pd.DataFrame, keys: list[str],
            checks: dict) -> tuple[pd.DataFrame, list[dict]]:
    merged = legacy.merge(new, on=keys, how="inner", suffixes=("_legacy", "_new"))
    mismatches, stats = [], []
    for col, tol in checks.items():
        a, b = merged[f"{col}_legacy"], merged[f"{col}_new"]
        both_missing = a.isna() & b.isna()
        if tol is None:
            bad = ~((a == b) | both_missing)
            max_diff = ""
        else:
            diff = (a.astype(float) - b.astype(float)).abs()
            bad = ~((diff <= tol) | both_missing)
            max_diff = f"{diff.max():.3g}" if len(diff) else "0"
        stats.append({"column": col, "tolerance": "exact" if tol is None else tol,
                      "mismatches": int(bad.sum()), "max_abs_diff": max_diff})
        for _, row in merged[bad].iterrows():
            mismatches.append({**{k: row[k] for k in keys}, "column": col,
                               "legacy": row[f"{col}_legacy"], "new": row[f"{col}_new"]})
    return pd.DataFrame(mismatches), stats


def table(rows: list[dict]) -> str:
    if not rows:
        return "_none_\n"
    cols = list(rows[0])
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(r[c]) for c in cols) + " |" for r in rows]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--legacy", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--legacy-summary")
    ap.add_argument("--new-summary")
    ap.add_argument("--outdir", default="reports")
    ap.add_argument("--name", default="reconciliation")
    args = ap.parse_args()

    legacy, new = load(args.legacy), load(args.new)
    failures = []

    # 1. Keys
    dup_l = legacy[KEY][legacy[KEY].duplicated()].tolist()
    dup_n = new[KEY][new[KEY].duplicated()].tolist()
    only_l = sorted(set(legacy[KEY]) - set(new[KEY]))
    only_n = sorted(set(new[KEY]) - set(legacy[KEY]))
    if dup_l or dup_n or only_l or only_n:
        failures.append("key mismatch")

    # 2. Loan-level columns
    loan_mm, loan_stats = compare(legacy, new, [KEY], LOAN_CHECKS)
    if len(loan_mm):
        failures.append(f"{len(loan_mm)} loan-level differences")

    # 3. Totals and summary
    totals = []
    for col in ["ead", "ecl"]:
        tl, tn = legacy[col].sum(), new[col].sum()
        totals.append({"measure": f"total {col}", "legacy": f"{tl:,.2f}",
                       "new": f"{tn:,.2f}", "difference": f"{tn - tl:,.2f}"})
        if abs(tn - tl) > 0.01:
            failures.append(f"total {col} differs by {tn - tl:,.2f}")

    sum_stats, sum_mm = [], pd.DataFrame()
    if args.legacy_summary and args.new_summary:
        sum_mm, sum_stats = compare(load(args.legacy_summary), load(args.new_summary),
                                    SUMMARY_KEYS, SUMMARY_CHECKS)
        if len(sum_mm):
            failures.append(f"{len(sum_mm)} summary differences")

    status = "PASS" if not failures else "FAIL"
    matched = len(set(legacy[KEY]) & set(new[KEY]))
    bad_loans = loan_mm[KEY].nunique() if len(loan_mm) else 0
    match_rate = (matched - bad_loans) / max(len(legacy), 1)

    # Report
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    if len(loan_mm):
        loan_mm.to_csv(out / f"{args.name}_mismatches.csv", index=False)

    by_col = []
    if len(loan_mm):
        by_col = (loan_mm.groupby("column").size().rename("loans").reset_index()
                  .to_dict("records"))

    report = [
        f"# Parallel-run reconciliation: {status}\n",
        f"- Run at: {datetime.now():%Y-%m-%d %H:%M}",
        f"- Legacy: `{args.legacy}` ({len(legacy):,} rows)",
        f"- New: `{args.new}` ({len(new):,} rows)",
        f"- Loans matching on every column: {match_rate:.2%}\n",
        "## 1. Keys\n",
        f"- Only in legacy: {len(only_l)} {only_l[:10]}",
        f"- Only in new: {len(only_n)} {only_n[:10]}",
        f"- Duplicate keys: legacy {len(dup_l)}, new {len(dup_n)}\n",
        "## 2. Loan-level columns\n",
        table(loan_stats),
        "## 3. Portfolio totals\n",
        table(totals),
    ]
    if sum_stats:
        report += ["## 4. Segment x stage summary\n", table(sum_stats)]
    if len(loan_mm):
        report += ["## Mismatch sample (first 15)\n",
                   table(loan_mm.head(15).to_dict("records")),
                   f"Full list: `{args.name}_mismatches.csv`\n"]
    if failures:
        report += ["## Result\n", "FAIL: " + "; ".join(failures) + "\n"]
    else:
        report += ["## Result\n", "PASS: outputs are functionally identical within tolerance.\n"]
    (out / f"{args.name}.md").write_text("\n".join(report))

    print(f"{status}  match rate {match_rate:.2%}  ({len(loan_mm)} differences)")
    for r in by_col:
        print(f"  {r['column']}: {r['loans']} loans differ")
    print(f"Report: {out / (args.name + '.md')}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
