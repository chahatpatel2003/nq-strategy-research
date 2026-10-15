# PHASE5_FEATURE_REGISTRY.md — Phase 5 causal state

**Written and frozen BEFORE any Phase-5 label or outcome was computed.**

## The universe is unchanged

Phase 5 reuses the **exact 55-feature causal state of Phase 4**, without
addition, substitution or redefinition. The authoritative definitions live in

    strategies/state_discovery/FEATURE_REGISTRY.md
    sha256 128c0e7455cf4b27ac721b995558a5f869fe852196b38b1dd3e1085b401d66de

and the implementation is the frozen `src/nqr/p4/features4.py`
(sha256 `636af03cc537fb992003113dd5602cf6ee21a1b21cb52e630344df574d8dc216`),
imported read-only. Phase 5 adds no feature code of its own.

| family | features | count |
|---|---|---:|
| 1 — returns / displacement | `ret_norm_{5,15,30,60,120,300}`, `eff_60`, `eff_300` | 8 |
| 2 — velocity / acceleration | `vel_15_norm`, `vel_60_norm`, `vel_ratio_15_60`, `accel_15_60`, `persist_60` | 5 |
| 3 — volatility / range | `atr1m`, `rv_60_norm`, `rv_300_norm`, `vol_ratio_60_300`, `range_60_norm`, `atr_pct_rank`, `vol_expansion` | 7 |
| 4 — micro structure | `dist_high_300_norm`, `dist_low_300_norm`, `dist_high_1800_norm`, `dist_low_1800_norm`, `n_new_highs_300`, `n_new_lows_300`, `pullback_depth`, `secs_since_high_300`, `secs_since_low_300` | 9 |
| 5 — trade intensity | `trades_per_s_60`, `vol_per_s_60`, `avg_trade_size_60`, `max_trade_size_60_rel`, `intensity_ratio_60_300`, `volume_ratio_60_300` | 6 |
| 6 — trade side / delta | `delta_60_norm`, `delta_300_norm`, `delta_per_vol_60`, `delta_per_vol_300`, `cum_delta_norm`, `delta_accel` | 6 |
| 7 — time / session | `secs_since_open`, `is_second_hour`, `weekday` | 3 |
| 8 — objective location | `dist_open_norm`, `dist_vwap_norm`, `dist_pdh_norm`, `dist_pdl_norm`, `dist_or30_hi_norm`, `dist_or30_lo_norm` | 6 |
| 9 — event sequence | `last_dc_dir`, `last_dc_mag_norm`, `last_overshoot_norm`, `prev2_dc_dir`, `secs_since_last_dc` | 5 |
| | **total** | **55** |

## Nothing removed

The registry permits removing a feature before outcomes for a documented
technical reason. **Nothing was removed.** One candidate was considered and
rejected, and the reasoning is recorded here so the decision is auditable:

* **`atr1m` (feature 14) is the only feature expressed in raw NQ points.**
  Every other feature is a ratio, a normalised distance, a count or a duration.
  Across 2021–2023 its session median moves 10.54 → 16.75 → 11.54 points
  (a 1.59× spread) while the NQ price level moves only 1.19×, so it carries a
  regime component that the other 54 do not.
* It was **kept** anyway. The brief is explicit that the previously dominant
  features must not be forced in *or* out and that the bounded model decides.
  Removing it would also mean Phase 5 was no longer testing "the same state at a
  larger horizon", which is the entire hypothesis. The non-stationarity is
  recorded in `PHASE5_SPEC.md` §5 as a known risk, and its stationary companion
  `atr_pct_rank` (feature 19, a trailing within-day percentile) is already in the
  universe for the model to prefer if it is the better variable.

## Trade side / delta retained

Family 6 is retained exactly as in Phase 4. The native Databento `side` field
was verified in Phase 2 against a causal MBP-1 quote rule at **99.998 %
agreement over 3,882,344 trades** (`results/p2_signing_verification.json`,
unchanged). Phase 5 therefore reads `side` straight from the Trades files and
**never opens MBP-1**; `holdout5.assert_path_allowed` refuses any path
containing `mbp1`.

Phase 4 found family 6 contributed **zero** importance at a 5-second clock with
a 30-minute horizon. Whether that survives a 60-second clock with a 60-minute
horizon is one of the questions Phase 5 answers, so the family stays in and is
reported on either way.

## What changes between Phase 4 and Phase 5

Only these, and none of them is a feature:

| | Phase 4 | Phase 5 |
|---|---|---|
| decision clock | 5 s | **60 s** |
| R | 0.50 × ATR14(1m) | **2.0 / 3.0 / 4.0 × ATR14(1m)** |
| maximum hold | 30 min | **60 min** |
| timeout exit | last print before the cutoff | **first print at or after the cutoff** |
| cooldown | none | **one full decision interval after exit** |
| trade selection | \|score\| quantile | **edge over a training-only control baseline** |

## Causality

Unchanged and inherited whole. The Phase-4 truncation test
(`test_features_are_invariant_to_truncating_the_future`) deletes the entire
future tape and requires all 55 values to be bit-identical; it still runs in the
Phase-5 suite. The grid convention is unchanged: grid second `[T0+i, T0+i+1)` is
index `i`, and the decision stamped `T0+i+1` reads `grid[i]`, so every input
second has closed before it is used.
