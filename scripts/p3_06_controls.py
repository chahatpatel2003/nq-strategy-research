"""Pre-registered Phase-3 controls (DIRECTIONAL_CHANGE_SPEC.md §9).

C1  matched random entries      - also the event-time vs clock-time test
C2  direction control           - the same entry resolved the OPPOSITE way
C3  no-edge first-passage baseline

All three were defined before being run.
"""
import argparse, json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import numpy as np
import polars as pl
import yaml

from nqr.backtest.engine import find_entry
from nqr.metrics.stats import wilson_ci
from nqr.p2.controls import bootstrap_diff_ci, permutation_p
from nqr.p3 import cache3, holdout3 as H3
from nqr.p3.fastpass import resolve_fast
from nqr.p3.metrics3 import enrich
from strategies.directional_change.runner import build_day_path, et_sec

NS = 1_000_000_000
ap = argparse.ArgumentParser()
ap.add_argument("--tag", required=True)
ap.add_argument("--split", required=True, choices=list(H3.SPLITS))
ap.add_argument("--k", type=int, default=3)
ap.add_argument("--max-signals", type=int, default=20000,
                help="random subsample for tractability; stated in the report")
ap.add_argument("--n-boot", type=int, default=4000)
ap.add_argument("--n-perm", type=int, default=4000)
ap.add_argument("--seed", type=int, default=20260819)
ap.add_argument("--window", default="w_0930_1130")
ap.add_argument("--unlock-validation", action="store_true")
ap.add_argument("--config", default=str(ROOT / "strategies" / "directional_change" /
                                        "config" / "baseline.yaml"))
a = ap.parse_args()
if a.unlock_validation:
    H3.unlock_phase3_validation("I_AM_UNLOCKING_ONLY_2025_H2_FOR_PHASE3_VALIDATION")

cfg = yaml.safe_load(Path(a.config).read_text())
RUN = ROOT / "strategies" / "directional_change" / "results" / f"run_{a.tag}"
FR = cfg["costs"]["primary_friction_points"]
lat = int(cfg["entry"]["latency_ms"]) * 1_000_000
maxw = int(cfg["entry"]["max_wait_ms"]) * 1_000_000
rng = np.random.default_rng(a.seed)
out = {"tag": a.tag, "split": a.split, "window": a.window, "friction_points": FR,
       "controls_per_signal": a.k, "families": {}}

for fam in ("DC_A", "DC_B", "DC_C"):
    p = RUN / f"trades_{fam}.parquet"
    if not p.exists():
        continue
    t = enrich(pl.read_parquet(p))
    acc = t.filter((pl.col("status") == "ACCEPTED") & pl.col(a.window))
    if acc.height == 0:
        continue
    if acc.height > a.max_signals:
        idx = rng.choice(acc.height, size=a.max_signals, replace=False)
        acc = acc[np.sort(idx)]
        sub = True
    else:
        sub = False
    print(f"{fam}: {acc.height} signals (subsampled={sub})", flush=True)

    by_day = {}
    for r in acc.iter_rows(named=True):
        by_day.setdefault(r["trading_date"], []).append(r)

    ctrl_R, ctrl_w, opp_R, opp_w = [], [], [], []
    t0 = time.time()
    cur_ym, month = None, None
    for d in sorted(by_day):
        ym = f"{d.year:04d}-{d.month:02d}"
        if ym != cur_ym:
            month, cur_ym = cache3.load_month(ym), ym
        day = month.filter(pl.col("trading_date") == d)
        dp = build_day_path(day, cfg, d)
        if dp is None:
            continue
        ts, px = dp.ts, dp.px_t
        hard = et_sec(d, cfg["targets"]["hard_exit_et"]) * NS
        for r in by_day[d]:
            R = r["r_points"]; dirn = r["direction"]
            # ---- C2: the same entry, opposite direction -------------------
            e0 = int(np.searchsorted(ts, r["entry_ns"], side="left"))
            if e0 < len(ts):
                epx = r["entry_price"]
                end = min(hard, r["entry_ns"] + int(cfg["targets"]["max_hold_seconds"]) * NS)
                f = resolve_fast(ts, px, e0, end, -dirn, epx - dirn * R, epx + dirn * R)
                pts = (f.price - epx) * -dirn - FR
                opp_R.append(pts / R); opp_w.append(pts > 0)
            # ---- C1: matched random entries in the same 30-minute bucket ---
            b0 = (r["entry_ns"] // NS // 1800) * 1800
            m = (ts >= b0 * NS) & (ts < (b0 + 1800) * NS)
            cand = np.flatnonzero(m)
            if cand.size == 0:
                continue
            for j in rng.choice(cand.size, size=min(a.k, cand.size), replace=False):
                i0 = int(cand[j])
                ent = find_entry(ts, px, int(ts[i0]) + lat, maxw)
                if ent is None:
                    continue
                ci, cts, cpx = ent
                end = min(hard, cts + int(cfg["targets"]["max_hold_seconds"]) * NS)
                f = resolve_fast(ts, px, ci, end, dirn, cpx + dirn * R, cpx - dirn * R)
                pts = (f.price - cpx) * dirn - FR
                ctrl_R.append(pts / R); ctrl_w.append(pts > 0)

    sig_pts = acc["r1p0_points"].to_numpy() - FR
    sig_R = sig_pts / acc["r_points"].to_numpy()
    sw = (sig_pts > 0).astype(float)
    cw = np.asarray(ctrl_w, float); cR = np.asarray(ctrl_R, float)
    ow = np.asarray(opp_w, float); oR = np.asarray(opp_R, float)

    d_wr, lo_wr, hi_wr = bootstrap_diff_ci(sw, cw, a.n_boot, np.random.default_rng(a.seed + 1))
    d_R, lo_R, hi_R = bootstrap_diff_ci(sig_R, cR, a.n_boot, np.random.default_rng(a.seed + 2))
    p_wr = permutation_p(sw, cw, a.n_perm, np.random.default_rng(a.seed + 3))
    do_wr, lo_o, hi_o = bootstrap_diff_ci(sw, ow, a.n_boot, np.random.default_rng(a.seed + 4))

    out["families"][fam] = {
        "n_signals_used": int(acc.height), "subsampled": bool(sub),
        "signal": {"win_rate": float(sw.mean()),
                   "ci95": list(wilson_ci(int(sw.sum()), len(sw))),
                   "expectancy_R": float(sig_R.mean())},
        "C1_matched_random_control": {
            "n": int(cw.size), "win_rate": float(cw.mean()),
            "ci95": list(wilson_ci(int(cw.sum()), len(cw))),
            "expectancy_R": float(cR.mean()),
            "win_rate_diff_signal_minus_control": d_wr,
            "win_rate_diff_ci95": [lo_wr, hi_wr],
            "win_rate_permutation_p": p_wr,
            "expectancy_R_diff": d_R, "expectancy_R_diff_ci95": [lo_R, hi_R]},
        "C2_direction_control": {
            "n": int(ow.size), "opposite_win_rate": float(ow.mean()),
            "opposite_ci95": list(wilson_ci(int(ow.sum()), len(ow))),
            "opposite_expectancy_R": float(oR.mean()),
            "win_rate_diff_signal_minus_opposite": do_wr,
            "win_rate_diff_ci95": [lo_o, hi_o]},
        "C3_no_edge_baseline_1R": 0.5,
        "runtime_s": round(time.time() - t0, 1),
    }
    print(json.dumps(out["families"][fam], indent=2, default=str), flush=True)

(RUN / "controls.json").write_text(json.dumps(out, indent=2, default=str))
print(f"wrote {RUN/'controls.json'}")
