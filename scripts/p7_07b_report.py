"""Phase-7 reports part 2: controls, ablation/incremental MBP, nulls, importance,
prop metrics, regime diagnostics."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))
import numpy as np, polars as pl
from nqr.p7 import features7 as F7

SD = ROOT / "strategies" / "orderbook_state"
REP = SD / "reports"
sel = pl.read_parquet(SD / "models" / "selection_2022.parquet")
ref = sel.sort("net_ER", descending=True).row(0, named=True)
dg = json.loads((SD / "results" / "diagnostics.json").read_text())
rm = json.loads((SD / "results" / "reference_metrics.json").read_text())
FAIL = ("> **Phase 7 FAILED at the 2022 gate** — no candidate was selected, 2023 was\n"
        "> never scored, and 2025-H1 stays sealed. The \"reference configuration\"\n"
        f"> below is `{ref['config']}`, the **least-bad of the 12**, used only so the\n"
        "> mandatory diagnostics have something concrete to run on. It is not a\n"
        "> candidate and was never frozen.\n")

mrc = rm["matched_random"]["cross_day"]; mrs = rm["matched_random"]["same_day_forward"]
op = rm["opposite"]
(REP / "CONTROLS.md").write_text(f"""# CONTROLS.md — Phase 7

{FAIL}
All controls read the same tick-resolved labels as the strategy, so execution,
bracket, horizon, timeout and friction are identical by construction. Control
causality is asserted at **runtime** and raises `ControlCausalityViolation` on any
breach — the direct fix for the defect Phase 6 found in Phase 5.

## Matched random — the primary null

| variant | control n | control E[R] | control WR | Δ E[R] | 95 % day-block CI | verdict |
|---|---:|---:|---:|---:|---|---|
| **cross-day (primary)** | {mrc['n_trades']:,} | {mrc['expectancy_R']:+.4f} | {mrc['win_rate']:.4f} | **{mrc['diff_ER']['diff']:+.4f}** | [{mrc['diff_ER']['ci95_lo']:+.4f}, {mrc['diff_ER']['ci95_hi']:+.4f}] | contains 0 |
| same-day-forward (secondary) | {mrs['n_trades']:,} | {mrs['expectancy_R']:+.4f} | {mrs['win_rate']:.4f} | {mrs['diff_ER']['diff']:+.4f} | [{mrs['diff_ER']['ci95_lo']:+.4f}, {mrs['diff_ER']['ci95_hi']:+.4f}] | contains 0 |

Win-rate difference (cross-day): {mrc['diff_WR']['diff']:+.4f},
CI [{mrc['diff_WR']['ci95_lo']:+.4f}, {mrc['diff_WR']['ci95_hi']:+.4f}].

**Both variants contain zero**, and the primary one is negative. The model's
selection of *which* 5-second book state to trade adds nothing over a random
comparable state.

Two independently-constructed causal controls agreeing is worth more than one:
cross-day matches time-of-day exactly and gives up the day; same-day-forward
matches the day and gives up exact time-of-day. Neither shows an effect.

## Opposite direction

| | E[R] | WR |
|---|---:|---:|
| strategy | {op['strategy']['expectancy_R']:+.4f} | {op['strategy']['win_rate']:.4f} |
| flipped | {op['opposite']['expectancy_R']:+.4f} | {op['opposite']['win_rate']:.4f} |
| difference | {op['diff_ER']['diff']:+.4f} | {op['diff_WR']['diff']:+.4f} |
| 95 % CI | [{op['diff_ER']['ci95_lo']:+.4f}, {op['diff_ER']['ci95_hi']:+.4f}] | [{op['diff_WR']['ci95_lo']:+.4f}, {op['diff_WR']['ci95_hi']:+.4f}] |

The flip is worse, but the interval contains zero — the direction call is not
distinguishable from its own inverse. Nothing is flipped.

## Friction sweep — is there a gross edge?

| friction | E[R] | PF(R) | WR |
|---|---:|---:|---:|
""" + "\n".join(f"| {k} pt | {v['expectancy_R']:+.4f} | {v['profit_factor_R']:.3f} | {v['win_rate']:.4f} |"
                for k, v in rm["friction_sweep"].items()) + f"""

