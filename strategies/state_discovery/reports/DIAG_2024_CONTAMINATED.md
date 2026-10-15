# DIAG_2024_CONTAMINATED — Phase 4

# CONTAMINATED DIAGNOSTIC — NOT VALIDATION

*Frozen production strategy `B_tree:depth=3` top20, tau = 0.017941 · frozen id `statedisc-1.0.0+c147134184dfb32d`*

Period **2024-01-01 … 2024-12-31**. 2024 was consumed as Phase-1 and Phase-2 validation. It may not select features, models, thresholds,
directions, sessions, stop sizes or strategies, and it did not: the production
strategy was frozen as `statedisc-1.0.0+c147134184dfb32d` **before** this ran, and it is
unchanged after.

## Result, 09:30–11:30, 1R, 1.0 pt round trip

| | |
|---|---|
| trading days | 255 |
| executed trades | 36,092 (141.5/day) |
| win rate | 0.4900 |
| **net expectancy** | **-0.1986 R** |
| profit factor | 0.729 |
| total | -7,169 R |
| profitable days | 7.1% |
| gross expectancy (0.0 pt) | -0.0185 R |

## Against matched random entries

| statistic | strategy | matched control | Δ | 95 % day-block CI |
|---|---:|---:|---:|---|
| expectancy (R) | -0.1986 | -0.2003 | +0.0017 | [-0.0062, +0.0099] |
| win rate | 0.4900 | 0.4880 | +0.0020 | [-0.0019, +0.0060] |

Both intervals contain zero.

## Gates, applied to 2024

| gate | value | result |
|---|---|:---:|
| 1 — frequency ≥ 100 trades | 36,092 | PASS |
| 2 — net expectancy > 0 R | -0.1986 R | **FAIL** |
| 3 — profit factor > 1.10 | 0.729 | **FAIL** |
| 4 — raw WR > 50 % *(preference)* | 0.4900 | **FAIL** |
| 5 — ΔE[R] vs control, CI lower > 0 | +0.0017, CI [-0.0062, +0.0099] | **FAIL** |
| 6 — ΔWR vs control, CI lower > 0 | +0.0020, CI [-0.0019, +0.0060] | **FAIL** |
| 7 — profit concentration | total -7,169 R, ex-best-week -7,158 R | **FAIL** |

**1 of 7 gates met on 2024.** These are the 2026-Q1 gates applied to a development/diagnostic period; they are shown to make the shortfall concrete, not because this period is validation.

### Nothing changed after seeing this

The frozen id before this diagnostic and after it is the same:
`statedisc-1.0.0+c147134184dfb32d`. `scripts/p4_09_integrity.py` re-verifies it.
