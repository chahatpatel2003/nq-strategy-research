# PHASE6_LEAKAGE_AUDIT.md

Phase 6 produced **no frozen candidate**: no entry mechanic passed the
preregistered development gates and the causal context does not beat non-context,
so 2026-Q1 was never opened. This audit covers the development work that was done
and confirms the seals it did not spend.

Test names refer to `tests/test_p6_context.py` unless stated.

**Phase 6's headline is itself a leakage finding** — the Phase-5 decomposition
that motivated this phase used future information. That is documented in full in
`strategies/context_entry/CONTEXT_CAUSALITY_AUDIT.md` and summarised at item 17.

---

### 1. Context activation is causal

The context is the **first** qualifying signal in its bucket, and nothing about
it depends on anything later.
*Checked by* `test_context_uses_no_information_after_its_activation_timestamp`,
which deletes the entire future tape and every later signal and requires the
activation timestamp, direction, R and reference price to be identical.

### 2. Direction is known at activation and locked

`test_direction_is_locked_for_the_rest_of_the_bucket` plants a later signal with
the **opposite** direction and a higher score and requires it to be ignored.

### 3. No future half-hour information selects the context

`test_context_activates_on_the_FIRST_qualifying_signal_in_a_bucket` plants a
*higher-scoring* signal later in the same bucket and asserts the earlier, weaker
one is used. A bucket is never chosen because of what happens in it later, and
`test_at_most_one_context_per_bucket_and_four_buckets` confirms one context per
bucket across all four.

### 4. Entry conditions use only prices already traded

Every mechanic scans forward from `act_idx` and triggers on a print that has
already occurred. `test_every_entry_is_the_first_print_AFTER_the_trigger_plus_latency`
asserts, for all six, that the fill index is the first print at or after
`trigger + 250 ms` and that the preceding print was strictly earlier.

### 5. Pullback extremes are causal

E5/E6 measure the resumption from `np.minimum.accumulate` / `maximum.accumulate`
— the extreme **known so far**, never the eventual one.
`test_E5_never_uses_the_eventual_low_only_the_low_so_far` appends a much deeper
low *after* the entry and requires the entry timestamp not to move.

### 6. Resumption entry occurs after the threshold is reached

`test_E5_E6_require_a_resumption_off_the_CAUSAL_running_extreme` checks the exact
index on a hand-computed tape;
`test_resumption_that_never_completes_gives_no_trade` checks a monotonically
falling tape produces no trade.

### 7. Random controls occur only after context activation

`test_random_control_entries_are_never_before_activation` asserts every drawn
minute satisfies `activation ≤ t < bucket_end` across 50 seeded draws.
`test_random_control_count_shrinks_as_the_bucket_runs_out` confirms a context
activating with two minutes left yields exactly one control, not ten — late
activations get less room, honestly.

**This is the precise defect the Phase-5 control had** (item 17).

### 8. No future data enters the context/model features

The 55 features are imported read-only from the frozen `nqr.p4.features4` and are
unchanged since Phase 4, where the master truncation test
(`tests/test_p4_features.py::test_features_are_invariant_to_truncating_the_future`)
deletes the whole future tape and requires all 55 values to be bit-identical.
That test still runs in this suite. `test_phase6_defines_no_features_and_no_new_R`
asserts Phase 6 defines neither a feature list nor an R rule of its own.

The model, preprocessing, baseline and τ are the frozen Phase-5 objects loaded
from `production_model.pkl`, fitted on 2021 only. **2021 is therefore in-sample
for the context model**, which is stated in every report and is the single most
important caveat on the context result (item 16).

### 9. 2025-H1 never accessed

Never opened by any phase. The Phase-6 guard refuses every date in the window
**and keeps refusing with the 2026-Q1 unlock active**; `assert_path_allowed`
refuses any path containing `2025_H1`; `assert_range_allowed` refuses any range
spanning it. Exactly one unlock function exists and it is named for 2026-Q1.
*Checked by* `test_2025_h1_blocked_even_with_the_unlock` and
`scripts/p6_09_integrity.py`.

### 10. MBP-1 never opened

`assert_path_allowed` refuses `mbp1`, `mbp-1` and any raw `.dbn`/`.dbn.zst`.
`test_mbp1_and_raw_dbn_are_refused` covers four spellings.
`p6_09_integrity.py` additionally asserts that **no Phase-6 module calls
`read_parquet` at all** — Phase 6 consumes only the Phase-5 dataset and the
frozen Phase-4 tick cache through their own guarded loaders, so it has no path to
any raw file.

### 11. 2026 untouched

**No Phase-6 code read a single 2026 row.** `p6_09_integrity.py` confirms no 2026
month in any tick cache, no `run_val2026q1` directory, and no
`front_map_p6val.parquet` — the front map a validation build would have had to
create first. The only contact any phase has ever had with `2026_H1.parquet`
remains the Phase-4 parquet-footer read; no row has ever been decoded.

