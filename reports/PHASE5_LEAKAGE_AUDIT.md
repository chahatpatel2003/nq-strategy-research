# PHASE5_LEAKAGE_AUDIT.md

Phase 5 produced **no frozen candidate**: the selected configuration failed the
preregistered Gate F on 2023 and was rejected, so 2026-Q1 was never opened. This
audit therefore covers the development work that was done, and confirms that the
seals it did not spend are intact.

Test names refer to `tests/test_p5_holdout.py`, `tests/test_p5_labels.py` and the
inherited `tests/test_p4_features.py`.

---

### 1. Features are causal

Phase 5 **adds no feature code**. The 55-feature state is imported read-only from
the frozen `nqr.p4.features4`
(sha256 `636af03cc537fb992003113dd5602cf6ee21a1b21cb52e630344df574d8dc216`,
inside the Phase-4 manifest and re-verified by `p5_09_integrity.py`).
`test_phase5_adds_no_feature_code` asserts no Phase-5 module defines a feature
list of its own.

The Phase-4 master causality test still runs in this suite:
`test_features_are_invariant_to_truncating_the_future` rebuilds the whole state
vector from a tape physically cut off at the decision timestamp and requires all
55 values to be bit-identical, at 10:15, 11:00 and 11:29:55 on a real session.

### 2. No future bars or extrema

Every aggregate is `_roll_sum` / `_roll_max` / `_roll_min` / `_shift(k>0)` or a
cumulative sum — all one-sided and closed at the decision index. There is no
centred, symmetric or two-sided window anywhere.
*Covered by* `test_trailing_extremes_never_see_the_future`,
`test_rolling_windows_are_trailing_and_closed`.

### 3. No incomplete-bar leakage

The volatility unit is ATR14 of **completed** 1-minute bars: the value published
for minute *m* uses minutes *m−14 … m−1*.
`test_atr_uses_only_completed_minutes` rewrites the current minute's high and low
by ±500 points and asserts the ATR published inside that minute does not move.
Because R is derived from that same ATR, **R itself cannot see its own minute**.
*Also covered by* `test_r_is_volatility_normalised_and_railed`.

### 4. Scaling is training-only

Winsorisation bounds (0.1 % / 99.9 %) and standardisation constants are fitted on
the **2021 partition alone** — 30,360 rows — and never refitted. The fitted object
records `fit_on = "train2021"`, and `scripts/p5_03_run_split.py` asserts
`pre.fit_on == "train2021"` before scoring any split.

The **control baseline** is the same story and matters more here than in Phase 4,
because Phase 5 thresholds on edge-over-control rather than on a raw score.
`b_long[k]` and `b_short[k]` are per-30-minute-bucket base rates estimated on
2021 rows only; `τ` is a 2021 quantile of the resulting edge score, frozen as a
number and applied unchanged to 2022, 2023, 2024 and 2025-H2. No control
information from any later period enters either.
*Covered by* `test_baseline_is_estimated_per_bucket_from_training_rows_only`,
`test_threshold_is_a_training_quantile_then_a_fixed_number`,
`test_scaler_is_fitted_only_on_training_rows` (inherited).

A consequence worth stating rather than hiding: because `b` is fitted on 2021 —
a strong up year — the 2021 long base rate at `r4p0` is 0.5161 and reaches 0.5404
in the 11:00–11:30 bucket. That imports 2021's directional drift into where and
in which direction the strategy fires in later years. It is leak-free, but it is
a fragility, and it is recorded as H5-4 in `FUTURE_HYPOTHESES.md`.

### 5. Configuration selection used only allowed development data

`scripts/p5_02_develop.py` loads the dev split and asserts
`set(years) == {2021, 2022, 2023}` and that every boundary date maps to
`DISCOVERY_TRAIN` / `SELECTION` / `INTERNAL_TEST`. All 18 configurations were
scored against **2022 only**, on the single criterion in
`PHASE5_SEARCH_BUDGET.md` §5. 2023, 2024, 2025-H2 and 2026 took no part.

