# PHASE4_START_INTEGRITY.md

**Run:** 2026-08-19 · resumption of Phase 4 after the macOS Desktop permission
failure interrupted the previous session mid-write.

**Result: ALL CHECKS PASSED. Phase 4 resumes from where it stopped; nothing was
restarted, nothing from Phases 1–3 was touched.**

---

## 1. Desktop access

`~/Desktop/nq_strategy_research` is readable and writable again. The project was
**not** relocated. The Samsung T9 is mounted at `/Volumes/T9` and the trades and
MBP-1 folders resolve exactly as before:

    trades : /Volumes/T9/nq data/raw/trades   (2021_H1 … 2026_H1)
    mbp1   : /Volumes/T9/nq data/raw/mbp1     (2021_H1 … 2025_H1)  — NOT OPENED

## 2. Test suite

    python -m pytest tests -q   ->   218 passed

Same count as before the interruption.

## 3. Phase 1–3 integrity and frozen identities

| phase | script | result | frozen id |
|---|---|---|---|
| 1 | `scripts/07_integrity_check.py` | ALL CHECKS PASSED | `fastslow-1.0.0+5980044a44eebf7b` |
| 2 | `scripts/p2_09_integrity.py` | ALL CHECKS PASSED | `impexh-1.0.0.impl2+48c76a0e68b88947` |
| 3 | `scripts/p3_11_integrity.py` | ALL CHECKS PASSED | `dcevent-1.0.0.impl3+d33e5d5d116f1adb` |

All three match the identities recorded before the interruption, byte for byte.
Phase 2's check independently re-verifies Phase 1's frozen id, and Phase 3's
manifest re-verifies both.

## 4. Source data unmodified

Every original T9 parquet still carries a modification time that predates this
project (the marker Phase 1 froze). Nothing was written to the drive.

| file | bytes | mtime (UTC) | < project start |
|---|---:|---|---|
| `trades/2021_H1.parquet` | 1,106,822,528 | 2026-06-17 11:09:12 | yes |
| `trades/2021_H2.parquet` | 1,095,809,070 | 2026-06-17 11:13:48 | yes |
| `trades/2022_H1.parquet` | 1,513,326,861 | 2026-06-17 11:22:00 | yes |
| `trades/2022_H2.parquet` | 1,433,552,589 | 2026-06-17 11:27:44 | yes |
| `trades/2023_H1.parquet` | 1,305,762,398 | 2026-06-17 11:33:42 | yes |
| `trades/2023_H2.parquet` | 1,295,214,885 | 2026-06-17 11:38:58 | yes |
| `trades/2024_H1.parquet` | 1,304,195,721 | 2026-06-17 11:44:36 | yes |
| `trades/2024_H2.parquet` | 1,229,612,152 | 2026-06-17 11:50:04 | yes |
| `trades/2025_H1.parquet` | 1,319,305,616 | 2026-06-17 11:55:14 | yes |
| `trades/2025_H2.parquet` | 1,141,481,524 | 2026-06-17 11:59:50 | yes |
| `trades/2026_H1.parquet` | 1,171,996,449 | 2026-06-17 12:05:08 | yes |
| `mbp1/2021_H1.parquet` | 18,623,606,865 | 2026-06-17 13:11:00 | yes |
| `mbp1/2021_H2.parquet` | 19,809,165,365 | 2026-06-17 14:37:56 | yes |
| `mbp1/2022_H1.parquet` | 27,081,974,141 | 2026-06-17 16:19:52 | yes |
| `mbp1/2022_H2.parquet` | 23,611,473,537 | 2026-06-17 17:49:02 | yes |
| `mbp1/2023_H1.parquet` | 21,865,069,299 | 2026-06-17 19:24:42 | yes |
| `mbp1/2023_H2.parquet` | 24,346,223,113 | 2026-06-17 21:05:50 | yes |
| `mbp1/2024_H1.parquet` | 24,400,970,262 | 2026-06-17 22:35:18 | yes |
| `mbp1/2024_H2.parquet` | 27,120,421,538 | 2026-06-18 00:09:30 | yes |
| `mbp1/2025_H1.parquet` | 35,273,318,808 | 2026-06-18 02:17:46 | yes |

## 5. Recovery of the interrupted write

`src/nqr/p4/holdout4.py` — **complete and correct**, 153 lines, no repair needed.

`src/nqr/p4/features4.py` — **truncated by the interruption**. What survived was
the module docstring, `FEATURE_NAMES`, the rolling helpers, `build_grid` and
`causal_atr`; the state-vector builder that consumes them was missing entirely,
so the module could not produce a single feature row. It was completed from
`FEATURE_REGISTRY.md`, which was already on disk and is **unchanged**.

