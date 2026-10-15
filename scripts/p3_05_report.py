"""Phase-3 markdown report for one run."""
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import polars as pl
import yaml

from nqr.metrics.report import df_to_md, kv_table
from nqr.metrics.stats import breakeven_win_rate, by_group, compute
from nqr.p3.metrics3 import TAG_LABEL, TAGS, enrich, window_report

ap = argparse.ArgumentParser()
ap.add_argument("--tag", required=True)
ap.add_argument("--title", default=None)
ap.add_argument("--config", default=str(ROOT / "strategies" / "directional_change" /
                                        "config" / "baseline.yaml"))
a = ap.parse_args()
cfg = yaml.safe_load(Path(a.config).read_text())
RUN = ROOT / "strategies" / "directional_change" / "results" / f"run_{a.tag}"
REP = ROOT / "strategies" / "directional_change" / "reports"
REP.mkdir(parents=True, exist_ok=True)
meta = json.loads((RUN / "run_meta.json").read_text())
FR = cfg["costs"]["round_trip_points_grid"]
PRIM = cfg["costs"]["primary_friction_points"]
WINDOWS = [("w_0930_1130", "09:30-11:30 ET  (PRIMARY)"),
           ("w_0930_1030", "09:30-10:30 ET  (diagnostic)"),
           ("w_1030_1130", "10:30-11:30 ET  (diagnostic)"),
           ("w_0930_1200", "09:30-12:00 ET  (diagnostic)"),
           ("w_0930_1600", "09:30-16:00 ET  (diagnostic)")]
n_days = meta["trading_days"]

S = [f"# {a.title or ('Directional Change — ' + a.tag)}\n"]
if meta.get("is_contaminated_diagnostic"):
    S.append("> # ⚠ 2024 IS NOT FRESH VALIDATION\n>\n"
             "> 2024 was already consumed as the validation split in Phase 1 and Phase 2 "
             "and has therefore already influenced this project's research process. "
             "Everything below is **contaminated diagnostic evidence only** and can "
             "never satisfy a Phase-3 PASS criterion.\n")
if meta.get("is_fresh_validation"):
    S.append("> # FRESH VALIDATION — 2025-H2\n>\n"
             "> Run once, after the freeze, on data never previously touched by this "
             "project. This is the split the pre-registered verdict is based on.\n")
S.append(f"* spec `{meta['spec_version']}` | theta = `{meta['theta_vu']} x VU`")
S.append(f"* period **{meta['start']} .. {meta['end']}**, {n_days} trading days")
S.append(f"* runtime {meta['runtime_s']}s\n")

fams = [f for f in ("DC_A", "DC_B", "DC_C") if (RUN / f"trades_{f}.parquet").exists()]
data = {f: enrich(pl.read_parquet(RUN / f"trades_{f}.parquet")) for f in fams}

# ---------------------------------------------------------- headline -------
rows = []
for f in fams:
    acc = data[f].filter(pl.col("status") == "ACCEPTED")
    for wcol, wlab in WINDOWS:
        sub = acc.filter(pl.col(wcol))
        if sub.height == 0:
            continue
        for fr in FR:
            m = compute(sub, "r1p0", friction=fr, n_days=n_days)
            rows.append({"family": f, "window": wlab.split("  ")[0], "friction": fr,
                         "trades": m["n_trades"], "win_rate": m["win_rate"],
                         "ci_lo": m["win_rate_ci95_lo"], "ci_hi": m["win_rate_ci95_hi"],
                         "expectancy_R": m["expectancy_R"],
                         "expectancy_pts": m["expectancy_points"],
                         "PF": m["profit_factor"], "p_value": m["p_value_gt_breakeven"]})
S.append("## 1. Headline — family x window x round-trip friction (target 1R)\n")
S.append("The no-edge baseline for a symmetric +-1R bracket is 50 %. "
         "`p_value` is the one-sided binomial test against it.\n")
S.append(df_to_md(pl.DataFrame(rows), max_rows=200))

HEAD = [("n_trades", "executed trades"), ("trades_per_day_mean", "trades / day (mean)"),
        ("trades_per_day_median", "trades / day (median)"),
        ("longs", "long"), ("shorts", "short"), ("wins", "wins"), ("losses", "losses"),
        ("win_rate", "win rate"), ("win_rate_ci95_lo", "win rate 95% CI low"),
        ("win_rate_ci95_hi", "win rate 95% CI high"),
        ("breakeven_wr_at_friction", "break-even WR at this friction"),
        ("p_value_gt_breakeven", "p(WR > 50%), one-sided"),
        ("expectancy_R", "expectancy (R)"), ("median_R", "median R"),
        ("expectancy_points", "expectancy (pts)"), ("profit_factor", "profit factor"),
        ("avg_winner_points", "avg winner (pts)"), ("avg_loser_points", "avg loser (pts)"),
        ("avg_R_distance_points", "avg R distance (pts)"),
        ("max_drawdown_R", "max drawdown (R, trade seq)"),
        ("max_drawdown_R_daily", "max drawdown (R, daily)"),
        ("longest_win_streak", "longest winning streak"),
        ("longest_loss_streak", "longest losing streak"),
        ("avg_MFE_points", "avg MFE (pts)"), ("avg_MAE_points", "avg MAE (pts)"),
        ("adverse_excursion_before_winner", "avg MAE on winners (pts)"),
        ("favorable_excursion_before_loser", "avg MFE on losers (pts)"),
        ("avg_hold_min", "avg hold (min)"), ("median_hold_min", "median hold (min)"),
        ("tp_hits", "TP exits"), ("sl_hits", "SL exits"), ("timeouts", "timeout exits"),
        ("t_stat_R", "t-stat of mean R")]
