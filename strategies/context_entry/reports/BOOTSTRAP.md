# BOOTSTRAP.md — Phase 6 uncertainty

*Context model: the FROZEN Phase-5 `r4p0:A_logit:top2`, τ = 0.179938, R = 4.0 × ATR14(1-min), 1R/1R, 60-minute hold.*

> **Phase 6 FAILED before validation.** No entry mechanic passed the
> preregistered gates and the causal context does not beat non-context.
> 2026-Q1 was never opened.

Contexts cluster by day and a day can carry up to four of them, so no interval
here treats a trade or a context as independent. Every figure is a **trading-day
block bootstrap**: 10 000 resamples of whole trading days, with the candidate and
its control resampled **together** so the pairing survives.

## Primary gate G4 — each mechanic minus CONTROL_RANDOM

| method | n | Δ expectancy (R) | 95 % CI | verdict | Δ win rate | 95 % CI |
|---|---:|---:|---|---|---:|---|
| E1 | 369 | -0.0442 | [-0.1064, +0.0173] | contains 0 | -0.0362 | [-0.0712, -0.0012] |
| E2 | 328 | -0.0669 | [-0.1350, -0.0006] | excludes 0 (worse) | -0.0419 | [-0.0814, -0.0026] |
| E3 | 323 | -0.0070 | [-0.0846, +0.0712] | contains 0 | -0.0124 | [-0.0555, +0.0307] |
| E4 | 227 | -0.0909 | [-0.1960, +0.0110] | contains 0 | -0.0621 | [-0.1187, -0.0064] |
| E5 | 321 | -0.0247 | [-0.1002, +0.0511] | contains 0 | -0.0152 | [-0.0575, +0.0271] |
| E6 | 221 | -0.0931 | [-0.1982, +0.0099] | contains 0 | -0.0624 | [-0.1197, -0.0057] |
| CONTROL_IMMEDIATE | 409 | -0.0032 | [-0.0728, +0.0671] | contains 0 | +0.0039 | [-0.0340, +0.0418] |

Not one interval lies above zero. **E2's lies entirely below it**: a fixed
10-minute delay is significantly *worse* than entering at a random minute.

## Context vs non-context

| statistic | difference | 95 % CI | verdict |
|---|---:|---|---|
| expectancy (R) | +0.0752 | [-0.0234, +0.1721] | contains 0 |
| win rate | +0.0399 | [-0.0137, +0.0925] | contains 0 |

Pooled over 334 trading days.

## Why day blocks matter here

The Phase-6 books are small — 221–409 trades per
mechanic across five years — and up to four contexts share a day and therefore
share that day's regime. An i.i.d. interval on 409 trades would be
roughly half the width of the day-block interval and would have declared several
of these differences significant. It would have been wrong.