**This is recovery from an interrupted filesystem write, not a strategy
modification.** The registered universe is untouched: 55 features, family sizes
8 / 5 / 7 / 9 / 6 / 6 / 3 / 6 / 5, exactly as registered.

Three defects in the surviving fragment were found and repaired. All three are
implementation bugs that would have produced silently wrong numbers; none of
them changes what the registry says a feature *is*:

1. **`build_grid` seeded `high`/`low` with NaN and then called
   `np.maximum.at` / `np.minimum.at`.** `np.maximum(nan, x)` is `nan`, so every
   second's high and low would have come out NaN. Seeds are now `-inf`/`+inf`.
2. **`open`/`close` were assigned through duplicate fancy indices**, relying on
   "last write wins", which NumPy does not guarantee. Now resolved with an
   explicit first-of-run / last-of-run index, which is deterministic.
3. **`pl.Series(close).forward_fill()` was a silent no-op.** Polars treats
   `np.nan` as a *value*, not a null, so the fill did nothing and 1,438 untraded
   seconds a day stayed NaN — which then propagated through every cumulative-sum
   feature and would have made `eff_*`, `rv_*` and `vol_ratio_60_300` NaN for
   **100 %** of decisions. Now `fill_nan(None).forward_fill()`.

Regression tests for all three are in `tests/test_p4_features.py`.

After repair, a full day (2021-03-10, NQH1, 363,488 prints) yields **0
non-finite cells across 4,680 decisions × 55 features**.

## 6. Guard verification

`nqr.p4.holdout4` behaviour, checked live:

| date | period | result |
|---|---|---|
| 2021-06-01 | DISCOVERY_TRAIN | allowed |
| 2022-06-01 | SELECTION | allowed |
| 2023-06-01 | INTERNAL_TEST | allowed |
| 2024-06-01 | CONTAM_2024 | allowed (contaminated, diagnostic only) |
| **2025-03-01** | **SEALED_2025H1** | **blocked — no unlock path exists** |
| 2025-09-01 | CONTAM_2025H2 | allowed (contaminated, diagnostic only) |
| 2026-02-01 | FRESH_VAL | blocked until the explicit one-time unlock |
| **2026-05-01** | **SEALED_FINAL** | **blocked — no unlock path exists** |

Path guard: `2025_H1.parquet` refused unconditionally; `2026_H2.parquet` refused
unconditionally; `2026_H1.parquet` refused until the validation unlock;
`2024_H2.parquet` allowed. There is **no code path in `holdout4` that can open
2025-H1 or 2026-04-01+**, and the validation unlock opens 2026-Q1 and nothing
else.

## 7. No stray Phase-4 artifacts

The permission failure created nothing it should not have. As of this report:

* no Phase-4 feature dataset;
* no Phase-4 labels;
* no Phase-4 model;
* no Phase-4 P&L or trade log;
* `strategies/state_discovery/` holds only `FEATURE_REGISTRY.md`,
  `SEARCH_BUDGET.md`, `PREREG_ADDENDUM.md` and empty subdirectories.

## 8. 2026 coverage — footer metadata only

`2026_H1.parquet` was inspected through the **parquet footer only**; not one row
was decoded and no market content was read.

    num_rows       47,081,888
    row groups     719
    first rg ts    2026-01-01 23:00:00+00:00
    last  rg ts    2026-06-17 03:03:02+00:00
    row groups whose min ts < 2026-04-01 : 377 of 719

Two consequences, both important:

* 2026-Q1 is fully covered, so Gate 1 (≥ 100 trades) stays at 100.
* **the file also contains sealed April-2026+ data.** Any read of it must carry
  a hard trading-date predicate. `holdout4.sql_window_guard` supplies one and
  refuses any range reaching 2026-04-01; row-group statistics are present, so
  the predicate prunes at the file level as well.

## 9. 2025-H1 and MBP-1

2025-H1 was never opened, in any form, by any phase. MBP-1 has not been opened
in Phase 4 and will not be: Family 6 uses the native Databento `side` field from
the Trades files, on the strength of the Phase-2 verification already archived
in `results/p2_signing_verification.json` (99.998 % agreement over 3,882,344
trades). That file is unchanged.

## 10. Pre-registration completed before any label existed

`strategies/state_discovery/PREREG_ADDENDUM.md` was written **before** the first
Phase-4 label was computed. It fixes the handful of decisions the earlier
documents left open — TIMEOUT handling, the classification target, direction
logic, the threshold population, the matched-control definition, and the Gate 7
concentration rule — so that no outcome can have influenced them.
