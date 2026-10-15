# PHASE7_START_INTEGRITY.md

**Run:** 2026-08-20, before any Phase-7 market content was read.

**Result: ALL CHECKS PASSED.** Phases 1–6 are unchanged, the source data is
unmodified, 2025-H1 has never been opened, 2026 has never been opened, and
Phase 7 has no code path to 2026 at all.

---

## 1. Test suite

    python -m pytest tests -q   ->   369 passed

Same count as at the close of Phase 6 (218 Phases 1–3, 66 Phase 4, 51 Phase 5,
34 Phase 6).

## 2. Frozen identities — all four match

| phase | frozen id | files | drift |
|---|---|---:|---|
| 1 Fast-Slow | `fastslow-1.0.0+5980044a44eebf7b` | 14 | none |
| 2 Impulse exhaustion | `impexh-1.0.0.impl2+48c76a0e68b88947` | 15 | none |
| 3 Directional change | `dcevent-1.0.0.impl3+d33e5d5d116f1adb` | 14 | none |
| 4 Causal state discovery | `statedisc-1.0.0+c147134184dfb32d` | 14 | none |

Phase 5 has no frozen manifest (its candidate was rejected at Gate F); its
artifacts are pinned at `d0783a6638d88aec` (11 files) and re-verified with **no
drift**. Phase 6 likewise froze nothing — no mechanic passed its gates — and its
verdict file is present and unchanged.

All six end-of-phase integrity scripts were re-run:

    scripts/07_integrity_check.py   ->  ALL CHECKS PASSED
    scripts/p2_09_integrity.py      ->  ALL CHECKS PASSED
    scripts/p3_11_integrity.py      ->  ALL CHECKS PASSED
    scripts/p4_09_integrity.py      ->  ALL CHECKS PASSED
    scripts/p5_09_integrity.py      ->  ALL CHECKS PASSED
    scripts/p6_09_integrity.py      ->  ALL CHECKS PASSED

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

## 4. MBP-1 inventory and coverage (footer metadata only)

Nine files, **7,893,313,081 rows, 222 GB**, schema identical across all of them.
Full detail in `strategies/orderbook_state/MBP1_SCHEMA_AUDIT.md`.

**MBP-1 coverage runs 2021-H1 … 2025-H1 and stops.** There is no 2025-H2 and no
2026 MBP-1 file. That makes 2025-H1 not merely the last *untouched* MBP window
but **the last one that exists** — which is why Phase 7's gates are strict about
earning it.

`2025_H1.parquet` coverage, established **without decoding a row**:
1,236,114,072 rows, 18,862 row groups, 2024-12-29 13:00 UTC → 2025-06-30 23:59
UTC. Its first timestamps fall in December 2024, so any read must carry the
Globex trading-date predicate rather than a file-level assumption.

Half-year files overlap at their boundaries (`2023_H2` ends and `2024_H1`
begins at the identical timestamp), so Phase 7 bounds every scan by explicit
per-month `ts_event` limits **as well as** the trading-date guard.

## 5. 2025-H1 remains sealed

Never opened by any phase. The Phase-7 guard refuses it with a single narrow
unlock:

| probe | result |
|---|---|
| `assert_date_allowed(2025-03-01)` | blocked — `FRESH_VAL`, unlock not given |
| `assert_path_allowed("mbp1/2025_H1.parquet")` | blocked |
| `assert_range_allowed(2024-01-01, 2025-03-01)` | blocked — spans the seal |
| `sql_window_guard(2025-01-01, 2026-01-01)` | raises before emitting SQL |
| a Phase-6 confirmation phrase | rejected |

Only market **metadata** has been read: the footer figures in §4. No feature, no
label, no statistic, no chart, no sample day.

## 6. 2026 has no Phase-7 code path

| probe | result |
|---|---|
| `assert_date_allowed(2026-01-02 / 2026-03-31 / 2026-06-01)` | blocked |
| the same, **with the 2025-H1 unlock active** | **still blocked** |
| `assert_path_allowed("2026_H1.parquet" / "2026_H2.parquet")` | blocked |

2026-Q1 remains an independent untouched Trades-only reserve — Phases 4, 5 and 6
each declined to spend it — and 2026-04-01+ remains the final holdout. Phase 7
neither needs nor can reach either.

## 7. 2025-H2 is not a Phase-7 period

Blocked outright (`NOT_PHASE7`), with and without the unlock. It was spent as
Phase-3 validation and has no MBP-1 file in any case.

## 8. Raw DBN archives blocked

`assert_path_allowed` refuses any `.dbn` / `.dbn.zst`, so the
`NQ_HOLDOUT/GLBX-…` archives on the drive are unreachable by construction.

## 9. Phase-7 module created

    src/nqr/p7/holdout7.py    period guard: one unlock, scoped to 2025-H1; 2026 unreachable
    src/nqr/p7/cache7.py      causal MBP-1 merger -> per-second book cache
    src/nqr/p7/features7.py   the 40 registered causal features
    src/nqr/p7/dataset7.py    5-second decision dataset, both R labels
    src/nqr/p7/model7.py      2 families, 12 configurations, 2021-only thresholds
    src/nqr/p7/backtest7.py   strategy, matched controls, runtime causality assertions
    strategies/orderbook_state/   specs, results, reports, diagnostics

Execution, first passage and the ATR are **imported read-only** from the frozen
Phase-1/2/4/5 code. Phase 7 adds no execution model and no risk machinery.

## 10. Pre-registration completed before any outcome

Written and fixed before the first Phase-7 label existed:

* `MBP1_SCHEMA_AUDIT.md` — what MBP-1 contains and, explicitly, what it does not
  (no depth beyond `_00`, no order IDs, no queue position, no hidden liquidity);
  the event-ordering audit; the book-state semantics; the data-quality check.
* `FEATURE_REGISTRY.md` — 40 features, the hard cap exactly reached, with every
  formula stated and the three ablation groups fixed.
* `SEARCH_BUDGET.md` — the 12 configurations enumerated by name, the two model
  families fully specified, and every gate for 2022, 2023, 2024 and 2025-H1.
* `PHASE7_SPEC.md` — the complete a-priori specification, including the
  production-training procedure to be used **if** 2025-H1 is ever earned, decided
  now so it cannot be chosen on performance.

## 11. The Phase-6 lesson is enforced in code

Phase 6 closed on a control-causality defect: 44.1 % of Phase-5's matched
controls entered **before** the signal that gave them their direction. Phase 7
does not rely on remembering that. `backtest7.assert_control_causality` raises
`ControlCausalityViolation` and **fails the run** if any control's entry is not
strictly after its own decision, if any same-day control decides before its
signal, or if any cross-day control lands on the signal's own day. The assertion
is itself unit tested.
