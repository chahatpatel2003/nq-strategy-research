# PROP_FIRM_METRICS.md — Phase 4

*Frozen production strategy `B_tree:depth=3` top20, tau = 0.017941 · frozen id `statedisc-1.0.0+c147134184dfb32d`*

09:30–11:30 ET, 1R target / 1R stop, 1.0 NQ point round-trip friction.
No dollar position sizing is applied.

| metric | 2021 train | 2022 selection | 2023 internal OOS | 2024 CONTAMINATED | 2025-H2 CONTAMINATED |
|---|---|---|---|---|---|
| total trades | 34,653 | 37,667 | 36,145 | 36,092 | 18,000 |
| trades / day | 136.4 | 148.3 | 142.3 | 141.5 | 140.6 |
| median trades / day | 146 | 150 | 148 | 145 | 140 |
| % zero-trade days | 0.4% | 0.0% | 0.4% | 0.0% | 0.0% |
| % 1-trade days | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| % 2-trade days | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| % 3+-trade days | 99.6% | 100.0% | 99.6% | 100.0% | 100.0% |
| 09:30–10:30 trades | 21,136 | 21,859 | 21,668 | 21,345 | 10,469 |
| 10:30–11:30 trades | 13,517 | 15,808 | 14,477 | 14,747 | 7,531 |
| win rate | 0.4908 | 0.5023 | 0.4826 | 0.4900 | 0.4933 |
| expectancy (R) | -0.2428 | -0.1395 | -0.2449 | -0.1986 | -0.1745 |
| profit factor | 0.689 | 0.798 | 0.671 | 0.729 | 0.762 |
| R / day | -33.13 | -20.68 | -34.85 | -28.11 | -24.53 |
| median R / day | -32.01 | -19.17 | -31.57 | -26.88 | -23.61 |
| profitable-day % | 5.1% | 7.5% | 2.0% | 7.1% | 5.5% |
| max daily loss (R) | -155.3 | -102.1 | -146.0 | -163.8 | -118.0 |
| 95th pct daily loss (R) | -68.9 | -46.6 | -66.2 | -59.6 | -47.2 |
| max drawdown (R) | 8,417 | 5,254 | 8,859 | 7,181 | 3,141 |
| longest losing streak | 38 | 14 | 131 | 33 | 14 |
| longest winning streak | 12 | 16 | 13 | 16 | 12 |
| drawdown recovery (days) | ∞ | ∞ | ∞ | ∞ | ∞ |
| average hold (min) | 0.58 | 0.59 | 0.59 | 0.62 | 0.62 |
| median hold (min) | 0.36 | 0.38 | 0.39 | 0.41 | 0.40 |
| average MFE (pt) | 4.03 | 6.05 | 4.08 | 4.99 | 5.86 |
| average MAE (pt) | 3.91 | 5.85 | 4.01 | 4.91 | 5.75 |
| average R (pt) | 5.60 | 8.44 | 5.68 | 6.98 | 8.16 |
| longs | 2,431 | 4,279 | 3,216 | 4,424 | 3,052 |
| shorts | 32,222 | 33,388 | 32,929 | 31,668 | 14,948 |
| long WR | 0.5150 | 0.5151 | 0.4944 | 0.4966 | 0.4784 |
| short WR | 0.4889 | 0.5007 | 0.4814 | 0.4891 | 0.4964 |

## What this profile actually is

The brief asked for a strategy with a repeatable edge, a high win rate, several
opportunities per active morning and manageable drawdown. What the preregistered
search produced is none of those, and the metrics say why in three numbers.

**~140 trades per day in a two-hour window.** With one position at a time and a
median hold of about 23 seconds, the book
is in the market almost continuously. `% 3+-trade days` is
100%; there is essentially no such thing
as a selective day. This is a consequence of R being small — R averages
5.7 points, half of a 1-minute ATR — so
a ±1R bracket is resolved by ordinary tick noise within seconds.

**Friction is ~0.22 R per trade.**
A 1.0 point round trip against an average R of
5.7 points is a
18% tax on every trade. At 140
trades a day nothing survives that, and the gross numbers confirm there was
nothing to survive it with.

**Profitable days are 2%.** Drawdown never
recovers in any period — the equity curve is monotonically down, which is why
`drawdown recovery (days)` is infinite everywhere. Max daily loss reaches
164 R.

A viable prop profile would need R measured in tens of points, a hold measured in
tens of minutes, and a handful of trades per day. That is a different hypothesis
and it belongs to `FUTURE_HYPOTHESES.md`, not to Phase 4.

## Subgroup tables

Per-period CSVs in `strategies/state_discovery/results/run_<split>/`:
`by_month.csv`, `by_weekday.csv`, `by_hour.csv`, `by_dir_label.csv`,
`by_r_quartile.csv`, `by_edge_quartile.csv`. No subgroup is promoted; they exist
so that the absence of a profitable pocket is checkable rather than asserted.
