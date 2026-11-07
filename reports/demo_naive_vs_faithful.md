# Parallel-run reconciliation: FAIL

- Run at: 2026-11-06 18:03
- Legacy: `output/python_ecl_loan_level.csv` (5,000 rows)
- New: `output/python_naive_ecl_loan_level.csv` (5,000 rows)
- Loans matching on every column: 38.54%

## 1. Keys

- Only in legacy: 0 []
- Only in new: 0 []
- Duplicate keys: legacy 0, new 0

## 2. Loan-level columns

| column | tolerance | mismatches | max_abs_diff |
|---|---|---|---|
| segment | exact | 0 |  |
| stage | exact | 90 |  |
| pd_source | exact | 0 |  |
| term_months | exact | 2954 |  |
| ead | 0.005 | 179 | 0.01 |
| pd_curr | 1e-08 | 0 | 0 |
| pd_lifetime | 1e-08 | 2954 | 0.0217 |
| pd_used | 1e-08 | 574 | 0.302 |
| lgd | 1e-06 | 0 | 0 |
| ecl | 0.005 | 583 | 5.67e+04 |

## 3. Portfolio totals

| measure | legacy | new | difference |
|---|---|---|---|
| total ead | 1,076,980,974.74 | 1,076,980,972.95 | -1.79 |
| total ecl | 20,084,550.06 | 19,853,973.71 | -230,576.35 |

## 4. Segment x stage summary

| column | tolerance | mismatches | max_abs_diff |
|---|---|---|---|
| n_loans | exact | 8 |  |
| total_ead | 0.01 | 9 | 1.1e+07 |
| total_ecl | 0.01 | 9 | 3.07e+05 |
| coverage | 1e-08 | 8 | 0.00428 |

## Mismatch sample (first 15)

| loan_id | column | legacy | new |
|---|---|---|---|
| L000007 | stage | 2.0 | 1.0 |
| L000016 | stage | 2.0 | 1.0 |
| L000062 | stage | 2.0 | 1.0 |
| L000101 | stage | 2.0 | 1.0 |
| L000148 | stage | 2.0 | 1.0 |
| L000165 | stage | 2.0 | 1.0 |
| L000225 | stage | 2.0 | 1.0 |
| L000281 | stage | 2.0 | 1.0 |
| L000392 | stage | 2.0 | 1.0 |
| L000403 | stage | 2.0 | 1.0 |
| L000415 | stage | 2.0 | 1.0 |
| L000564 | stage | 2.0 | 1.0 |
| L000668 | stage | 2.0 | 1.0 |
| L000683 | stage | 2.0 | 1.0 |
| L000705 | stage | 2.0 | 1.0 |

Full list: `demo_naive_vs_faithful_mismatches.csv`

## Result

FAIL: 7334 loan-level differences; total ead differs by -1.79; total ecl differs by -230,576.35; 34 summary differences
