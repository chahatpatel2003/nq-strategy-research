"""Build the Phase-4 causal state dataset for one split.

    python scripts/p4_01_build_dataset.py --split dev
    python scripts/p4_01_build_dataset.py --split contam2024
    python scripts/p4_01_build_dataset.py --split contam2025h2
    python scripts/p4_01_build_dataset.py --split val2026q1 --unlock-validation

2025-H1 and 2026-04-01+ have no code path.
"""
import argparse, json, sys, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import polars as pl

from nqr import paths
from nqr.p4 import cache4, dataset4
from nqr.p4 import holdout4 as H4

UNLOCK = "I_AM_UNLOCKING_ONLY_2026_Q1_FOR_PHASE4_VALIDATION"


def _worker(args):
    ym, split, unlocked = args
    if unlocked:
        H4.unlock_phase4_validation(UNLOCK)
    lv, roll = _levels_and_rolls(split)
    return dataset4.build_month(ym, split, lv, roll, cache4.load_month)


def _levels_and_rolls(split: str):
    if split in ("dev", "train2021", "select2022", "itest2023", "contam2024"):
        ext = cache4.day_extremes_from_phase1_bars()
        front = pl.read_parquet(paths.RESULTS_DIR / "front_map.parquet")
    else:
        ext = pl.read_parquet(cache4.levels_path(split))
        fm = {"contam2025h2": "front_map_p3val.parquet",
              "val2026q1": "front_map_p4val.parquet"}[split]
        front = pl.read_parquet(paths.RESULTS_DIR / fm)
    roll = set(front.filter(pl.col("is_roll_day"))["trading_date"].to_list())
    return cache4.prev_day_levels(ext), roll


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=list(H4.SPLITS), required=True)
    ap.add_argument("--unlock-validation", action="store_true")
    ap.add_argument("--workers", type=int, default=5)
    a = ap.parse_args()
    if a.unlock_validation:
        H4.unlock_phase4_validation(UNLOCK)

    s, e = H4.SPLITS[a.split]
    H4.assert_range_allowed(s, e, f"--split {a.split}")
    if a.split in ("contam2024", "contam2025h2"):
        print("*** CONTAMINATED DIAGNOSTIC SPLIT - NOT VALIDATION ***")
    if a.split == "val2026q1":
        print("*** FRESH VALIDATION SPLIT - one shot only ***")
    months = cache4.months_for(a.split)
    print(f"split={a.split} {s}..{e} months={len(months)} workers={a.workers}")

    t0 = time.time()
    recs = []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for r in ex.map(_worker, [(ym, a.split, a.unlock_validation) for ym in months]):
            recs.append(r)
            print(f"  {r['ym']}: days={r['days']:3d} rows={r['rows']:,}"
                  f"  [{time.time()-t0:.0f}s]", flush=True)

    meta = {"split": a.split, "start": str(s), "end": str(e),
            "trading_days": sum(r["days"] for r in recs),
            "rows": sum(r["rows"] for r in recs),
            "months": recs, "runtime_s": round(time.time() - t0, 1),
            "is_contaminated": a.split in ("contam2024", "contam2025h2"),
            "is_fresh_validation": a.split == "val2026q1"}
    d = dataset4.out_dir(a.split); d.mkdir(parents=True, exist_ok=True)
    (d / "build_meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps({k: v for k, v in meta.items() if k != "months"}, indent=2))
