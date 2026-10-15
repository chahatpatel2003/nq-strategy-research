"""Build the Phase-3 FRESH VALIDATION cache: 2025-07-01 .. 2025-12-31 only.

Reads `2025_H2.parquet` and nothing else.  2025-H1 and 2026 are refused by
`nqr.p3.holdout3` with no unlock path.

The front contract for each 2025-H2 day uses the standard previous-trading-day
volume rule computed WITHIN 2025-H2, so 2025-H1 is never consulted.  The first
day therefore has no prior basis and is flagged a roll day and excluded - one
day out of ~128, at zero cost to the seal.
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
from nqr.p3 import cache3
from nqr.p3 import holdout3 as H3

ap = argparse.ArgumentParser()
ap.add_argument("--confirm", required=True,
                help="must be the exact Phase-3 validation unlock phrase")
a = ap.parse_args()
H3.unlock_phase3_validation(a.confirm)

cfg = yaml.safe_load((ROOT / "config" / "fast_slow_baseline.yaml").read_text())
OUTRIGHT = cfg["contracts"]["outright_regex"]

trades_dir = paths.find_dataset_dir("trades")
val_file = trades_dir / "2025_H2.parquet"
H3.assert_path_allowed(val_file)
for forbidden in ("2025_H1.parquet", "2026_H1.parquet"):
    try:
        H3.assert_path_allowed(trades_dir / forbidden)
        raise SystemExit(f"SAFETY FAILURE: {forbidden} was not blocked")
    except H3.Phase3Violation:
        pass
print(f"validation source: {val_file}")
print("2025_H1 and 2026_H1 verified blocked by the guard")

con = connect(memory_limit="6GB", threads=6)
con.execute(f"SET temp_directory='{ROOT/'data_cache'/'duckdb_tmp'}';")

t0 = time.time()
dv = cache3.validation_daily_volume(con, val_file, OUTRIGHT)
front = build_front_map(dv)
front.write_parquet(paths.RESULTS_DIR / "front_map_p3val.parquet")
r = roll_dates(front)
print(f"front map: {front.height} trading days, {r.height} excluded roll days "
      f"(incl. the first day, which has no prior basis)")
print(r.select(["trading_date", "front_symbol"]).to_pandas().to_string(index=False))

if cache3.P3_TICKS.exists() and any(cache3.P3_TICKS.iterdir()):
    print("p3 validation tick cache already present - skipping")
else:
    cache3.build_validation_cache(con, val_file, OUTRIGHT, front)
print(f"done in {time.time()-t0:.0f}s")
