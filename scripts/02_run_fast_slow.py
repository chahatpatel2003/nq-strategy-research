"""Run the Fast-Slow baseline over a date range.

    python scripts/02_run_fast_slow.py --split dev
    python scripts/02_run_fast_slow.py --split val

The holdout guard rejects any --start/--end on or after 2025-01-01 unless
--unlock-holdout is passed (which Phase 1 never does).
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
from nqr.data.cache import BARS_DIR, TICKS_DIR, load_month_ticks, month_keys
from nqr.holdout import assert_range_allowed, unlock_holdout, split_of
from nqr.levels.build import (build_level_segments, daily_atr, day_extremes,
                              session_extremes, segments_to_frame)
from nqr.sessions.calendar import day_bounds_utc, to_utc, ET
from nqr.signals import triggers as TG
from nqr.execution.simulate import simulate_day
from strategies.fast_slow.runner import (VARIANTS, find_candidates, order_key,
                                         select_variant)

NS = 1_000_000_000

ap = argparse.ArgumentParser()
ap.add_argument("--split", choices=["dev", "val"], required=True)
ap.add_argument("--config", default=str(ROOT / "config" / "fast_slow_baseline.yaml"))
ap.add_argument("--unlock-holdout", action="store_true")
ap.add_argument("--tag", default=None)
a = ap.parse_args()
if a.unlock_holdout:
    unlock_holdout("I_AM_DELIBERATELY_UNSEALING_THE_HOLDOUT")

cfg = yaml.safe_load(Path(a.config).read_text())
s, e = cfg["reporting"]["splits"][a.split]
start, end = dt.date.fromisoformat(s), dt.date.fromisoformat(e)
assert_range_allowed(start, end, f"--split {a.split}")
tag = a.tag or a.split
print(f"split={a.split} {start}..{end} spec={cfg['spec_version']}")

t0 = time.time()
bars = pl.read_parquet(BARS_DIR / "bars_2m.parquet")
front = pl.read_parquet(paths.RESULTS_DIR / "front_map.parquet")
roll_days = set(front.filter(pl.col("is_roll_day"))["trading_date"].to_list())

# ---- levels are built from the FULL available history so that the first day
# ---- of a split still has its previous-day levels and a warm ATR window.
sess_ext = session_extremes(bars.filter(pl.col("session") != "HALT"))
day_ext = day_extremes(bars)
atr = daily_atr(day_ext, lookback=20)
all_dates = sorted(bars["trading_date"].unique().to_list())
segs_all = build_level_segments(
    all_dates, sess_ext, day_ext, atr,
    min_session_bars=cfg["levels"]["min_session_bars"],
    tol_atr_frac=cfg["levels"]["tolerance_atr_frac"],
    tol_min=cfg["levels"]["tolerance_min_points"],
    tol_max=cfg["levels"]["tolerance_max_points"],
    dedup_mult=cfg["levels"]["dedup_tolerance_mult"],
)
segs_by_day: dict[dt.date, list] = {}
for sg in segs_all:
    segs_by_day.setdefault(sg.trading_date, []).append(sg)
segments_to_frame(segs_all).write_parquet(paths.RESULTS_DIR / f"level_segments_{tag}.parquet")
print(f"levels built ({len(segs_all)} segments) at {time.time()-t0:.0f}s")

# ---- global causal arrays -------------------------------------------------
bars = bars.sort("bar_ns")
o = bars["open"].to_numpy(); h = bars["high"].to_numpy()
l = bars["low"].to_numpy(); c = bars["close"].to_numpy()
bar_ns_all = bars["bar_ns"].to_numpy()
tdates = bars["trading_date"].to_list()
tcode = np.array([d.toordinal() for d in tdates], dtype=np.int64)
atr2m = TG.atr2m(h, l, c, cfg["trigger"]["atr2m_lookback"])
trig = TG.all_triggers(o, h, l, c, atr2m, cfg["trigger"])
atr_map = {r["trading_date"]: r["atr20_prev"] for r in atr.iter_rows(named=True)}

day_start_idx: dict[dt.date, tuple[int, int]] = {}
i = 0
while i < len(tcode):
    j = i
    while j + 1 < len(tcode) and tcode[j + 1] == tcode[i]:
        j += 1
    day_start_idx[tdates[i]] = (i, j + 1)
    i = j + 1

# ---- walk the split day by day, month-chunked tick loading ----------------
dates = [d for d in all_dates if start <= d <= end]
all_rows = {v: [] for v in VARIANTS}
all_rejects = []
cand_count = 0
skipped_days = {"ROLL_DAY": 0, "NO_LEVELS": 0, "NO_ATR": 0, "TOO_FEW_BARS": 0}
cur_ym, ts_arr, px_arr = None, None, None

for d in dates:
    if d in roll_days:
        skipped_days["ROLL_DAY"] += 1
        continue
    if d not in segs_by_day:
        skipped_days["NO_LEVELS"] += 1
        continue
    a20 = atr_map.get(d)
    if a20 is None or not np.isfinite(a20):
        skipped_days["NO_ATR"] += 1
        continue
    g0, g1 = day_start_idx[d]
    if g1 - g0 < 60:
        skipped_days["TOO_FEW_BARS"] += 1
        continue
    day_bars = bars[g0:g1]
    cands, rej = find_candidates(day_bars, segs_by_day[d], cfg, trig, g0,
                                 bar_ns_all, tcode, o, h, l, c, float(a20))
    all_rejects.extend(rej)
    cand_count += len(cands)
    if not cands:
        continue
    ym = f"{d.year:04d}-{d.month:02d}"
    if ym != cur_ym:
        tk = load_month_ticks(ym)
        ts_arr = tk["ts_ns"].to_numpy()
        px_arr = tk["px_ticks"].to_numpy().astype(np.int64)
        cur_ym = ym
        print(f"  ticks {ym}: {len(ts_arr):,}  [{time.time()-t0:.0f}s]", flush=True)
    _, day_end = day_bounds_utc(d)
    day_end_ns = int(day_end.timestamp() * NS)
    hh, mm = cfg["targets"]["timeout_exit_et"].split(":")
    timeout_ns = int(to_utc(d, dt.time(int(hh), int(mm))).timestamp() * NS)
    for vname, fams in VARIANTS.items():
        sel = select_variant(cands, fams, cfg["trigger"]["precedence"])
        if sel:
            all_rows[vname].extend(simulate_day(sel, ts_arr, px_arr,
                                                day_end_ns, timeout_ns, cfg))

out_dir = paths.RESULTS_DIR / f"fast_slow_{tag}"
out_dir.mkdir(parents=True, exist_ok=True)
meta = {"split": a.split, "start": str(start), "end": str(end),
        "spec_version": cfg["spec_version"], "abc_candidates": cand_count,
        "days_considered": len(dates), "days_skipped": skipped_days,
        "runtime_s": round(time.time() - t0, 1)}
for v, rows in all_rows.items():
    if not rows:
        continue
    df = pl.DataFrame(rows, strict=False)
    df.write_parquet(out_dir / f"trades_{v}.parquet")
    meta[f"signals_{v}"] = df.height
    meta[f"accepted_{v}"] = int((df["status"] == "ACCEPTED").sum())
if all_rejects:
    pl.DataFrame(all_rejects, strict=False).write_parquet(out_dir / "abc_rejects.parquet")
(out_dir / "run_meta.json").write_text(json.dumps(meta, indent=2, default=str))
print(json.dumps(meta, indent=2, default=str))
