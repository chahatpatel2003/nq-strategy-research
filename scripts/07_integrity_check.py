"""End-of-phase integrity check: holdout untouched + source data unmodified."""
import datetime as dt, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import polars as pl
from nqr import paths
from nqr.holdout import HOLDOUT_START

fails = []
def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}{'  ' + detail if detail else ''}")
    if not ok:
        fails.append(name)

# 1. no derived artefact contains data on/after the holdout start
bars = pl.read_parquet(paths.CACHE_DIR / "bars" / "bars_2m.parquet")
check("bar cache max trading date < 2025-01-01", bars["trading_date"].max() < HOLDOUT_START,
      f"max={bars['trading_date'].max()}")
ymax = max(p.name.split("=")[1] for p in (paths.CACHE_DIR / "ticks").glob("ym=*"))
check("tick cache max partition < 2025-01", ymax < "2025-01", f"max={ymax}")
for f in sorted(paths.RESULTS_DIR.rglob("trades_*.parquet")):
    t = pl.read_parquet(f)
    check(f"{f.parent.name}/{f.name} max date < 2025-01-01",
          t["trading_date"].max() < HOLDOUT_START, f"max={t['trading_date'].max()}")
dv = pl.read_parquet(paths.RESULTS_DIR / "contract_daily_volume.parquet")
check("contract volume table max date < 2025-01-01",
      dv["trading_date"].max().date() < HOLDOUT_START, f"max={dv['trading_date'].max()}")

# 2. holdout source files were never opened by this project
audited = json.loads((paths.RESULTS_DIR / "data_audit.json").read_text())["audited_halves"]
check("no 2025/2026 half audited", not any(h[:4] >= "2025" for h in audited), str(audited))

# 3. original T9 parquet files are untouched (mtimes all predate this project)
proj_start = (ROOT / "pyproject.toml").stat().st_mtime
for kind in ("trades", "mbp1"):
    for k, p in sorted(paths.half_files(kind).items()):
        check(f"T9 {kind}/{k}.parquet unmodified", p.stat().st_mtime < proj_start)

# 4. frozen manifest still matches the files on disk
import hashlib
man = json.loads((paths.RESULTS_DIR / "frozen_manifest.json").read_text())
bad = [rel for rel, d in man["files"].items()
       if hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() != d]
check("frozen file manifest matches disk", not bad, f"drifted={bad}" if bad else man["frozen_id"])

print("\nRESULT:", "ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURES: {fails}")
sys.exit(1 if fails else 0)
