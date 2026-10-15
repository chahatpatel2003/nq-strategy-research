# PHASE6_START_INTEGRITY.md

**Run:** 2026-08-20, before any Phase-6 code touched market content.

**Result: ALL CHECKS PASSED.** Phases 1–5 are unchanged, the source data is
unmodified, 2025-H1 has never been opened, MBP-1 has never been opened by any
phase since Phase 2's archived verification, and no 2026 market content exists
anywhere in the project.

---

## 1. Test suite

    python -m pytest tests -q   ->   335 passed

Same count as at the close of Phase 5 (218 from Phases 1–3, 66 from Phase 4,
51 from Phase 5).

## 2. Frozen identities — all four match

| phase | frozen id | files | drift |
|---|---|---:|---|
| 1 Fast-Slow | `fastslow-1.0.0+5980044a44eebf7b` | 14 | none |
| 2 Impulse exhaustion | `impexh-1.0.0.impl2+48c76a0e68b88947` | 15 | none |
| 3 Directional change | `dcevent-1.0.0.impl3+d33e5d5d116f1adb` | 14 | none |
| 4 Causal state discovery | `statedisc-1.0.0+c147134184dfb32d` | 14 | none |

Each manifest was re-hashed against disk file by file, and every phase's own
end-of-phase integrity script was re-run:

    scripts/07_integrity_check.py   ->  ALL CHECKS PASSED
    scripts/p2_09_integrity.py      ->  ALL CHECKS PASSED
    scripts/p3_11_integrity.py      ->  ALL CHECKS PASSED
    scripts/p4_09_integrity.py      ->  ALL CHECKS PASSED
    scripts/p5_09_integrity.py      ->  ALL CHECKS PASSED

## 3. Phase-5 artifacts

Phase 5 has **no frozen manifest of its own** — its candidate was rejected at
Gate F and never frozen, so there was nothing to freeze. Because Phase 6 reuses
its direction model, its R architecture and its label engine read-only,
`scripts/p6_00_fingerprint.py` records their hashes now so any later drift is
detectable:

    results/p5_artifact_manifest.json
    combined fingerprint  d0783a6638d88aec   (11 files)

covering `src/nqr/p5/*.py`, the Phase-5 spec / budget / registry / verdict, and
`production_model.pkl` + `development_meta.json`. `p6_09_integrity.py` re-checks
it, and also re-checks that `PHASE5_VERDICT.md` still records FAIL before
validation.

## 4. Source data unmodified

Every original T9 parquet still carries a modification time predating this
project — the marker Phase 1 froze. All 19 files (11 trades halves 2021_H1 …
2026_H1, 8 MBP-1 halves 2021_H1 … 2025_H1) pass. Nothing has ever been written
to the drive.

## 5. 2025-H1 remains sealed

Never opened by any phase, in any form. The Phase-6 guard
(`src/nqr/p6/holdout6.py`) refuses it with **no unlock path**:

| probe | result |
|---|---|
| `assert_date_allowed(2025-03-01)` | blocked — `SEALED_2025H1` |
| same, **with the 2026-Q1 unlock active** | still blocked |
| `assert_path_allowed("2025_H1.parquet")` | blocked unconditionally |
| `assert_range_allowed(2024-12-01, 2025-08-01)` | blocked — spans the seal |

There is exactly one unlock function in the module and it is named for 2026-Q1.

## 6. MBP-1 cannot be opened by Phase 6

`assert_path_allowed` refuses any path containing `mbp1` or `mbp-1`, and any raw
`.dbn` / `.dbn.zst` archive. Verified live for
`/Volumes/T9/nq data/raw/mbp1/2021_H1.parquet`, `/x/MBP-1/a.parquet`, `/x/a.dbn`
and `/x/glbx-mdp3-20260617.trades.dbn.zst`.

`p6_09_integrity.py` additionally asserts that **no Phase-6 module calls
`read_parquet` at all** — Phase 6 consumes only the Phase-5 dataset and the
frozen Phase-4 tick cache through their own guarded loaders.

## 7. No 2026 market content exists

