# SAS to Python: a guide for the team

A short handover guide for analysts who know SAS and will maintain the Python version.

## 1. Quick translation table

| SAS | pandas |
|---|---|
| `data out; set in; ... run;` | `df = df.copy()` then column operations |
| `if x then y = 1; else y = 0;` | `df["y"] = np.where(df["x"], 1, 0)` |
| `select (seg); when ('A') ...` | `df["seg"].map({...})` or `np.select(...)` |
| `missing(x)` | `df["x"].isna()` |
| `keep a b c;` | `df[["a", "b", "c"]]` |
| `proc sql; ... group by` | `df.groupby([...]).agg(...)` |
| `calculated total_ecl` | compute after `agg`, as a new column |
| `proc sort; by k;` | `df.sort_values("k")` |
| `first.k / last.k` | `df.groupby("k").head(1)` / `.tail(1)` |
| `retain` | `cumsum()`, `cummax()`, or `groupby().shift()` |
| `intck('month', a, b)` | `ifrs9.sas_compat.intck_month` (not days / 30) |
| `round(x, 0.01)` | `ifrs9.sas_compat.sas_round` (not `round()`) |

## 2. The traps we hit in the parallel run

A first-draft port (`python -m ifrs9.ecl --naive`) matched SAS on only **~39% of loans**.
Every difference traced back to one of these:

### Missing values compare differently
In SAS a missing number is lower than any number, so `0.012 >= .` is **true**.
In pandas any comparison with `NaN` is **false**.
Our staging rule `pd_curr >= 2 * pd_orig` therefore put loans with a missing
`pd_orig` in **Stage 2 in SAS** and **Stage 1 in Python**: 90 loans moved stage
and their ECL changed.
Fix: `sas_ge()`. Then raise it with the model owners, because the SAS behaviour
is accidental, not a policy decision. Changing it is a business decision, not a
migration one.

### INTCK counts boundaries, not time
`intck('month', '31OCT2026'd, '01NOV2026'd)` is 1. Days/30 gives 0.
This changed `term_months` on ~59% of loans, which changed lifetime PD for every
Stage 2 loan.

### Rounding
SAS `ROUND` rounds halves away from zero. Python's `round()` and numpy use
banker's rounding (`2.5 -> 2`). With a CCF of 0.5 or 0.6, half-cent EADs are
common: 179 loans were off by one cent.

### Reading SAS exports
PROC EXPORT can write `.` for missing values, pad numbers with spaces, and
apply display formats that cut decimals. `validate.py` reads everything as text
first and cleans it before comparing. Use explicit formats (e.g. `12.10`) on
any number you need to compare precisely.

### Line endings
SAS on Linux reading a Windows CSV gets `\r` on the last field, which turns it
missing. Write CSVs with `\n` or use `termstr=crlf`.

## 3. How to change the model safely

1. Change the SAS and Python versions together while both are running.
2. Add a test in `tests/` for the new rule.
3. Re-run `validate.py`. Nothing ships until it says PASS.
4. Update `docs/data_dictionary.md` and `docs/lineage.md`.
