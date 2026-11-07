# Data lineage

```mermaid
flowchart LR
    G[generate_data.py<br/>seed 20261031] --> L[(data/loans.csv)]

    L --> S1[SAS: DATA step<br/>read + fill PD + EAD<br/>+ INTCK term + stage + ECL]
    S1 --> S2[SAS: PROC SQL<br/>segment x stage summary]
    S1 --> SO1[(sas_ecl_loan_level.csv)]
    S2 --> SO2[(sas_ecl_summary.csv)]

    L --> P1[Python: ifrs9/ecl.py<br/>same 7 steps, SAS-compatible helpers]
    P1 --> PO1[(python_ecl_loan_level.csv)]
    P1 --> PO2[(python_ecl_summary.csv)]

    SO1 --> V{validate.py<br/>parallel run}
    PO1 --> V
    SO2 --> V
    PO2 --> V
    V --> R[(reports/reconciliation.md<br/>+ mismatches.csv)]
```

## Field-level lineage

| Output field | Input fields | Transformation |
|---|---|---|
| pd_curr | pd_curr, segment | Fill missing with segment default |
| pd_source | pd_curr | Flag MODEL / DEFAULT |
| ead | balance, ccf, undrawn_limit | balance + ccf × undrawn, rounded to cents |
| term_months | maturity_date | Month boundaries from reporting date, min 1 |
| pd_lifetime | pd_curr, term_months | 1 − (1 − PD)^(years) |
| stage | days_past_due, pd_curr, pd_orig | DPD backstops + SICR (PD doubled) |
| pd_used | stage, pd_curr, pd_lifetime | Stage-dependent PD |
| ecl | pd_used, lgd, ead | PD × LGD × EAD, rounded to cents |

Step numbers match the comments in `sas/ifrs9_ecl.sas` and the functions in `ifrs9/ecl.py`.
