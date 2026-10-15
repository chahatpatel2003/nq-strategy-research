# SEARCH_BUDGET_COMPLETION.md

Completion record required by `SEARCH_BUDGET.md` §5.

`SEARCH_BUDGET.md` itself is hashed into `STATE_DISCOVERY_SPEC_FROZEN.md` and is
therefore immutable after the freeze; the completion figure is recorded here and
in `STATE_DISCOVERY_SPEC.md` §16, which is inside the frozen manifest.

# TOTAL CONFIGURATIONS EVALUATED: 18

of a preregistered ceiling of **18**.

| dimension | permitted | used |
|---|---:|---:|
| base features | ≤ 60 | 55 |
| return / velocity horizons | 6 | 6 |
| hand-built interactions | 0 | 0 |
| decision clocks | 1 | 1 |
| R definitions | 1 | 1 |
| holding horizons | 1 | 1 |
| execution models | 1 | 1 |
| model families | 2 | 2 |
| hyperparameter combinations | ≤ 6 | 6 |
| confidence thresholds | 3 | 3 |
| **configurations scored against an outcome** | **≤ 18** | **18** |
| production candidates frozen | exactly 1 | 1 |
| fresh-validation runs | exactly 1 | **0 — not spent** |

Every configuration was scored against **2022 only**, on the single criterion in
`SEARCH_BUDGET.md` §4. No configuration outside the enumerated 18 ever had an
outcome computed against it, on any split. `enumerate_configs()` raises
`BudgetViolation` if the count is anything other than 18, `build_estimator()`
raises for any family outside the two preregistered ones, and
`scripts/p4_09_integrity.py` re-checks all of it.

The budget was **not** reopened after the 18 failed. Post-hoc observations went
to `FUTURE_HYPOTHESES.md` marked **POST-HOC — REQUIRES NEW UNTOUCHED DATA**.

## Additional systematic scans run as diagnostics

None. `SEARCH_BUDGET.md` §3 anticipated a symbolic-sequence enumeration as a
possible extra diagnostic requiring Benjamini–Hochberg adjustment; it was not
run, so no FDR correction is owed.
