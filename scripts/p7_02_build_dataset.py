"""Build the Phase-7 decision dataset (40 features + both R labels) for one split.

    python scripts/p7_02_build_dataset.py --split dev
    python scripts/p7_02_build_dataset.py --split contam2024
    python scripts/p7_02_build_dataset.py --split val2025h1 --confirm <phrase>
"""
import argparse, json, sys, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import polars as pl

from nqr import paths
from nqr.p7 import cache7, dataset7
from nqr.p7 import holdout7 as H7

UNLOCK = "I_AM_UNLOCKING_ONLY_2025_H1_FOR_PHASE7_FRESH_VALIDATION"


def _rolls(split: str) -> set:
    fm = "front_map_p7val.parquet" if split == "val2025h1" else "front_map.parquet"
    f = pl.read_parquet(paths.RESULTS_DIR / fm)
    return set(f.filter(pl.col("is_roll_day"))["trading_date"].to_list())


def _worker(args):
    ym, split, unlocked = args
    if unlocked:
        H7.unlock_phase7_validation(UNLOCK)
    return dataset7.build_month(ym, split, _rolls(split))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=list(H7.SPLITS), required=True)
    ap.add_argument("--confirm", default="")
    ap.add_argument("--workers", type=int, default=5)
    a = ap.parse_args()
    if a.split == "val2025h1":
        H7.unlock_phase7_validation(a.confirm)
        print("*** FRESH MBP-1 VALIDATION - 2025-H1 - ONE SHOT ***")
    if a.split == "contam2024":
        print("*** CONTAMINATED DIAGNOSTIC - NOT VALIDATION ***")

    s, e = H7.SPLITS[a.split]
    H7.assert_range_allowed(s, e, f"--split {a.split}")
    have = set(cache7.months_available())
    months = [m for m in cache7.months_for(a.split) if m in have]
    missing = [m for m in cache7.months_for(a.split) if m not in have]
    print(f"split={a.split} {s}..{e}  book-cache months {len(months)}"
          + (f"  MISSING {missing}" if missing else ""))
    print(f"R scales {dataset7.R_POINTS}  hold {dataset7.MAX_HOLD_S//60}min  "
          f"clock 5s  session 09:30-11:30 ET")

    t0 = time.time(); recs = []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for r in ex.map(_worker, [(m, a.split, a.split == "val2025h1") for m in months]):
            recs.append(r)
            print(f"  {r['ym']}: days={r['days']:3d} rows={r['rows']:,}  "
                  f"[{time.time()-t0:.0f}s]", flush=True)
    meta = {"split": a.split, "start": str(s), "end": str(e),
            "r_points": dataset7.R_POINTS, "max_hold_s": dataset7.MAX_HOLD_S,
            "decision_step_s": 5, "n_features": 40,
            "trading_days": sum(r["days"] for r in recs),
            "rows": sum(r["rows"] for r in recs), "months": recs,
            "runtime_s": round(time.time() - t0, 1),
            "is_contaminated": a.split == "contam2024",
            "is_fresh_validation": a.split == "val2025h1"}
    d = dataset7.out_dir(a.split); d.mkdir(parents=True, exist_ok=True)
    (d / "build_meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps({k: v for k, v in meta.items() if k != "months"}, indent=2))
