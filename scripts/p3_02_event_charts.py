"""Random raw DC-sequence charts (Phase 3A visual validation)."""
import argparse, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import numpy as np, polars as pl, yaml
from nqr import paths
from nqr.p3 import cache3, holdout3 as H3
from nqr.p3.charts3 import plot_events
from strategies.directional_change.runner import build_day_path, et_sec, run_day

ap = argparse.ArgumentParser()
ap.add_argument("--split", default="dev")
ap.add_argument("--n", type=int, default=20)
ap.add_argument("--minutes", type=int, default=12)
ap.add_argument("--seed", type=int, default=20260819)
ap.add_argument("--config", default=str(ROOT / "strategies" / "directional_change" /
                                        "config" / "baseline.yaml"))
a = ap.parse_args()
cfg = yaml.safe_load(Path(a.config).read_text())
start, end = H3.SPLITS[a.split]
front = pl.read_parquet(paths.RESULTS_DIR / "front_map.parquet")
roll = set(front.filter(pl.col("is_roll_day"))["trading_date"].to_list())
OUT = ROOT / "strategies" / "directional_change" / "diagnostics" / f"events_{a.split}"
OUT.mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(a.seed)
months = cache3.months_for(a.split)
pick_m = sorted(rng.choice(len(months), size=min(a.n, len(months)), replace=False))
made = 0
for mi in pick_m:
    m = cache3.load_month(months[mi])
    if m.height == 0:
        continue
    days = [d for d in m["trading_date"].unique().sort().to_list()
            if start <= d <= end and d not in roll]
    if not days:
        continue
    d = days[int(rng.integers(0, len(days)))]
    p = build_day_path(m.filter(pl.col("trading_date") == d), cfg, d)
    if p is None:
        continue
    evs, _ = run_day(p, cfg)
    if not evs:
        continue
    lo_s = et_sec(d, "09:30"); hi_s = et_sec(d, "11:30")
    t0 = int(rng.integers(lo_s, max(hi_s - a.minutes * 60, lo_s + 1)))
    plot_events(p, evs, OUT / f"dcseq_{d}_{t0}.png",
                t0 * 10**9, (t0 + a.minutes * 60) * 10**9,
                title=f" | random {a.minutes}-minute window")
    made += 1
print(f"{made} raw DC-sequence charts under {OUT}")
