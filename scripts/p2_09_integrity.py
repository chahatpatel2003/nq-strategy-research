"""Phase-2 integrity check.  Also re-runs the Phase-1 check so nothing regressed."""
import hashlib, json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import polars as pl
from nqr import paths
from nqr.holdout import HOLDOUT_START
from nqr.p2 import cache2

fails = []
def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}{'  ' + detail if detail else ''}")
    if not ok:
        fails.append(name)

print("=== Phase 1 (must still pass untouched) ===")
r = subprocess.run([sys.executable, str(ROOT / "scripts" / "07_integrity_check.py")],
                   capture_output=True, text=True)
print(r.stdout.strip().splitlines()[-1])
check("Phase-1 integrity check passes", r.returncode == 0)

print("\n=== Phase 2 ===")
for name, d in (("p2 tick cache", cache2.P2_TICKS), ("p2 bbo cache", cache2.P2_BBO1S)):
    ms = cache2.months_available(d)
    check(f"{name} max month < 2025-01", (max(ms) < "2025-01") if ms else False,
          f"max={max(ms) if ms else 'EMPTY'}  ({len(ms)} months)")

P2 = ROOT / "strategies" / "impulse_exhaustion" / "results"
for f in sorted(P2.rglob("*.parquet")):
    df = pl.read_parquet(f)
    if "trading_date" in df.columns and df.height:
        check(f"{f.parent.name}/{f.name} max date < 2025-01-01",
              df["trading_date"].max() < HOLDOUT_START, f"max={df['trading_date'].max()}")

man_p = paths.RESULTS_DIR / "p2_frozen_manifest.json"
if man_p.exists():
    man = json.loads(man_p.read_text())
    bad = [rel for rel, d in man["files"].items()
           if hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() != d]
    check("Phase-2 frozen manifest matches disk", not bad,
          f"drifted={bad}" if bad else man["frozen_id"])

p1 = json.loads((paths.RESULTS_DIR / "frozen_manifest.json").read_text())
check("Phase-1 frozen id unchanged", p1["frozen_id"] == "fastslow-1.0.0+5980044a44eebf7b",
      p1["frozen_id"])
for f in ("FAST_SLOW_SPEC_FROZEN.md", "PHASE1_VERDICT.md", "DATA_AUDIT.md"):
    check(f"Phase-1 deliverable {f} present", (ROOT / f).exists())

print("\nRESULT:", "ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURES: {fails}")
sys.exit(1 if fails else 0)