**At zero friction the reference configuration returns +0.0011 R** — indistinguishable
from nothing, against an unconditional baseline of −0.0448 R. So Phase 7 is not a
case of "edge destroyed by cost": there is no gross edge to destroy. Friction at
these R scales is only 0.040–0.067 R, the smallest of any phase except Phase 5.
""")

ab = {r["arm"]: r for r in dg["ablation"]}
inc = dg["incremental_mbp"]["expectancy_R"]; incw = dg["incremental_mbp"]["win_rate"]
q = dg["full_vs_quote_only"]
(REP / "INCREMENTAL_MBP.md").write_text(f"""# INCREMENTAL_MBP.md — Phase 7

# Does MBP-1 add anything over trades and price?

{FAIL}
This is the mandatory test and the central research question. Each arm gets its
**own** 2021-fitted scaler and its **own** 2021 selectivity threshold, on identical
dates, R, model family, selectivity level and execution.

| arm | features | train acc | n | WR | gross E[R] | net E[R] | PF(R) | vs matched random |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **A0 full** | 40 | {ab['A0_full']['train_acc']:.4f} | {ab['A0_full']['n_trades']:,} | {ab['A0_full']['win_rate']:.4f} | {ab['A0_full']['gross_ER']:+.4f} | {ab['A0_full']['net_ER']:+.4f} | {ab['A0_full']['pf_r']:.3f} | {ab['A0_full']['advantage_R']:+.4f} |
| A1 quote-only | 32 | {ab['A1_quote_only']['train_acc']:.4f} | {ab['A1_quote_only']['n_trades']:,} | {ab['A1_quote_only']['win_rate']:.4f} | {ab['A1_quote_only']['gross_ER']:+.4f} | {ab['A1_quote_only']['net_ER']:+.4f} | {ab['A1_quote_only']['pf_r']:.3f} | {ab['A1_quote_only']['advantage_R']:+.4f} |
| A2 trades + context | 8 | {ab['A2_trades_context']['train_acc']:.4f} | {ab['A2_trades_context']['n_trades']:,} | {ab['A2_trades_context']['win_rate']:.4f} | {ab['A2_trades_context']['gross_ER']:+.4f} | {ab['A2_trades_context']['net_ER']:+.4f} | {ab['A2_trades_context']['pf_r']:.3f} | {ab['A2_trades_context']['advantage_R']:+.4f} |

| comparison | Δ E[R] | 95 % day-block CI | Δ WR | 95 % CI |
|---|---:|---|---:|---|
| **A0 full − A2 trades+context** | **{inc['diff']:+.4f}** | **[{inc['ci95_lo']:+.4f}, {inc['ci95_hi']:+.4f}]** | {incw['diff']:+.4f} | [{incw['ci95_lo']:+.4f}, {incw['ci95_hi']:+.4f}] |
| A0 full − A1 quote-only | {q['diff']:+.4f} | [{q['ci95_lo']:+.4f}, {q['ci95_hi']:+.4f}] | | |

## The naive reading, and why it is wrong

Taken alone, `A0 − A2 = {inc['diff']:+.4f} R` with an interval excluding zero looks
like a positive finding: *MBP-1 adds information*. **It is not**, and reporting it
that way would be misleading. The comparison is against an arm that is worse than
doing nothing.

Against the unconditional 2022 baseline of **−0.0448 R** (every decision, both
directions, net at 1.0 pt):

| arm | net E[R] | **vs doing nothing** |
|---|---:|---:|
| A0 full (40) | −0.0389 | **+0.0059** |
| A1 quote-only (32) | −0.0611 | −0.0162 |
| A2 trades + context (8) | −0.1173 | −0.0724 |
| *(no model at all)* | *−0.0448* | *0* |

> The full model lands **+0.006 R** from doing nothing — noise. The apparent
> "+0.078 R of incremental MBP value" is the book features **undoing the damage**
> the trades-only arm does, not creating edge above the baseline.

That the trades-only arm is actively harmful is itself consistent with Phases 4–6,
which found trades-derived flow uninformative at two other horizons.

## Verdict on the central question

> **Phase 7 did not establish incremental tradable information from MBP-1.** The
> book features measurably outperform a trades-and-price model, but only by
> returning it to the level of no model at all.
""")

p = dg["null_permutation"]; s = dg["null_temporal_shift"]
(REP / "NULL_TESTS.md").write_text(f"""# NULL_TESTS.md — Phase 7

