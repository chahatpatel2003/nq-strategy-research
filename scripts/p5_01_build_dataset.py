"""Build the Phase-5 larger-R state dataset for one split.

    python scripts/p5_01_build_dataset.py --split dev
    python scripts/p5_01_build_dataset.py --split contam2024
    python scripts/p5_01_build_dataset.py --split contam2025h2
    python scripts/p5_01_build_dataset.py --split val2026q1 --unlock-validation

2025-H1 and 2026-04-01+ have no code path.
"""
import argparse, json, sys, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import polars as pl

from nqr import paths
from nqr.p4 import cache4                    # frozen tick access, read-only
from nqr.p5 import dataset5
from nqr.p5 import holdout5 as H5

UNLOCK = "I_AM_UNLOCKING_ONLY_2026_Q1_FOR_PHASE5_VALIDATION"
FRONT = {"contam2025h2": "front_map_p3val.parquet", "val2026q1": "front_map_p5val.parquet"}


def _levels_and_rolls(split: str):
    if split in ("dev", "train2021", "select2022", "itest2023", "contam2024"):
        ext = cache4.day_extremes_from_phase1_bars()
        front = pl.read_parquet(paths.RESULTS_DIR / "front_map.parquet")
    else:
        ext = pl.read_parquet(cache4.levels_path(
            "contam2025h2" if split == "contam2025h2" else "val2026q1"))
        front = pl.read_parquet(paths.RESULTS_DIR / FRONT[split])
    roll = set(front.filter(pl.col("is_roll_day"))["trading_date"].to_list())
    return cache4.prev_day_levels(ext), roll


def _worker(args):
    ym, split, unlocked = args
    if unlocked:
        H5.unlock_phase5_validation(UNLOCK)
    lv, roll = _levels_and_rolls(split)
    return dataset5.build_month(ym, split, lv, roll, cache4.load_month)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=list(H5.SPLITS), required=True)
    ap.add_argument("--unlock-validation", action="store_true")
    ap.add_argument("--workers", type=int, default=5)
    a = ap.parse_args()
    if a.unlock_validation:
        H5.unlock_phase5_validation(UNLOCK)

    s, e = H5.SPLITS[a.split]
    H5.assert_range_allowed(s, e, f"--split {a.split}")
    if a.split in ("contam2024", "contam2025h2"):
        print("*** CONTAMINATED DIAGNOSTIC SPLIT - NOT VALIDATION ***")
    if a.split == "val2026q1":
        print("*** FRESH VALIDATION SPLIT - one shot only ***")
    months = cache4.months_for(a.split)
    print(f"split={a.split} {s}..{e} months={len(months)} workers={a.workers}")
    print(f"R scales={dataset5.R_MULTS}  clock={dataset5.DECISION_STEP_S}s  "
          f"hold={dataset5.MAX_HOLD_S//60}min")

    t0 = time.time()
    recs = []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        for r in ex.map(_worker, [(ym, a.split, a.unlock_validation) for ym in months]):
            recs.append(r)
            print(f"  {r['ym']}: days={r['days']:3d} rows={r['rows']:,}"
                  f"  [{time.time()-t0:.0f}s]", flush=True)

    meta = {"split": a.split, "start": str(s), "end": str(e),
            "spec_version": "largerr-1.0.0",
            "r_mults": dataset5.R_MULTS, "decision_step_s": dataset5.DECISION_STEP_S,
            "max_hold_s": dataset5.MAX_HOLD_S,
            "trading_days": sum(r["days"] for r in recs),
            "rows": sum(r["rows"] for r in recs),
            "months": recs, "runtime_s": round(time.time() - t0, 1),
            "is_contaminated": a.split in ("contam2024", "contam2025h2"),
            "is_fresh_validation": a.split == "val2026q1"}
    d = dataset5.out_dir(a.split); d.mkdir(parents=True, exist_ok=True)
    (d / "build_meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps({k: v for k, v in meta.items() if k != "months"}, indent=2))