The Phase-6 unlock phrase is distinct from Phase 5's, so a stale confirmation
string cannot open it: `test_2026_q1_needs_the_phase6_phrase_and_pushes_the_date_predicate`.

### 12. April 2026 onward never accessed

Refused with or without the unlock (`test_april_2026_blocked_even_with_the_unlock`).
`sql_window_guard` **raises before emitting any predicate** for a window reaching
2026-04-01 — including the boundary window `2026-01-01 … 2026-04-01` — so an
April+ row cannot be produced even transiently, despite living in the same file.

### 13. Only six entry strategies were tested

`ENTRY_METHODS` is a 6-tuple; `entry_of` raises `ValueError` for anything else
(`test_only_six_entry_methods_exist`). The parameters are asserted at their
preregistered values: 5 and 10 minutes, 0.25 R and 0.50 R, 0.125 R resumption.
No nearby value was tried. `development_verdict.json` records
`total_configurations_evaluated = 6`, re-checked by `p6_09_integrity.py`.

### 14. No post-hoc threshold changed

The gates were fixed in `PHASE6_SEARCH_BUDGET.md` §6 before any mechanic had an
outcome, and were applied as written. **One diagnostic deliberately not used as a
gate** is recorded transparently: restricting `CONTROL_RANDOM` to only the
contexts each mechanic actually entered makes E3–E6 look *better* (E4's interval
excludes zero). That comparison is reported in `ENTRY_MECHANICS.md` and logged as
hypothesis H6-2, and it did **not** rescue any candidate, because swapping the
preregistered comparison for a more favourable one after seeing results is the
exact failure the budget exists to prevent.

### 15. PF units are explicit

Every profit factor in Phase 6 is `PF(R)`, computed in R units by
`backtest6.pf_r` and labelled as such; the points figure appears beside it in
`PROP_FIRM_METRICS.md` and is never used for a gate.
*Checked by* `test_pf_r_is_computed_in_R_units`.

### 16. The selection rule cannot favour a tiny sample

G1 imposes a 300-trade floor **before** any ranking, which excluded E4 (227) and
E6 (221) automatically. G2 requires 4 of 5 periods positive, which no mechanic
reached. Selection among survivors would have used the **median** per-period
advantage, not any single period's expectancy. This is the direct correction of
the Phase-5 defect where ranking on expectancy alone picked the smallest book.

### 17. The Phase-5 decomposition was NOT causal — quantified

`nqr.p5.backtest5.matched_controls` drew control entries from the whole 30-minute
bucket and assigned them the strategy's direction. Measured on the stored Phase-5
control logs:

| period | controls | entered **before** the signal that gave them direction | share |
|---|---:|---:|---:|
| 2021 | 846 | 363 | 42.9 % |
| 2022 | 1,119 | 453 | 40.5 % |
| 2023 | 838 | 382 | 45.6 % |
| 2024 | 687 | 335 | 48.8 % |
| 2025-H2 | 491 | 222 | 45.2 % |
| **total** | **3,981** | **1,755** | **44.1 %** |

Median lead 6–8 minutes, maximum 29. Re-running with the draw restricted to
minutes at or after the signal drops the "context" return from **+0.1034 to
+0.0521 R** on average, and reverses the count of periods in which the Phase-5
strategy beat its control from 2-of-5 to **3-of-5**.

Phase 5 is immutable and was **not** edited. The correction lives in
`CONTEXT_CAUSALITY_AUDIT.md`, in `PHASE6_VERDICT.md` §3, and here.

---

## Residual weaknesses, stated rather than hidden

1. **2021 is in-sample for the context model** and is the only period where the
   context beats non-context with a CI excluding zero. Excluding 2021 the sign
   reverses. Every context claim in Phase 6 carries this caveat.
2. **All five development periods are contaminated for Phase 6** — the hypothesis
   came from Phase-5 diagnostics run on them. There is no out-of-sample evidence
   in this phase at all, by construction, which is why the gates were made
   stability-based rather than expectancy-based.
3. **Books are small**: 221–369 trades per mechanic across five years, and only
   502 contexts. The day-block intervals are correspondingly wide, and Phase 6
   could not have detected a small entry effect even if one existed.
4. **`CONTROL_NONCONTEXT` samples a different bucket on the same day**, since the
   matched bucket is by definition occupied by the context. Day and R scale are
   matched, direction is drawn from the context direction distribution, but the
   time-of-day is not identical — a limitation of the comparison, not a leak.
5. **The 250 ms latency is applied to clock-triggered mechanics too** (E1/E2),
   where a live system would already have the order resting. This is conservative
   and is applied identically to every arm, so it cannot bias the comparison.
