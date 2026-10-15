# PHASE5_START_INTEGRITY.md

**Run:** 2026-08-20, before any Phase-5 code touched market content.

**Result: ALL CHECKS PASSED.** Phases 1–4 are byte-identical, the source data is
unmodified, 2025-H1 has never been opened, and no 2026 market content exists
anywhere in the project.

---

## 1. Test suite

    python -m pytest tests -q   ->   284 passed

Same count as at the close of Phase 4 (218 from Phases 1–3, 66 from Phase 4).

## 2. Frozen identities — all four match

| phase | frozen id | files hashed | drift |
|---|---|---:|---|
| 1 Fast-Slow | `fastslow-1.0.0+5980044a44eebf7b` | 14 | none |
| 2 Impulse exhaustion | `impexh-1.0.0.impl2+48c76a0e68b88947` | 15 | none |
| 3 Directional change | `dcevent-1.0.0.impl3+d33e5d5d116f1adb` | 14 | none |
| 4 Causal state discovery | `statedisc-1.0.0+c147134184dfb32d` | 14 | none |

Each manifest was re-hashed against disk file by file. Every phase's own
end-of-phase integrity script was also re-run:

    scripts/07_integrity_check.py   ->  ALL CHECKS PASSED
    scripts/p2_09_integrity.py      ->  ALL CHECKS PASSED
    scripts/p3_11_integrity.py      ->  ALL CHECKS PASSED
    scripts/p4_09_integrity.py      ->  ALL CHECKS PASSED

## 3. Source data unmodified

Every original T9 parquet still carries a modification time predating this
project — the marker Phase 1 froze. Nothing has ever been written to the drive.

| file | bytes | mtime (UTC) | predates project |
|---|---:|---|:---:|
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

## 4. 2025-H1 remains sealed

Never opened by any phase, in any form. The Phase-5 guard
(`src/nqr/p5/holdout5.py`) refuses it with **no unlock path**:

| probe | result |
|---|---|
| `assert_date_allowed(2025-03-01)` | blocked — `SEALED_2025H1` |
| `assert_date_allowed(2025-03-01)` **with the 2026-Q1 unlock active** | still blocked |
| `assert_path_allowed("2025_H1.parquet")` | blocked unconditionally |
| `assert_range_allowed(2024-12-01, 2025-08-01)` | blocked — spans the seal |

There is exactly one unlock function in the module and it is named for 2026-Q1.

## 5. MBP-1 remains unopened by Phase 5

The Phase-5 guard is **stricter than Phase 4's**: `assert_path_allowed` now also
refuses any path containing `mbp1`/`mbp-1` and any raw `.dbn` / `.dbn.zst`
archive, so a trades-only phase cannot reach order-book data or the raw 2026
holdout archives even by accident.

## 6. No 2026 market content exists

| location | contents |
|---|---|
| `data_cache/p4_ticks/` | 2025-07 … 2025-12 only |
| `data_cache/p3_ticks/` | 2025-07 … 2025-12 only |
| `data_cache/p2_ticks/`, `ticks/` | 2021-01 … 2024-12 only |
| `strategies/state_discovery/features/` | `split=dev`, `split=contam2024`, `split=contam2025h2` |
| `strategies/state_discovery/results/` | run_train2021, run_select2022, run_itest2023, run_contam2024, run_contam2025h2 |

No `split=val2026q1`, no `run_val2026q1`, no 2026 month in any cache.

## 7. 2026-Q1 is still untouched

The only contact any phase has ever had with `2026_H1.parquet` is a **parquet
footer** read during Phase 4 — row count, row-group count and the first/last
row-group timestamps. **No row has ever been decoded.** Phase 4 declined to spend
the quarter and closed on its development result.

## 8. April 2026 onward remains blocked

| probe | result |
|---|---|
| `assert_date_allowed(2026-04-01)` | blocked — `SEALED_FINAL` |
| `assert_date_allowed(2026-06-17)` **with the 2026-Q1 unlock active** | still blocked |
| `assert_path_allowed("2026_H2.parquet")` | blocked unconditionally |
| `assert_path_allowed("…/glbx-mdp3-20260617.trades.dbn.zst")` | blocked unconditionally |
| `sql_window_guard(2026-01-01, 2026-12-31)` | raises before emitting any SQL |

This matters more than usual: **`2026_H1.parquet` physically contains April, May
and June 2026** (it runs to 2026-06-17, 47,081,888 rows across 719 row groups).
`sql_window_guard` is therefore the only sanctioned way for Phase 5 to read it,
and it refuses any range reaching 2026-04-01 *before* returning a predicate — the
guard fires at query-construction time, not after a scan.

## 9. Phase-5 module created

    src/nqr/p5/holdout5.py    period guard, stricter than Phase 4's
    src/nqr/p5/labels5.py     larger-R first passage + executable timeout
    src/nqr/p5/dataset5.py    60-second decision dataset, three R scales
    strategies/larger_r/      specs, config, results, reports, diagnostics

The 55-feature causal state is **imported read-only** from the frozen
`nqr.p4.features4`; Phase 5 adds no feature code.

## 10. Pre-registration completed before any label existed

Written and fixed before the first Phase-5 label was computed:

* `strategies/larger_r/PHASE5_FEATURE_REGISTRY.md` — the 55 features, unchanged;
* `strategies/larger_r/PHASE5_SEARCH_BUDGET.md` — 18 configurations, the single
  selection criterion, and the eligibility gates that allow Phase 5 to fail
  before validation;
* `strategies/larger_r/PHASE5_SPEC.md` — the complete a-priori specification.

The two decisions the brief left open were made from **feature-side statistics on
development data only**, with no P&L computed beforehand:

* **R architecture — volatility-normalised.** Session-median ATR14(1m) spans
  1.59× across the three development years (10.54 → 16.75 → 11.54 pt) while the
  price level spans only 1.19×, and the 2022 intraday decile range alone spans
  2.6×. A fixed-point R would be a materially different bet in each regime.
  The 1-minute basis was chosen over the 5-minute basis because it is fully RTH
  14 minutes after the open, where the 5-minute basis needs 70 minutes — more
  than half the session.
* **Maximum hold — 60 minutes.** Chosen after a review reporting *resolution
  rates only*, never outcomes: 98.0 % / 82.2 % / 59.9 % of trades resolve within
  60 minutes at the three R scales, with median holds of 12 / 27 / 39 minutes.
