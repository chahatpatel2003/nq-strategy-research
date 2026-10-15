"""Build the front-contract map, the tick cache and the 2-minute bar table.

Reads only halves permitted by the holdout guard.  Original T9 files are
opened read-only; every output lands in ./data_cache and ./results.
"""
import sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import polars as pl
import yaml

from nqr import paths
from nqr.data.audit import connect
from nqr.data.cache import (TICKS_DIR, BARS_DIR, build_tick_cache,
                            load_month_ticks, build_bars_from_ticks, month_keys)
from nqr.data.contracts import build_front_map, roll_dates
from nqr.holdout import assert_paths_allowed
from nqr.sessions.calendar import add_session

cfg = yaml.safe_load((ROOT / "config" / "fast_slow_baseline.yaml").read_text())

t0 = time.time()
dv = pl.read_parquet(paths.RESULTS_DIR / "contract_daily_volume.parquet")
front = build_front_map(dv)
front.write_parquet(paths.RESULTS_DIR / "front_map.parquet")
rolls = roll_dates(front)
rolls.write_parquet(paths.RESULTS_DIR / "roll_dates.parquet")
print(f"front map: {front.height} trading days, {rolls.height} roll days")

files = paths.allowed_half_files("trades")
assert_paths_allowed(files.values())

con = connect(memory_limit="6GB", threads=8)
con.register("front_map_pl", front.select(["trading_date", "front_symbol"]).to_pandas())
con.execute("CREATE OR REPLACE TABLE front_map AS SELECT * FROM front_map_pl")

if TICKS_DIR.exists() and any(TICKS_DIR.iterdir()):
    print("tick cache already present - skipping (delete data_cache/ticks to rebuild)")
else:
    build_tick_cache(con, files, cfg["contracts"]["outright_regex"])
print(f"ticks done at {time.time()-t0:.0f}s")

BARS_DIR.mkdir(parents=True, exist_ok=True)
mks = sorted(p.name.split("=")[1] for p in TICKS_DIR.glob("ym=*"))
parts = []
for ym in mks:
    tk = load_month_ticks(ym)
    if tk.height == 0:
        continue
    b = build_bars_from_ticks(tk, cfg["data"]["bar_minutes"])
    parts.append(b)
    print(f"  bars {ym}: {b.height} bars from {tk.height} ticks", flush=True)
bars = pl.concat(parts).sort("bar_ns")
bars = bars.with_columns(
    pl.from_epoch(pl.col("bar_ns"), time_unit="ns").dt.replace_time_zone("UTC").alias("bar_start"),
    pl.from_epoch(pl.col("bar_end_ns"), time_unit="ns").dt.replace_time_zone("UTC").alias("bar_end"),
)
bars = add_session(bars, "bar_start")
bars.write_parquet(BARS_DIR / "bars_2m.parquet")
print(f"bars: {bars.height} rows, {bars['trading_date'].n_unique()} trading days, "
      f"{time.time()-t0:.0f}s total")
