"""Phase-5 reports, part 2: prop metrics, time/state diagnostics, contaminated runs."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import numpy as np
import polars as pl

SD = ROOT / "strategies" / "larger_r"
REP = SD / "reports"; RES = SD / "results"; DIA = SD / "diagnostics"
LABEL = {"train2021": "2021 train", "select2022": "2022 selection",
         "itest2023": "2023 internal OOS", "contam2024": "2024 CONTAMINATED",
         "contam2025h2": "2025-H2 CONTAMINATED"}
P = [s for s in LABEL if (RES / f"run_{s}" / "results.json").exists()]
R = {s: json.loads((RES / f"run_{s}" / "results.json").read_text()) for s in P}
W = {s: R[s]["windows"]["0930_1130"] for s in P}
dev = json.loads((SD / "models" / "development_meta.json").read_text())
CAND = dev["winner"]["config"]
HDR = (f"*Candidate `{CAND}` — R = 4.0 × ATR14(1-min), 60-second clock, "
       f"60-minute hold, τ = {dev['winner']['tau']:.6f}*")
REJ = ("> **This candidate was REJECTED** at the 2023 internal out-of-sample test\n"
       "> (`ITEST_2023.md`). It was never frozen and 2026-Q1 was never opened.\n")

# ------------------------------------------------------- prop metrics ----
K = [("n_trades", "total trades", "{:,.0f}"), ("trades_per_day", "trades / day", "{:.2f}"),
     ("median_trades_per_day", "median trades / day", "{:.0f}"),
     ("pct_zero_trade_days", "% 0-trade days", "{:.1%}"),
     ("pct_1_trade_days", "% 1-trade days", "{:.1%}"),
     ("pct_2_trade_days", "% 2-trade days", "{:.1%}"),
     ("pct_3plus_trade_days", "% 3+-trade days", "{:.1%}"),
     ("trades_0930_1030", "09:30–10:30 trades", "{:,.0f}"),
     ("trades_1030_1130", "10:30–11:30 trades", "{:,.0f}"),
     ("win_rate", "win rate", "{:.4f}"),
     ("win_rate_ci95_lo", "WR 95 % CI low", "{:.4f}"),
     ("win_rate_ci95_hi", "WR 95 % CI high", "{:.4f}"),
     ("expectancy_R", "expectancy (R)", "{:+.4f}"),
     ("profit_factor_R", "profit factor (R)", "{:.3f}"),
     ("profit_factor_points", "profit factor (points)", "{:.3f}"),
     ("R_per_day", "R / day", "{:+.4f}"), ("median_R_per_day", "median R / day", "{:+.2f}"),
     ("pct_profitable_days", "profitable-day %", "{:.1%}"),
     ("max_daily_loss_R", "max daily loss (R)", "{:+.2f}"),
     ("p95_daily_loss_R", "95th pct daily loss (R)", "{:+.2f}"),
     ("max_drawdown_R", "max drawdown (R)", "{:.2f}"),
     ("longest_loss_streak", "longest losing streak", "{:.0f}"),
     ("longest_win_streak", "longest winning streak", "{:.0f}"),
     ("drawdown_recovery_days", "drawdown recovery (days)", "{:.0f}"),
     ("avg_hold_min", "average hold (min)", "{:.1f}"),
     ("median_hold_min", "median hold (min)", "{:.1f}"),
     ("avg_MAE_points", "avg adverse excursion (pt)", "{:.1f}"),
     ("avg_MFE_points", "avg favourable excursion (pt)", "{:.1f}"),
     ("avg_R_distance_points", "average R (pt)", "{:.1f}"),
     ("tp_hits", "TP", "{:.0f}"), ("sl_hits", "SL", "{:.0f}"),
     ("timeouts", "TIMEOUT", "{:.0f}"),
     ("longs", "longs", "{:.0f}"), ("shorts", "shorts", "{:.0f}")]


def cell(s, k, f):
    v = W[s].get(k)
    if v is None:
        return "—"
    if isinstance(v, float) and not np.isfinite(v):
        return "∞" if v == float("inf") else "—"
    return f.format(v)


body = "\n".join("| " + lab + " | " + " | ".join(cell(s, k, f) for s in P) + " |"
                 for k, lab, f in K)
(REP / "PROP_FIRM_METRICS.md").write_text(f"""# PROP_FIRM_METRICS.md — Phase 5

{HDR}

{REJ}
09:30–11:30 ET, 1R target / 1R stop, 1.0 NQ point round-trip friction.
No dollar position sizing is applied.

| metric | {" | ".join(LABEL[s] for s in P)} |
|---|{"---|" * len(P)}
{body}

## What the larger-R profile actually looks like

The *shape* is the one the brief asked for, and it is a genuine improvement on
Phase 4:

