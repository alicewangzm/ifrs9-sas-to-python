import numpy as np
import pandas as pd

from ifrs9.sas_compat import intck_month, sas_ge, sas_round

RPT = pd.Timestamp("2026-10-31")


def test_intck_counts_month_boundaries_not_elapsed_days():
    ends = pd.Series(pd.to_datetime(["2026-11-01", "2026-11-30", "2026-12-01", "2027-10-31"]))
    assert intck_month(RPT, ends).tolist() == [1, 1, 2, 12]


def test_sas_ge_treats_missing_as_lowest_value():
    a = pd.Series([0.01, 0.01, np.nan, np.nan])
    b = pd.Series([0.02, np.nan, 0.01, np.nan])
    # 0.01>=0.02 F, 0.01>=. T, .>=0.01 F, .>=. T
    assert sas_ge(a, b).tolist() == [False, True, False, True]


def test_sas_round_halves_away_from_zero():
    x = pd.Series([2.5, 3.5, -2.5, 2.675, 0.125])
    assert sas_round(x, 1).tolist() == [3.0, 4.0, -3.0, 3.0, 0.0]
    assert np.allclose(sas_round(x, 0.01), [2.5, 3.5, -2.5, 2.68, 0.13])
