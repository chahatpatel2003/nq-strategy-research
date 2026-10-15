"""Phase-6 end-of-phase integrity check."""
import hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import polars as pl

from nqr import paths
from nqr.p4.features4 import FEATURE_NAMES
from nqr.p5 import dataset5
from nqr.p6 import context6 as C6
from nqr.p6 import holdout6 as H6

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
    check(f"{rel} matches disk", not bad and man["frozen_id"] == fid, man["frozen_id"])

print("\n=== phase 5 artifacts unchanged ===")
P5 = json.loads((ROOT / "results" / "p5_artifact_manifest.json").read_text()) \
    if (ROOT / "results" / "p5_artifact_manifest.json").exists() else None
if P5:
    bad = [f for f, d in P5["files"].items()
           if hashlib.sha256((ROOT / f).read_bytes()).hexdigest() != d]
    check("Phase-5 artifact manifest matches disk", not bad, f"drifted={bad}" if bad else
          f"{len(P5['files'])} files")
else:
    check("Phase-5 artifact manifest present", False, "run scripts/p6_00_fingerprint.py")
check("Phase-5 verdict still records FAIL before validation",
      "FAIL" in (ROOT / "strategies/larger_r/PHASE5_VERDICT.md").read_text()[:600])

print("\n=== source data unmodified ===")
proj = (ROOT / "pyproject.toml").stat().st_mtime
for kind in ("trades", "mbp1"):
    for k, p in sorted(paths.half_files(kind).items()):
        check(f"T9 {kind}/{k}.parquet unmodified", p.stat().st_mtime < proj)

print("\n=== seals intact ===")
for d in (H6.SEALED_H1_START, H6.SEALED_H1_END, H6.SEALED_FINAL_START):
    try:
        H6.assert_date_allowed(d); check(f"{d} refused", False)
    except H6.Phase6Violation:
        check(f"{d} refused by the guard", True)
H6._VAL_UNLOCKED = True
try:
    for d in (H6.SEALED_H1_START, H6.SEALED_FINAL_START):
        try:
            H6.assert_date_allowed(d); check(f"{d} refused WITH the unlock", False)
        except H6.Phase6Violation:
            check(f"{d} refused even with the 2026-Q1 unlock active", True)
finally:
    H6._VAL_UNLOCKED = False
check("exactly one unlock function", [n for n in dir(H6) if n.startswith("unlock")]
      == ["unlock_phase6_validation"])
check("the phase-6 unlock phrase is phase-6 specific",
      H6._UNLOCK_PHRASE.endswith("PHASE6_VALIDATION"))
for bad_path in ("/x/2025_H1.parquet", "/x/2026_H2.parquet", "/x/mbp1/a.parquet",
                 "/x/MBP-1/a.parquet", "/x/a.dbn.zst"):
    try:
        H6.assert_path_allowed(bad_path); check(f"{bad_path} refused", False)
    except H6.Phase6Violation:
        check(f"{bad_path} refused", True)
try:
    H6.sql_window_guard(H6.VAL_START, H6.SEALED_FINAL_START)
    check("sql guard refuses a window reaching 2026-04-01", False)
except H6.Phase6Violation:
    check("sql guard refuses a window reaching 2026-04-01", True)

print("\n=== no phase-6 artifact touches a sealed window ===")
SD = ROOT / "strategies" / "context_entry"
for f in sorted((SD / "results").rglob("*.parquet")):
    try:
        d = pl.read_parquet(f, columns=["trading_date"])
    except Exception:
        continue
    if d.height == 0:
        continue
    lo, hi = d["trading_date"].min(), d["trading_date"].max()
    ok = (not (lo <= H6.SEALED_H1_END and hi >= H6.SEALED_H1_START)) and hi < H6.SEALED_FINAL_START
    check(f"{f.relative_to(ROOT)} avoids sealed windows", ok, f"{lo}..{hi}")

print("\n=== 2026 never opened, MBP-1 never opened ===")
p4t = ROOT / "data_cache" / "p4_ticks"
ym = sorted(p.name.split("=")[1] for p in p4t.glob("ym=*")) if p4t.exists() else []
check("tick cache holds no 2025-H1 month",
      not any(m in ym for m in ("2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06")),
      str(ym))
check("tick cache holds no 2026 month", not any(m.startswith("2026") for m in ym))
check("no Phase-6 validation run directory", not list((SD / "results").glob("run_val2026q1*")))
check("no 2026 front map exists", not (paths.RESULTS_DIR / "front_map_p6val.parquet").exists()
      and not (paths.RESULTS_DIR / "front_map_p5val.parquet").exists())
src = "".join((ROOT / "src" / "nqr" / "p6" / f).read_text()
              for f in ("holdout6.py", "context6.py", "backtest6.py"))
check("no Phase-6 module opens a parquet directly", "read_parquet" not in src)

print("\n=== budget, geometry and direction model unchanged ===")
check("exactly six entry methods", C6.ENTRY_METHODS ==
      ("E1", "E2", "E3", "E4", "E5", "E6"))
check("E1/E2 delays are 5 and 10 minutes", (C6.E1_DELAY_S, C6.E2_DELAY_S) == (300, 600))
check("E3/E4 pullbacks are 0.25R and 0.50R",
      (C6.E3_PULLBACK_R, C6.E4_PULLBACK_R) == (0.25, 0.50))
check("resumption is 0.125R", C6.RESUME_R == 0.125)
check("R is the frozen Phase-5 r4p0", dataset5.R_MULTS["r4p0"] == 4.0)
check("max hold is the frozen 60 minutes", dataset5.MAX_HOLD_S == 3600)
check("feature universe untouched (55)", len(FEATURE_NAMES) == 55)
check("four 30-minute buckets", C6.N_BUCKETS == 4 and C6.BUCKET_S == 1800)
V = SD / "models" / "development_verdict.json"
if V.exists():
    v = json.loads(V.read_text())
    check("total entry configurations evaluated == 6",
          v["total_configurations_evaluated"] == 6)
    check("no candidate was promoted", not v["eligible"], str(v["eligible"]))
check("no Phase-6 spec was frozen (no candidate qualified)",
      not (SD / "PHASE6_SPEC_FROZEN.md").exists())

print("\nRESULT:", "ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURES: {fails}")
sys.exit(1 if fails else 0)