{FAIL}
## N1 — label permutation within trading days ({p['n_perm']} refits)

The target is permuted **inside each training day**, preserving day structure and
feature marginals; the identical model is refitted, thresholds recomputed by the
same rule, and 2022 rescored.

| quantity | value |
|---|---:|
| observed 2022 E[R] | **{p['observed_ER']:+.4f}** |
| null E[R], mean ± sd | {p['null_mean_ER']:+.4f} ± {p['null_sd_ER']:.4f} |
| null E[R] range | {p['null_min_ER']:+.4f} … {p['null_max_ER']:+.4f} |
| observed WR | {p['observed_WR']:.4f} |
| null WR mean | {p['null_mean_WR']:.4f} |
| **p(null ≥ observed), E[R]** | **{p['p_null_ge_observed_ER']:.3f}** |
| p(null ≥ observed), WR | {p['p_null_ge_observed_WR']:.3f} |

The real model is **{(p['observed_ER']-p['null_mean_ER'])/p['null_sd_ER']:+.1f} standard
deviations from the null mean — on the wrong side.** A model trained on scrambled
labels does *better* than the real one, 84 % of the time. There is no skill here
to detect.

Contrast Phase 4, where the same test gave p = 0.00 and the model beat its
permutation null by 5 σ. That was a real (if tiny) signal. This is not.

## N2 — temporal shift (+7 trading days)

Each decision's features are paired with the labels of the **same time-of-day slot
7 trading days later**, preserving both marginal distributions and destroying only
the causal link.

| | observed | temporally shifted |
|---|---:|---:|
| n | {p['observed_ER'] and rm['prop_metrics']['n_trades']:,} | {s['n_trades']:,} |
| WR | {p['observed_WR']:.4f} | {s['win_rate']:.4f} |
| E[R] | {p['observed_ER']:+.4f} | {s['expectancy_R']:+.4f} |
| **difference** | | **{s['observed_minus_shift']:+.4f} R** |

{s['rows_shifted']:,} rows were shifted. **Destroying the causal feature→outcome
relationship changes the result by 0.0001 R.** Whatever the model is doing is
entirely explained by structure that survives a week-long displacement — that is,
by nothing causal at all.

Taken together, N1 and N2 are more informative than the gates: the gates say the
strategy is unprofitable, the nulls say there was never a relationship to trade.
""")

fi = dg["feature_importance"]
top = "\n".join(f"| `{n}` | {v:+.5f} | {F7.FAMILY_OF[n]} |" for n, v in fi["top15"])
fam = "\n".join(f"| {k} | {v:.1%} |" for k, v in
                sorted(fi["family_share"].items(), key=lambda x: -x[1]))
(REP / "FEATURE_IMPORTANCE.md").write_text(f"""# FEATURE_IMPORTANCE.md — Phase 7

{FAIL}
Elastic-net logistic (C = 0.1, l1_ratio = 0.5), 2021-fitted, standardised
features so coefficients are directly comparable.

## Top 15 by |coefficient|

| feature | coefficient | family |
|---|---:|---:|
{top}

## Share of total |coefficient| mass by family

| family | share |
|---|---:|
{fam}

**Pure order-book families (1–7) carry {fi['book_share_1_7']:.1%} of the coefficient
mass**, so the model genuinely leans on the book rather than on the price/trade
context. It just does not help.

## What the model actually weighted

* **`bid_px_chg_per_s_15` is the single largest coefficient (−0.106)** — the rate
  at which the best bid changes price. A quote-churn / instability measure, not a
  directional one.
* **BBO state (25.2 %) and quote-update intensity (19.9 %) dominate**; imbalance
  persistence adds 12.3 %.
* **OFI carries just 1.2 %** of the mass. This is the striking one: order-flow
  imbalance is the canonical top-of-book predictor in the microstructure
  literature, and an L1-regularised model with 40 features to choose from very
  nearly discarded all three of its horizons.
* **Trade aggression 1.3 % and failure-to-advance 0.2 %** — the trades-derived
  families are again near-zero, now for the third independent time (Phases 4, 5, 7).

