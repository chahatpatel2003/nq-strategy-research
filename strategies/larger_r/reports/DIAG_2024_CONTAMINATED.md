# DIAG_2024_CONTAMINATED — Phase 5

# CONTAMINATED DIAGNOSTIC — NOT VALIDATION

*Candidate `r4p0:A_logit:top2` — R = 4.0 × ATR14(1-min), 60-second clock, 60-minute hold, τ = 0.179938*

> **This candidate was REJECTED** at the 2023 internal out-of-sample test
> (`ITEST_2023.md`). It was never frozen and 2026-Q1 was never opened.

Period **2024-01-01 … 2024-12-31**. 2024 was consumed as Phase-1 and Phase-2 validation. It may not select anything, and it did not: the
candidate had **already been rejected** on 2023 before this ran. It is reported
because it is informative about *how* the candidate fails, not because it can
change the outcome.

## Result, 09:30–11:30, 1R, 1.0 pt round trip

| | |
|---|---|
| trading days | 255 |
| executed trades | 83 (0.33/day) |
| win rate | 0.5542 (95 % [0.4473, 0.6564]) |
| gross expectancy (0.0 pt) | +0.1117 R |
| net expectancy (1.0 pt) | **+0.0826 R** |
| profit factor (R) | 1.241 |
| median hold | 29.5 min |
| max drawdown | 4.76 R |

## Against matched random

| statistic | strategy | matched control | Δ | 95 % day-block CI |
|---|---:|---:|---:|---|
| expectancy (R) | +0.0826 | +0.0791 | +0.0034 | [-0.1279, +0.1370] |
| win rate | 0.5542 | 0.5517 | +0.0025 | [-0.0735, +0.0793] |

The interval contains zero. Absolute performance is positive, the advantage over
a random entry in the same context is not — the same pattern as every other
period.

### Nothing changed after seeing this

The candidate was rejected before this diagnostic ran and remains rejected.
2026-Q1 remains sealed.
