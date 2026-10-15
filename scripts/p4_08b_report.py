"""Phase-4 reports, part 2: OOS, diagnostics, calibration, prop-firm metrics."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import numpy as np
import polars as pl

SD = ROOT / "strategies" / "state_discovery"
REP = SD / "reports"; RES = SD / "results"
LABEL = {"train2021": "2021 train", "select2022": "2022 selection",
         "itest2023": "2023 internal OOS", "contam2024": "2024 CONTAMINATED",
         "contam2025h2": "2025-H2 CONTAMINATED"}
present = [s for s in LABEL if (RES / f"run_{s}" / "results.json").exists()]
R = {s: json.loads((RES / f"run_{s}" / "results.json").read_text()) for s in present}
meta = json.loads((SD / "models" / "production_meta.json").read_text())
frozen = json.loads((ROOT / "results" / "p4_frozen_manifest.json").read_text())
HDR = (f"*Frozen production strategy `{meta['model_key']}` top{int(meta['threshold_q']*100)}, "
       f"tau = {meta['tau']:.6f} · frozen id `{frozen['frozen_id']}`*")


def W(s):
    return R[s]["windows"]["0930_1130"]


def gate_block(s, name):
    w = W(s); v = R[s]["vs_matched"]["expectancy_R"]; ww = R[s]["vs_matched"]["win_rate"]
    c = R[s]["concentration"]
    g = [("1 — frequency ≥ 100 trades", w["n_trades"] >= 100, f"{w['n_trades']:,}"),
         ("2 — net expectancy > 0 R", w["expectancy_R"] > 0, f"{w['expectancy_R']:+.4f} R"),
         ("3 — profit factor > 1.10", w["profit_factor"] > 1.10, f"{w['profit_factor']:.3f}"),
         ("4 — raw WR > 50 % *(preference)*", w["win_rate"] > 0.50, f"{w['win_rate']:.4f}"),
         ("5 — ΔE[R] vs control, CI lower > 0", v["ci95_lo"] > 0,
          f"{v['diff']:+.4f}, CI [{v['ci95_lo']:+.4f}, {v['ci95_hi']:+.4f}]"),
         ("6 — ΔWR vs control, CI lower > 0", ww["ci95_lo"] > 0,
          f"{ww['diff']:+.4f}, CI [{ww['ci95_lo']:+.4f}, {ww['ci95_hi']:+.4f}]"),
         ("7 — profit concentration", c["gate7_pass"],
          f"total {c['total_net_R']:+,.0f} R, ex-best-week {c['total_ex_best_week_R']:+,.0f} R")]
    rows = "\n".join(f"| {n} | {val} | {'PASS' if ok else '**FAIL**'} |" for n, ok, val in g)
    npass = sum(ok for _, ok, _ in g)
    return (f"| gate | value | result |\n|---|---|:---:|\n{rows}\n\n"
            f"**{npass} of 7 gates met on {name}.** These are the 2026-Q1 gates applied "
            f"to a development/diagnostic period; they are shown to make the shortfall "
            f"concrete, not because this period is validation.")


# ------------------------------------------------------------ 2023 OOS ----
w = W("itest2023"); v = R["itest2023"]["vs_matched"]
(REP / "ITEST_2023.md").write_text(f"""# ITEST_2023.md — Phase 4 internal out-of-sample test

{HDR}

2023 was **not** consulted during model fitting, threshold calibration or
configuration selection. It was scored once, after `{meta['config_name']}` had
already been chosen on 2022, and it could not change that choice.

## Result, 09:30–11:30, 1R, 1.0 pt round trip

| | |
|---|---|
| trading days | {w['n_trading_days_available']} |
| executed trades | {w['n_trades']:,} ({w['trades_per_day']:.1f}/day) |
| win rate | {w['win_rate']:.4f} (Wilson 95 % [{w['win_rate_ci95_lo']:.4f}, {w['win_rate_ci95_hi']:.4f}]) |
| **net expectancy** | **{w['expectancy_R']:+.4f} R** |
| profit factor | {w['profit_factor']:.3f} |
| total | {w['total_R']:+,.0f} R |
| R per day | {w['R_per_day']:+.2f} |
| profitable days | {w['pct_profitable_days']:.1%} |
| median hold | {w['median_hold_min']:.2f} min |
| max drawdown | {w['max_drawdown_R']:,.0f} R |
| longest losing streak | {w['longest_loss_streak']} |

## Against matched random entries

