"""Helpers that reproduce SAS behaviour where Python behaves differently.

Each of these was a real source of mismatches in the parallel run.
See docs/sas_to_python_guide.md for the full explanation.
"""
import numpy as np
import pandas as pd


def intck_month(start: pd.Timestamp, end: pd.Series) -> pd.Series:
    """SAS INTCK('month', start, end): number of month boundaries crossed.

    31OCT2026 -> 01NOV2026 is 1 month in SAS even though only one day passed,
    and 01NOV2026 -> 30NOV2026 is 0. Elapsed-days arithmetic gets this wrong.
    """
    end = pd.to_datetime(end)
    return (end.dt.year - start.year) * 12 + (end.dt.month - start.month)


def sas_ge(a: pd.Series, b: pd.Series) -> pd.Series:
    """SAS `a >= b` with missing values.

    SAS treats a missing numeric as smaller than every number, so `x >= .`
    is TRUE and `. >= .` is TRUE. In pandas any comparison with NaN is FALSE.
    """
    a_ = a.fillna(-np.inf)
    b_ = b.fillna(-np.inf)
    return a_ >= b_


def sas_round(x: pd.Series, unit: float = 0.01) -> pd.Series:
    """SAS ROUND(x, unit): halves round away from zero.

    Python's round() and numpy's round() use banker's rounding (2.5 -> 2).
    The small fuzz term mimics SAS, which treats 2.675 (stored as
    2.67499999...) as a true half and rounds it up.
    """
    mult = 1 / unit
    scaled = np.abs(x) * mult
    fuzz = np.maximum(scaled * 1e-12, 1e-9)   # relative, so large balances round the same way
    return np.sign(x) * np.floor(scaled + 0.5 + fuzz) / mult
