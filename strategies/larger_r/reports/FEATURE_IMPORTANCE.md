# FEATURE_IMPORTANCE.md — Phase 5

*Candidate `r4p0:A_logit:top2` — R = 4.0 × ATR14(1-min), 60-second clock, 60-minute hold, τ = 0.179938 (top 2 % of the edge score on 2021)*

> **This candidate was REJECTED.** It failed the preregistered Gate F on the
> 2023 internal out-of-sample test, so it was never frozen and 2026-Q1 was
> never opened. Everything below describes a rejected candidate.

The selected family was **A — elastic-net logistic regression** (C = 0.1,
l1_ratio = 0.5), fitted on 2021 with training-only standardisation, so the
coefficients below are directly comparable across features.
52 of 55 coefficients are non-zero; L1 eliminated
3 (`delta_accel`, `ret_norm_15`, `vel_15_norm`).

## Top 15 by |coefficient|

| feature | coefficient |
|---|---:|
| `dist_or30_lo_norm` | -0.34476 |
| `secs_since_open` | +0.33343 |
| `dist_open_norm` | +0.29186 |
| `dist_vwap_norm` | +0.12945 |
| `is_second_hour` | -0.12469 |
| `atr_pct_rank` | +0.11680 |
| `volume_ratio_60_300` | +0.10432 |
| `secs_since_low_300` | +0.10043 |
| `cum_delta_norm` | -0.09140 |
| `dist_low_1800_norm` | -0.09073 |
| `dist_or30_hi_norm` | +0.08926 |
| `dist_pdh_norm` | +0.08751 |
| `delta_per_vol_300` | -0.08270 |
| `rv_300_norm` | +0.08270 |
| `avg_trade_size_60` | -0.07980 |

## What the larger horizon actually selected

Phase 4's tree was dominated by **`atr1m` (39.7 %)** — a raw-points volatility
level, and a regime variable that did not generalise. At the 60-minute horizon
the picture is different and, on its face, healthier:

* **Session location dominates.** `dist_or30_lo_norm` (−0.345),
  `dist_open_norm` (+0.292), `dist_vwap_norm` (+0.129), `dist_or30_hi_norm`
  (+0.089), `dist_pdh_norm` (+0.088) — family 8, objective location, takes five
  of the top eleven slots.
* **Clock position is the second theme.** `secs_since_open` (+0.333) and
  `is_second_hour` (−0.125) are family 7. The model leans heavily on *when* in
  the session it is.
* **Volatility enters in its stationary form.** `atr_pct_rank` (+0.117), the
  trailing within-day percentile, is in the top six while the raw `atr1m` is
  **not in the top 15** at all. The elastic-net preferred the stationary
  companion — the opposite of Phase 4's choice, and the right one.

## Trade side / delta — still close to irrelevant

| feature | coefficient |
|---|---:|
| `delta_60_norm` | +0.04021 |
| `delta_300_norm` | +0.05319 |
| `delta_per_vol_60` | -0.01997 |
| `delta_per_vol_300` | -0.08270 |
| `cum_delta_norm` | -0.09140 |
| `delta_accel` | +0.00000 |

Mean |coefficient| for family 6 is **0.04791** against **0.05599** across all
55 — slightly *below* average, with `delta_accel` eliminated outright. In the
unconditional state diagnostics the delta quartiles are flat to four decimal
places (−0.0066 to −0.0132 R).

Phase 4 found family 6 contributed exactly zero at a 5-second clock and a
30-minute horizon. Phase 5 finds it contributes almost nothing at a 60-second
clock and a 60-minute horizon either. **Two independent horizons, same answer:
trades-derived order flow carries no usable directional information here.**
This says nothing about MBP-1 book data, which neither phase opened.
