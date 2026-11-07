import numpy as np
import pandas as pd
import pytest

from ifrs9.ecl import run


@pytest.fixture
def loans_csv(tmp_path):
    rows = [
        # id,  seg,       orig,        maturity,    bal,    undrawn, ccf, pd_orig, pd_curr, lgd,  dpd
        ("A1", "MORTGAGE", "2020-01-15", "2036-01-15", 200000, 0, 0.0, 0.004, 0.004, 0.15, 0),
        ("A2", "CARD", "2024-05-01", "2028-05-01", 5000, 10000, 0.6, 0.02, 0.05, 0.75, 0),
        ("A3", "AUTO", "2023-01-01", "2029-01-01", 20000, 0, 0.0, 0.01, 0.012, 0.35, 45),
        ("A4", "SME", "2022-06-01", "2027-06-01", 100000, 50000, 0.5, 0.02, 0.03, 0.45, 120),
        ("A5", "AUTO", "2023-01-01", "2029-01-01", 20000, 0, 0.0, None, 0.012, 0.35, 0),
        ("A6", "CARD", "2024-05-01", "2028-05-01", 1000, 0, 0.6, 0.03, None, 0.75, 0),
    ]
    cols = ["loan_id", "segment", "origination_date", "maturity_date", "balance",
            "undrawn_limit", "ccf", "pd_orig", "pd_curr", "lgd", "days_past_due"]
    p = tmp_path / "loans.csv"
    pd.DataFrame(rows, columns=cols).to_csv(p, index=False)
    return str(p)


def by_id(df):
    return df.set_index("loan_id")


def test_staging_rules(loans_csv):
    out = by_id(run(loans_csv)[0])
    assert out.loc["A1", "stage"] == 1  # performing, no PD change
    assert out.loc["A2", "stage"] == 2  # PD more than doubled (SICR)
    assert out.loc["A3", "stage"] == 2  # 30+ days past due
    assert out.loc["A4", "stage"] == 3  # 90+ days past due


def test_missing_origination_pd_follows_sas_rule(loans_csv):
    faithful = by_id(run(loans_csv)[0])
    naive = by_id(run(loans_csv, naive=True)[0])
    assert faithful.loc["A5", "stage"] == 2  # SAS: 0.012 >= . is TRUE
    assert naive.loc["A5", "stage"] == 1     # pandas: comparison with NaN is FALSE


def test_missing_current_pd_uses_segment_default(loans_csv):
    out = by_id(run(loans_csv)[0])
    assert out.loc["A6", "pd_curr"] == 0.030
    assert out.loc["A6", "pd_source"] == "DEFAULT"


def test_ead_and_ecl(loans_csv):
    out = by_id(run(loans_csv)[0])
    assert out.loc["A2", "ead"] == pytest.approx(11000.00)          # 5000 + 0.6 * 10000
    assert out.loc["A4", "ecl"] == pytest.approx(0.45 * 125000.00)  # Stage 3: PD = 1
    assert out.loc["A1", "ecl"] == pytest.approx(round(0.004 * 0.15 * 200000, 2))


def test_lifetime_pd_used_for_stage_2(loans_csv):
    out = by_id(run(loans_csv)[0])
    row = out.loc["A2"]
    expected = 1 - (1 - 0.05) ** (row["term_months"] / 12)
    assert row["pd_used"] == pytest.approx(expected)


def test_summary_ties_to_loan_level(loans_csv):
    loan_level, summary = run(loans_csv)
    assert summary["total_ecl"].sum() == pytest.approx(loan_level["ecl"].sum())
    assert summary["n_loans"].sum() == len(loan_level)
    assert np.all(summary["coverage"] <= 1)
