"""Phase-2 markdown report for one run."""
import argparse, json, sys, datetime as dt
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import polars as pl
import yaml

from nqr import paths
from nqr.metrics.report import df_to_md, kv_table, _fmt
from nqr.metrics.stats import compute, by_group
from nqr.p2.metrics2 import enrich, window_report

ap = argparse.ArgumentParser()
ap.add_argument("--tag", required=True)
ap.add_argument("--title", default=None)
ap.add_argument("--config", default=str(ROOT / "strategies" / "impulse_exhaustion" /
                                        "config" / "baseline.yaml"))
a = ap.parse_args()

cfg = yaml.safe_load(Path(a.config).read_text())
RUN = ROOT / "strategies" / "impulse_exhaustion" / "results" / f"run_{a.tag}"
REP = ROOT / "strategies" / "impulse_exhaustion" / "reports"
REP.mkdir(parents=True, exist_ok=True)
meta = json.loads((RUN / "run_meta.json").read_text())
FR = cfg["costs"]["round_trip_points_grid"]
PRIM = cfg["costs"]["primary_friction_points"]
TAGS = {"r1p0": "1R", "r1p25": "1.25R", "r1p5": "1.5R", "r2p0": "2R"}
WINDOWS = [("w_0930_1130", "09:30-11:30 ET  (PRIMARY)"),
           ("w_0930_1200", "09:30-12:00 ET  (diagnostic)"),
           ("w_0930_1600", "09:30-16:00 ET  (diagnostic)")]

t = pl.read_parquet(RUN / "trades.parquet") if (RUN / "trades.parquet").exists() else pl.DataFrame()
t = enrich(t)
acc_all = t.filter(pl.col("status") == "ACCEPTED") if t.height else t

# trading-day counts per window come from the tick cache calendar
diag = pl.read_parquet(RUN / "daily_diag.parquet") if (RUN / "daily_diag.parquet").exists() else pl.DataFrame()
n_days = diag.height if diag.height else meta["trading_days"]

S = []
S.append(f"# {a.title or ('Impulse Exhaustion — ' + a.tag)}\n")
S.append(f"* spec: `{meta['spec_version']}` | entry stage: `{meta.get('entry_stage')}`"
         f" | ablation: `{meta.get('ablation')}`")
S.append(f"* period **{meta['start']} .. {meta['end']}**, {n_days} Globex trading days processed")
S.append(f"* signals: **{meta['signals']}** | accepted: **{meta.get('accepted', 0)}**"
         f" | skipped: **{meta.get('skipped', 0)}** | rejected candidates: **{meta['rejected_candidates']}**")
S.append(f"* runtime {meta['runtime_s']}s\n")

if t.height and "skip_reason" in t.columns:
    sk = t.filter(pl.col("status") == "SKIPPED").group_by("skip_reason").len().sort("len", descending=True)
    if sk.height:
        S.append("**Skip reasons**\n")
        S.append(df_to_md(sk))

rj = RUN / "rejects.parquet"
if rj.exists():
    r = pl.read_parquet(rj)
    S.append("\n**Candidate rejections (state machine)**\n")
    S.append(df_to_md(r.group_by("reject_reason").len().sort("len", descending=True)))

if acc_all.height == 0:
    S.append("\n_No accepted trades._")
    (REP / f"REPORT_{a.tag}.md").write_text("\n".join(S))
    print(f"wrote {REP / f'REPORT_{a.tag}.md'} (no trades)")
    raise SystemExit(0)

# ------------------------------------------------- headline matrix ----------
rows = []
for wcol, wlab in WINDOWS:
    sub = acc_all.filter(pl.col(wcol))
    for tg, tlab in TAGS.items():
        for f in FR:
            m = compute(sub, tg, friction=f, n_days=n_days)
            rows.append({"window": wlab.split("  ")[0], "target": tlab, "friction": f,
                         "trades": m.get("n_trades", 0), "win_rate": m.get("win_rate"),
                         "expectancy_R": m.get("expectancy_R"),
                         "expectancy_pts": m.get("expectancy_points"),
                         "PF": m.get("profit_factor"), "total_pts": m.get("total_points"),
                         "maxDD_R": m.get("max_drawdown_R"), "p_value": m.get("p_value_gt_breakeven")})
S.append("\n## 1. Headline matrix — window x target x round-trip friction\n")
S.append(df_to_md(pl.DataFrame(rows), max_rows=100))

