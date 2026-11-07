# Data dictionary

Reporting date: 2026-10-31. All data is synthetic.

## Input: `data/loans.csv`

| Field | Type | Description | Rules / notes |
|---|---|---|---|
| loan_id | text(10) | Unique loan identifier | Primary key, format `L000001` |
| segment | text(10) | Product segment | MORTGAGE, AUTO, CARD, SME |
| origination_date | date | Date the loan was booked | ISO `YYYY-MM-DD` |
| maturity_date | date | Contractual maturity | Can be on or before the reporting date |
| balance | number(2dp) | Drawn balance | ≥ 0 |
| undrawn_limit | number(2dp) | Committed but undrawn amount | 0 for MORTGAGE and AUTO |
| ccf | number | Credit conversion factor applied to undrawn | 0 to 1 |
| pd_orig | number | 12-month PD at origination | **~2% missing** |
| pd_curr | number | Current 12-month PD from the model | **~3% missing** |
| lgd | number | Loss given default | 0.05 to 0.95 |
| days_past_due | integer | Days past due at reporting date | ≥ 0 |

## Output: `*_ecl_loan_level.csv`

| Field | Type | Derivation | Source step |
|---|---|---|---|
| loan_id | text | From input | 1 |
| segment | text | From input | 1 |
| pd_source | text | `MODEL` if pd_curr was present, else `DEFAULT` | 2 |
| pd_curr | number | Input pd_curr, or segment default if missing (MORTGAGE 0.004, AUTO 0.015, CARD 0.030, SME 0.025, other 0.050) | 2 |
| ead | number(2dp) | ROUND(balance + ccf × undrawn_limit, 0.01) | 3 |
| term_months | integer | INTCK('month', reporting date, maturity_date), floored at 1 | 4 |
| pd_lifetime | number | 1 − (1 − pd_curr)^(term_months / 12) | 4 |
| stage | integer | 3 if DPD ≥ 90; 2 if DPD ≥ 30 or pd_curr ≥ 2 × pd_orig (SAS missing-value rules); else 1 | 5 |
| pd_used | number | Stage 1: pd_curr; Stage 2: pd_lifetime; Stage 3: 1 | 6 |
| lgd | number | From input | 1 |
| ecl | number(2dp) | ROUND(pd_used × lgd × ead, 0.01) | 6 |

## Output: `*_ecl_summary.csv`

| Field | Type | Derivation |
|---|---|---|
| segment, stage | key | Group-by keys |
| n_loans | integer | Count of loans |
| total_ead | number | Sum of ead |
| total_ecl | number | Sum of ecl |
| coverage | number | total_ecl / total_ead |
