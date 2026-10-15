"""Run the frozen impulse-exhaustion baseline over one split.

    python scripts/p2_03_run.py --split dev
    python scripts/p2_03_run.py --split val

The Phase-1 holdout guard rejects any split touching 2025+.
"""
import argparse, datetime as dt, json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import numpy as np
import polars as pl
import yaml

from nqr import paths
from nqr.holdout import assert_range_allowed
from nqr.p2 import cache2
from nqr.p2.absorption import TrailingPercentile
from strategies.impulse_exhaustion.runner import build_day_grid, run_day, simulate_day

NS = 1_000_000_000
OUT = ROOT / "strategies" / "impulse_exhaustion" / "results"
OUT.mkdir(parents=True, exist_ok=True)

ap = argparse.ArgumentParser()
ap.add_argument("--split", choices=["dev", "val"], required=True)
ap.add_argument("--config", default=str(ROOT / "strategies" / "impulse_exhaustion" /
                                        "config" / "baseline.yaml"))
ap.add_argument("--tag", default=None)
ap.add_argument("--ablation", default=None,
                choices=["A_impulse", "B_deterioration", "C_absorption", "D_full"],
                help="DIAGNOSTIC ONLY - the baseline is always D_full")
ap.add_argument("--count-only", action="store_true",
                help="report signal counts only; never computes P&L")
ap.add_argument("--primary-target-only", action="store_true",
                help="resolve only the 1R target (used for the ablation runs)")
ap.add_argument("--max-month", default=None,
                help="stop after this YYYY-MM (smoke tests / partial caches)")
a = ap.parse_args()

cfg = yaml.safe_load(Path(a.config).read_text())
STAGE = {"A_impulse": "IMPULSE", "B_deterioration": "DETERIORATION",
         "C_absorption": "ABSORPTION", "D_full": "FAILED_CONTINUATION"}
entry_stage = STAGE[a.ablation] if a.ablation else "FAILED_CONTINUATION"
tag = a.tag or (a.split if not a.ablation else f"{a.split}_{a.ablation}")

s, e = cfg["reporting"]["splits"][a.split]
start, end = dt.date.fromisoformat(s), dt.date.fromisoformat(e)
assert_range_allowed(start, end, f"--split {a.split}")
print(f"split={a.split} {start}..{end} spec={cfg['spec_version']} tag={tag}")

t0 = time.time()
front = pl.read_parquet(paths.RESULTS_DIR / "front_map.parquet")
roll = set(front.filter(pl.col("is_roll_day"))["trading_date"].to_list())

months = cache2.months_available(cache2.P2_TICKS)
if a.max_month:
    months = [m for m in months if m <= a.max_month]
bbo_months = set(cache2.months_available(cache2.P2_BBO1S))
# absorption history is a rolling window that persists across days, so the run
# must start early enough for it to be warm; we always stream from 2021-01.
hist = {-1: TrailingPercentile(cfg["absorption"]["history_len"],
                               cfg["absorption"]["history_min_obs"]),
        1: TrailingPercentile(cfg["absorption"]["history_len"],
                              cfg["absorption"]["history_min_obs"])}

rows, rejects, diags = [], [], []
n_days = 0
for ym in months:
    if ym not in bbo_months:
        continue                     # BBO is mandatory (cfg data.bbo_required)
    tk_m = cache2.load_month_ticks(ym)
    if tk_m.height == 0:
        continue
    bb_m = cache2.load_month_bbo(ym)
    for d in tk_m["trading_date"].unique().sort().to_list():
        if d in roll:
            continue
        dt_ticks = tk_m.filter(pl.col("trading_date") == d)
        dt_bbo = bb_m.filter(pl.col("trading_date") == d) if bb_m.height else pl.DataFrame()
        g = build_day_grid(dt_ticks, dt_bbo, cfg, d)
        if g is None:
            continue
        cands, rej, diag = run_day(g, cfg, hist, entry_stage)
        in_split = start <= d <= end
        if not in_split:
            continue                      # history still warmed by the day above
        n_days += 1
        diag["trading_date"] = d
        diags.append(diag)
        for r in rej:
            r["trading_date"] = d
            rejects.append(r)
        if cands and not a.count_only:
            ts = dt_ticks["ts_ns"].to_numpy()
            px = dt_ticks["px_ticks"].to_numpy().astype(np.int64)
            rows.extend(simulate_day(cands, g, ts, px, cfg,
                                     primary_only=a.primary_target_only))
        elif cands:
            rows.extend({"trading_date": d, "direction": c.direction,
                         "signal_ns": int((g.sec[c.signal_idx] + 1) * NS)} for c in cands)
    print(f"  {ym}: cum signals={len(rows)}  [{time.time()-t0:.0f}s]", flush=True)

meta = {"split": a.split, "tag": tag, "ablation": a.ablation,
        "entry_stage": entry_stage,
        "start": str(start), "end": str(end), "spec_version": cfg["spec_version"],
        "trading_days": n_days, "signals": len(rows),
        "rejected_candidates": len(rejects),
        "runtime_s": round(time.time() - t0, 1),
        "primary_target_only": bool(a.primary_target_only),
        "count_only": bool(a.count_only)}
d_out = OUT / f"run_{tag}"
d_out.mkdir(parents=True, exist_ok=True)
if rows:
    pl.DataFrame(rows, strict=False).write_parquet(d_out / "trades.parquet")
    if not a.count_only:
        df = pl.DataFrame(rows, strict=False)
        meta["accepted"] = int((df["status"] == "ACCEPTED").sum())
        meta["skipped"] = int((df["status"] == "SKIPPED").sum())
        meta["skip_reasons"] = {k: int(v) for k, v in
                                zip(*df.filter(pl.col("status") == "SKIPPED")
                                    .group_by("skip_reason").len())} if meta["skipped"] else {}
if rejects:
    pl.DataFrame(rejects, strict=False).write_parquet(d_out / "rejects.parquet")
if diags:
    pl.DataFrame(diags, strict=False).write_parquet(d_out / "daily_diag.parquet")
(d_out / "run_meta.json").write_text(json.dumps(meta, indent=2, default=str))
print(json.dumps(meta, indent=2, default=str))