| location | contents |
|---|---|
| `data_cache/p4_ticks/` | 2025-07 … 2025-12 only |
| `data_cache/p2_ticks/`, `ticks/` | 2021-01 … 2024-12 only |
| `strategies/larger_r/features/` | `split=dev`, `split=contam2024`, `split=contam2025h2` |
| `strategies/larger_r/results/` | five development runs, no `run_val2026q1` |
| `results/` | no `front_map_p5val.parquet`, no `front_map_p6val.parquet` |

No 2026 month in any cache. Neither Phase 4 nor Phase 5 spent the quarter.

## 8. 2026-Q1 untouched; April 2026 onward blocked

The only contact any phase has ever had with `2026_H1.parquet` is the Phase-4
**parquet-footer** read — row count, row-group count, first/last row-group
timestamps. **No row has ever been decoded.**

| probe | result |
|---|---|
| `assert_date_allowed(2026-02-01)` | blocked until the explicit unlock |
| `assert_date_allowed(2026-04-01)` | blocked — `SEALED_FINAL` |
| same, **with the 2026-Q1 unlock active** | still blocked |
| `assert_path_allowed("2026_H2.parquet")` | blocked unconditionally |
| `sql_window_guard(2026-01-01, 2026-12-31)` | raises before emitting any SQL |
| `sql_window_guard(2026-01-01, 2026-04-01)` | raises before emitting any SQL |

This matters because **`2026_H1.parquet` physically contains April, May and June
2026** (47,081,888 rows, running to 2026-06-17). `sql_window_guard` is the only
sanctioned way to read it and it refuses at **query-construction time**, not
after a scan, so an April+ row cannot be produced even transiently. Row-group
statistics are present, so an allowed Q1 predicate also prunes at file level.

The Phase-6 unlock phrase is distinct from Phase 5's — passing
`..._FOR_PHASE5_VALIDATION` to the Phase-6 guard raises. Verified live.

## 9. Phase-6 module created

    src/nqr/p6/holdout6.py    period guard, own unlock phrase, MBP-1 and .dbn refused
    src/nqr/p6/context6.py    causal context activation + the six entry mechanics
    src/nqr/p6/backtest6.py   books, controls, Phase-5 trade geometry reused
    strategies/context_entry/ specs, results, reports, diagnostics

The 55 causal features, the direction model, R, the bracket, the horizon, the
timeout rule and the execution model are all **imported read-only** from the
frozen Phase-4/Phase-5 code. Phase 6 adds no feature and no risk parameter;
`p6_09_integrity.py` asserts `FEATURE_NAMES` is still 55 and that Phase 6 defines
no `R_MULTS` of its own.

## 10. Period roles for Phase 6

The Phase-6 hypothesis was generated from Phase-5 diagnostics, so the split names
inherited from earlier phases would be actively misleading here. `holdout6.role_of`
returns the Phase-6 reading:

| period | Phase-6 role |
|---|---|
| 2021 | DEVELOPMENT — **also in-sample for the context model** |
| 2022 | DEVELOPMENT |
| 2023 | DEVELOPMENT (contaminated: Phase 5 rejected its candidate here) |
| 2024 | DEVELOPMENT (contaminated) |
| 2025-H2 | DEVELOPMENT (contaminated) |
| **2025-H1** | **FORBIDDEN** |
| **2026-Q1** | **THE ONLY FRESH VALIDATION** |
| **2026-04-01+** | **FORBIDDEN** |

Nothing in Phase 6 calls 2023, 2024 or 2025-H2 out-of-sample.

## 11. Pre-registration completed before any outcome

* `strategies/context_entry/PHASE6_SEARCH_BUDGET.md` — six entry mechanics, the
  frozen inherited geometry, the four development gates and the explicit
  "no least-bad candidate" rule, written before any mechanic had an outcome
  computed against it.
* `strategies/context_entry/CONTEXT_CAUSALITY_AUDIT.md` — the required audit of
  the Phase-5 decomposition, and the causal context activation rule that replaced
  it, written before any entry mechanic was evaluated.
