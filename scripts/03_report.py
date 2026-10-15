"""Build the full markdown report + CSV trade logs for one run."""
import argparse, json, sys, datetime as dt
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import polars as pl
import yaml

from nqr import paths
from nqr.metrics.stats import compute, by_group
from nqr.metrics.report import enrich, kv_table, HEADLINE, df_to_md

ap = argparse.ArgumentParser()
ap.add_argument("--tag", required=True)
ap.add_argument("--title", default=None)
ap.add_argument("--config", default=str(ROOT / "config" / "fast_slow_baseline.yaml"))
a = ap.parse_args()

cfg = yaml.safe_load(Path(a.config).read_text())
run_dir = paths.RESULTS_DIR / f"fast_slow_{a.tag}"
meta = json.loads((run_dir / "run_meta.json").read_text())
bars = pl.read_parquet(paths.CACHE_DIR / "bars" / "bars_2m.parquet")
start = dt.date.fromisoformat(meta["start"]); end = dt.date.fromisoformat(meta["end"])
n_days = bars.filter((pl.col("trading_date") >= start) & (pl.col("trading_date") <= end))["trading_date"].n_unique()

FRICTION = cfg["costs"]["round_trip_points_grid"]
GROUPS = [("year", "Year"), ("month", "Month"), ("family", "Level family"),
          ("trigger_type", "Trigger type"), ("side", "Direction"),
          ("session", "Session"), ("tr_bucket", "Fast-Slow time-ratio bucket")]

sec = []
title = a.title or f"Fast-Slow NQ - {a.tag}"
sec.append(f"# {title}\n")
sec.append(f"* spec version: `{meta['spec_version']}`")
sec.append(f"* period: **{meta['start']} .. {meta['end']}** ({n_days} Globex trading days with data)")
rej_p = run_dir / "abc_rejects.parquet"
if rej_p.exists():
    _rej = pl.read_parquet(rej_p)
    _gate_fail = _rej.filter(~pl.col("skip_reason").is_in(["NO_TRIGGER", "LEVEL_BROKEN"])).height
    _no_trig = _rej.height - _gate_fail
    sec.append(f"* A-B-C instances examined: **{_rej.height + meta.get('signals_ANY', 0):,}** "
               f"(rejected by the pattern gates: {_gate_fail:,})")
    sec.append(f"* A-B-C patterns passing every gate: **{_no_trig + meta.get('signals_ANY', 0):,}** "
               f"(of which {_no_trig:,} produced no valid reversal trigger)")
sec.append(f"* reversal-trigger hits before per-pattern dedup: **{meta['abc_candidates']:,}**")
sec.append(f"* days considered: {meta['days_considered']}, skipped: `{json.dumps(meta['days_skipped'])}`")
sec.append(f"* runtime: {meta['runtime_s']}s\n")

variants = ["ANY", "ENGULFING", "PIN", "STAR"]
avail = [v for v in variants if (run_dir / f"trades_{v}.parquet").exists()]

# ---------------- summary matrix across variants / targets / friction -------
rows = []
for v in avail:
    df = enrich(pl.read_parquet(run_dir / f"trades_{v}.parquet"))
    acc = df.filter(pl.col("status") == "ACCEPTED")
    for tag in ("r1", "r2"):
        for f in FRICTION:
            m = compute(acc, tag, friction=f, n_days=n_days)
            rows.append({"variant": v, "target": "1R" if tag == "r1" else "2R",
                         "friction_pts": f, "trades": m.get("n_trades", 0),
                         "win_rate": m.get("win_rate"), "expectancy_R": m.get("expectancy_R"),
                         "expectancy_pts": m.get("expectancy_points"),
                         "total_pts": m.get("total_points"),
                         "profit_factor": m.get("profit_factor"),
                         "max_dd_R": m.get("max_drawdown_R"),
                         "p_value": m.get("p_value_gt_breakeven")})
summary = pl.DataFrame(rows)
sec.append("## 1. Headline matrix - variant x target x round-trip friction\n")
sec.append("Friction is applied as a flat round-trip cost in NQ points on every trade "
           "(entry already pays the modelled first-print slippage on top of this).\n")
sec.append(df_to_md(summary))
sec.append("")

# ---------------- per-variant detail ---------------------------------------
for v in avail:
    df = enrich(pl.read_parquet(run_dir / f"trades_{v}.parquet"))
    acc = df.filter(pl.col("status") == "ACCEPTED")
    skip = df.filter(pl.col("status") == "SKIPPED")
    sec.append(f"\n## 2.{avail.index(v)+1} Variant `{v}`\n")
    sec.append(f"* signals generated: **{df.height}** | accepted: **{acc.height}** | "
               f"skipped: **{skip.height}**")
    if skip.height:
        sr = skip.group_by("skip_reason").len().sort("len", descending=True)
        sec.append("\nSkip reasons:\n")
        sec.append(df_to_md(sr))
    if acc.height == 0:
        continue
    rth = acc.filter(pl.col("is_0930_1130"))
    sec.append(f"\n* 09:30-11:30 ET trades: **{rth.height}** "
               f"({rth.height / max(n_days,1):.3f} / trading day)")
    for tag, lab in (("r1", "1R (primary)"), ("r2", "2R (secondary)")):
        m = compute(acc, tag, friction=0.0, n_days=n_days)
        sec.append(f"\n### {v} - target {lab} - GROSS (0.0 pts friction)\n")
        sec.append(kv_table(m, HEADLINE))
        for fr in FRICTION[1:]:
            mf = compute(acc, tag, friction=fr, n_days=n_days)
            sec.append(f"\n<small>friction {fr} pts -> expectancy {mf['expectancy_R']:.4f} R "
                       f"/ {mf['expectancy_points']:.3f} pts, PF {mf['profit_factor']:.3f}, "
                       f"total {mf['total_points']:.1f} pts</small>\n")
    # breakdowns on the primary target, gross
    sec.append(f"\n### {v} - breakdowns (target 1R, gross)\n")
    for col, lab in GROUPS:
        sec.append(f"\n**{lab}**\n")
        sec.append(df_to_md(by_group(acc, "r1", col)))
    sec.append("\n**09:30-11:30 ET subset**\n")
    if rth.height:
        m = compute(rth, "r1", 0.0, n_days=n_days)
        sec.append(kv_table(m, HEADLINE[:14]))
    else:
        sec.append("_(none)_")

# ---------------- rejected A-B-C diagnostics --------------------------------
rj = run_dir / "abc_rejects.parquet"
if rj.exists():
    r = pl.read_parquet(rj)
    sec.append("\n## 3. A-B-C candidates rejected before any trigger test\n")
    sec.append(df_to_md(r.group_by("skip_reason").len().sort("len", descending=True)))

out = paths.REPORTS_DIR / f"REPORT_{a.tag}.md"
out.write_text("\n".join(sec))

# CSV trade logs
for v in avail:
    df = enrich(pl.read_parquet(run_dir / f"trades_{v}.parquet"))
    df.write_csv(run_dir / f"trades_{v}.csv")
summary.write_csv(run_dir / "summary_matrix.csv")
print(f"wrote {out} ({out.stat().st_size/1024:.0f} KB)")
