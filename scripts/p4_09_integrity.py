"""Phase-4 end-of-phase integrity check.

Verifies: the frozen spec still matches disk; Phases 1-3 are untouched; the
original T9 files are unmodified; 2025-H1 was never read; 2026-04-01+ was never
read; no Phase-4 output contains a sealed date; the search budget was not
widened; and the 2026-Q1 unlock was used at most once.
"""
import hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import polars as pl

from nqr import paths
from nqr.p4 import holdout4 as H4
from nqr.p4 import model4
from nqr.p4.features4 import FEATURE_NAMES

fails = []


def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}{('  ' + detail) if detail else ''}")
    if not ok:
        fails.append(name)


print("=== previous phases immutable ===")
for rel, fid in (("results/frozen_manifest.json", "fastslow-1.0.0+5980044a44eebf7b"),
                 ("results/p2_frozen_manifest.json", "impexh-1.0.0.impl2+48c76a0e68b88947"),
                 ("results/p3_frozen_manifest.json", "dcevent-1.0.0.impl3+d33e5d5d116f1adb")):
    man = json.loads((ROOT / rel).read_text())
    bad = [f for f, d in man["files"].items()
           if hashlib.sha256((ROOT / f).read_bytes()).hexdigest() != d]
    check(f"{rel} matches disk", not bad and man["frozen_id"] == fid,
          man["frozen_id"] if not bad else f"drifted={bad}")

print("\n=== phase-4 spec frozen ===")
p4 = json.loads((paths.RESULTS_DIR / "p4_frozen_manifest.json").read_text())
bad = [f for f, d in p4["files"].items()
       if hashlib.sha256((ROOT / f).read_bytes()).hexdigest() != d]
check("Phase-4 frozen manifest matches disk", not bad,
      p4["frozen_id"] if not bad else f"drifted={bad}")

print("\n=== source data unmodified ===")
proj = (ROOT / "pyproject.toml").stat().st_mtime
for kind in ("trades", "mbp1"):
    for k, p in sorted(paths.half_files(kind).items()):
        check(f"T9 {kind}/{k}.parquet unmodified", p.stat().st_mtime < proj)

print("\n=== seals intact ===")
for d in (H4.SEALED_H1_START, H4.SEALED_H1_END, H4.SEALED_FINAL_START):
    try:
        H4.assert_date_allowed(d); check(f"{d} refused", False)
    except H4.Phase4Violation:
        check(f"{d} refused by the guard", True)
H4._VAL_UNLOCKED = True
try:
    for d in (H4.SEALED_H1_START, H4.SEALED_FINAL_START):
        try:
            H4.assert_date_allowed(d); check(f"{d} refused WITH the unlock active", False)
        except H4.Phase4Violation:
            check(f"{d} refused even with the 2026-Q1 unlock active", True)
finally:
    H4._VAL_UNLOCKED = False
check("exactly one unlock function exists",
      [n for n in dir(H4) if n.startswith("unlock")] == ["unlock_phase4_validation"])

print("\n=== no phase-4 artifact touches a sealed window ===")
SD = ROOT / "strategies" / "state_discovery"
for f in sorted(list((SD / "features").rglob("*.parquet")) +
                list((SD / "results").rglob("*.parquet"))):
    try:
        d = pl.read_parquet(f, columns=["trading_date"])
    except Exception:
        continue
    if d.height == 0:
        continue
    lo, hi = d["trading_date"].min(), d["trading_date"].max()
    ok = not (lo <= H4.SEALED_H1_END and hi >= H4.SEALED_H1_START) and hi < H4.SEALED_FINAL_START
    check(f"{f.relative_to(ROOT)} avoids sealed windows", ok, f"{lo}..{hi}")

print("\n=== 2025-H1 and MBP-1 never opened ===")
p4t = ROOT / "data_cache" / "p4_ticks"
ym = sorted(p.name.split("=")[1] for p in p4t.glob("ym=*")) if p4t.exists() else []
check("p4 tick cache holds no 2025-H1 month", not any(m in ym for m in
      ("2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06")), str(ym))
check("p4 tick cache holds no 2026-Q2+ month",
      not any(m >= "2026-04" for m in ym), str(ym))
src = "".join((ROOT / "src" / "nqr" / "p4" / f).read_text()
              for f in ("features4.py", "cache4.py", "dataset4.py", "model4.py",
                        "backtest4.py", "metrics4.py", "holdout4.py"))
check("no Phase-4 module references mbp1", "mbp1" not in src.lower().replace("mbp-1", ""))

print("\n=== search budget ===")
meta = json.loads((SD / "models" / "production_meta.json").read_text())
sel = pl.read_parquet(SD / "models" / "selection_2022.parquet")
check("configurations enumerated == 18", len(model4.enumerate_configs()) == 18)
check("configurations evaluated == 18", sel.height == 18, f"n={sel.height}")
check("total recorded == 18", meta["total_configurations_evaluated"] == 18)
check("exactly one production candidate", (SD / "models" / "production_model.pkl").exists()
      and isinstance(meta["model_key"], str))
check("feature universe still 55 <= 60", len(FEATURE_NAMES) == 55)

print("\n=== fresh validation used at most once ===")
runs = sorted(p.name for p in (SD / "results").glob("run_val2026q1*"))
check("at most one 2026-Q1 validation run", len(runs) <= 1, str(runs) or "not yet run")

print("\nRESULT:", "ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURES: {fails}")
sys.exit(1 if fails else 0)
