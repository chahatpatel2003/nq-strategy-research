# ENTRY_QUALITY_DIAGNOSTICS.md — Phase 6

# DIAGNOSTIC ONLY — POST-HOC — REQUIRES NEW UNTOUCHED DATA

*Context model: the FROZEN Phase-5 `r4p0:A_logit:top2`, τ = 0.179938, R = 4.0 × ATR14(1-min), 1R/1R, 60-minute hold.*

The candidate set was already rejected by the preregistered gates before any of
this was computed. Nothing here modified Phase 6. Cell counts are given so the
reader can discount for multiplicity.

## 1. Time within context (5 cells)

Measured on `CONTROL_RANDOM`, so it is not confounded by any mechanic's own
selection.

| wait after activation | n | WR | gross E[R] | net E[R] | PF(R) | avg MAE (pt) |
|---|---:|---:|---:|---:|---:|---:|
| 0-5 min | 1,278 | 0.5603 | +0.1050 | +0.0770 | 1.217 | 27.65 |
| 5-10 | 1,025 | 0.5522 | +0.0997 | +0.0701 | 1.192 | 27.32 |
| 10-15 | 767 | 0.5567 | +0.1016 | +0.0716 | 1.195 | 27.38 |
| 15-20 | 596 | 0.5403 | +0.0925 | +0.0637 | 1.173 | 28.00 |
| 20+ | 818 | 0.5379 | +0.0991 | +0.0683 | 1.177 | 25.71 |

**Essentially flat, with a mild decline.** The first five minutes are the best
cell (+0.0770 R) and 15–20 minutes the worst
(+0.0637 R). Whatever the context is worth, it is worth
slightly *more* early — which is why every delay mechanic loses to random and to
immediate entry.

## 2. Half-hour bucket × direction (8 cells)

| bucket | side | n | WR | gross E[R] | net E[R] | PF(R) |
|---|---|---:|---:|---:|---:|---:|
| 09:30-10:00 | LONG | 54 | 0.6481 | +0.2830 | +0.2526 | 1.811 |
| 09:30-10:00 | SHORT | 898 | 0.5367 | +0.0771 | +0.0348 | 1.073 |
| 10:00-10:30 | LONG | 97 | 0.6186 | +0.0358 | +0.0179 | 1.065 |
| 10:00-10:30 | SHORT | 306 | 0.6340 | +0.1983 | +0.1723 | 1.572 |
| 10:30-11:00 | LONG | 449 | 0.5546 | +0.1415 | +0.1148 | 1.405 |
| 10:30-11:00 | SHORT | 596 | 0.5805 | +0.1220 | +0.0968 | 1.269 |
| 11:00-11:30 | LONG | 549 | 0.6412 | +0.2861 | +0.2554 | 2.115 |
| 11:00-11:30 | SHORT | 1,535 | 0.4906 | +0.0055 | -0.0194 | 0.952 |

The spread across 8 cells is very wide — **11:00–11:30 LONG at
+0.2554 R
and PF(R) 2.12
against 11:00–11:30 SHORT at
-0.0194 R** —
and the short side supplies most of the volume. This is exactly the kind of
subgroup the brief forbids promoting, and it is not promoted. See
`FUTURE_HYPOTHESES.md` H6-3.

## 3. Entry quality — what each mechanic buys

| method | n | fill/context | median wait | fill improvement (R) | pre-entry MAE (R) | pre-entry MFE (R) | median bucket left (min) | trade MFE (pt) | trade MAE (pt) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| E1 | 369 | 0.74 | 5.0m | +0.0372 | 0.4901 | 0.4428 | 21.0 | 29.01 | 27.94 |
| E2 | 328 | 0.65 | 10.0m | +0.0733 | 0.6965 | 0.6278 | 18.0 | 28.02 | 27.88 |
| E3 | 323 | 0.64 | 1.6m | +0.2573 | 0.2786 | 0.2789 | 21.2 | 29.09 | 26.42 |
| E4 | 227 | 0.45 | 4.4m | +0.5036 | 0.5296 | 0.3821 | 20.9 | 26.38 | 26.66 |
| E5 | 321 | 0.64 | 2.1m | +0.2542 | 0.3837 | 0.2775 | 21.0 | 28.65 | 26.64 |
| E6 | 221 | 0.44 | 4.6m | +0.5084 | 0.6346 | 0.3844 | 21.1 | 26.32 | 26.81 |
| CONTROL_IMMEDIATE | 409 | 0.81 | 0.0m | +0.0000 | 0.0000 | 0.0000 | 22.0 | 29.42 | 27.76 |

The `pre-entry MAE` column is the whole story: waiting costs more adverse
excursion than the price improvement it buys, at every depth. Full decomposition
in `ENTRY_MECHANICS.md`.
