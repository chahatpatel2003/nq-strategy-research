# PHASE7_LEAKAGE_AUDIT.md

Phase 7 produced **no frozen candidate**: none of the 12 configurations passed the
2022 gates, so 2023 was never scored, 2024 was never opened, and **2025-H1 stays
sealed**. This audit covers the development work that was done.

Test names refer to `tests/test_p7_causality.py`.

---

### 1. No future quotes in features

Every book aggregate is a trailing window (1 s / 5 s / 15 s) closed at the
decision second. The grid convention is inherited and tested: index `i` is the
second `[T0+i, T0+i+1)`, and the decision stamped `T0+i+1` reads `grid[i]`, so
every input second has closed.
*Checked by* `test_state_matrix_uses_no_future_second`, which truncates the grid
immediately after a decision second and requires all 40 features to be identical,
and `test_rolling_windows_are_trailing_and_closed`.

### 2. No future trades in features

Trade-derived families (8, 9, 10) read the same per-second aggregates from the
same trailing windows. The `T` rows come from the MBP-1 stream itself, so they are
natively aligned to the book state rather than joined to it.

### 3. No nearest-future-quote joins

There is no join of any kind between quotes and decisions — the book state is
carried on a dense second grid and forward-filled **only from the past**.
`test_book_grid_forward_fills_state_but_not_flow` asserts that state persists
across event-less seconds while every flow counter is zero there, which is the
exact asymmetry a future-leaking fill would break.

### 4. Same-timestamp ordering handled safely

Audited before any feature was written. `sequence` is monotone in `ts_event`
(0 decreases over a sampled RTH day) but **not unique**: 12,283 of 592,404
sampled timestamps have ties it cannot break, because a multi-message exchange
packet — e.g. one aggressive order sweeping two levels — shares both fields.

Frozen rule: **`ORDER BY ts_event, sequence, file_row_number`**. File row order is
the exchange's within-packet order and is deterministic. Because the decision
clock is 5 s and features aggregate to whole seconds, tied rows always fall in the
same second, so ordering affects *transitions*, not the assignment of events to
decisions.

### 5. Feature windows are trailing only

All windows are `_roll_sum` / `_roll_mean` / `_shift(k>0)` over the second grid.
There is no centred, symmetric or two-sided window anywhere in
`src/nqr/p7/features7.py`.

### 6. No centred smoothing

None exists. Grep-checked by the source assertions in
`test_phase7_assumes_only_one_book_level`, which also confirms no `_01`…`_09`
column and no `queue_position` / `order_id` / `hidden` / `iceberg` reference.

### 7. No future replenishment inside features

Family 9 (`ask_repl_per_buy_15`, `bid_repl_per_sell_15`) uses only size increases
that have **already occurred** in the trailing 15 s. There is no
"eventually replenished" construct and no forward search.

### 8. No future best-price changes inside features

Family 7 counts best-price steps that have already happened in the trailing 15 s.
OFI (family 5) is computed on transitions between **consecutive past events**.

### 9. Scaling uses 2021 only

The winsorise + standardise preprocessor is fitted on **364,320 rows from 2021
alone**, records `fit_on = "train2021"`, and is asserted before scoring any split.
Never refitted.

### 10. Selectivity thresholds use 2021 only

`thresholds_from_train` takes quantiles of `|p − 0.5|` on the 2021 rows and the
result is frozen as a number. It is never recomputed on 2022 or later.
*Checked by* `test_thresholds_come_from_the_training_confidence_distribution`.

The **control matching quartile edges** (ATR, spread) are likewise 2021-only and
frozen — a control cannot be matched using a boundary derived from the data it is
being compared on.

### 11. Configuration selection used only allowed data

All 12 configurations were scored against **2022 only**. `p7_03_develop.py`
asserts `set(years) == {2021, 2022, 2023}` on load and that every boundary date
maps to TRAIN/SELECT/ITEST.

### 12. 2023 was not used to retune — it was never scored at all

The preregistered rule is that failing the 2022 gate ends the phase before 2023.
It failed, so **no Phase-7 model was ever scored on 2023**. 2023 rows exist in the
dataset (it was built in one pass) but no model touched them. The diagnostics —
ablation, both nulls, feature importance, regime tables — were deliberately run on
**2022**, the split already spent by selection, so that nothing new was consumed.

### 13. 2024 is untouched

Never built, never scored. It is a post-freeze stress gate and there was no
freeze.

### 14. 2025-H1 untouched before freeze — and it stays untouched

**No Phase-7 code decoded a single 2025-H1 row.** Only parquet-footer metadata was
read (row count, row-group count, first/last timestamps), recorded in
`MBP1_SCHEMA_AUDIT.md` §1.

The guard refuses every date in the window and any path containing `2025_H1`
until the explicit Phase-7 phrase is given; a Phase-6 phrase is rejected.
`p7_09_integrity.py` confirms the book cache contains no 2025 month and no
`run_val2025h1` directory exists.
*Checked by* `test_2025h1_blocked_before_the_unlock`,
`test_2025h1_opens_only_with_the_phase7_phrase`.

### 15. 2026 untouched, with no unlock path at all

