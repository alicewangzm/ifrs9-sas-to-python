"""IFRS 9 Expected Credit Loss (simplified) - Python port of sas/ifrs9_ecl.sas.

Each function maps to one step in the SAS program, so a reviewer can read
the two side by side.

Usage:
    python -m ifrs9.ecl                      # faithful port (matches SAS)
    python -m ifrs9.ecl --naive              # "first draft" port with Python defaults,
                                             # to show what the parallel run catches
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from .sas_compat import intck_month, sas_ge, sas_round

REPORTING_DATE = pd.Timestamp("2026-10-31")

SEGMENT_DEFAULT_PD = {"MORTGAGE": 0.004, "AUTO": 0.015, "CARD": 0.030, "SME": 0.025}
OTHER_DEFAULT_PD = 0.050

OUTPUT_COLUMNS = ["loan_id", "segment", "stage", "pd_source", "term_months", "ead",
                  "pd_curr", "pd_lifetime", "pd_used", "lgd", "ecl"]


# Step 1 ---------------------------------------------------------------
def read_loans(path: str) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"loan_id": str, "segment": str},
                       parse_dates=["origination_date", "maturity_date"])


# Step 2 ---------------------------------------------------------------
def fill_current_pd(df: pd.DataFrame) -> pd.DataFrame:
    missing = df["pd_curr"].isna()
    default = df["segment"].map(SEGMENT_DEFAULT_PD).fillna(OTHER_DEFAULT_PD)
    df["pd_curr"] = df["pd_curr"].where(~missing, default)
    df["pd_source"] = np.where(missing, "DEFAULT", "MODEL")
    return df


# Step 3 ---------------------------------------------------------------
def exposure_at_default(df: pd.DataFrame, naive: bool) -> pd.DataFrame:
    raw = df["balance"] + df["ccf"] * df["undrawn_limit"]
    df["ead"] = raw.round(2) if naive else sas_round(raw, 0.01)
    return df


# Step 4 ---------------------------------------------------------------
def remaining_term_and_lifetime_pd(df: pd.DataFrame, naive: bool) -> pd.DataFrame:
    if naive:
        # Looks reasonable, but is not what INTCK does.
        months = (df["maturity_date"] - REPORTING_DATE).dt.days // 30
    else:
        months = intck_month(REPORTING_DATE, df["maturity_date"])
    df["term_months"] = months.clip(lower=1).astype(int)
    df["pd_lifetime"] = 1 - (1 - df["pd_curr"]) ** (df["term_months"] / 12)
    return df


# Step 5 ---------------------------------------------------------------
def assign_stage(df: pd.DataFrame, naive: bool) -> pd.DataFrame:
    doubled = 2 * df["pd_orig"]
    if naive:
        sicr = df["pd_curr"] >= doubled          # NaN comparison -> False
    else:
        sicr = sas_ge(df["pd_curr"], doubled)    # SAS: number >= missing -> True
    dpd = df["days_past_due"]
    df["stage"] = np.select([dpd >= 90, (dpd >= 30) | sicr], [3, 2], default=1)
    return df


# Step 6 ---------------------------------------------------------------
def expected_credit_loss(df: pd.DataFrame, naive: bool) -> pd.DataFrame:
    df["pd_used"] = np.select([df["stage"] == 1, df["stage"] == 2],
                              [df["pd_curr"], df["pd_lifetime"]], default=1.0)
    raw = df["pd_used"] * df["lgd"] * df["ead"]
    df["ecl"] = raw.round(2) if naive else sas_round(raw, 0.01)
    return df


# Step 7 ---------------------------------------------------------------
def summarise(df: pd.DataFrame) -> pd.DataFrame:
    out = (df.groupby(["segment", "stage"], as_index=False)
             .agg(n_loans=("loan_id", "size"),
                  total_ead=("ead", "sum"),
                  total_ecl=("ecl", "sum")))
    out["coverage"] = out["total_ecl"] / out["total_ead"]
    return out.sort_values(["segment", "stage"]).reset_index(drop=True)


def run(loans_path: str, naive: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = read_loans(loans_path)
    df = fill_current_pd(df)
    df = exposure_at_default(df, naive)
    df = remaining_term_and_lifetime_pd(df, naive)
    df = assign_stage(df, naive)
    df = expected_credit_loss(df, naive)
    loan_level = df[OUTPUT_COLUMNS]
    return loan_level, summarise(loan_level)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--loans", default="data/loans.csv")
    ap.add_argument("--outdir", default="output")
    ap.add_argument("--naive", action="store_true",
                    help="use plain Python semantics instead of SAS-compatible ones")
    args = ap.parse_args()

    loan_level, summary = run(args.loans, args.naive)
    prefix = "python_naive" if args.naive else "python"
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    loan_level.to_csv(out / f"{prefix}_ecl_loan_level.csv", index=False)
    summary.to_csv(out / f"{prefix}_ecl_summary.csv", index=False)

    print(f"Loans: {len(loan_level):,}   Total ECL: {loan_level['ecl'].sum():,.2f}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
