# PHASE4_LEAKAGE_AUDIT.md

Frozen strategy `statedisc-1.0.0+c147134184dfb32d`. Every claim below is backed by an executable check, not
by inspection. Test names refer to `tests/test_p4_features.py`,
`tests/test_p4_backtest.py` and `tests/test_p4_holdout.py`.

## The master check

`test_features_are_invariant_to_truncating_the_future` rebuilds the entire
55-feature state vector from a tape that has been **cut off at the decision
timestamp** — every later print physically deleted — and requires all 55 values
to be identical to the ones computed with the full day present. It is run at
10:15, 11:00 and 11:29:55 on a real session. A feature that consulted even one
future print cannot pass it. Items 1–5 below are corollaries; each also has its
own targeted test.

---

### 1. No future returns in features

Every return is `c[t] − c[t−h]` for a fixed `h ∈ {5, 15, 30, 60, 120, 300}` s,
both endpoints at or before `t`.
*Checked by* `test_fixed_horizon_returns_match_a_direct_computation`,
`test_features_are_invariant_to_truncating_the_future`.

### 2. No future extrema

All extrema come from `_roll_max`/`_roll_min` over a window **ending at** the
current index. `_secs_since_extreme` scans backwards only.
*Checked by* `test_trailing_extremes_never_see_the_future` (exact expected
sequences), `test_rolling_windows_are_trailing_and_closed`.

### 3. No centred windows

There is no centred, symmetric or two-sided window anywhere in
`src/nqr/p4/features4.py`. Every aggregate is built from `_roll_sum`,
`_roll_max`, `_roll_min`, `_shift(k>0)` or a cumulative sum, all of which are
one-sided and backward-looking by construction.

### 4. No incomplete-bar OHLC leakage

The volatility unit is ATR14 of **completed** 1-minute bars: the value published
for minute *m* uses minutes *m−14 … m−1*. `test_atr_uses_only_completed_minutes`
rewrites the *current* minute's high and low by ±500 points and asserts the ATR
published inside that minute does not move.
`test_causal_atr_matches_frozen_phase2_implementation` asserts the values equal
the frozen Phase-2 `causal_atr_minutes` exactly.

### 5. Trailing statistics only

`atr_pct_rank` ranks the current ATR against the **strictly prior** 120 minutes
of same-day values — the current value is never in its own reference window.
*Checked by* `test_trailing_percentile_is_strictly_prior`, which recomputes one
bucket by hand.

The opening range is a special case and is handled explicitly: `dist_or30_*` is
**0 for every decision before 10:00 ET** and only becomes live once the
09:30–10:00 range has completed. *Checked by*
`test_opening_range_is_zero_until_it_completes`.

Cumulative delta and session VWAP accumulate forward from 09:30 only.
*Checked by* `test_cumulative_delta_starts_at_the_open_and_is_bounded`.

Family 9 (directional-change context) uses the frozen Phase-3 engine, in which an
extreme is never known before its confirmation. The Phase-4 grid mapping admits
event *k* only from the second in which `conf_ts` falls.
*Checked by* `test_dc_context_matches_the_frozen_phase3_runner` (event-for-event
equality with the Phase-3 runner) and `test_dc_features_only_use_confirmed_events`
(`secs_since_last_dc ≥ 0` everywhere).

### 6. Training-only scaling

Winsorisation bounds (0.1 % / 99.9 %) and standardisation constants are fitted on
the **2021 partition alone** and never refitted. The fitted object records
`fit_on = "train2021"` and `n_fit = 364,320`, and
`scripts/p4_03_run_split.py` asserts `pre.fit_on == "train2021"` before scoring
any split.
*Checked by* `test_scaler_is_fitted_only_on_training_rows` (transforming
wildly-different data must not move the constants),
`test_winsorisation_bounds_come_from_training_only`.

The signal threshold is likewise a **2021** quantile of `|score|`, frozen as the
number `tau = 0.017941` and applied unchanged to 2022, 2023, 2024 and 2025-H2.
*Checked by* `test_threshold_is_a_training_quantile_and_then_a_fixed_number`.