### 6. 2023 remained internal OOS

2023 was scored once, by `p5_03_run_split.py`, **after**
`production_model.pkl` already existed on disk from the 2022 selection step. It
could not and did not change the choice — it rejected it. Nothing was re-tuned
afterwards; the candidate was abandoned, not adjusted.

### 7. 2024 marked contaminated

`holdout5.period_of` returns `CONTAM_2024`, `CONTAMINATED` contains it, the build
script and runner both print `*** CONTAMINATED DIAGNOSTIC - NOT VALIDATION ***`,
`results.json` carries `is_contaminated: true`, and the report is titled
**CONTAMINATED DIAGNOSTIC — NOT VALIDATION**. It ran after the candidate had
already been rejected and changed nothing.

### 8. 2025-H2 marked contaminated

Identical treatment (`CONTAM_2025H2`). Consumed as Phase-3 fresh validation, run
after the rejection, changed nothing.

### 9. 2025-H1 never opened

Never opened by any phase. The Phase-5 guard refuses every date in
2025-01-01 … 2025-06-30 **and keeps refusing with the 2026-Q1 unlock active** —
the unlock is scoped to Q1 and nothing else. `assert_path_allowed` refuses any
path containing `2025_H1` unconditionally, and `assert_range_allowed` refuses any
range spanning the window. There is exactly one unlock function in the module and
it is named for 2026-Q1.

The 2025-H2 diagnostic reads `2025_H2.parquet` only; the tick cache it draws on
contains months 2025-07 … 2025-12 and nothing earlier.

*Covered by* `test_2025_h1_is_hard_blocked`,
`test_2025_h1_stays_blocked_even_with_the_validation_unlock`,
`test_exactly_one_unlock_function_exists_and_it_is_named_for_q1`,
`test_range_spanning_a_sealed_window_is_refused`, and `p5_09_integrity.py`.

### 10. 2026-Q1 untouched

**No Phase-5 code ever read a single 2026 row.** `p5_09_integrity.py` confirms
there is no 2026 month in any tick cache, no `split=val2026q1` feature directory,
no `run_val2026q1` result directory, and no `front_map_p5val.parquet` — the front
map that a validation build would have had to create first.

The only contact any phase has ever had with `2026_H1.parquet` is the Phase-4
**parquet-footer** read (row count, row-group count, first/last row-group
timestamps). No row has ever been decoded.

### 11. April 2026 onward never read

`assert_date_allowed` refuses every date ≥ 2026-04-01 with or without the unlock;
`assert_range_allowed` refuses any range reaching it; `assert_path_allowed`
refuses `2026_H2` and, new in Phase 5, **any raw `.dbn` / `.dbn.zst` archive** —
the drive's `NQ_HOLDOUT/GLBX-…` directory begins 2026-06-17 and is now
unreachable by construction.

This matters because **`2026_H1.parquet` physically contains April, May and June
2026** (47,081,888 rows to 2026-06-17). `sql_window_guard` is the only sanctioned
way to read it and it **raises before emitting any predicate** for a window
reaching 2026-04-01 — the guard fires at query-construction time, not after a
scan. `test_sql_guard_on_2026_fires_before_emitting_any_predicate` asserts exactly
that, including for the boundary window 2026-01-01 … 2026-04-01.

### 12. Strategy and controls use identical execution

Strategy trades, matched-random controls and opposite-direction controls all read
the **same** tick-resolved labels from the same dataset rows: same 250 ms latency,
same first-print-after entry, same ±1R bracket off the realised fill, same
touch-then-market stop, same trade-through-by-a-tick target, same 60-minute
horizon, same executable timeout, same friction grid. There is no second
execution model in Phase 5.
*Covered by* `test_matched_controls_share_day_bucket_direction_and_R`,
`test_opposite_direction_control_flips_only_the_sign`.