# ------------------------------------------------- per-window detail --------
HEAD = [("n_trades", "executed trades"), ("trades_per_day_mean", "trades / trading day"),
        ("longs", "long"), ("shorts", "short"), ("wins", "wins"), ("losses", "losses"),
        ("win_rate", "win rate"), ("win_rate_ci95_lo", "win rate 95% CI low"),
        ("win_rate_ci95_hi", "win rate 95% CI high"),
        ("p_value_gt_breakeven", "p(WR > 50%), one-sided"),
        ("expectancy_R", "expectancy (R)"), ("median_R", "median R"),
        ("expectancy_points", "expectancy (pts)"), ("profit_factor", "profit factor"),
        ("avg_winner_points", "avg winner (pts)"), ("avg_loser_points", "avg loser (pts)"),
        ("max_drawdown_R", "max drawdown (R, trade seq)"),
        ("max_drawdown_R_daily", "max drawdown (R, daily)"),
        ("longest_win_streak", "longest winning streak"),
        ("longest_loss_streak", "longest losing streak"),
        ("avg_MFE_points", "avg MFE (pts)"), ("avg_MAE_points", "avg MAE (pts)"),
        ("adverse_excursion_before_winner", "avg MAE on winners (pts)"),
        ("favorable_excursion_before_loser", "avg MFE on losers (pts)"),
        ("avg_hold_min", "avg hold (min)"), ("median_hold_min", "median hold (min)"),
        ("tp_hits", "TP exits"), ("sl_hits", "SL exits"), ("timeouts", "timeout exits"),
        ("avg_R_distance_points", "avg R distance (pts)"), ("t_stat_R", "t-stat of mean R")]
PROP = [("pct_days_zero_trades", "% days with zero trades"),
        ("pct_days_1_trade", "% days with 1 trade"),
        ("pct_days_2_trades", "% days with 2 trades"),
        ("pct_days_3plus_trades", "% days with 3+ trades"),
        ("trades_per_active_day_median", "median trades / active day"),
        ("pct_profitable_days", "% profitable days"),
        ("daily_R_mean", "daily R mean"), ("daily_R_median", "daily R median"),
        ("daily_R_p05", "daily R 5th pct"), ("daily_R_p95", "daily R 95th pct"),
        ("worst_day_R", "max daily loss (R)"), ("best_day_R", "best day (R)"),
        ("max_recovery_days", "longest drawdown (days below peak)")]

for wi, (wcol, wlab) in enumerate(WINDOWS, start=2):
    sub = acc_all.filter(pl.col(wcol))
    S.append(f"\n## {wi}. {wlab}\n")
    if sub.height == 0:
        S.append("_no trades_"); continue
    m = window_report(sub, "r1p0", PRIM, n_days)
    S.append(f"### 1R target, **{PRIM} pt** round-trip friction (primary friction)\n")
    S.append(kv_table(m, HEAD))
    S.append("\n**Prop-firm daily profile**\n")
    S.append(kv_table(m, PROP))
    S.append("\n**Friction sensitivity (1R)**\n")
    fr_rows = [{"friction": f, **{k: compute(sub, "r1p0", friction=f).get(k) for k in
                                 ("win_rate", "expectancy_R", "expectancy_points",
                                  "profit_factor", "total_points")}} for f in FR]
    S.append(df_to_md(pl.DataFrame(fr_rows)))
    S.append("\n**Hour-of-day (1R, primary friction)**\n")
    S.append(df_to_md(by_group(sub, "r1p0", "et_hour", PRIM)))
    for c, lab in (("w_0930_1030", "09:30-10:30"), ("w_1030_1130", "10:30-11:30")):
        s2 = sub.filter(pl.col(c))
        if s2.height:
            mm = compute(s2, "r1p0", PRIM, n_days=n_days)
            S.append(f"\n* **{lab}**: n={mm['n_trades']} WR={mm['win_rate']:.3f} "
                     f"[{mm['win_rate_ci95_lo']:.3f}, {mm['win_rate_ci95_hi']:.3f}] "
                     f"expR={mm['expectancy_R']:+.4f} PF={mm['profit_factor']:.3f} "
                     f"({mm['n_trades']/max(n_days,1):.3f} trades/day)")

# ------------------------------------------------- breakdowns ---------------
prim = acc_all.filter(pl.col("w_0930_1130"))
S.append("\n## 5. Diagnostic breakdowns — PRIMARY window, 1R, primary friction\n")
S.append("_Diagnostics only. No subgroup is promoted to the strategy._\n")
for col, lab in [("year", "Year"), ("month", "Month"), ("side", "Direction"),
                 ("imp_size_bucket", "Impulse magnitude (x VU)"),
                 ("imp_dur_bucket", "Impulse duration (s)"),
                 ("agg_drop_bucket", "Aggression deterioration (leg3/leg1)"),
                 ("absorption_bucket", "Absorption percentile"),
                 ("stop_bucket", "Stop distance (R / VU)")]:
    if col in prim.columns and prim.height:
        S.append(f"\n**{lab}**\n")
        S.append(df_to_md(by_group(prim, "r1p0", col, PRIM)))

S.append("\n## 6. Target sensitivity on the SAME entries (primary window)\n")
S.append("_1R is the pre-registered primary. The others are diagnostics and are not selected on._\n")
tr = [{"target": tl, **{k: compute(prim, tg, PRIM).get(k) for k in
                        ("n_trades", "win_rate", "expectancy_R", "expectancy_points",
                         "profit_factor", "avg_hold_min")}} for tg, tl in TAGS.items()]
S.append(df_to_md(pl.DataFrame(tr)))

out = REP / f"REPORT_{a.tag}.md"
out.write_text("\n".join(S))
t.write_csv(RUN / "trades.csv")
print(f"wrote {out} ({out.stat().st_size/1024:.0f} KB)")
