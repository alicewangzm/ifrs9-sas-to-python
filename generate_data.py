"""Generate a synthetic retail/SME loan portfolio for the IFRS 9 ECL migration demo.

All data is fake. A fixed seed makes the file reproducible, so the SAS and
Python runs always read exactly the same input.

Usage:
    python generate_data.py                # 5,000 loans -> data/loans.csv
    python generate_data.py --n 20000
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

REPORTING_DATE = pd.Timestamp("2026-10-31")

# segment: (share, base 12m PD, LGD, CCF, balance range, undrawn range, term months)
SEGMENTS = {
    "MORTGAGE": (0.35, 0.004, 0.15, 0.00, (80_000, 650_000), (0, 0), (120, 300)),
    "AUTO":     (0.25, 0.015, 0.35, 0.00, (5_000, 60_000), (0, 0), (36, 84)),
    "CARD":     (0.25, 0.030, 0.75, 0.60, (0, 15_000), (500, 20_000), (12, 60)),
    "SME":      (0.15, 0.025, 0.45, 0.50, (20_000, 900_000), (0, 250_000), (12, 120)),
}


def generate(n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    names = list(SEGMENTS)
    shares = [SEGMENTS[s][0] for s in names]
    segment = rng.choice(names, size=n, p=shares)

    rows = []
    for i, seg in enumerate(segment, start=1):
        _, base_pd, lgd, ccf, bal_rng, und_rng, term_rng = SEGMENTS[seg]
        term = int(rng.integers(*term_rng))
        age = int(rng.integers(1, term + 6))  # some loans are at or past maturity
        orig = REPORTING_DATE - pd.DateOffset(months=age) + pd.Timedelta(days=int(rng.integers(0, 28)))
        mat = orig + pd.DateOffset(months=term)

        pd_orig = base_pd * rng.lognormal(0, 0.4)
        drift = rng.choice([0.8, 1.0, 1.3, 2.5, 4.0], p=[0.25, 0.40, 0.20, 0.10, 0.05])
        pd_curr = min(pd_orig * drift * rng.lognormal(0, 0.15), 0.95)

        dpd = int(rng.choice([0, rng.integers(1, 30), rng.integers(30, 90), rng.integers(90, 365)],
                             p=[0.86, 0.07, 0.04, 0.03]))

        rows.append({
            "loan_id": f"L{i:06d}",
            "segment": seg,
            "origination_date": orig.date().isoformat(),
            "maturity_date": mat.date().isoformat(),
            "balance": round(float(rng.uniform(*bal_rng)), 2),
            "undrawn_limit": round(float(rng.uniform(*und_rng)), 2),
            "ccf": ccf,
            "pd_orig": round(pd_orig, 6),
            "pd_curr": round(pd_curr, 6),
            "lgd": round(min(max(lgd * rng.lognormal(0, 0.1), 0.05), 0.95), 4),
            "days_past_due": dpd,
        })

    df = pd.DataFrame(rows)
    # Real portfolios have gaps. These two are deliberate: they expose how SAS
    # and Python treat missing values differently (see docs/sas_to_python_guide.md).
    df.loc[rng.random(n) < 0.03, "pd_curr"] = np.nan
    df.loc[rng.random(n) < 0.02, "pd_orig"] = np.nan
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=20261031)
    ap.add_argument("--out", default="data/loans.csv")
    args = ap.parse_args()

    df = generate(args.n, args.seed)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False, lineterminator="\n")  # NaN -> empty field; \n so SAS on Linux reads it cleanly
    print(f"Wrote {len(df):,} loans to {args.out}")
    print(df["segment"].value_counts().to_string())


if __name__ == "__main__":
    main()
