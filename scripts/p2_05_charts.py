"""Random-sample diagnostic charts (never cherry-picked)."""
import argparse, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import numpy as np
import polars as pl
import yaml

from nqr.p2 import cache2
from nqr.p2.charts import plot_candidate
from strategies.impulse_exhaustion.runner import build_day_grid

ap = argparse.ArgumentParser()
ap.add_argument("--tag", required=True)
ap.add_argument("--n", type=int, default=20)
ap.add_argument("--seed", type=int, default=20260819)
ap.add_argument("--config", default=str(ROOT / "strategies" / "impulse_exhaustion" /
                                        "config" / "baseline.yaml"))
a = ap.parse_args()
cfg = yaml.safe_load(Path(a.config).read_text())
RUN = ROOT / "strategies" / "impulse_exhaustion" / "results" / f"run_{a.tag}"
OUT = ROOT / "strategies" / "impulse_exhaustion" / "diagnostics" / f"charts_{a.tag}"

t = pl.read_parquet(RUN / "trades.parquet")
acc = t.filter(pl.col("status") == "ACCEPTED")
groups = {
    "winners": acc.filter(pl.col("r1p0_points") > 0),
    "losers": acc.filter(pl.col("r1p0_points") <= 0),
    "rejected_or_skipped": t.filter(pl.col("status") == "SKIPPED"),
}
if acc.height and "absorption_pct" in acc.columns:
    s = acc.sort("absorption_pct", descending=True)
    groups["highest_absorption"] = s.head(max(a.n * 2, 40))
    groups["lowest_qualifying_absorption"] = s.tail(max(a.n * 2, 40))

rng = np.random.default_rng(a.seed)
made = {}
# cache day grids lazily, one month at a time
need_days = sorted({r for df in groups.values() if df.height
                    for r in df["trading_date"].to_list()})
picks = {}
for name, df in groups.items():
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    if df.height == 0:
        made[name] = 0; continue
    idx = rng.choice(df.height, size=min(a.n, df.height), replace=False)
    picks[name] = [df.row(int(i), named=True) for i in sorted(idx)]
    made[name] = 0

by_day = {}
for name, rows in picks.items():
    for r in rows:
        by_day.setdefault(r["trading_date"], []).append((name, r))

cur_ym, tk_m, bb_m = None, None, None
for d in sorted(by_day):
    ym = f"{d.year:04d}-{d.month:02d}"
    if ym != cur_ym:
        tk_m, bb_m, cur_ym = cache2.load_month_ticks(ym), cache2.load_month_bbo(ym), ym
    dt_ticks = tk_m.filter(pl.col("trading_date") == d)
    dt_bbo = bb_m.filter(pl.col("trading_date") == d) if bb_m.height else pl.DataFrame()
    g = build_day_grid(dt_ticks, dt_bbo, cfg, d)
    if g is None:
        continue
    for name, r in by_day[d]:
        try:
            plot_candidate(r, g, OUT / name / f"{name}_{d}_{r['signal_ns']}.png")
            made[name] += 1
        except Exception as e:
            print(f"  chart failed {d} {name}: {e}")
print(f"charts under {OUT}: {made}")