Phase 7 does not need 2026 and cannot reach it: `assert_date_allowed` refuses
every 2026 date **with and without** the 2025-H1 unlock active, and
`assert_path_allowed` refuses `2026_H1` / `2026_H2`. 2025-H2 is likewise refused
as `NOT_PHASE7`.
*Checked by* `test_2026_has_no_phase7_unlock_path_at_all`,
`test_2025h2_is_not_a_phase7_period`.

### 16. Controls are causal — asserted at runtime, not assumed

Phase 6 found that 44.1 % of Phase-5's controls entered before the signal that
gave them their direction. Phase 7 does not rely on remembering that.
`assert_control_causality` raises `ControlCausalityViolation` and **fails the run**
if any control's entry is not strictly after its own decision, if any same-day
control decides before its signal, or if any cross-day control lands on the
signal's own day. It is itself unit tested by
`test_control_causality_assertion_actually_fires`.

Same-day **backward** sampling — the Phase-5 construction — is not offered at all.

Two independently-constructed causal controls were run and agree: cross-day
(matches time-of-day exactly, gives up the day) and same-day-forward (matches the
day, gives up exact time-of-day).

### 17. Strategy and control execution are identical

Both read the same tick-resolved labels from the same dataset rows: same 250 ms
latency, same first-print-after entry, same ±R bracket off the realised fill, same
touch-then-market stop, same trade-through-by-a-tick target, same 15-minute
horizon, same executable timeout, same friction grid. There is no second
execution model in Phase 7.
*Checked by* `test_controls_match_direction_R_and_bucket`.

### 18. No subgroup rescued a failed strategy

63 regime/time cells were examined **after** the phase had already failed, and
every one is labelled diagnostic-only and carried to `FUTURE_HYPOTHESES.md`. The
best cells are +0.1149 R on n = 89 and +0.96 R on **n = 1**. Nothing was promoted.

### 19. No search expansion beyond 12

12 enumerated, 12 evaluated, 12 recorded. `enumerate_configs()` raises
`BudgetViolation` for any other count and `build_estimator` raises for any family
outside the two preregistered ones. No third R, no fourth threshold, no nearby
parameter value.
*Checked by* `test_budget_is_exactly_12_and_cannot_grow`,
`test_only_two_families_and_the_tree_is_depth_3`.

### 20. The incremental-MBP ablation was performed honestly

A0 (40) / A1 (32) / A2 (8), each with its own 2021 scaler and its own 2021
threshold, identical dates, R, family, selectivity and execution. The headline
number (`A0 − A2 = +0.0784 R`, CI excluding zero) is reported **together with** the
unconditional baseline that makes it interpretable: the full model sits +0.006 R
from doing nothing, and the "gain" is the book undoing the harm the trades-only
arm does. Reporting the ablation alone would have been misleading, and
`INCREMENTAL_MBP.md` says so explicitly.

---

## Two real bugs found, both in tooling, both fixed

The book-sequence audit exists to catch sequencing and alignment errors. It caught
two — in itself:

1. **uint32 underflow.** `bid_sz_00`/`ask_sz_00` are `uint32`; subtracting them in
   pandas wraps (`1 − 2 → 4294967295`), which turned displayed imbalance into
   ~1.4 × 10⁹. **The production SQL casts to `BIGINT` first**, and 1,353,049 cached
   seconds were re-checked to confirm imbalance stays in [−1, 1] and the microprice
   inside the spread. Now guarded by
   `test_cache_sql_casts_sizes_before_subtracting` and
   `test_built_cache_has_valid_imbalance_and_microprice`.
2. **DuckDB session timezone.** A naive `TIMESTAMPTZ` literal is parsed in the
   *session* timezone (here `America/Los_Angeles`), and results are returned
   converted to it — so the audit was querying a window 8 hours from the intended
   one. **`cache7.BOOK_SQL` is unaffected** because `_month_bounds` emits explicit
   `+0000` offsets; now asserted by
   `test_cache_sql_uses_explicit_utc_offsets_in_its_literals`.

Neither touched the cache or any result. They are recorded because a leakage audit
that reports only clean findings is not doing its job.

## Residual weaknesses, stated rather than hidden

1. **Every pre-2026 period in this project has now been examined many times.**
   2022 is a selection split, not out-of-sample, and Phase 7's development
   evidence rests on it alone.
2. **The depth-3 tree collapsed its three selectivity levels**, so the 12
   configurations are really 8 distinct strategies plus 4 duplicates. Disclosed,
   not adjusted.
3. **Spread is degenerate for NQ** — the 2021 quartile edges are [2, 2, 2] ticks —
   so the matched control effectively conditions on day/time/direction/volatility
   only, not spread regime.
4. **`ret_15s_norm` uses mid**, a book quantity, and survives into the A2
   "trades + context" arm. A2 is therefore not purely trade-derived; this is
   stated in `FEATURE_REGISTRY.md` so the arm can be discounted accordingly.
5. **MBP-1 is not MBO.** A negative here is evidence about the **top of book
   only** — not about queue position, order-level behaviour, hidden liquidity or
   deeper book shape, none of which this data contains.
