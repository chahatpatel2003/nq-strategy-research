"""Theta sensitivity — DIAGNOSTIC ONLY, development only.

Pre-authorised in the spec (§10).  These are NOT alternative strategies: the
baseline stays 0.50 x VU whatever this shows, and every grid point is reported
including the bad ones.

Runs in-process and keeps only the few fields the summary needs, so the dense
theta=0.25 grid point does not exhaust memory.  All four thresholds are
evaluated on the SAME strided sample of development days, so they are compared
like for like.
"""
import argparse, json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import numpy as np
import polars as pl
import yaml

from nqr import paths
from nqr.metrics.stats import wilson_ci
from nqr.p3 import cache3, holdout3 as H3
from strategies.directional_change.runner import build_day_path, et_sec, run_day, simulate

ap = argparse.ArgumentParser()
ap.add_argument("--stride", type=int, default=3, help="use every Nth development day")
ap.add_argument("--config", default=str(ROOT / "strategies" / "directional_change" /
                                        "config" / "baseline.yaml"))
a = ap.parse_args()
cfg = yaml.safe_load(Path(a.config).read_text())
GRID = cfg["sensitivity"]["theta_vu_grid"]
BASE = cfg["event"]["theta_vu"]
FR = cfg["costs"]["primary_friction_points"]
RES = ROOT / "strategies" / "directional_change" / "results"
start, end = H3.SPLITS["dev"]

front = pl.read_parquet(paths.RESULTS_DIR / "front_map.parquet")
roll = set(front.filter(pl.col("is_roll_day"))["trading_date"].to_list())

# one fixed day sample, shared by every grid point
days_by_month = {}
for ym in cache3.months_for("dev"):
    m = cache3.load_month(ym)
    if m.height == 0:
        continue
    days_by_month[ym] = [d for d in m["trading_date"].unique().sort().to_list()
                         if start <= d <= end and d not in roll]
all_days = [d for ds in days_by_month.values() for d in ds]
sample = set(sorted(all_days)[::a.stride])
print(f"sensitivity sample: {len(sample)} of {len(all_days)} development days "
      f"(stride {a.stride}), identical for every theta")

rows = []
for th in GRID:
    c = {**cfg, "event": {**cfg["event"], "theta_vu": th}}
    acc = {f: {"pts": [], "r": [], "win": []} for f in ("DC_A", "DC_B", "DC_C")}
    n_days = 0
    t0 = time.time()
    for ym in cache3.months_for("dev"):
        want = [d for d in days_by_month.get(ym, []) if d in sample]
        if not want:
            continue
        m = cache3.load_month(ym)
        for d in want:
            p = build_day_path(m.filter(pl.col("trading_date") == d), c, d)
            if p is None:
                continue
            n_days += 1
            _, sigs = run_day(p, c)
            lo, hi = et_sec(d, "09:30"), et_sec(d, "11:30")
            for f in ("DC_A", "DC_B", "DC_C"):
                if not sigs[f]:
                    continue
                for r in simulate(sigs[f], p, c):
                    if r["status"] != "ACCEPTED" or r["entry_ns"] is None:
                        continue
                    if not (lo <= r["entry_ns"] // 10**9 < hi):
                        continue
                    net = r["r1p0_points"] - FR
                    acc[f]["pts"].append(net)
                    acc[f]["r"].append(r["r_points"])
                    acc[f]["win"].append(r["r1p0_points"] > 0)
    for f, v in acc.items():
        if not v["pts"]:
            continue
        pts = np.array(v["pts"]); r = np.array(v["r"]); w = np.array(v["win"])
        R = pts / r
        gp = pts[pts > 0].sum(); gl = -pts[pts < 0].sum()
        lo_ci, hi_ci = wilson_ci(int(w.sum()), len(w))
        rows.append({"theta_vu": th, "is_baseline": th == BASE, "family": f,
                     "trades": len(pts), "trades_per_day": len(pts) / max(n_days, 1),
                     "median_R_pts": float(np.median(r)),
                     "WR_gross": float(w.mean()), "ci_lo": lo_ci, "ci_hi": hi_ci,
                     "expR_1pt": float(R.mean()),
                     "PF_1pt": float(gp / gl) if gl > 0 else float("inf"),
                     "breakeven_WR_1pt": 0.5 + FR / (2 * float(r.mean()))})
    print(f"  theta={th}: {n_days} days, {time.time()-t0:.0f}s", flush=True)

df = pl.DataFrame(rows).sort(["family", "theta_vu"])
df.write_csv(RES / "sensitivity_theta_dev.csv")
(RES / "sensitivity_meta.json").write_text(json.dumps(
    {"note": "DIAGNOSTIC ONLY. The frozen baseline is theta = 0.50 x VU and is not "
             "changed by anything here. All grid points are reported.",
     "sample_days": len(sample), "stride": a.stride,
     "population_days": len(all_days), "grid": GRID}, indent=2))
print(df.to_pandas().to_string(index=False))
