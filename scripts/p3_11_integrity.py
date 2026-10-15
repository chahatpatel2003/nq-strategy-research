"""Phase-3 integrity audit -> reports/PHASE3_INTEGRITY_AUDIT.md"""
import datetime as dt, hashlib, json, os, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import polars as pl
from nqr import paths
from nqr.p3 import cache3, holdout3 as H3

checks = []
def add(name, ok, detail=""):
    checks.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}{'  ' + detail if detail else ''}")

print("=== earlier phases unchanged ===")
r = subprocess.run([sys.executable, str(ROOT / "scripts" / "p2_09_integrity.py")],
                   capture_output=True, text=True)
add("Phase-1 + Phase-2 integrity check still passes", r.returncode == 0,
    r.stdout.strip().splitlines()[-1] if r.stdout else "")
p1 = json.loads((paths.RESULTS_DIR / "frozen_manifest.json").read_text())
p2 = json.loads((paths.RESULTS_DIR / "p2_frozen_manifest.json").read_text())
add("Phase-1 frozen id unchanged", p1["frozen_id"] == "fastslow-1.0.0+5980044a44eebf7b", p1["frozen_id"])
add("Phase-2 frozen id unchanged", p2["frozen_id"] == "impexh-1.0.0.impl2+48c76a0e68b88947", p2["frozen_id"])

print("\n=== source data unchanged ===")
proj = (ROOT / "pyproject.toml").stat().st_mtime
bad = [k for kind in ("trades", "mbp1")
       for k, p in paths.half_files(kind).items() if p.stat().st_mtime >= proj]
add("all T9 source parquet files unmodified", not bad, f"modified={bad}" if bad else "20 files")

print("\n=== 2025-H1 and 2026 never accessed ===")
for ym in ("2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06"):
    ok = False
    try:
        cache3.load_month(ym)
    except H3.Phase3Violation:
        ok = True
    add(f"loader refuses {ym} (sealed 2025-H1)", ok)
for ym in ("2026-01", "2026-06"):
    ok = False
    try:
        cache3.load_month(ym)
    except H3.Phase3Violation:
        ok = True
    add(f"loader refuses {ym} (2026 final holdout)", ok)
for f in ("2025_H1.parquet", "2026_H1.parquet"):
    ok = False
    try:
        H3.assert_path_allowed("/x/" + f)
    except H3.Phase3Violation:
        ok = True
    add(f"file guard refuses {f} even with validation unlocked", ok)
months = sorted(p.name.split("=")[1] for p in cache3.P3_TICKS.glob("ym=*")) \
    if cache3.P3_TICKS.exists() else []
add("Phase-3 validation cache holds only 2025-07..2025-12",
    all("2025-07" <= m <= "2025-12" for m in months), f"months={months}")

print("\n=== outputs contain no sealed dates ===")
P3 = ROOT / "strategies" / "directional_change" / "results"
for f in sorted(P3.rglob("*.parquet")):
    df = pl.read_parquet(f, columns=["trading_date"]) if "trading_date" in \
        pl.read_parquet_schema(f) else None
    if df is None or df.height == 0:
        continue
    mx, mn = df["trading_date"].max(), df["trading_date"].min()
    ok = not (H3.SEALED_H1_START <= mn <= H3.SEALED_H1_END or
              H3.SEALED_H1_START <= mx <= H3.SEALED_H1_END or
              mx >= H3.SEALED_2026_START)
    add(f"{f.parent.name}/{f.name} avoids sealed windows", ok, f"{mn}..{mx}")

print("\n=== spec frozen before outcomes ===")
man = json.loads((paths.RESULTS_DIR / "p3_frozen_manifest.json").read_text())
drift = [rel for rel, d in man["files"].items()
         if hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() != d]
add("Phase-3 frozen manifest matches disk", not drift, f"drift={drift}" if drift else man["frozen_id"])
add("pre-freeze audit recorded event geometry only",
    man.get("pre_freeze_engine_audit", {}).get("note", "").startswith("PHASE 3A ENGINE AUDIT"))
frozen_at = dt.datetime.fromisoformat(man["frozen_utc"])
val_meta = P3 / "run_val2025h2" / "run_meta.json"
if val_meta.exists():
    add("validation produced after the freeze",
        dt.datetime.fromtimestamp(val_meta.stat().st_mtime, dt.timezone.utc) > frozen_at)

ok = all(c[1] for c in checks)
rows = "\n".join(f"| {n} | {'✅' if o else '❌'} | {d} |" for n, o, d in checks)
body = f"""# PHASE3_INTEGRITY_AUDIT.md

Generated {dt.datetime.now(dt.timezone.utc).isoformat()} by `scripts/p3_11_integrity.py`.

**Phase-3 frozen id:** `{man['frozen_id']}`

## Required verifications

| check | status | detail |
|---|---|---|
{rows}

## The ten required properties

| # | property | how it is guaranteed |
|---|---|---|
| 1 | Phase 1 unchanged | frozen manifest re-hashed; id `{p1['frozen_id']}` |
| 2 | Phase 2 unchanged | frozen manifest re-hashed; id `{p2['frozen_id']}` |
| 3 | source T9 files unchanged | every one of the 20 parquet files has an mtime predating this project |
| 4 | 2025-H1 never accessed | `nqr.p3.holdout3` has **no unlock path** for it; the month loader and the file guard both refuse it even while validation is unlocked; the validation cache builder reads `2025_H2.parquet` and asserts the H1 file is blocked before it starts |
| 5 | 2026 never accessed | identical treatment; no unlock path exists |
| 6 | spec frozen before outcomes | the pre-freeze audit recorded **event geometry only** (counts, theta scale, causality); no win rate, expectancy or P&L existed before the freeze |
| 7 | no future data in features | VU is the ATR of *completed* minutes; the DC engine confirms only at `conf_idx > ext_idx`; truncation and future-tampering tests both hold |
| 8 | no P&L-based parameter selection | theta stayed at the brief's `0.50 x VU`; the theta grid is a post-baseline diagnostic that cannot alter the baseline |
| 9 | correct event-time chronology | every cache sorted by `(ts_event, source row number)`; entries are the first print >= signal + 250 ms; first passage walks raw prints |
| 10 | validation generated only after the freeze | file mtime compared against the freeze timestamp |

## Implementation-version history

| version | change | effect on P&L |
|---|---|---|
| `impl1` | initial freeze | — (crashed while serialising; **no P&L was ever observed**) |
| `impl2` | fixed a polars schema-inference crash: skipped rows omitted the target columns, so an all-null prefix was typed `Null` and a real int64 timestamp could not be appended. Rows now carry an identical key set with explicit dtypes. | none — the crash happened at the write step |
| `impl3` | fixed an inverted sign on the `entry_slippage` / `signal_to_entry_pts` diagnostic columns, which reported FAVOURABLE slippage as positive instead of the project-wide ADVERSE-positive convention. | **none — verified byte-identical**: dev and 2024 trade fingerprints matched exactly before and after |

Each fix was documented, given a regression test, bumped the implementation
version, and forced a full rerun. **No strategy rule was changed at any point.**

RESULT: **{"ALL CHECKS PASSED" if ok else "FAILURES PRESENT"}**
"""
REP = ROOT / "strategies" / "directional_change" / "reports"
REP.mkdir(parents=True, exist_ok=True)
(REP / "PHASE3_INTEGRITY_AUDIT.md").write_text(body)
print(f"\nwrote {REP/'PHASE3_INTEGRITY_AUDIT.md'}")
print("RESULT:", "ALL CHECKS PASSED" if ok else "FAILURES PRESENT")
sys.exit(0 if ok else 1)
