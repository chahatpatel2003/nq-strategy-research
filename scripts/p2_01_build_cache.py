"""Phase-2 cache build: signed front-contract ticks + 1-second MBP-1 BBO.

Reads only halves permitted by the Phase-1 holdout guard.  Original T9 files
are read-only.  Phase-1 caches and outputs are untouched.
"""
import argparse, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import polars as pl
import yaml

from nqr import paths
from nqr.data.audit import connect
from nqr.holdout import assert_paths_allowed
from nqr.p2 import cache2

ap = argparse.ArgumentParser()
ap.add_argument("--what", choices=["ticks", "bbo", "both"], default="both")
a = ap.parse_args()

cfg = yaml.safe_load((ROOT / "config" / "fast_slow_baseline.yaml").read_text())
OUTRIGHT = cfg["contracts"]["outright_regex"]

front = pl.read_parquet(paths.RESULTS_DIR / "front_map.parquet")
con = connect(memory_limit="6GB", threads=6)
con.execute(f"SET temp_directory='{ROOT / 'data_cache' / 'duckdb_tmp'}'; SET max_temp_directory_size='12GB';")
con.register("front_map_pl", front.select(["trading_date", "front_symbol"]).to_pandas())
con.execute("CREATE OR REPLACE TABLE front_map AS SELECT * FROM front_map_pl")

t0 = time.time()
if a.what in ("ticks", "both"):
    f = paths.allowed_half_files("trades")
    assert_paths_allowed(f.values())
    print("trade halves:", list(f))
    if cache2.P2_TICKS.exists() and any(cache2.P2_TICKS.iterdir()):
        print("p2 tick cache present - skipping")
    else:
        cache2.build_tick_cache(con, f, OUTRIGHT)
    print(f"ticks done {time.time()-t0:.0f}s")

if a.what in ("bbo", "both"):
    f = paths.allowed_half_files("mbp1")
    assert_paths_allowed(f.values())
    print("mbp1 halves:", list(f))
    if cache2.P2_BBO1S.exists() and any(cache2.P2_BBO1S.iterdir()):
        print("p2 bbo cache present - skipping")
    else:
        cache2.build_bbo_cache(con, f, OUTRIGHT)
    print(f"bbo done {time.time()-t0:.0f}s")