| statistic | strategy | matched control | Δ | 95 % day-block CI |
|---|---:|---:|---:|---|
| expectancy (R) | {w['expectancy_R']:+.4f} | {R['itest2023']['matched_control']['expectancy_R']:+.4f} | {v['expectancy_R']['diff']:+.4f} | [{v['expectancy_R']['ci95_lo']:+.4f}, {v['expectancy_R']['ci95_hi']:+.4f}] |
| win rate | {w['win_rate']:.4f} | {R['itest2023']['matched_control']['win_rate']:.4f} | {v['win_rate']['diff']:+.4f} | [{v['win_rate']['ci95_lo']:+.4f}, {v['win_rate']['ci95_hi']:+.4f}] |

**Both intervals contain zero.** On the year it had never seen, the strategy is
statistically indistinguishable from random entries matched on day, hour,
direction and volatility — while losing {abs(w['expectancy_R']):.2f} R per trade
after friction.

The friction sweep is the sharper statement: at **0.0 pt** friction 2023
expectancy is {R['itest2023']['friction_sweep']['0.0']['expectancy_R']:+.4f} R.
There is no gross edge here for costs to erode.

## Gates, applied to 2023

{gate_block("itest2023", "2023")}

## Verdict of the development stage

The single production candidate permitted by the budget fails the hard gates on
untouched development data by a wide margin, in the same direction and by a
similar amount as on its own training year. Phase 4's development stage has
already answered the research question in the negative.
""")

# ----------------------------------------------------- contaminated diags ----
for s, fname, period, why in (
        ("contam2024", "DIAG_2024_CONTAMINATED.md", "2024-01-01 … 2024-12-31",
         "2024 was consumed as Phase-1 and Phase-2 validation."),
        ("contam2025h2", "DIAG_2025H2_CONTAMINATED.md", "2025-07-01 … 2025-12-31",
         "2025-H2 was consumed as Phase-3 fresh validation.")):
    w = W(s); v = R[s]["vs_matched"]
    seal = ("\n## The 2025-H1 seal held\n\nThis diagnostic reads **`2025_H2.parquet` only**. "
            "`2025_H1.parquet` is refused unconditionally by `nqr.p4.holdout4` — there is no "
            "unlock path for it — and the build script asserts that refusal before opening "
            "anything. The DuckDB scan additionally carries a trading-date predicate of "
            "`>= 2025-07-01`, and `p4_09_integrity.py` confirms the resulting tick cache "
            "contains no month from 2025-01 to 2025-06.\n"
            if s == "contam2025h2" else "")
    (REP / fname).write_text(f"""# {fname[:-3]} — Phase 4

# CONTAMINATED DIAGNOSTIC — NOT VALIDATION

{HDR}

Period **{period}**. {why} It may not select features, models, thresholds,
directions, sessions, stop sizes or strategies, and it did not: the production
strategy was frozen as `{frozen['frozen_id']}` **before** this ran, and it is
unchanged after.

## Result, 09:30–11:30, 1R, 1.0 pt round trip

| | |
|---|---|
| trading days | {w['n_trading_days_available']} |
| executed trades | {w['n_trades']:,} ({w['trades_per_day']:.1f}/day) |
| win rate | {w['win_rate']:.4f} |
| **net expectancy** | **{w['expectancy_R']:+.4f} R** |
| profit factor | {w['profit_factor']:.3f} |
| total | {w['total_R']:+,.0f} R |
| profitable days | {w['pct_profitable_days']:.1%} |
| gross expectancy (0.0 pt) | {R[s]['friction_sweep']['0.0']['expectancy_R']:+.4f} R |

## Against matched random entries

| statistic | strategy | matched control | Δ | 95 % day-block CI |
|---|---:|---:|---:|---|
| expectancy (R) | {w['expectancy_R']:+.4f} | {R[s]['matched_control']['expectancy_R']:+.4f} | {v['expectancy_R']['diff']:+.4f} | [{v['expectancy_R']['ci95_lo']:+.4f}, {v['expectancy_R']['ci95_hi']:+.4f}] |
| win rate | {w['win_rate']:.4f} | {R[s]['matched_control']['win_rate']:.4f} | {v['win_rate']['diff']:+.4f} | [{v['win_rate']['ci95_lo']:+.4f}, {v['win_rate']['ci95_hi']:+.4f}] |

Both intervals contain zero.

## Gates, applied to {period[:4]}

{gate_block(s, period[:4])}
{seal}
### Nothing changed after seeing this