* **average hold {np.mean([W[s]['avg_hold_min'] for s in P]):.0f} minutes** against Phase 4's 0.5 min;
* **average R {np.mean([W[s]['avg_R_distance_points'] for s in P]):.0f} points** against 7;
* **max drawdown {np.mean([W[s]['max_drawdown_R'] for s in P]):.1f} R** against Phase 4's thousands;
* **longest losing streak 3–7 trades** against 14–131;
* **profitable days {np.mean([W[s]['pct_profitable_days'] for s in P]):.0%}** against 2–7 %;
* win rate 49–62 % at 1:1, with drawdown that recovers in most periods.

Two things are wrong with it.

**Frequency is far below target.** The brief wanted roughly 2–7 quality trades a
day; this produces **{np.mean([W[s]['trades_per_day'] for s in P]):.2f}**, with
**{np.mean([W[s]['pct_zero_trade_days'] for s in P]):.0%} zero-trade days** and a
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
""")

# ----------------------------------------------- time / state diagnostics ----
D = json.loads((DIA / "state_diagnostics.json").read_text())


def tab(name, title, note=""):
    t = D["tables"].get(name)
    if not t:
        return ""
    rows = "\n".join(
        f"| {r['cell']} | {r['n']:,} | {r['long_ER']:+.4f} | {r['long_WR']:.4f} | "
        f"{r['short_ER']:+.4f} | {r['short_WR']:.4f} | {r['best_dir']} | {r['best_ER']:+.4f} |"
        for r in t)
    return (f"\n### {title}\n\n{note}\n\n"
            "| cell | n | long E[R] | long WR | short E[R] | short WR | better side | best E[R] |\n"
            "|---|---:|---:|---:|---:|---:|:---:|---:|\n" + rows + "\n")


(REP / "TIME_AND_STATE_DIAGNOSTICS.md").write_text(f"""# TIME_AND_STATE_DIAGNOSTICS.md — Phase 5

# DIAGNOSTIC / HYPOTHESIS GENERATION ONLY

# POST-HOC — REQUIRES NEW UNTOUCHED DATA

Everything here is computed on the **unconditional decision population** — every
60-second decision row, no model involved — over the **development years
2021–2023 only** ({D['n_rows']:,} rows). It therefore describes the *market*, not
the strategy, at R = 4.0 × ATR14(1-min) with a 60-minute horizon, net of 1.0 pt
friction.

**{D['n_cells_examined']} cells were examined.** No multiplicity correction is
applied because none of this is a test — it is hypothesis generation on data that
has already been used. Nothing here modified Phase 5, and nothing here may be
traded without new untouched data.

The unconditional baseline for the whole population is **−0.024 R** (mean of both
directions), so a cell only matters if it is well above that.
{tab("bucket15", "Time of day — fifteen-minute buckets",
     "This is the table the brief specifically asked for.")}
**Reading it:** the only genuinely positive cells are the last two,
**11:00–11:30 long** (+0.0076 and +0.0277 R, WR 52.3 % and 53.0 %). The
10:15–10:45 pair leans short, the early session leans long, and every magnitude
is inside ±0.03 R. Against a −0.024 R baseline the late-session long tilt is the
one visible effect — and it is 2 cells out of 8, on three years of already-used
data.
{tab("dist_open_quartile", "Distance from the session open (quartiles of `dist_open_norm`)",
     "The strongest single effect in the whole diagnostic set.")}
**Reading it:** the top quartile — price furthest **above** the 09:30 open —
returns **+0.0391 R long at 53.96 % WR**, against −0.0487 R for longs in the
bottom quartile. That is a clean continuation/trend-day signature and it is the
largest, most monotone effect found. It is also already inside the model:
`dist_open_norm` is the third-largest coefficient (+0.292).
{tab("above_open", "Above vs below the session open", "0 = below, 1 = above.")}
{tab("vol_quartile", "Volatility quartile (`atr1m`)")}
Essentially flat. Volatility level does **not** separate outcomes at this
horizon — which is notable, because it was Phase 4's dominant feature.
{tab("near_pdh", "Near the previous-day high (|dist_pdh_norm| < 1.0)", "1 = near.")}
{tab("near_pdl", "Near the previous-day low (|dist_pdl_norm| < 1.0)", "1 = near.")}
Near PDH the short side turns marginally positive (+0.0068 R) while the long side
drops to −0.0555 — a mild fade-the-high tilt on 4,769 rows. Near PDL shows
nothing.
{tab("velocity_quartile", "Directional velocity quartile (`vel_60_norm`)")}
{tab("efficiency_quartile", "Path efficiency quartile (`eff_60`)")}
{tab("intensity_quartile", "Trade intensity quartile (`trades_per_s_60`)")}
{tab("delta_quartile", "Delta state quartile (`delta_per_vol_60`)")}
**Velocity, efficiency, intensity and delta are all flat**, spanning less than
0.02 R end to end. The delta table is the flattest of the four (−0.0066 to
−0.0132 R), which is the third independent confirmation that trades-derived order
flow carries nothing directional here.
{tab("weekday_f", "Weekday", "0 = Monday … 4 = Friday.")}
Thursday longs (+0.0438 R) and Monday longs (+0.0157 R) look good; Wednesday
leans short. **Treat this as noise.** Five cells, no mechanism, and weekday
effects are the canonical spurious finding — Phase 1 already burned a subgroup
this way (the ENGULFING trigger, 56.7 % on dev → 45.0 % on validation).
{tab("yr", "Year")}
The long tilt strengthens across 2021 → 2023 while the short side weakens, which
is consistent with a drift term rather than a state effect.

