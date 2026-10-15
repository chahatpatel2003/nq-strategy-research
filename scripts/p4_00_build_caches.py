"""Build the Phase-4 signed tick cache + PDH/PDL table for a later split.

    python scripts/p4_00_build_caches.py --split contam2025h2
    python scripts/p4_00_build_caches.py --split val2026q1 --confirm <phrase>

2021-2024 need nothing: they reuse the Phase-2 signed tick cache and the frozen
Phase-1 2-minute bars, both read-only.

2025-H1 has no code path.  2026-04-01+ has no code path.  The 2026 source file
physically contains April+ rows, so every read of it carries the trading-date
guard AND a per-month timestamp bound; both are asserted before the scan.
"""
import argparse, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import polars as pl
import yaml

from nqr import paths
from nqr.data.audit import connect
from nqr.data.contracts import build_front_map, roll_dates
from nqr.p4 import cache4
from nqr.p4 import holdout4 as H4

SRC = {"contam2025h2": "2025_H2.parquet", "val2026q1": "2026_H1.parquet"}
FRONT_OUT = {"contam2025h2": "front_map_p3val.parquet",
             "val2026q1": "front_map_p4val.parquet"}

ap = argparse.ArgumentParser()
ap.add_argument("--split", choices=list(SRC), required=True)
ap.add_argument("--confirm", default="", help="required for val2026q1")
a = ap.parse_args()
if a.split == "val2026q1":
    H4.unlock_phase4_validation(a.confirm)
    print("*** 2026-Q1 VALIDATION UNLOCK ACTIVE - Q1 ONLY ***")
if a.split == "contam2025h2":
    print("*** CONTAMINATED DIAGNOSTIC DATA - NOT VALIDATION ***")

cfg = yaml.safe_load((ROOT / "config" / "fast_slow_baseline.yaml").read_text())
OUTRIGHT = cfg["contracts"]["outright_regex"]
trades_dir = paths.find_dataset_dir("trades")
src = trades_dir / SRC[a.split]
H4.assert_path_allowed(src)

# prove the seals are live before touching anything
for forbidden in ("2025_H1.parquet", "2026_H2.parquet"):
    try:
        H4.assert_path_allowed(trades_dir / forbidden)
        raise SystemExit(f"SAFETY FAILURE: {forbidden} was not blocked")
    except H4.Phase4Violation:
        pass
for d in (H4.SEALED_H1_START, H4.SEALED_H1_END, H4.SEALED_FINAL_START):
    try:
        H4.assert_date_allowed(d)
        raise SystemExit(f"SAFETY FAILURE: {d} was not blocked")
    except H4.Phase4Violation:
        pass
s, e = H4.SPLITS[a.split]
guard = H4.sql_window_guard(s, e, "ts_event")
print(f"source: {src}\nwindow: {s} .. {e}\nguard : {guard}")
print("2025_H1, 2026_H2, 2025-H1 dates and 2026-04-01+ all verified blocked")

con = connect(memory_limit="6GB", threads=6)
con.execute(f"SET temp_directory='{ROOT/'data_cache'/'duckdb_tmp'}';")

t0 = time.time()
dv = cache4.daily_volume(con, src, OUTRIGHT, a.split)
front = build_front_map(dv)
assert front["trading_date"].min() >= s and front["trading_date"].max() <= e
front.write_parquet(paths.RESULTS_DIR / FRONT_OUT[a.split])
r = roll_dates(front)
print(f"front map: {front.height} trading days, {r.height} excluded roll days "
      f"[{time.time()-t0:.0f}s]")
print(r.select(["trading_date", "front_symbol"]).to_pandas().to_string(index=False))

ext = cache4.build_day_extremes(con, src, OUTRIGHT, front, a.split)
assert ext["trading_date"].min() >= s and ext["trading_date"].max() <= e, "guard leak"
cache4.P4_LEVELS.mkdir(parents=True, exist_ok=True)
ext.write_parquet(cache4.levels_path(a.split))
print(f"day extremes: {ext.height} days "
      f"({ext['trading_date'].min()} .. {ext['trading_date'].max()})  [{time.time()-t0:.0f}s]")

out = cache4.P4_TICKS
have = {p.name.split("=")[1] for p in out.glob("ym=*")} if out.exists() else set()
want = set(cache4.months_for(a.split))
if want <= have:
    print("tick cache already present - skipping")
else:
    cache4.build_tick_cache(con, src, OUTRIGHT, front, a.split)
print(f"done in {time.time()-t0:.0f}s")
