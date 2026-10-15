# ITEST_2023.md — Phase 5 internal out-of-sample test

*Candidate `r4p0:A_logit:top2` — R = 4.0 × ATR14(1-min), 60-second clock, 60-minute hold, τ = 0.179938 (top 2 % of the edge score on 2021)*

2023 took no part in fitting, baseline estimation, threshold calibration or
configuration selection. It was scored once, after `r4p0:A_logit:top2` had already been
chosen on 2022.

## Gate F — the preregistered prerequisite for freezing

| requirement | value | result |
|---|---|:---:|
| net expectancy > 0 R | -0.0379 R | **FAIL** |
| profit factor > 1.05 | 0.911 in R units (1.256 in points) | **FAIL** |
| advantage over matched random > 0 | -0.1307 R, CI [-0.2471, -0.0017] | **FAIL** |
| ≥ 100 executed trades | 93 | **FAIL** |

**All four fail.** Per `PHASE5_SEARCH_BUDGET.md` §6 this ends Phase 5:
the candidate is not frozen, the contaminated diagnostics cannot revive it, and
**2026-Q1 stays sealed**.

## The numbers

| | |
|---|---|
| trading days | 254 |
| executed trades | 93 (0.37/day) |
| win rate | 0.4946 (Wilson 95 % [0.3953, 0.5944]) |
| **gross expectancy (0.0 pt)** | **-0.0049 R** |
| **net expectancy (1.0 pt)** | **-0.0379 R** |
| profit factor (R units) | 0.911 |
| median hold | 25.5 min |
| average R | 38.1 pt |
| TP / SL / TIMEOUT | 33 / 35 / 25 |
| max drawdown | 7.9 R |

## Against matched random

| statistic | strategy | matched control | Δ | 95 % day-block CI |
|---|---:|---:|---:|---|
| expectancy (R) | -0.0379 | +0.0928 | -0.1307 | [-0.2471, -0.0017] |
| win rate | 0.4946 | 0.5501 | -0.0555 | [-0.1221, +0.0163] |

The expectancy interval lies **entirely below zero**. On the one development year
it had never seen, the strategy is not merely no better than random entries
matched on day, time bucket and direction — it is **significantly worse**.

Note what the control itself earned: **+0.0928 R**.
The days, half-hours and directions the model selected were profitable. The
specific minutes it chose inside them were not.

## A reporting note on profit factor

`metrics4.summarize` computes profit factor on **points** while expectancy is in
**R**. With a volatility-scaled R those can disagree in sign — here PF(points) is
1.256 while PF(R) is 0.911 — because a
large-R trade contributes more points but the same ±1R. Phase 5 sizes risk per
trade, so **PF in R units is the figure the gates mean**, and it is the one used
above. Both are reported everywhere.