FREQ = [("pct_days_0_trades", "% days with 0 trades"),
        ("pct_days_1_trade", "% days with 1"), ("pct_days_2_trades", "% days with 2"),
        ("pct_days_3_4_trades", "% days with 3-4"),
        ("pct_days_5plus_trades", "% days with 5+"),
        ("trades_per_day_0930_1030", "trades/day 09:30-10:30"),
        ("trades_per_day_1030_1130", "trades/day 10:30-11:30"),
        ("median_minutes_between_trades", "median minutes between trades"),
        ("pct_profitable_days", "% profitable days"),
        ("daily_R_mean", "daily R mean"), ("daily_R_p05", "daily R 5th pct"),
        ("worst_day_R", "max daily loss (R)"),
        ("longest_drawdown_days", "longest stretch below peak (days)")]

for i, f in enumerate(fams, start=2):
    acc = data[f].filter(pl.col("status") == "ACCEPTED")
    sk = data[f].filter(pl.col("status") == "SKIPPED")
    S.append(f"\n## {i}. Family `{f}`\n")
    S.append(f"* signals **{data[f].height:,}** | accepted **{acc.height:,}** | "
             f"skipped **{sk.height:,}**")
    if sk.height:
        S.append("\n" + df_to_md(sk.group_by("skip_reason").len().sort("len", descending=True)))
    prim = acc.filter(pl.col("w_0930_1130"))
    if prim.height == 0:
        S.append("\n_no trades in the primary window_"); continue
    m = window_report(prim, "r1p0", PRIM, n_days)
    S.append(f"\n### {f} — PRIMARY 09:30-11:30 ET, 1R, {PRIM} pt friction\n")
    S.append(kv_table(m, HEAD))
    S.append("\n**Frequency / prop-firm profile**\n")
    S.append(kv_table(m, FREQ))
    S.append("\n**Other windows (1R, primary friction)**\n")
    wr = []
    for wcol, wlab in WINDOWS:
        sub = acc.filter(pl.col(wcol))
        if sub.height == 0:
            continue
        mm = compute(sub, "r1p0", PRIM, n_days=n_days)
        wr.append({"window": wlab.split("  ")[0], "trades": mm["n_trades"],
                   "win_rate": mm["win_rate"], "ci_lo": mm["win_rate_ci95_lo"],
                   "ci_hi": mm["win_rate_ci95_hi"], "expectancy_R": mm["expectancy_R"],
                   "PF": mm["profit_factor"],
                   "trades_per_day": mm["n_trades"] / max(n_days, 1)})
    S.append(df_to_md(pl.DataFrame(wr)))
    S.append("\n**Target sensitivity on the SAME entries (primary window, primary friction)**\n")
    S.append("_1R is the pre-registered primary. Each target is shown against its own "
             "no-edge break-even, so a high hit rate at a small target is not mistaken "
             "for an edge._\n")
    tr = []
    for t in TAGS:
        if f"{t}_points" not in prim.columns:
            continue
        mm = compute(prim, t, PRIM)
        tr.append({"target": TAG_LABEL[t], "trades": mm["n_trades"],
                   "win_rate": mm["win_rate"],
                   "no_edge_breakeven": breakeven_win_rate(t),
                   "excess_vs_breakeven": mm["win_rate"] - breakeven_win_rate(t),
                   "expectancy_R": mm["expectancy_R"], "PF": mm["profit_factor"]})
    S.append(df_to_md(pl.DataFrame(tr)))
    S.append(f"\n### {f} — stability breakdowns (primary window, 1R, primary friction)\n")
    S.append("_Diagnostics only. No subgroup is promoted to the strategy._\n")
    for col, lab in [("year", "Year"), ("month", "Month"), ("side", "Direction"),
                     ("et_hour", "Hour of day"), ("vol_bucket", "Volatility (VU) quartile-ish"),
                     ("theta_bucket", "Theta bucket (pts)"),
                     ("event_size_bucket", "Event size (DC magnitude / theta)"),
                     ("overshoot_bucket", "Prior overshoot / theta")]:
        if col in prim.columns:
            g = by_group(prim, "r1p0", col, PRIM)
            if g.height:
                S.append(f"\n**{lab}**\n")
                S.append(df_to_md(g))

out = REP / f"REPORT_{a.tag}.md"
out.write_text("\n".join(S))
for f in fams:
    acc = data[f].filter(pl.col("status") == "ACCEPTED").filter(pl.col("w_0930_1130"))
    acc.head(50000).write_csv(RUN / f"trades_{f}_primary_sample.csv")
print(f"wrote {out} ({out.stat().st_size/1024:.0f} KB)")
