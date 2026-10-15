"""PHASE 3A - build and audit the directional-change event log.

Produces the event log only.  No strategy, no P&L.
"""
import argparse, json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import numpy as np
import polars as pl
import yaml

from nqr import paths
from nqr.p3 import cache3
from nqr.p3 import holdout3 as H3
from strategies.directional_change.runner import build_day_path, et_sec, run_day

OUT = ROOT / "strategies" / "directional_change" / "results"
OUT.mkdir(parents=True, exist_ok=True)

ap = argparse.ArgumentParser()
ap.add_argument("--split", choices=list(H3.SPLITS), required=True)
ap.add_argument("--config", default=str(ROOT / "strategies" / "directional_change" /
                                        "config" / "baseline.yaml"))
ap.add_argument("--max-days", type=int, default=0, help="0 = all")
ap.add_argument("--tag", default=None)
ap.add_argument("--unlock-validation", action="store_true")
a = ap.parse_args()
if a.unlock_validation:
    H3.unlock_phase3_validation("I_AM_UNLOCKING_ONLY_2025_H2_FOR_PHASE3_VALIDATION")

cfg = yaml.safe_load(Path(a.config).read_text())
start, end = H3.SPLITS[a.split]
H3.assert_range_allowed(start, end, f"--split {a.split}")
tag = a.tag or a.split
print(f"[PHASE 3A] split={a.split} {start}..{end} spec={cfg['spec_version']}")

front = pl.read_parquet(paths.RESULTS_DIR / "front_map.parquet")
if a.split == "val2025h2":
    front = pl.read_parquet(paths.RESULTS_DIR / "front_map_p3val.parquet")
roll = set(front.filter(pl.col("is_roll_day"))["trading_date"].to_list())

t0 = time.time()
rows, daily = [], []
n_days = 0
for ym in cache3.months_for(a.split):
    m = cache3.load_month(ym)
    if m.height == 0:
        continue
    for d in m["trading_date"].unique().sort().to_list():
        if not (start <= d <= end) or d in roll:
            continue
        if a.max_days and n_days >= a.max_days:
            break
        day = m.filter(pl.col("trading_date") == d)
        p = build_day_path(day, cfg, d)
        if p is None:
            continue
        evs, _ = run_day(p, cfg)
        n_days += 1
        lo = et_sec(d, cfg["reporting"]["primary_window_et"][0])
        hi = et_sec(d, cfg["reporting"]["primary_window_et"][1])
        rth_lo = et_sec(d, cfg["data"]["signal_start_et"])
        rth_hi = et_sec(d, cfg["data"]["signal_end_et"])
        cs = np.array([e.conf_ts // 10**9 for e in evs]) if evs else np.array([])
        daily.append(dict(trading_date=d, symbol=p.symbol, n_ticks=len(p.ts),
                          n_compressed=len(p.c_px), n_events=len(evs),
                          n_events_rth=int(((cs >= rth_lo) & (cs < rth_hi)).sum()),
                          n_events_primary=int(((cs >= lo) & (cs < hi)).sum()),
                          median_theta=float(np.median([e.theta for e in evs])) if evs else np.nan,
                          median_vu=float(np.median([e.vu for e in evs])) if evs else np.nan))
        for e in evs:
            r = dict(trading_date=d, symbol=p.symbol)
            r.update({k: v for k, v in e.__dict__.items()})
            rows.append(r)
    print(f"  {ym}: days={n_days} events={len(rows)}  [{time.time()-t0:.0f}s]", flush=True)
    if a.max_days and n_days >= a.max_days:
        break

ev = pl.DataFrame(rows, strict=False)
dd = pl.DataFrame(daily, strict=False)
d_out = OUT / f"events_{tag}"
d_out.mkdir(parents=True, exist_ok=True)
ev.write_parquet(d_out / "events.parquet")
dd.write_parquet(d_out / "daily.parquet")
meta = {"split": a.split, "start": str(start), "end": str(end),
        "spec_version": cfg["spec_version"], "theta_vu": cfg["event"]["theta_vu"],
        "trading_days": n_days, "n_events": ev.height,
        "events_per_day": ev.height / max(n_days, 1),
        "events_per_day_rth": float(dd["n_events_rth"].mean()) if dd.height else 0,
        "events_per_day_primary": float(dd["n_events_primary"].mean()) if dd.height else 0,
        "median_theta_points": float(ev["theta"].median()) if ev.height else None,
        "median_vu_points": float(ev["vu"].median()) if ev.height else None,
        "runtime_s": round(time.time() - t0, 1)}
(d_out / "meta.json").write_text(json.dumps(meta, indent=2, default=str))
print(json.dumps(meta, indent=2, default=str))
