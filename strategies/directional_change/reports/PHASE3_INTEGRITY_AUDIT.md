# PHASE3_INTEGRITY_AUDIT.md

Generated 2026-08-21T03:35:45.421104+00:00 by `scripts/p3_11_integrity.py`.

**Phase-3 frozen id:** `dcevent-1.0.0.impl3+d33e5d5d116f1adb`

## Required verifications

| check | status | detail |
|---|---|---|
| Phase-1 + Phase-2 integrity check still passes | ✅ | RESULT: ALL CHECKS PASSED |
| Phase-1 frozen id unchanged | ✅ | fastslow-1.0.0+5980044a44eebf7b |
| Phase-2 frozen id unchanged | ✅ | impexh-1.0.0.impl2+48c76a0e68b88947 |
| all T9 source parquet files unmodified | ✅ | 20 files |
| loader refuses 2025-01 (sealed 2025-H1) | ✅ |  |
| loader refuses 2025-02 (sealed 2025-H1) | ✅ |  |
| loader refuses 2025-03 (sealed 2025-H1) | ✅ |  |
| loader refuses 2025-04 (sealed 2025-H1) | ✅ |  |
| loader refuses 2025-05 (sealed 2025-H1) | ✅ |  |
| loader refuses 2025-06 (sealed 2025-H1) | ✅ |  |
| loader refuses 2026-01 (2026 final holdout) | ✅ |  |
| loader refuses 2026-06 (2026 final holdout) | ✅ |  |
| file guard refuses 2025_H1.parquet even with validation unlocked | ✅ |  |
| file guard refuses 2026_H1.parquet even with validation unlocked | ✅ |  |
| Phase-3 validation cache holds only 2025-07..2025-12 | ✅ | months=['2025-07', '2025-08', '2025-09', '2025-10', '2025-11', '2025-12'] |
| events_engine_audit/daily.parquet avoids sealed windows | ✅ | 2021-01-05..2023-12-29 |
| events_engine_audit/events.parquet avoids sealed windows | ✅ | 2021-01-05..2023-12-29 |
| events_val2025h2/daily.parquet avoids sealed windows | ✅ | 2025-07-02..2025-12-31 |
| events_val2025h2/events.parquet avoids sealed windows | ✅ | 2025-07-02..2025-12-31 |
| run_dev/daily.parquet avoids sealed windows | ✅ | 2021-01-05..2023-12-29 |
| run_dev/trades_DC_A.parquet avoids sealed windows | ✅ | 2021-01-05..2023-12-29 |
| run_dev/trades_DC_B.parquet avoids sealed windows | ✅ | 2021-01-05..2023-12-29 |
| run_dev/trades_DC_C.parquet avoids sealed windows | ✅ | 2021-01-05..2023-12-29 |
| run_diag2024/daily.parquet avoids sealed windows | ✅ | 2024-01-02..2024-12-31 |
| run_diag2024/trades_DC_A.parquet avoids sealed windows | ✅ | 2024-01-02..2024-12-31 |
| run_diag2024/trades_DC_B.parquet avoids sealed windows | ✅ | 2024-01-02..2024-12-31 |
| run_diag2024/trades_DC_C.parquet avoids sealed windows | ✅ | 2024-01-02..2024-12-31 |
| run_val2025h2/daily.parquet avoids sealed windows | ✅ | 2025-07-02..2025-12-31 |
| run_val2025h2/trades_DC_A.parquet avoids sealed windows | ✅ | 2025-07-02..2025-12-31 |
| run_val2025h2/trades_DC_B.parquet avoids sealed windows | ✅ | 2025-07-02..2025-12-31 |
| run_val2025h2/trades_DC_C.parquet avoids sealed windows | ✅ | 2025-07-02..2025-12-31 |
| Phase-3 frozen manifest matches disk | ✅ | dcevent-1.0.0.impl3+d33e5d5d116f1adb |
| pre-freeze audit recorded event geometry only | ✅ |  |
| validation produced after the freeze | ✅ |  |

## The ten required properties

| # | property | how it is guaranteed |
|---|---|---|
| 1 | Phase 1 unchanged | frozen manifest re-hashed; id `fastslow-1.0.0+5980044a44eebf7b` |
| 2 | Phase 2 unchanged | frozen manifest re-hashed; id `impexh-1.0.0.impl2+48c76a0e68b88947` |
| 3 | source T9 files unchanged | every one of the 20 parquet files has an mtime predating this project |
| 4 | 2025-H1 never accessed | `nqr.p3.holdout3` has **no unlock path** for it; the month loader and the file guard both refuse it even while validation is unlocked; the validation cache builder reads `2025_H2.parquet` and asserts the H1 file is blocked before it starts |
| 5 | 2026 never accessed | identical treatment; no unlock path exists |
| 6 | spec frozen before outcomes | the pre-freeze audit recorded **event geometry only** (counts, theta scale, causality); no win rate, expectancy or P&L existed before the freeze |
| 7 | no future data in features | VU is the ATR of *completed* minutes; the DC engine confirms only at `conf_idx > ext_idx`; truncation and future-tampering tests both hold |
| 8 | no P&L-based parameter selection | theta stayed at the brief's `0.50 x VU`; the theta grid is a post-baseline diagnostic that cannot alter the baseline |
| 9 | correct event-time chronology | every cache sorted by `(ts_event, source row number)`; entries are the first print >= signal + 250 ms; first passage walks raw prints |
| 10 | validation generated only after the freeze | file mtime compared against the freeze timestamp |

## Implementation-version history

| version | change | effect on P&L |
|---|---|---|
| `impl1` | initial freeze | — (crashed while serialising; **no P&L was ever observed**) |
| `impl2` | fixed a polars schema-inference crash: skipped rows omitted the target columns, so an all-null prefix was typed `Null` and a real int64 timestamp could not be appended. Rows now carry an identical key set with explicit dtypes. | none — the crash happened at the write step |
| `impl3` | fixed an inverted sign on the `entry_slippage` / `signal_to_entry_pts` diagnostic columns, which reported FAVOURABLE slippage as positive instead of the project-wide ADVERSE-positive convention. | **none — verified byte-identical**: dev and 2024 trade fingerprints matched exactly before and after |

Each fix was documented, given a regression test, bumped the implementation
version, and forced a full rerun. **No strategy rule was changed at any point.**

RESULT: **ALL CHECKS PASSED**
