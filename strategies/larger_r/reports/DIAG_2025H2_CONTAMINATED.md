# DIAG_2025H2_CONTAMINATED — Phase 5

# CONTAMINATED DIAGNOSTIC — NOT VALIDATION

*Candidate `r4p0:A_logit:top2` — R = 4.0 × ATR14(1-min), 60-second clock, 60-minute hold, τ = 0.179938*

> **This candidate was REJECTED** at the 2023 internal out-of-sample test
> (`ITEST_2023.md`). It was never frozen and 2026-Q1 was never opened.

Period **2025-07-01 … 2025-12-31**. 2025-H2 was consumed as Phase-3 fresh validation. It may not select anything, and it did not: the
candidate had **already been rejected** on 2023 before this ran. It is reported
because it is informative about *how* the candidate fails, not because it can
change the outcome.

## Result, 09:30–11:30, 1R, 1.0 pt round trip

| | |
|---|---|
| trading days | 128 |
| executed trades | 56 (0.44/day) |
| win rate | 0.5357 (95 % [0.4070, 0.6598]) |
| gross expectancy (0.0 pt) | +0.0558 R |
| net expectancy (1.0 pt) | **+0.0292 R** |
| profit factor (R) | 1.076 |
| median hold | 26.0 min |
| max drawdown | 7.91 R |

## Against matched random

| statistic | strategy | matched control | Δ | 95 % day-block CI |
|---|---:|---:|---:|---|
| expectancy (R) | +0.0292 | +0.0395 | -0.0103 | [-0.1992, +0.1595] |
| win rate | 0.5357 | 0.5336 | +0.0021 | [-0.0983, +0.0935] |

The interval contains zero. Absolute performance is positive, the advantage over
a random entry in the same context is not — the same pattern as every other
period.

## The 2025-H1 seal held

This diagnostic reads **`2025_H2.parquet` only**. `2025_H1.parquet` is refused unconditionally by `nqr.p5.holdout5` — there is no unlock path for it — and the tick cache it draws on contains no month between 2025-01 and 2025-06. `p5_09_integrity.py` re-checks both.

### Nothing changed after seeing this

The candidate was rejected before this diagnostic ran and remains rejected.
2026-Q1 remains sealed.
