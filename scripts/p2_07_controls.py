"""Pre-registered random-control and label-shuffle null tests.

Both procedures were fixed in IMPULSE_EXHAUSTION_SPEC.md §13 before running.
Neither may touch holdout data.
"""
import argparse, json, sys, datetime as dt
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import numpy as np
import polars as pl
import yaml
from scipy import stats as sps

from nqr import paths
from nqr.metrics.stats import wilson_ci
from nqr.p2 import cache2
from nqr.p2.controls import (bootstrap_diff_ci, control_entries, label_shuffle_null,
                             permutation_p, resolve_control)
from nqr.p2.metrics2 import enrich
from strategies.impulse_exhaustion.runner import build_day_grid, _et_sec

NS = 1_000_000_000
ap = argparse.ArgumentParser()
ap.add_argument("--tag", required=True)
ap.add_argument("--k", type=int, default=5)
ap.add_argument("--n-boot", type=int, default=5000)
ap.add_argument("--n-perm", type=int, default=5000)
ap.add_argument("--n-null", type=int, default=2000)
ap.add_argument("--seed", type=int, default=20260819)
ap.add_argument("--window", default="w_0930_1130")
ap.add_argument("--config", default=str(ROOT / "strategies" / "impulse_exhaustion" /
                                        "config" / "baseline.yaml"))
a = ap.parse_args()

cfg = yaml.safe_load(Path(a.config).read_text())
RUN = ROOT / "strategies" / "impulse_exhaustion" / "results" / f"run_{a.tag}"
t = enrich(pl.read_parquet(RUN / "trades.parquet"))
acc = t.filter((pl.col("status") == "ACCEPTED") & pl.col(a.window))
print(f"{acc.height} accepted signals in {a.window}")
if acc.height == 0:
    raise SystemExit("no trades")

rng = np.random.default_rng(a.seed)
lat = int(cfg["entry"]["latency_ms"]) * 1_000_000
maxw = int(cfg["entry"]["max_wait_ms"]) * 1_000_000
FR = cfg["costs"]["primary_friction_points"]

by_day = {}
for r in acc.iter_rows(named=True):
    by_day.setdefault(r["trading_date"], []).append(r)

ctrl_rows, ts_by_day, sig_rows = [], {}, []
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
    ts = dt_ticks["ts_ns"].to_numpy()
    px = dt_ticks["px_ticks"].to_numpy().astype(np.int64)
    hard = _et_sec(d, cfg["targets"]["hard_exit_et"]) * NS
    ts_by_day[d] = (ts, px, hard)
    for r in by_day[d]:
        sig_rows.append(r)
        # matched 30-minute time-of-day bucket
        b0 = (r["signal_ns"] // NS // 1800) * 1800
        for ci in control_entries(rng, g.sec, g.traded, g.vu, b0, b0 + 1800, a.k):
            end_ns = min(hard, int((g.sec[ci] + 1)) * NS + int(cfg["targets"]["max_hold_seconds"]) * NS)
            c = resolve_control(ts, px, int((g.sec[ci] + 1) * NS), r["direction"],
                                r["r_points"], end_ns, lat, maxw)
            if c:
                c.update(trading_date=d, matched_signal_ns=r["signal_ns"])
                ctrl_rows.append(c)

ctrl = pl.DataFrame(ctrl_rows, strict=False)
sig_pts = acc["r1p0_points"].to_numpy() - FR
sig_R = sig_pts / acc["r_points"].to_numpy()
ctrl_pts = ctrl["points"].to_numpy() - FR
ctrl_R = ctrl_pts / ctrl["r_points"].to_numpy()
sw = (sig_pts > 0).astype(float)
cw = (ctrl_pts > 0).astype(float)

d_wr, lo_wr, hi_wr = bootstrap_diff_ci(sw, cw, a.n_boot, np.random.default_rng(a.seed + 1))
d_R, lo_R, hi_R = bootstrap_diff_ci(sig_R, ctrl_R, a.n_boot, np.random.default_rng(a.seed + 2))
p_wr = permutation_p(sw, cw, a.n_perm, np.random.default_rng(a.seed + 3))
p_R = permutation_p(sig_R, ctrl_R, a.n_perm, np.random.default_rng(a.seed + 4))

long_frac = float((acc["direction"] > 0).mean())
null = label_shuffle_null(ts_by_day, [
    {"trading_date": r["trading_date"], "entry_ns": r["entry_ns"],
     "entry_price": r["entry_price"], "r_points": r["r_points"]} for r in sig_rows],
    a.n_null, np.random.default_rng(a.seed + 5), long_frac)
nwr, nex = null["null_win_rate"], null["null_expectancy_R"]
real_wr = float(sw.mean()); real_ex = float(sig_R.mean())

out = {
    "tag": a.tag, "window": a.window, "friction_points": FR,
    "signal": {"n": int(acc.height), "win_rate": real_wr,
               "win_rate_ci95": list(wilson_ci(int(sw.sum()), len(sw))),
               "expectancy_R": real_ex},
    "control": {"n": int(ctrl.height), "per_signal": a.k, "win_rate": float(cw.mean()),
                "win_rate_ci95": list(wilson_ci(int(cw.sum()), len(cw))),
                "expectancy_R": float(ctrl_R.mean())},
    "difference": {
        "win_rate_diff": d_wr, "win_rate_diff_ci95": [lo_wr, hi_wr],
        "win_rate_permutation_p": p_wr,
        "expectancy_R_diff": d_R, "expectancy_R_diff_ci95": [lo_R, hi_R],
        "expectancy_R_permutation_p": p_R},
    "label_shuffle_null": {
        "n_replications": a.n_null, "long_fraction_preserved": long_frac,
        "null_win_rate_mean": float(np.nanmean(nwr)),
        "null_win_rate_p05": float(np.nanquantile(nwr, 0.05)),
        "null_win_rate_p95": float(np.nanquantile(nwr, 0.95)),
        "real_win_rate_percentile_in_null": float((nwr < real_wr).mean()),
        "null_expectancy_mean": float(np.nanmean(nex)),
        "null_expectancy_p95": float(np.nanquantile(nex, 0.95)),
        "real_expectancy_percentile_in_null": float((nex < real_ex).mean())},
}
(RUN / "controls.json").write_text(json.dumps(out, indent=2, default=str))
ctrl.write_parquet(RUN / "control_trades.parquet")
print(json.dumps(out, indent=2, default=str))
