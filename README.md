# IFRS 9 ECL: SAS-to-Python migration with parallel-run validation

A toy version of a real bank migration. A legacy SAS program calculates IFRS 9
Expected Credit Loss on a loan book. This repo ports it to Python, then proves the
two produce the same numbers, loan by loan.

All data is synthetic. The IFRS 9 logic is deliberately simplified (no discounting,
no macroeconomic scenarios). The point is the migration process, not the model.

## What's here

| Path                  | What it does                                                                                             |
| --------------------- | -------------------------------------------------------------------------------------------------------- |
| `generate_data.py`    | Builds a fake 5,000-loan portfolio (mortgage, auto, card, SME), with gaps in the PD data like a real one |
| `sas/ifrs9_ecl.sas`   | The "legacy" program: DATA step + PROC SQL                                                               |
| `ifrs9/ecl.py`        | Python port, one function per SAS step                                                                   |
| `ifrs9/sas_compat.py` | Helpers that reproduce SAS behaviour (missing values, INTCK, ROUND)                                      |
| `validate.py`         | Parallel-run harness: keys, every column, totals, summary; writes a reconciliation report                |
| `tests/`              | pytest unit tests for the staging rules and SAS-compatibility helpers                                    |
| `docs/`               | Data dictionary, data lineage, and a SAS-to-Python handover guide                                        |

## Pipeline

1. **Fill PD gaps**: missing current PD gets a segment default and a `DEFAULT` flag
2. **EAD** = balance + CCF × undrawn limit
3. **Remaining term** (SAS `INTCK`) and **lifetime PD**
4. **Stage**: 3 if 90+ days past due; 2 if 30+ DPD or PD has doubled since origination; else 1
5. **ECL** = PD × LGD × EAD (12-month PD for Stage 1, lifetime for Stage 2, 1 for Stage 3)
6. **Summary** by segment and stage, with coverage ratio

## What the parallel run caught

A first-draft port with ordinary Python defaults (`--naive`) matched SAS on only
**~39% of loans** and was off by **$230K in total ECL**. Three causes:

- **Missing values**: SAS treats `x >= .` as true, pandas treats `x >= NaN` as false. 90 loans changed stage.
- **INTCK**: counts month boundaries, not elapsed days. Remaining term was wrong on ~59% of loans.
- **Rounding**: SAS rounds halves away from zero; Python uses banker's rounding. 179 EADs off by a cent.

After fixing these in `sas_compat.py`, the port matches SAS on every column within tolerance.
Details: `docs/sas_to_python_guide.md`.

## Run it

```bash
pip install -r requirements.txt
python -m pytest -q                     # unit tests
python generate_data.py                 # data/loans.csv (already included)
python -m ifrs9.ecl                     # Python run  -> output/python_ecl_*.csv
python -m ifrs9.ecl --naive             # first-draft port, for comparison
```

### SAS run (SAS OnDemand for Academics, free)

1. Sign in at https://welcome.oda.sas.com and open **SAS Studio**.
2. Under **Server Files and Folders > Files (Home)**, create a folder `ifrs9`.
3. Upload `data/loans.csv` and `sas/ifrs9_ecl.sas` into it.
4. Open `ifrs9_ecl.sas` and press **Run** (F3).
5. Check the **Log** tab: no `ERROR` lines. One `NOTE: Missing values were generated` is
   expected (that's the missing `pd_orig` case).
6. Download `sas_ecl_loan_level.csv` and `sas_ecl_summary.csv` into `output/`.

### Parallel-run validation

```bash
python validate.py \
  --legacy output/sas_ecl_loan_level.csv  --new output/python_ecl_loan_level.csv \
  --legacy-summary output/sas_ecl_summary.csv --new-summary output/python_ecl_summary.csv
```

Writes `reports/reconciliation.md` (and `reconciliation_mismatches.csv` if anything differs).
Exit code 0 = PASS, 1 = FAIL.

To see the harness catch the naive port:

```bash
python validate.py \
  --legacy output/python_ecl_loan_level.csv --new output/python_naive_ecl_loan_level.csv \
  --legacy-summary output/python_ecl_summary.csv --new-summary output/python_naive_ecl_summary.csv \
  --name demo_naive_vs_faithful
```

## Results

| Run               | Loans | Total ECL     | Match vs SAS |
| ----------------- | ----- | ------------- | ------------ |
| SAS (legacy)      | 5,000 | 20,084,550.06 | —            |
| Python (faithful) | 5,000 | 20,084,550.06 | 100%         |
| Python (naive)    | 5,000 | 19,853,973.71 | 38.54%       |
