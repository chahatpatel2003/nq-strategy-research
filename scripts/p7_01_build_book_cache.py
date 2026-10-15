"""Build the Phase-7 per-second MBP-1 book cache for one split.

    python scripts/p7_01_build_book_cache.py --split dev
    python scripts/p7_01_build_book_cache.py --split contam2024
    python scripts/p7_01_build_book_cache.py --split val2025h1 --confirm <phrase>

2025-H2 and 2026 have no code path.
"""
import argparse, json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import polars as pl
import yaml

from nqr import paths
from nqr.data.audit import connect
from nqr.p7 import cache7
from nqr.p7 import holdout7 as H7

ap = argparse.ArgumentParser()
ap.add_argument("--split", choices=["dev", "train2021", "select2022", "itest2023",
                                    "contam2024", "val2025h1"], required=True)
ap.add_argument("--confirm", default="")
ap.add_argument("--months", default="", help="comma-separated YYYY-MM subset, for benchmarking")
ap.add_argument("--threads", type=int, default=6)
ap.add_argument("--memory", default="8GB")
a = ap.parse_args()
if a.split == "val2025h1":
    H7.unlock_phase7_validation(a.confirm)
    print("*** FRESH MBP-1 VALIDATION UNLOCK - 2025-H1 ONLY - ONE SHOT ***")
if a.split == "contam2024":
    print("*** CONTAMINATED DIAGNOSTIC DATA - NOT VALIDATION ***")

s, e = H7.SPLITS[a.split]
H7.assert_range_allowed(s, e, f"--split {a.split}")
# prove the seals are live before touching anything
for forbidden in ("2025_H2.parquet", "2026_H1.parquet", "2026_H2.parquet"):
    try:
        H7.assert_path_allowed(paths.find_dataset_dir("mbp1") / forbidden)
        raise SystemExit(f"SAFETY FAILURE: {forbidden} was not blocked")
    except H7.Phase7Violation:
        pass
if a.split != "val2025h1":
    try:
        H7.assert_path_allowed(paths.find_dataset_dir("mbp1") / "2025_H1.parquet")
        raise SystemExit("SAFETY FAILURE: 2025_H1 was not blocked")
    except H7.Phase7Violation:
        pass
print(f"split={a.split} {s}..{e}  band {cache7.BAND_START_ET}-{cache7.BAND_END_ET} ET")
print("2025_H2, 2026_H1, 2026_H2 verified blocked")

cfg = yaml.safe_load((ROOT / "config" / "fast_slow_baseline.yaml").read_text())
OUTRIGHT = cfg["contracts"]["outright_regex"]
front = pl.read_parquet(paths.RESULTS_DIR / (
    "front_map_p7val.parquet" if a.split == "val2025h1" else "front_map.parquet"))
front = front.filter((pl.col("trading_date") >= s) & (pl.col("trading_date") <= e))
print(f"front map: {front.height} trading days, "
      f"{int(front['is_roll_day'].sum())} roll days (excluded at feature time)")

con = connect(memory_limit=a.memory, threads=a.threads)
con.execute(f"SET temp_directory='{ROOT/'data_cache'/'duckdb_tmp'}';")
con.execute("SET preserve_insertion_order=false;")

t0 = time.time()
if a.months:
    want = set(a.months.split(","))
    import nqr.p7.cache7 as C
    orig = C.months_of
    C.months_of = lambda sp: [(int(x[:4]), int(x[5:])) for x in sorted(want)]
    recs = cache7.build_book_cache(con, front, a.split, outright=OUTRIGHT)
    C.months_of = orig
else:
    recs = cache7.build_book_cache(con, front, a.split, outright=OUTRIGHT)

meta = {"split": a.split, "start": str(s), "end": str(e),
        "band": [cache7.BAND_START_ET, cache7.BAND_END_ET],
        "months": recs, "runtime_s": round(time.time() - t0, 1)}
d = cache7.P7_BOOK; d.mkdir(parents=True, exist_ok=True)
mf = d / f"build_meta_{a.split}.json"
mf.write_text(json.dumps(meta, indent=2))
print(f"\ndone in {time.time()-t0:.0f}s -> {d}")