Controls are deliberately **not** subject to the one-position or cooldown rules —
they are independent hypothetical entries — and that is stated wherever they are
compared.

### 13. No post-hoc subgroup became the strategy

The candidate was fixed by the preregistered process and then rejected. The
time-of-day, volatility, PDH/PDL, session-open, velocity, efficiency, intensity,
delta and weekday tables in `TIME_AND_STATE_DIAGNOSTICS.md` were computed
**after** that rejection, on the unconditional decision population, and 46 cells
are examined. Every one is labelled **POST-HOC — REQUIRES NEW UNTOUCHED DATA**
and carried to `FUTURE_HYPOTHESES.md`. None of them was added to a model,
threshold, session or filter.

### 14. Search budget respected

18 configurations enumerated, 18 evaluated, 18 recorded — 3 R scales × 2 model
families × 3 selectivity levels. `enumerate_configs()` raises `BudgetViolation`
for any other count and `build_estimator` raises for any family outside the two
preregistered ones. The budget was **not** reopened after the candidate failed:
no fourth R scale, no extra threshold, no third family, no feature added.
*Covered by* `test_budget_is_exactly_18_and_cannot_grow`,
`test_only_the_two_preregistered_families_exist`, and `p5_09_integrity.py`.

### 15. Overlap and horizon bounds, measured

Adjacent 60-second rows can share up to 60 minutes of future tape, so every
interval in Phase 5 is a **day-block bootstrap** (10 000 resamples of whole
trading days, strategy and control resampled together), and performance is
measured on the non-overlapping executed trades produced by the one-position
rule plus the cooldown.

Measured across all 137,400 decision rows:

| split | rows with an entry | entry latency min | max hold | labels crossing the day |
|---|---:|---:|---:|---:|
| dev 2021–2023 | 91,200 | 250.0 ms | 60.5 min | **0** |
| 2024 | 30,600 | 250.0 ms | 60.2 min | **0** |
| 2025-H2 | 15,360 | 250.0 ms | 60.7 min | **0** |

Latency is never below the 250 ms model. Holds exceed 60 minutes by up to 42
seconds **by design** — the timeout waits for the first executable print at or
after the cutoff (§5 of `LABELS.md`) — and never beyond the 60 s wait rail.
No label crosses a trading day, so whole-year splits need no purge or embargo.

---

## Residual weaknesses, stated rather than hidden

1. **The winner was the smallest sample.** Ranking 18 configurations on
   expectancy alone systematically favours the noisiest cell. The selected
   configuration had 128 trades from 30,480 rows and its Gate-E advantage
   (+0.058 R) had a CI of [−0.027, +0.148] — it passed on a point estimate with
   no statistical support. The gate as written did not require the CI to exclude
   zero. **That is a defect in the preregistration, not in the execution**, and
   the fix belongs to the next phase's gates, not to this one's results.
2. **Sample sizes throughout are small** — 56 to 128 trades per period. Nothing
   here could have resolved an effect of the size Phase 4 measured (~0.02 R)
   even if it were present.
3. **PF unit ambiguity.** `PHASE5_SEARCH_BUDGET.md` §6 said "profit factor > 1.05"
   without naming a unit, and `metrics4.summarize` returns it on points while
   expectancy is in R. With a volatility-scaled R the two can disagree in sign
   (2023: 1.256 on points, 0.911 in R). Both are reported everywhere and the
   R-consistent figure is used for the gate, since Phase 5 sizes risk per trade.
   Gate F fails on three other criteria regardless, so nothing turns on it.
4. **The 2021-fitted baseline imports 2021's drift** into where and in which
   direction the strategy fires (§4 above). Leak-free but fragile.
5. **PDH/PDL for 2021–2024 comes from the frozen Phase-1 2-minute bars** rather
   than re-aggregated raw trades. `max(bar high)` over a day equals
   `max(trade price)` over that day, so they are identical by construction, but
   the code path differs from the one used for 2025-H2.
