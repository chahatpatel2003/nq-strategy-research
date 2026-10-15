# DIAG_2025H2_CONTAMINATED — Phase 4

# CONTAMINATED DIAGNOSTIC — NOT VALIDATION

*Frozen production strategy `B_tree:depth=3` top20, tau = 0.017941 · frozen id `statedisc-1.0.0+c147134184dfb32d`*

Period **2025-07-01 … 2025-12-31**. 2025-H2 was consumed as Phase-3 fresh validation. It may not select features, models, thresholds,
directions, sessions, stop sizes or strategies, and it did not: the production
strategy was frozen as `statedisc-1.0.0+c147134184dfb32d` **before** this ran, and it is
unchanged after.

## Result, 09:30–11:30, 1R, 1.0 pt round trip

| | |
|---|---|
| trading days | 128 |
| executed trades | 18,000 (140.6/day) |
| win rate | 0.4933 |
| **net expectancy** | **-0.1745 R** |
| profit factor | 0.762 |
| total | -3,140 R |
| profitable days | 5.5% |
| gross expectancy (0.0 pt) | -0.0160 R |

## Against matched random entries

| statistic | strategy | matched control | Δ | 95 % day-block CI |
|---|---:|---:|---:|---|
| expectancy (R) | -0.1745 | -0.1831 | +0.0086 | [-0.0033, +0.0210] |
| win rate | 0.4933 | 0.4882 | +0.0051 | [-0.0008, +0.0113] |

Both intervals contain zero.

## Gates, applied to 2025

| gate | value | result |
|---|---|:---:|
| 1 — frequency ≥ 100 trades | 18,000 | PASS |
| 2 — net expectancy > 0 R | -0.1745 R | **FAIL** |
| 3 — profit factor > 1.10 | 0.762 | **FAIL** |
| 4 — raw WR > 50 % *(preference)* | 0.4933 | **FAIL** |
| 5 — ΔE[R] vs control, CI lower > 0 | +0.0086, CI [-0.0033, +0.0210] | **FAIL** |
| 6 — ΔWR vs control, CI lower > 0 | +0.0051, CI [-0.0008, +0.0113] | **FAIL** |
| 7 — profit concentration | total -3,140 R, ex-best-week -3,105 R | **FAIL** |

**1 of 7 gates met on 2025.** These are the 2026-Q1 gates applied to a development/diagnostic period; they are shown to make the shortfall concrete, not because this period is validation.

## The 2025-H1 seal held

This diagnostic reads **`2025_H2.parquet` only**. `2025_H1.parquet` is refused unconditionally by `nqr.p4.holdout4` — there is no unlock path for it — and the build script asserts that refusal before opening anything. The DuckDB scan additionally carries a trading-date predicate of `>= 2025-07-01`, and `p4_09_integrity.py` confirms the resulting tick cache contains no month from 2025-01 to 2025-06.

### Nothing changed after seeing this

The frozen id before this diagnostic and after it is the same:
`statedisc-1.0.0+c147134184dfb32d`. `scripts/p4_09_integrity.py` re-verifies it.
