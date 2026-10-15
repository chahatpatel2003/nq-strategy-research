# PROP_METRICS_AND_REGIME.md — Phase 7

> **Phase 7 FAILED at the 2022 gate** — no candidate was selected, 2023 was
> never scored, and 2025-H1 stays sealed. The "reference configuration"
> below is `R25:A_logit:top1p0`, the **least-bad of the 12**, used only so the
> mandatory diagnostics have something concrete to run on. It is not a
> candidate and was never frozen.

2022, 09:30–11:30 ET, R = 25 pt, 1R/1R, 1.0 pt round-trip friction. No dollar
sizing. Profit factor is **PF(R)**, in R units.

| metric | value |
|---|---:|
| total trades | 2,229 |
| trades / day | 8.78 |
| median trades / day | 4 |
| % 0-trade days | 12.6% |
| % 1-trade days | 12.2% |
| % 2-trade days | 9.1% |
| % 3+-trade days | 66.1% |
| win rate | 0.4989 |
| WR 95 % CI low | 0.4781 |
| WR 95 % CI high | 0.5196 |
| gross expectancy (R) | +0.0011 |
| net expectancy (R) | -0.0389 |
| **PF(R)** | 0.924 |
| R / day | -0.3415 |
| median R / day | +0.00 |
| profitable-day % | 45.0% |
| max daily loss (R) | -15.08 |
| 95th pct daily loss (R) | -4.48 |
| max drawdown (R) | 100.37 |
| longest losing streak | 12 |
| longest winning streak | 9 |
| average hold (min) | 2.84 |
| median hold (min) | 1.70 |
| avg adverse excursion (pt) | 17.1 |
| avg favourable excursion (pt) | 17.5 |
| TP | 1081 |
| SL | 1075 |
| TIMEOUT | 73 |
| longs | 146 |
| shorts | 2083 |
| long WR | 0.4589 |
| short WR | 0.5017 |

## Reading it

The **frequency profile is the best of any phase** — 8.8 trades a
day, a median of 4, and 66% of days
with 3 or more. That is squarely in the 2–7/day band the brief called
interesting. It is also the only thing here that works.

**93% of trades are short** (2,083 vs
146) — the same lopsidedness Phases 5 and 6 flagged in a completely
different model, which is now a three-phase pattern.

Holds average 2.8 minutes against a 15-minute cap, and MAE
(17.1 pt) and MFE (17.5 pt) are almost
identical — the hallmark of a directionless signal.

## Regime and time diagnostics — DIAGNOSTIC ONLY

**63 cells examined** across fifteen-minute bucket, hour,
direction, volatility quartile, spread, BBO-size quartile, imbalance quartile,
microprice-pressure quartile, OFI quartile, confidence quartile, month and
weekday. CSVs in `results/reference_2022/by_*.csv`.

Nothing survives inspection: the best fifteen-minute bucket is +0.0383 R (n = 370)
against a worst of −0.1436; the best month is +0.1149 R on **n = 89**; the best
"spread" cell is +0.96 R on **n = 1**. These are the shapes of noise in 63 cells,
and **no subgroup may rescue a failed strategy** — they are recorded in
`FUTURE_HYPOTHESES.md` and nowhere else.

The one mildly interesting cell is the top **OFI quartile at +0.0121 R** versus
−0.1247 in the worst, which is at least directionally consistent with OFI meaning
something — but OFI carries only 1.2 % of the model's coefficient mass, and the
cell is 558 trades out of 2,229.
