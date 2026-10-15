# PROP_FIRM_METRICS.md — Phase 5

*Candidate `r4p0:A_logit:top2` — R = 4.0 × ATR14(1-min), 60-second clock, 60-minute hold, τ = 0.179938*

> **This candidate was REJECTED** at the 2023 internal out-of-sample test
> (`ITEST_2023.md`). It was never frozen and 2026-Q1 was never opened.

09:30–11:30 ET, 1R target / 1R stop, 1.0 NQ point round-trip friction.
No dollar position sizing is applied.

| metric | 2021 train | 2022 selection | 2023 internal OOS | 2024 CONTAMINATED | 2025-H2 CONTAMINATED |
|---|---|---|---|---|---|
| total trades | 105 | 128 | 93 | 83 | 56 |
| trades / day | 0.41 | 0.50 | 0.37 | 0.33 | 0.44 |
| median trades / day | 0 | 0 | 0 | 0 | 0 |
| % 0-trade days | 69.3% | 65.4% | 74.8% | 74.5% | 69.5% |
| % 1-trade days | 22.0% | 22.8% | 15.7% | 20.0% | 19.5% |
| % 2-trade days | 7.1% | 9.4% | 7.5% | 3.9% | 8.6% |
| % 3+-trade days | 1.6% | 2.4% | 2.0% | 1.6% | 2.3% |
| 09:30–10:30 trades | 42 | 44 | 23 | 26 | 15 |
| 10:30–11:30 trades | 63 | 84 | 70 | 57 | 41 |
| win rate | 0.6190 | 0.5625 | 0.4946 | 0.5542 | 0.5357 |
| WR 95 % CI low | 0.5235 | 0.4760 | 0.3953 | 0.4473 | 0.4070 |
| WR 95 % CI high | 0.7062 | 0.6454 | 0.5944 | 0.6564 | 0.6598 |
| expectancy (R) | +0.1875 | +0.0943 | -0.0379 | +0.0826 | +0.0292 |
| profit factor (R) | 1.569 | 1.261 | 0.911 | 1.241 | 1.076 |
| profit factor (points) | 1.863 | 1.262 | 1.256 | 1.182 | 0.965 |
| R / day | +0.0775 | +0.0475 | -0.0139 | +0.0269 | +0.0128 |
| median R / day | +0.00 | +0.00 | +0.00 | +0.00 | +0.00 |
| profitable-day % | 56.4% | 52.3% | 45.3% | 55.4% | 51.3% |
| max daily loss (R) | -2.11 | -2.05 | -2.09 | -2.04 | -2.06 |
| 95th pct daily loss (R) | -1.06 | -1.04 | -2.08 | -1.08 | -1.43 |
| max drawdown (R) | 4.47 | 7.72 | 7.89 | 4.76 | 7.91 |
| longest losing streak | 3 | 5 | 6 | 3 | 7 |
| longest winning streak | 5 | 6 | 5 | 6 | 5 |
| drawdown recovery (days) | 4 | 10 | 8 | 21 | ∞ |
| average hold (min) | 28.1 | 32.4 | 30.7 | 32.4 | 30.9 |
| median hold (min) | 23.7 | 27.9 | 25.5 | 29.5 | 26.0 |
| avg adverse excursion (pt) | 20.5 | 31.4 | 23.5 | 28.1 | 35.4 |
| avg favourable excursion (pt) | 27.0 | 31.9 | 24.4 | 31.8 | 32.9 |
| average R (pt) | 36.1 | 49.6 | 38.1 | 47.8 | 53.7 |
| TP | 52 | 49 | 33 | 31 | 22 |
| SL | 31 | 40 | 35 | 24 | 19 |
| TIMEOUT | 22 | 39 | 25 | 28 | 15 |
| longs | 27 | 28 | 25 | 30 | 16 |
| shorts | 78 | 100 | 68 | 53 | 40 |

## What the larger-R profile actually looks like

The *shape* is the one the brief asked for, and it is a genuine improvement on
Phase 4:

* **average hold 31 minutes** against Phase 4's 0.5 min;
* **average R 45 points** against 7;
* **max drawdown 6.5 R** against Phase 4's thousands;
* **longest losing streak 3–7 trades** against 14–131;
* **profitable days 52%** against 2–7 %;
* win rate 49–62 % at 1:1, with drawdown that recovers in most periods.

Two things are wrong with it.

**Frequency is far below target.** The brief wanted roughly 2–7 quality trades a
day; this produces **0.41**, with
**71% zero-trade days** and a
median of **0** trades per day. Combining the top-2 % selectivity, a 60-minute
hold and one position at a time leaves very little room: the 120-decision session
can physically fit only about two non-overlapping 30-minute trades, and the
threshold rarely fires twice. Sample sizes of 56–128 trades per period follow
directly, and they are too small to resolve the effect being tested.

**The performance is not attributable to the model.** See `MATCHED_RANDOM.md`:
random entries in the same day, half-hour and direction do as well or better.

## Subgroup tables

Per-period CSVs in `strategies/larger_r/results/run_<split>/`: `by_month.csv`,
`by_weekday.csv`, `by_hour.csv`, `by_dir_label.csv`, `by_bucket15.csv`,
`by_vol_quartile.csv`, `by_r_quartile.csv`, `by_edge_quartile.csv`. No subgroup
is promoted; they exist so the absence of a profitable pocket is checkable.
