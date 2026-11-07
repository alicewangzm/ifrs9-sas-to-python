# Parallel-run reconciliation: PASS

- Run at: 2026-11-07 10:19
- Legacy: `output/sas_ecl_loan_level.csv` (5,000 rows)
- New: `output/python_ecl_loan_level.csv` (5,000 rows)
- Loans matching on every column: 100.00%

## 1. Keys

- Only in legacy: 0 []
- Only in new: 0 []
- Duplicate keys: legacy 0, new 0

## 2. Loan-level columns

| column | tolerance | mismatches | max_abs_diff |
|---|---|---|---|
| segment | exact | 0 |  |
| stage | exact | 0 |  |
| pd_source | exact | 0 |  |
| term_months | exact | 0 |  |
| ead | 0.005 | 0 | 0 |
| pd_curr | 1e-08 | 0 | 0 |
| pd_lifetime | 1e-08 | 0 | 5e-11 |
| pd_used | 1e-08 | 0 | 4.99e-11 |
| lgd | 1e-06 | 0 | 0 |
| ecl | 0.005 | 0 | 0 |

## 3. Portfolio totals

| measure | legacy | new | difference |
|---|---|---|---|
| total ead | 1,076,980,974.74 | 1,076,980,974.74 | 0.00 |
| total ecl | 20,084,550.06 | 20,084,550.06 | 0.00 |

## 4. Segment x stage summary

| column | tolerance | mismatches | max_abs_diff |
|---|---|---|---|
| n_loans | exact | 0 |  |
| total_ead | 0.01 | 0 | 0 |
| total_ecl | 0.01 | 0 | 0 |
| coverage | 1e-08 | 0 | 4.9e-09 |

## Result

PASS: outputs are functionally identical within tolerance.
