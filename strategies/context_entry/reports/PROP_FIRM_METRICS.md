# PROP_FIRM_METRICS.md — Phase 6

*Context model: the FROZEN Phase-5 `r4p0:A_logit:top2`, τ = 0.179938, R = 4.0 × ATR14(1-min), 1R/1R, 60-minute hold.*

> **Phase 6 FAILED before validation.** No entry mechanic passed the
> preregistered gates and the causal context does not beat non-context.
> 2026-Q1 was never opened.

Pooled 2021–2025-H2: **1145 trading days, 502 contexts** (0.44/day of a
possible 4). 09:30–11:30 ET, 1R/1R, 1.0 NQ point round-trip friction. No dollar
sizing. Profit factor is reported in **R units** — `PF(R)` — per the Phase-5
correction; the points figure is shown alongside and never used for a gate.

| metric | E1 | E2 | E3 | E4 | E5 | E6 | CONTROL_IMMEDIATE | CONTROL_RANDOM |
|---|---|---|---|---|---|---|---|---|
| contexts/day | 0.44 | 0.44 | 0.44 | 0.44 | 0.44 | 0.44 | 0.44 | 0.44 |
| entry fill rate per context | 0.74 | 0.65 | 0.64 | 0.45 | 0.64 | 0.44 | 0.81 | 8.93 |
| total trades | 369 | 328 | 323 | 227 | 321 | 221 | 409 | 4,484 |
| trades / day | 0.322 | 0.286 | 0.282 | 0.198 | 0.280 | 0.193 | 0.357 | 3.916 |
| median trades / day | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| % 0-trade days | 73.6% | 75.7% | 75.8% | 82.5% | 76.2% | 83.0% | 70.8% | 70.8% |
| % 1-trade days | 21.0% | 20.1% | 20.4% | 15.3% | 19.7% | 14.9% | 23.2% | 0.6% |
| % 2-trade days | 4.8% | 4.0% | 3.5% | 2.0% | 3.8% | 1.9% | 5.3% | 0.9% |
| % 3+-trade days | 0.5% | 0.2% | 0.3% | 0.2% | 0.3% | 0.2% | 0.6% | 27.7% |
| win rate | 0.5149 | 0.5091 | 0.5387 | 0.4890 | 0.5358 | 0.4887 | 0.5550 | 0.5511 |
| WR 95 % CI low | 0.4640 | 0.4553 | 0.4842 | 0.4247 | 0.4812 | 0.4235 | 0.5066 | 0.5365 |
| WR 95 % CI high | 0.5655 | 0.5628 | 0.5923 | 0.5537 | 0.5896 | 0.5542 | 0.6024 | 0.5656 |
| net expectancy (R) | +0.0270 | +0.0043 | +0.0641 | -0.0197 | +0.0464 | -0.0219 | +0.0680 | +0.0711 |
| **PF(R)** | 1.067 | 1.010 | 1.161 | 0.957 | 1.115 | 0.952 | 1.181 | 1.194 |
| PF (points) | 1.147 | 1.017 | 1.167 | 0.957 | 1.117 | 0.963 | 1.240 | 1.217 |
| R / day | +0.0087 | +0.0012 | +0.0181 | -0.0039 | +0.0130 | -0.0042 | +0.0243 | +0.2786 |
| median R / day | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| profitable-day % | 49.0% | 47.8% | 50.9% | 47.0% | 51.8% | 47.7% | 53.6% | 52.7% |
| max daily loss (R) | -2.11 | -2.07 | -2.12 | -2.11 | -2.11 | -2.11 | -2.12 | -30.44 |
| 95th pct daily loss (R) | -1.06 | -1.06 | -1.06 | -1.06 | -1.07 | -1.07 | -1.06 | -10.53 |
| max drawdown (R) | 17.77 | 21.85 | 12.41 | 14.06 | 14.22 | 17.81 | 11.08 | 132.38 |
| longest losing streak | 7 | 7 | 7 | 7 | 5 | 7 | 6 | 43 |
| longest winning streak | 9 | 5 | 11 | 7 | 11 | 10 | 8 | 55 |
| drawdown recovery (days) | ∞ | ∞ | 47 | ∞ | ∞ | ∞ | 107 | 71 |
| average hold (min) | 30.0 | 30.6 | 28.4 | 24.0 | 28.6 | 24.7 | 29.5 | 32.6 |
| median hold (min) | 24.8 | 28.3 | 23.4 | 18.4 | 22.8 | 19.2 | 23.1 | 29.8 |
| avg adverse excursion (pt) | 27.9 | 27.9 | 26.4 | 26.7 | 26.6 | 26.8 | 27.8 | 27.2 |
| avg favourable excursion (pt) | 29.0 | 28.0 | 29.1 | 26.4 | 28.7 | 26.3 | 29.4 | 29.5 |
| average R (pt) | 44.7 | 43.7 | 43.5 | 40.5 | 43.1 | 40.3 | 44.8 | 44.7 |
| TP | 144 | 125 | 141 | 97 | 133 | 96 | 168 | 1772 |
| SL | 128 | 117 | 112 | 93 | 114 | 91 | 137 | 1373 |
| TIMEOUT | 97 | 86 | 70 | 37 | 74 | 34 | 104 | 1339 |

## Reading it

`CONTROL_RANDOM` is not a strategy — it is up to 10 independent entries per
context and is not subject to the one-position rule, so its trade count and
per-day figures are not comparable to the mechanics. Its **expectancy, win rate
and PF(R)** are, and those are the numbers the gates use.

Every mechanic is far below any usable frequency:
**0.32–0.32
trades per day** with **74%+
zero-trade days**, because a top-2 % context fires in about one bucket in nine and
the mechanics then decline 26–56 % of those.

Holds are 23–28 minutes
and average R is 44 points, both inherited
unchanged from the frozen Phase-5 geometry.