The frozen id before this diagnostic and after it is the same:
`{frozen['frozen_id']}`. `scripts/p4_09_integrity.py` re-verifies it.
""")

# ------------------------------------------------------------ calibration ----
ct = pl.read_csv(RES / "calibration_trades.csv")
rt = pl.read_csv(RES / "calibration_rows.csv").filter(pl.col("split") == "itest2023")
cal = json.loads((RES / "calibration.json").read_text())
tb = ["| period | \\|score\\| | trades | WR | E[R] | control E[R] | strategy − control |",
      "|---|---:|---:|---:|---:|---:|---:|"]
for r in ct.sort(["split", "edge"]).iter_rows(named=True):
    tb.append(f"| {LABEL.get(r['split'], r['split'])} | {r['edge']:.6f} | {r['n_trades']:,} | "
              f"{r['win_rate']:.4f} | {r['expectancy_R']:+.4f} | {r['control_expectancy_R']:+.4f} | "
              f"{r['edge_minus_control_R']:+.4f} |")
rb = ["| score | predicted P(long wins) | rows | traded | actual P(long wins) | gross R in model's direction |",
      "|---:|---:|---:|:---:|---:|---:|"]
for r in rt.iter_rows(named=True):
    rb.append(f"| {r['score']:+.6f} | {r['pred_p_long']:.4f} | {r['n_rows']:,} | "
              f"{'yes' if r['traded'] else 'no'} | {r['actual_p_long_win']:.4f} | {r['dir_gross_R']:+.4f} |")

(REP / "CALIBRATION.md").write_text(f"""# CALIBRATION.md — Phase 4

{HDR}

The question: **does more model confidence correspond to more realised edge?**
The answer is no, and in the most confident bucket it is inverted.

## Trade level — realised performance by \\|score\\|, with the matched control beside it

{chr(10).join(tb)}

Rank correlation between \\|score\\| and realised expectancy, by period:

| period | buckets | Spearman(\\|score\\|, E[R]) |
|---|---:|---:|
{chr(10).join(f"| {LABEL.get(k, k)} | {v['n_buckets']} | {v['spearman_edge_vs_expectancy']:+.2f} |" for k, v in cal.items())}

**The relationship is not monotone in any period**, and in 2025-H2 it is
negative. Concretely and consistently across all five periods:

* the **most confident short** bucket (`|score| = 0.051059`) is the **worst**
  bucket everywhere — E[R] between {ct.filter(pl.col('edge').round(6)==0.051059)['expectancy_R'].min():+.3f}
  and {ct.filter(pl.col('edge').round(6)==0.051059)['expectancy_R'].max():+.3f} R —
  and it *underperforms* its own matched control by
  {abs(ct.filter(pl.col('edge').round(6)==0.051059)['edge_minus_control_R'].min()):.2f} R
  in the worst case. High model confidence on the short side is an anti-signal.
* the **most confident long** bucket (`|score| = 0.062383`) is the **best**
  bucket everywhere and beats its control in all five periods — yet is still
  net-negative in all five.
* the **least confident traded** bucket (`|score| = 0.017941`, which is the bulk
  of the book) sits in between and also beats its control in all five periods.

A confidence score that does not order realised outcomes is not a usable
confidence score. The threshold is **not** being adjusted in response: PREREG A7
fixed it before any outcome, and moving it now would be threshold mining.

## Row level — 2023, every usable decision row bucketed by the model's score

{chr(10).join(rb)}

