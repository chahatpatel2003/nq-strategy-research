# ITEST_2023.md — Phase 4 internal out-of-sample test

*Frozen production strategy `B_tree:depth=3` top20, tau = 0.017941 · frozen id `statedisc-1.0.0+c147134184dfb32d`*

2023 was **not** consulted during model fitting, threshold calibration or
configuration selection. It was scored once, after `B_tree:depth=3:top20` had
already been chosen on 2022, and it could not change that choice.

## Result, 09:30–11:30, 1R, 1.0 pt round trip

| | |
|---|---|
| trading days | 254 |
| executed trades | 36,145 (142.3/day) |
| win rate | 0.4826 (Wilson 95 % [0.4774, 0.4877]) |
| **net expectancy** | **-0.2449 R** |
| profit factor | 0.671 |
| total | -8,853 R |
| R per day | -34.85 |
| profitable days | 2.0% |
| median hold | 0.39 min |
| max drawdown | 8,859 R |
| longest losing streak | 131 |

## Against matched random entries

| statistic | strategy | matched control | Δ | 95 % day-block CI |
|---|---:|---:|---:|---|
| expectancy (R) | -0.2449 | -0.2475 | +0.0026 | [-0.0061, +0.0113] |
| win rate | 0.4826 | 0.4799 | +0.0026 | [-0.0017, +0.0070] |

**Both intervals contain zero.** On the year it had never seen, the strategy is
statistically indistinguishable from random entries matched on day, hour,
direction and volatility — while losing 0.24 R per trade
after friction.

The friction sweep is the sharper statement: at **0.0 pt** friction 2023
expectancy is -0.0298 R.
There is no gross edge here for costs to erode.

## Gates, applied to 2023

| gate | value | result |
|---|---|:---:|
| 1 — frequency ≥ 100 trades | 36,145 | PASS |
| 2 — net expectancy > 0 R | -0.2449 R | **FAIL** |
| 3 — profit factor > 1.10 | 0.671 | **FAIL** |
| 4 — raw WR > 50 % *(preference)* | 0.4826 | **FAIL** |
| 5 — ΔE[R] vs control, CI lower > 0 | +0.0026, CI [-0.0061, +0.0113] | **FAIL** |
| 6 — ΔWR vs control, CI lower > 0 | +0.0026, CI [-0.0017, +0.0070] | **FAIL** |
| 7 — profit concentration | total -8,853 R, ex-best-week -8,785 R | **FAIL** |

**1 of 7 gates met on 2023.** These are the 2026-Q1 gates applied to a development/diagnostic period; they are shown to make the shortfall concrete, not because this period is validation.

## Verdict of the development stage

The single production candidate permitted by the budget fails the hard gates on
untouched development data by a wide margin, in the same direction and by a
similar amount as on its own training year. Phase 4's development stage has
already answered the research question in the negative.