### 7. Chronological model selection

2021 fits, 2022 selects, 2023 is scored once afterwards. The 18 configurations
were compared on 2022 **only**; `scripts/p4_02_develop.py` never loads a row
outside 2021–2023 and asserts `set(years) == {2021, 2022, 2023}`. 2023's numbers
were produced by `p4_03_run_split.py` after `production_model.pkl` already
existed on disk.

### 8. No random row shuffle

There is no `train_test_split`, no `shuffle=True` and no `KFold` anywhere in
Phase 4. Splits are whole calendar years, assigned by `holdout4.period_of`.

### 9. Overlap dependence handled

Adjacent 5-second rows share up to 30 minutes of future tape, so:

* performance is measured on **non-overlapping executed trades** produced by the
  one-position-at-a-time rule, never on the row population;
* every interval is a **day-block bootstrap** — 10 000 resamples of whole trading
  days, strategy and control resampled together;
* no p-value or CI in Phase 4 treats trades as i.i.d.

*Checked by* `test_bootstrap_is_over_trading_days_not_trades`, which asserts the
day-block interval is materially wider than the naive i.i.d. one on the same data,
and `test_only_one_position_is_ever_open`.

**Purging / embargo.** No label crosses a trading-day boundary, so a whole-year
split needs no purge. Verified empirically over all 5,264,639 decision rows:

| split | rows with an entry | entry latency min | hold max | labels crossing the day |
|---|---:|---:|---:|---:|
| dev 2021–2023 | 3,505,679 | 250.0 ms | 1,162 s | **0** |
| 2024 | 1,172,340 | 250.0 ms | 736 s | **0** |
| 2025-H2 | 586,620 | 250.0 ms | 753 s | **0** |

Entry latency is never below the 250 ms model and the hold never exceeds the
1,800 s cap.

### 10. 2024 marked contaminated

`holdout4.period_of` returns `CONTAM_2024`; `CONTAMINATED` contains it; the
build script and the runner both print
`*** CONTAMINATED DIAGNOSTIC - NOT VALIDATION ***`; `results.json` carries
`is_contaminated: true`; the report is titled
**CONTAMINATED DIAGNOSTIC — NOT VALIDATION**. It ran **after** the freeze and
changed nothing.

### 11. 2025-H2 marked contaminated

Identical treatment (`CONTAM_2025H2`). It was consumed as Phase-3 fresh
validation, ran after the Phase-4 freeze, and changed nothing.

### 12. 2025-H1 never accessed

`assert_date_allowed` raises for every date in 2025-01-01 … 2025-06-30, **and
keeps raising with the 2026-Q1 unlock active** — the unlock is scoped to Q1 and
nothing else. `assert_path_allowed` refuses any path containing `2025_H1`
unconditionally. There is exactly one unlock function in the module and it is
named for 2026-Q1.

The 2025-H2 diagnostic reads `2025_H2.parquet` only, under a trading-date
predicate of `>= 2025-07-01`; the build script proves the seal is live before
opening anything. The resulting cache contains months 2025-07 … 2025-12 and
nothing earlier.

*Checked by* `test_2025_h1_is_hard_blocked`,
`test_2025_h1_stays_blocked_even_with_the_validation_unlock`,
`test_no_unlock_function_can_open_2025_h1_or_the_final_holdout`,
`test_range_spanning_a_sealed_window_is_refused`, and
`scripts/p4_09_integrity.py`.

### 13. 2026-Q1 untouched until the freeze

At the time of writing, 2026-Q1 **market content has not been read at all**. The
only contact with `2026_H1.parquet` has been a **parquet footer** read — row
count, row-group count and the first/last row-group timestamps — recorded in
`reports/PHASE4_START_INTEGRITY.md`. No row was decoded.
`p4_09_integrity.py` confirms the Phase-4 tick cache holds no 2026 month and
that at most one validation run directory exists (currently zero).

### 14. April 2026 onward never accessed