`secs_since_open` appears at −0.032, well down the list — unlike Phase 4, where it
was among the features the tree leaned on hardest.
""")

m = rm["prop_metrics"]
K = [("n_trades", "total trades", "{:,.0f}"), ("trades_per_day", "trades / day", "{:.2f}"),
     ("median_trades_per_day", "median trades / day", "{:.0f}"),
     ("pct_zero_trade_days", "% 0-trade days", "{:.1%}"),
     ("pct_1_trade_days", "% 1-trade days", "{:.1%}"),
     ("pct_2_trade_days", "% 2-trade days", "{:.1%}"),
     ("pct_3plus_trade_days", "% 3+-trade days", "{:.1%}"),
     ("win_rate", "win rate", "{:.4f}"),
     ("win_rate_ci95_lo", "WR 95 % CI low", "{:.4f}"),
     ("win_rate_ci95_hi", "WR 95 % CI high", "{:.4f}"),
     ("gross_ER", "gross expectancy (R)", "{:+.4f}"),
     ("expectancy_R", "net expectancy (R)", "{:+.4f}"),
     ("profit_factor_R", "**PF(R)**", "{:.3f}"),
     ("R_per_day", "R / day", "{:+.4f}"), ("median_R_per_day", "median R / day", "{:+.2f}"),
     ("pct_profitable_days", "profitable-day %", "{:.1%}"),
     ("max_daily_loss_R", "max daily loss (R)", "{:+.2f}"),
     ("p95_daily_loss_R", "95th pct daily loss (R)", "{:+.2f}"),
     ("max_drawdown_R", "max drawdown (R)", "{:.2f}"),
     ("longest_loss_streak", "longest losing streak", "{:.0f}"),
     ("longest_win_streak", "longest winning streak", "{:.0f}"),
     ("avg_hold_min", "average hold (min)", "{:.2f}"),
     ("median_hold_min", "median hold (min)", "{:.2f}"),
     ("avg_MAE_points", "avg adverse excursion (pt)", "{:.1f}"),
     ("avg_MFE_points", "avg favourable excursion (pt)", "{:.1f}"),
     ("tp_hits", "TP", "{:.0f}"), ("sl_hits", "SL", "{:.0f}"),
     ("timeouts", "TIMEOUT", "{:.0f}"), ("longs", "longs", "{:.0f}"),
     ("shorts", "shorts", "{:.0f}"), ("long_win_rate", "long WR", "{:.4f}"),
     ("short_win_rate", "short WR", "{:.4f}")]


def c(k, f):
    v = m.get(k)
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "∞" if v == float("inf") else "—"
    return f.format(v)


rg = rm["regime_diagnostics"]
(REP / "PROP_METRICS_AND_REGIME.md").write_text(f"""# PROP_METRICS_AND_REGIME.md — Phase 7

{FAIL}
2022, 09:30–11:30 ET, R = 25 pt, 1R/1R, 1.0 pt round-trip friction. No dollar
sizing. Profit factor is **PF(R)**, in R units.

| metric | value |
|---|---:|
""" + "\n".join(f"| {lab} | {c(k, f)} |" for k, lab, f in K) + f"""

## Reading it

The **frequency profile is the best of any phase** — {m['trades_per_day']:.1f} trades a
day, a median of {m['median_trades_per_day']:.0f}, and {m['pct_3plus_trade_days']:.0%} of days
with 3 or more. That is squarely in the 2–7/day band the brief called
interesting. It is also the only thing here that works.

**{m['shorts']/(m['shorts']+m['longs']):.0%} of trades are short** ({m['shorts']:,} vs
{m['longs']:,}) — the same lopsidedness Phases 5 and 6 flagged in a completely
different model, which is now a three-phase pattern.

Holds average {m['avg_hold_min']:.1f} minutes against a 15-minute cap, and MAE
({m['avg_MAE_points']:.1f} pt) and MFE ({m['avg_MFE_points']:.1f} pt) are almost
identical — the hallmark of a directionless signal.

## Regime and time diagnostics — DIAGNOSTIC ONLY

**{rg['n_cells_examined']} cells examined** across fifteen-minute bucket, hour,
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
""")
print("wrote part 2")
for x in sorted(REP.glob("*.md")):
    print("  ", x.name, x.stat().st_size)