## Summary for hypothesis generation

| observation | size | confidence |
|---|---|---|
| price far **above** the session open → longs work | +0.039 R vs −0.049 R | strongest effect found; monotone across quartiles |
| **11:00–11:30 longs** | +0.028 R | modest, 2 of 8 time cells |
| near PDH → mild short tilt | +0.007 R | small, thin cell |
| volatility / velocity / efficiency / intensity / delta | < 0.02 R spread | no effect |
| weekday | up to +0.044 R | almost certainly noise |

Carried to `FUTURE_HYPOTHESES.md`. None of it may be added to Phase 5.
""")

# ---------------------------------------------------- contaminated runs ----
for s, fname, period, why in (
        ("contam2024", "DIAG_2024_CONTAMINATED.md", "2024-01-01 … 2024-12-31",
         "2024 was consumed as Phase-1 and Phase-2 validation."),
        ("contam2025h2", "DIAG_2025H2_CONTAMINATED.md", "2025-07-01 … 2025-12-31",
         "2025-H2 was consumed as Phase-3 fresh validation.")):
    w = W[s]; v = R[s]["vs_matched"]
    seal = ("\n## The 2025-H1 seal held\n\nThis diagnostic reads **`2025_H2.parquet` only**. "
            "`2025_H1.parquet` is refused unconditionally by `nqr.p5.holdout5` — there is no "
            "unlock path for it — and the tick cache it draws on contains no month between "
            "2025-01 and 2025-06. `p5_09_integrity.py` re-checks both.\n"
            if s == "contam2025h2" else "")
    (REP / fname).write_text(f"""# {fname[:-3]} — Phase 5

# CONTAMINATED DIAGNOSTIC — NOT VALIDATION

{HDR}

{REJ}
Period **{period}**. {why} It may not select anything, and it did not: the
candidate had **already been rejected** on 2023 before this ran. It is reported
because it is informative about *how* the candidate fails, not because it can
change the outcome.

## Result, 09:30–11:30, 1R, 1.0 pt round trip

| | |
|---|---|
| trading days | {w['n_trading_days_available']} |
| executed trades | {w['n_trades']} ({w['trades_per_day']:.2f}/day) |
| win rate | {w['win_rate']:.4f} (95 % [{w['win_rate_ci95_lo']:.4f}, {w['win_rate_ci95_hi']:.4f}]) |
| gross expectancy (0.0 pt) | {R[s]['friction_sweep']['0.0']['expectancy_R']:+.4f} R |
| net expectancy (1.0 pt) | **{w['expectancy_R']:+.4f} R** |
| profit factor (R) | {w['profit_factor_R']:.3f} |
| median hold | {w['median_hold_min']:.1f} min |
| max drawdown | {w['max_drawdown_R']:.2f} R |

## Against matched random

| statistic | strategy | matched control | Δ | 95 % day-block CI |
|---|---:|---:|---:|---|
| expectancy (R) | {w['expectancy_R']:+.4f} | {R[s]['matched_control']['expectancy_R']:+.4f} | {v['expectancy_R']['diff']:+.4f} | [{v['expectancy_R']['ci95_lo']:+.4f}, {v['expectancy_R']['ci95_hi']:+.4f}] |
| win rate | {w['win_rate']:.4f} | {R[s]['matched_control']['win_rate']:.4f} | {v['win_rate']['diff']:+.4f} | [{v['win_rate']['ci95_lo']:+.4f}, {v['win_rate']['ci95_hi']:+.4f}] |

The interval contains zero. Absolute performance is positive, the advantage over
a random entry in the same context is not — the same pattern as every other
period.
{seal}
### Nothing changed after seeing this

The candidate was rejected before this diagnostic ran and remains rejected.
2026-Q1 remains sealed.
""")
print("wrote part 2")
for x in sorted(REP.glob("*.md")):
    print("  ", x.name, x.stat().st_size)