Rows overlap by up to 30 minutes, so this is a shape diagnostic and not an
inference. Two things are visible anyway. The tree's predicted probability spans
only **{rt['pred_p_long'].min():.3f} to {rt['pred_p_long'].max():.3f}** — the
signal is weak by construction. And the mapping from predicted to actual is
loose: the bucket predicting {rt.sort('pred_p_long')['pred_p_long'][0]:.3f}
realised {rt.sort('pred_p_long')['actual_p_long_win'][0]:.3f}, while the bucket
predicting {rt.sort('pred_p_long')['pred_p_long'][-1]:.3f} realised
{rt.sort('pred_p_long')['actual_p_long_win'][-1]:.3f}. Directionally right at the
extremes, badly calibrated in between, and far too small either way.
""")

# ------------------------------------------------------- prop-firm metrics ----
K = [("n_trades", "total trades", "{:,.0f}"), ("trades_per_day", "trades / day", "{:.1f}"),
     ("median_trades_per_day", "median trades / day", "{:.0f}"),
     ("pct_zero_trade_days", "% zero-trade days", "{:.1%}"),
     ("pct_1_trade_days", "% 1-trade days", "{:.1%}"),
     ("pct_2_trade_days", "% 2-trade days", "{:.1%}"),
     ("pct_3plus_trade_days", "% 3+-trade days", "{:.1%}"),
     ("trades_0930_1030", "09:30–10:30 trades", "{:,.0f}"),
     ("trades_1030_1130", "10:30–11:30 trades", "{:,.0f}"),
     ("win_rate", "win rate", "{:.4f}"), ("expectancy_R", "expectancy (R)", "{:+.4f}"),
     ("profit_factor", "profit factor", "{:.3f}"), ("R_per_day", "R / day", "{:+.2f}"),
     ("median_R_per_day", "median R / day", "{:+.2f}"),
     ("pct_profitable_days", "profitable-day %", "{:.1%}"),
     ("max_daily_loss_R", "max daily loss (R)", "{:+.1f}"),
     ("p95_daily_loss_R", "95th pct daily loss (R)", "{:+.1f}"),
     ("max_drawdown_R", "max drawdown (R)", "{:,.0f}"),
     ("longest_loss_streak", "longest losing streak", "{:.0f}"),
     ("longest_win_streak", "longest winning streak", "{:.0f}"),
     ("drawdown_recovery_days", "drawdown recovery (days)", "{:.0f}"),
     ("avg_hold_min", "average hold (min)", "{:.2f}"),
     ("median_hold_min", "median hold (min)", "{:.2f}"),
     ("avg_MFE_points", "average MFE (pt)", "{:.2f}"),
     ("avg_MAE_points", "average MAE (pt)", "{:.2f}"),
     ("avg_R_distance_points", "average R (pt)", "{:.2f}"),
     ("longs", "longs", "{:,.0f}"), ("shorts", "shorts", "{:,.0f}"),
     ("long_win_rate", "long WR", "{:.4f}"), ("short_win_rate", "short WR", "{:.4f}")]


def cell(s, k, f):
    v = W(s).get(k)
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "∞" if v == float("inf") else "—"
    return f.format(v)


body = "\n".join("| " + lab + " | " + " | ".join(cell(s, k, f) for s in present) + " |"
                 for k, lab, f in K)
(REP / "PROP_FIRM_METRICS.md").write_text(f"""# PROP_FIRM_METRICS.md — Phase 4

{HDR}

09:30–11:30 ET, 1R target / 1R stop, 1.0 NQ point round-trip friction.
No dollar position sizing is applied.

| metric | {" | ".join(LABEL[s] for s in present)} |
|---|{"---|" * len(present)}
{body}

## What this profile actually is

The brief asked for a strategy with a repeatable edge, a high win rate, several
opportunities per active morning and manageable drawdown. What the preregistered
search produced is none of those, and the metrics say why in three numbers.

**~140 trades per day in a two-hour window.** With one position at a time and a
median hold of about {W('itest2023')['median_hold_min']*60:.0f} seconds, the book
is in the market almost continuously. `% 3+-trade days` is
{W('itest2023')['pct_3plus_trade_days']:.0%}; there is essentially no such thing
as a selective day. This is a consequence of R being small — R averages
{W('itest2023')['avg_R_distance_points']:.1f} points, half of a 1-minute ATR — so
a ±1R bracket is resolved by ordinary tick noise within seconds.

**Friction is ~{abs(W('itest2023')['expectancy_R'] - R['itest2023']['friction_sweep']['0.0']['expectancy_R']):.2f} R per trade.**
A 1.0 point round trip against an average R of
{W('itest2023')['avg_R_distance_points']:.1f} points is a
{1.0 / W('itest2023')['avg_R_distance_points']:.0%} tax on every trade. At 140
trades a day nothing survives that, and the gross numbers confirm there was
nothing to survive it with.

**Profitable days are {W('itest2023')['pct_profitable_days']:.0%}.** Drawdown never
recovers in any period — the equity curve is monotonically down, which is why
`drawdown recovery (days)` is infinite everywhere. Max daily loss reaches
{abs(W('contam2024')['max_daily_loss_R']):.0f} R.

A viable prop profile would need R measured in tens of points, a hold measured in
tens of minutes, and a handful of trades per day. That is a different hypothesis
and it belongs to `FUTURE_HYPOTHESES.md`, not to Phase 4.

## Subgroup tables

Per-period CSVs in `strategies/state_discovery/results/run_<split>/`:
`by_month.csv`, `by_weekday.csv`, `by_hour.csv`, `by_dir_label.csv`,
`by_r_quartile.csv`, `by_edge_quartile.csv`. No subgroup is promoted; they exist
so that the absence of a profitable pocket is checkable rather than asserted.
""")
print("wrote part 2")
for f in sorted(REP.glob("*.md")):
    print("  ", f.name, f.stat().st_size)
