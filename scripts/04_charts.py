"""Random-sample diagnostic charts: 20 winners, 20 losers, 20 skipped candidates."""
import argparse, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import polars as pl

from nqr import paths
from nqr.viz.charts import plot_trade

ap = argparse.ArgumentParser()
ap.add_argument("--tag", required=True)
ap.add_argument("--variant", default="ANY")
ap.add_argument("--n", type=int, default=20)
ap.add_argument("--seed", type=int, default=20260819)
a = ap.parse_args()

bars = pl.read_parquet(paths.CACHE_DIR / "bars" / "bars_2m.parquet").sort("bar_ns")
tr = pl.read_parquet(paths.RESULTS_DIR / f"fast_slow_{a.tag}" / f"trades_{a.variant}.parquet")
acc = tr.filter(pl.col("status") == "ACCEPTED")
groups = {
    "winners": acc.filter(pl.col("r1_points") > 0),
    "losers": acc.filter(pl.col("r1_points") <= 0),
    "skipped": tr.filter(pl.col("status") == "SKIPPED"),
}
rej_path = paths.RESULTS_DIR / f"fast_slow_{a.tag}" / "abc_rejects.parquet"
if rej_path.exists():
    groups["rejected_abc"] = pl.read_parquet(rej_path)
rng = np.random.default_rng(a.seed)
out_root = paths.REPORTS_DIR / "charts" / f"{a.tag}_{a.variant}"
made = {}
for name, df in groups.items():
    d = out_root / name
    d.mkdir(parents=True, exist_ok=True)
    if df.height == 0:
        made[name] = 0
        continue
    # RANDOM sample - never hand-picked
    idx = rng.choice(df.height, size=min(a.n, df.height), replace=False)
    idx.sort()
    n = 0
    for i in idx:
        row = df.row(int(i), named=True)
        try:
            plot_trade(row, bars, d / f"{name}_{row['trading_date']}_{row['signal_ns']}.png")
            n += 1
        except Exception as e:                      # never let one bad chart stop the run
            print(f"  chart failed {row['trading_date']}: {e}")
    made[name] = n
print(f"charts written under {out_root}: {made}")
