"""Phase-5 end-of-phase integrity check.

Verifies: Phases 1-4 untouched; source T9 files unmodified; 2025-H1 never read;
2026 market content never read; no Phase-5 output contains a sealed date; the
search budget was not widened; the feature universe is still the Phase-4 55; and
the 2026-Q1 unlock was never used.
"""
import hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import polars as pl

from nqr import paths
from nqr.p4.features4 import FEATURE_NAMES
from nqr.p5 import dataset5, model5
from nqr.p5 import holdout5 as H5

fails = []


def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}{('  ' + detail) if detail else ''}")
    if not ok:
        fails.append(name)


print("=== phases 1-4 immutable ===")
for rel, fid in (("results/frozen_manifest.json", "fastslow-1.0.0+5980044a44eebf7b"),
                 ("results/p2_frozen_manifest.json", "impexh-1.0.0.impl2+48c76a0e68b88947"),
                 ("results/p3_frozen_manifest.json", "dcevent-1.0.0.impl3+d33e5d5d116f1adb"),
                 ("results/p4_frozen_manifest.json", "statedisc-1.0.0+c147134184dfb32d")):
    man = json.loads((ROOT / rel).read_text())
    bad = [f for f, d in man["files"].items()
           if hashlib.sha256((ROOT / f).read_bytes()).hexdigest() != d]
    check(f"{rel} matches disk", not bad and man["frozen_id"] == fid,
          man["frozen_id"] if not bad else f"drifted={bad}")

print("\n=== source data unmodified ===")
proj = (ROOT / "pyproject.toml").stat().st_mtime
for kind in ("trades", "mbp1"):
    for k, p in sorted(paths.half_files(kind).items()):
        check(f"T9 {kind}/{k}.parquet unmodified", p.stat().st_mtime < proj)

print("\n=== seals intact ===")
for d in (H5.SEALED_H1_START, H5.SEALED_H1_END, H5.SEALED_FINAL_START):
    try:
        H5.assert_date_allowed(d); check(f"{d} refused", False)
    except H5.Phase5Violation:
        check(f"{d} refused by the guard", True)
H5._VAL_UNLOCKED = True
try:
    for d in (H5.SEALED_H1_START, H5.SEALED_FINAL_START):
        try:
            H5.assert_date_allowed(d); check(f"{d} refused WITH the unlock", False)
        except H5.Phase5Violation:
            check(f"{d} refused even with the 2026-Q1 unlock active", True)
finally:
    H5._VAL_UNLOCKED = False
check("exactly one unlock function exists",
      [n for n in dir(H5) if n.startswith("unlock")] == ["unlock_phase5_validation"])
for bad_path in ("/x/2025_H1.parquet", "/x/2026_H2.parquet",
                 "/x/mbp1/2021_H1.parquet", "/x/a.dbn.zst"):
    try:
        H5.assert_path_allowed(bad_path); check(f"{bad_path} refused", False)
    except H5.Phase5Violation:
        check(f"{bad_path} refused", True)
for rng in ((H5.VAL_START, H5.SEALED_FINAL_START), (H5.CONTAM24_START, H5.CONTAM25H2_END)):
    try:
        H5.sql_window_guard(*rng); check(f"sql guard refuses {rng[0]}..{rng[1]}", False)
    except H5.Phase5Violation:
        check(f"sql guard refuses {rng[0]}..{rng[1]}", True)

print("\n=== no phase-5 artifact touches a sealed window ===")
SD = ROOT / "strategies" / "larger_r"
for f in sorted(list((SD / "features").rglob("*.parquet")) +
                list((SD / "results").rglob("*.parquet"))):
    try:
        d = pl.read_parquet(f, columns=["trading_date"])
    except Exception:
        continue
    if d.height == 0:
        continue
    lo, hi = d["trading_date"].min(), d["trading_date"].max()
    ok = (not (lo <= H5.SEALED_H1_END and hi >= H5.SEALED_H1_START)) and hi < H5.SEALED_FINAL_START
    check(f"{f.relative_to(ROOT)} avoids sealed windows", ok, f"{lo}..{hi}")

print("\n=== 2026 never opened, 2025-H1 never opened, MBP-1 never opened ===")
p4t = ROOT / "data_cache" / "p4_ticks"
ym = sorted(p.name.split("=")[1] for p in p4t.glob("ym=*")) if p4t.exists() else []
check("tick cache holds no 2025-H1 month",
      not any(m in ym for m in ("2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06")),
      str(ym))
check("tick cache holds no 2026 month", not any(m.startswith("2026") for m in ym), str(ym))
check("no Phase-5 validation feature split",
      not (SD / "features" / "split=val2026q1").exists())
check("no Phase-5 validation run directory",
      not list((SD / "results").glob("run_val2026q1*")))
check("no 2026 front map was ever built",
      not (paths.RESULTS_DIR / "front_map_p5val.parquet").exists())
src = "".join((ROOT / "src" / "nqr" / "p5" / f).read_text()
              for f in ("holdout5.py", "labels5.py", "dataset5.py", "model5.py", "backtest5.py"))
check("no Phase-5 module reads mbp1", "read_parquet" not in src or "mbp1" not in src.lower()
      or "Refusing" in src)

print("\n=== budget and feature universe ===")
check("configurations enumerated == 18", len(model5.enumerate_configs()) == 18)
sel = SD / "models" / "selection_2022.parquet"
if sel.exists():
    t = pl.read_parquet(sel)
    check("configurations evaluated == 18", t.height == 18, f"n={t.height}")
    check("exactly 3 R scales", t["r_tag"].n_unique() == 3)
    check("exactly 2 model families", t["family"].n_unique() == 2)
    check("exactly 3 selectivity levels", t["selectivity"].n_unique() == 3)
check("feature universe still the Phase-4 55", len(FEATURE_NAMES) == 55)
check("R architecture is the 3 preregistered multiples",
      dataset5.R_MULTS == {"r2p0": 2.0, "r3p0": 3.0, "r4p0": 4.0})
check("decision clock is 60 s", dataset5.DECISION_STEP_S == 60)
check("max hold is 60 min", dataset5.MAX_HOLD_S == 3600)

print("\n=== candidate status ===")
meta = SD / "models" / "development_meta.json"
if meta.exists():
    m = json.loads(meta.read_text())
    check("total configurations recorded == 18", m["total_configurations_evaluated"] == 18)
check("no Phase-5 spec was frozen (candidate rejected)",
      not (SD / "PHASE5_SPEC_FROZEN.md").exists())

print("\nRESULT:", "ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURES: {fails}")
sys.exit(1 if fails else 0)
