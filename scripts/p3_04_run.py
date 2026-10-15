"""Run the frozen Phase-3 baseline over one split.

    python scripts/p3_04_run.py --split dev
    python scripts/p3_04_run.py --split diag2024
    python scripts/p3_04_run.py --split val2025h2 --unlock-validation

2025-H1 and 2026 have no code path.
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
from nqr.p3.strategies import FAMILIES
import polars as _pl
from strategies.directional_change.runner import (P3_SCHEMA_OVERRIDES, build_day_path,
                                                  run_day, simulate, target_tags)

OUT = ROOT / "strategies" / "directional_change" / "results"

ap = argparse.ArgumentParser()
ap.add_argument("--split", choices=list(H3.SPLITS), required=True)
ap.add_argument("--config", default=str(ROOT / "strategies" / "directional_change" /
                                        "config" / "baseline.yaml"))
ap.add_argument("--tag", default=None)
ap.add_argument("--unlock-validation", action="store_true")
ap.add_argument("--theta-vu", type=float, default=None,
                help="DIAGNOSTIC sensitivity only; the baseline is the frozen value")
ap.add_argument("--save-events", action="store_true")
a = ap.parse_args()
if a.unlock_validation:
    H3.unlock_phase3_validation("I_AM_UNLOCKING_ONLY_2025_H2_FOR_PHASE3_VALIDATION")

cfg = yaml.safe_load(Path(a.config).read_text())
if a.theta_vu is not None:
    cfg["event"] = {**cfg["event"], "theta_vu": a.theta_vu}
tag = a.tag or (a.split if a.theta_vu is None else f"{a.split}_theta{a.theta_vu}")
start, end = H3.SPLITS[a.split]
H3.assert_range_allowed(start, end, f"--split {a.split}")
print(f"split={a.split} {start}..{end} spec={cfg['spec_version']} "
      f"theta={cfg['event']['theta_vu']}xVU tag={tag}")
if a.split == "diag2024":
    print("*** 2024 IS NOT FRESH VALIDATION - CONTAMINATED DIAGNOSTIC ONLY ***")

fm = "front_map_p3val.parquet" if a.split == "val2025h2" else "front_map.parquet"
front = pl.read_parquet(paths.RESULTS_DIR / fm)
roll = set(front.filter(pl.col("is_roll_day"))["trading_date"].to_list())

t0 = time.time()
books = {f: [] for f in FAMILIES}
ev_rows, daily = [], []
n_days = 0
for ym in cache3.months_for(a.split):
    m = cache3.load_month(ym)
    if m.height == 0:
        continue
    for d in m["trading_date"].unique().sort().to_list():
        if not (start <= d <= end) or d in roll:
            continue
        p = build_day_path(m.filter(pl.col("trading_date") == d), cfg, d)
        if p is None:
            continue
        evs, sigs = run_day(p, cfg)
        n_days += 1
        daily.append(dict(trading_date=d, symbol=p.symbol, n_events=len(evs),
                          n_ticks=len(p.ts),
                          **{f"n_sig_{f}": len(sigs[f]) for f in FAMILIES}))
        if a.save_events:
            for e in evs:
                ev_rows.append(dict(trading_date=d, symbol=p.symbol, **e.__dict__))
        for f in FAMILIES:
            if sigs[f]:
                books[f].extend(simulate(sigs[f], p, cfg))
    print(f"  {ym}: days={n_days} "
          + " ".join(f"{f}={len(books[f])}" for f in FAMILIES)
          + f"  [{time.time()-t0:.0f}s]", flush=True)

d_out = OUT / f"run_{tag}"
d_out.mkdir(parents=True, exist_ok=True)
meta = {"split": a.split, "tag": tag, "start": str(start), "end": str(end),
        "spec_version": cfg["spec_version"], "theta_vu": cfg["event"]["theta_vu"],
        "is_contaminated_diagnostic": a.split == "diag2024",
        "is_fresh_validation": a.split == "val2025h2",
        "trading_days": n_days, "runtime_s": round(time.time() - t0, 1)}
for f in FAMILIES:
    if not books[f]:
        meta[f"{f}_signals"] = 0
        continue
    ov = {k: getattr(_pl, v) for k, v in P3_SCHEMA_OVERRIDES.items()}
    for t in target_tags(cfg):
        ov[f"{t}_outcome"] = _pl.String
        ov[f"{t}_exit_ns"] = _pl.Int64
        for c in ("exit_price", "points", "R", "mfe", "mae", "hold_s"):
            ov[f"{t}_{c}"] = _pl.Float64
        for fr in cfg["costs"]["round_trip_points_grid"]:
            ov[f"{t}_net_{str(fr).replace('.', 'p')}"] = _pl.Float64
    df = pl.DataFrame(books[f], strict=False, schema_overrides=ov)
    df.write_parquet(d_out / f"trades_{f}.parquet")
    meta[f"{f}_signals"] = df.height
    meta[f"{f}_accepted"] = int((df["status"] == "ACCEPTED").sum())
    meta[f"{f}_skipped"] = int((df["status"] == "SKIPPED").sum())
pl.DataFrame(daily, strict=False).write_parquet(d_out / "daily.parquet")
if ev_rows:
    pl.DataFrame(ev_rows, strict=False).write_parquet(d_out / "events.parquet")
(d_out / "run_meta.json").write_text(json.dumps(meta, indent=2, default=str))
print(json.dumps(meta, indent=2, default=str))