`assert_date_allowed` raises for every date ≥ 2026-04-01, with or without the
unlock. `assert_range_allowed` refuses any range reaching it.
`assert_path_allowed` refuses `2026_H2`. The raw DBN directory on the drive
(`NQ_HOLDOUT/GLBX-…`, which starts 2026-06-17) was never referenced by any
Phase-4 code path.

This matters more than usual here: **`2026_H1.parquet` physically contains April,
May and June 2026** (it runs to 2026-06-17). Any future read of it therefore
carries `sql_window_guard`, which refuses outright any range reaching
2026-04-01, plus a per-month timestamp bound, plus the 08:00–16:15 ET band
filter. Row-group statistics are present (719 groups), so the predicate prunes at
file level as well.

*Checked by* `test_april_2026_onward_is_hard_blocked`,
`test_sql_window_guard_refuses_forbidden_ranges_and_bounds_allowed_ones`.

### 15. Execution identical between strategy and controls

Strategy trades, matched-random controls, opposite-direction controls and the
shuffled null all read the **same** tick-resolved labels from the same dataset
rows: same 250 ms latency, same first-print-after entry, same ±1R bracket, same
touch-then-market stop, same trade-through-by-a-tick target, same 30-minute
horizon, same friction grid. There is no second execution model in Phase 4.
*Checked by* `test_controls_use_the_identical_execution_and_bracket`,
`test_opposite_direction_control_flips_and_nothing_else`.

### 16. Same corrected `ts_event` chronology

Ticks come from the Phase-2 cache (2021–2024) and the Phase-4 cache built with
the same SQL shape (2025-H2), both ordered by `(ts_event, file_row_number)` so
that a multi-fill sweep sharing one timestamp resolves deterministically. The
Globex trading date is
`CAST((ts_event AT TIME ZONE 'America/New_York') + INTERVAL 6 HOUR AS DATE)`
throughout, identical to Phases 1–3. Sessions are computed in
`America/New_York`, so DST is automatic.
*Checked by* `test_decision_clock_is_5s_and_dst_correct` (1440 decisions on both
EST and EDT days, first exactly at 09:30:00 ET), `test_et_sec_tracks_dst_offsets`.

### 17. No search-budget expansion

18 configurations enumerated, 18 evaluated, 18 recorded. `enumerate_configs()`
raises `BudgetViolation` if the count is anything else, and
`build_estimator` raises for any family outside the two preregistered ones.
`selection_2022.parquet` has exactly 18 rows. The feature universe is 55 of a
60 cap and was not touched after the interruption.
*Checked by* `test_budget_is_exactly_18_and_cannot_grow`,
`test_only_the_two_preregistered_families_exist`,
`test_tree_is_shallow_and_leaf_constrained`, and `p4_09_integrity.py`.

---

## Residual weaknesses, stated rather than hidden

Nothing found below rises to leakage; they are honest limitations.

1. **The realised selection rate is 75 %, not 20 %.** A depth-3 tree has ≤ 8
   distinct scores, so the 80th-percentile threshold lands inside a tie group and
   the preregistered "keep ties" rule admits the whole group. The nominal
   top-20 % label is therefore misleading about how selective the strategy is.
   Disclosed, not repaired — repairing it after seeing outcomes would be
   threshold mining.
2. **PDH/PDL for 2021–2024 is derived from the frozen Phase-1 2-minute bars**
   rather than re-aggregated from raw trades. `max(bar high)` over a day equals
   `max(trade price)` over that day, so the two are identical by construction,
   but the code path differs from the one used for 2025-H2.
3. **Model fitting uses overlapping rows.** This costs effective sample size and
   nothing else — no inference is drawn from the row population — but it does
   mean the tree's training signal is less independent than 364,320 rows suggests.
4. **`delta_300_norm` uses a 1,500 s trailing volume base**, the literal mirror
   of `delta_60_norm`'s 300 s base. `FEATURE_REGISTRY.md` says only "mirror over
   300 s"; the exact denominator is pinned in `STATE_DISCOVERY_SPEC.md` §4. Both
   readings are causal; the choice was made before any label existed and was not
   revisited.
