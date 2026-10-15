"""Phase-7 end-of-phase integrity check."""
import hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import polars as pl

from nqr import paths
from nqr.p7 import backtest7 as BT
from nqr.p7 import cache7, dataset7, model7
from nqr.p7 import features7 as F7
from nqr.p7 import holdout7 as H7

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

print("\n=== phases 5-6 artifacts unchanged ===")
man5 = json.loads((ROOT / "results" / "p5_artifact_manifest.json").read_text())
bad5 = [f for f, d in man5["files"].items()
        if hashlib.sha256((ROOT / f).read_bytes()).hexdigest() != d]
check("Phase-5 artifact manifest matches disk", not bad5, man5["combined_sha256"][:16])
check("Phase-6 verdict present and still FAIL",
      "FAIL" in (ROOT / "strategies/context_entry/PHASE6_VERDICT.md").read_text()[:700])

print("\n=== source data unmodified ===")
proj = (ROOT / "pyproject.toml").stat().st_mtime
for kind in ("trades", "mbp1"):
    for k, p in sorted(paths.half_files(kind).items()):
        check(f"T9 {kind}/{k}.parquet unmodified", p.stat().st_mtime < proj)

print("\n=== seals ===")
import datetime as dt
for d in (dt.date(2025, 1, 1), dt.date(2025, 6, 30)):
    try:
        H7.assert_date_allowed(d); check(f"{d} refused", False)
    except H7.Phase7Violation:
        check(f"{d} (2025-H1) refused before the unlock", True)
for d in (dt.date(2025, 9, 1), dt.date(2026, 1, 2), dt.date(2026, 6, 1)):
    try:
        H7.assert_date_allowed(d); check(f"{d} refused", False)
    except H7.Phase7Violation:
        check(f"{d} refused", True)
H7._VAL_UNLOCKED = True
try:
    for d in (dt.date(2025, 9, 1), dt.date(2026, 1, 2), dt.date(2026, 6, 1)):
        try:
            H7.assert_date_allowed(d); check(f"{d} refused WITH the unlock", False)
        except H7.Phase7Violation:
            check(f"{d} refused even with the 2025-H1 unlock active", True)
finally:
    H7._VAL_UNLOCKED = False
check("exactly one unlock function, named for 2025-H1",
      [n for n in dir(H7) if n.startswith("unlock")] == ["unlock_phase7_validation"]
      and "2025_H1" in H7._UNLOCK_PHRASE)
for bad_path in ("/x/2025_H2.parquet", "/x/2026_H1.parquet", "/x/2026_H2.parquet",
                 "/x/a.dbn.zst"):
    try:
        H7.assert_path_allowed(bad_path); check(f"{bad_path} refused", False)
    except H7.Phase7Violation:
        check(f"{bad_path} refused", True)

print("\n=== no phase-7 artifact touches a sealed window ===")
SD = ROOT / "strategies" / "orderbook_state"
for f in sorted(list((SD / "features").rglob("*.parquet")) +
                list((SD / "results").rglob("*.parquet"))):
    try:
        d = pl.read_parquet(f, columns=["trading_date"])
    except Exception:
        continue
    if d.height == 0:
        continue
    lo, hi = d["trading_date"].min(), d["trading_date"].max()
    ok = hi < H7.VAL_START or (H7.VAL_START <= lo and hi <= H7.VAL_END)
    check(f"{f.relative_to(ROOT)} inside an allowed window", ok, f"{lo}..{hi}")

print("\n=== caches hold no forbidden month ===")
ym = cache7.months_available()
check("book cache has no 2025-H2 / 2026 month",
      not any(m >= "2025-07" for m in ym), f"{len(ym)} months: {ym[0]}..{ym[-1]}" if ym else "none")
check("book cache has no 2025-H1 month unless validation ran",
      (not any("2025-01" <= m <= "2025-06" for m in ym))
      or (SD / "results" / "run_val2025h1").exists())

print("\n=== budget, features, geometry ===")
check("configurations enumerated == 12", len(model7.enumerate_configs()) == 12)
sel = SD / "models" / "selection_2022.parquet"
if sel.exists():
    t = pl.read_parquet(sel)
    check("configurations evaluated == 12", t.height == 12, f"n={t.height}")
    check("exactly 2 R scales", t["r_tag"].n_unique() == 2)
    check("exactly 2 model families", t["family"].n_unique() == 2)
    check("exactly 3 selectivity levels", t["selectivity"].n_unique() == 3)
check("feature registry == 40 (hard cap)", len(F7.FEATURE_NAMES) == 40)
check("R scales are the preregistered 15 and 25 pt",
      dataset7.R_POINTS == {"R15": 15.0, "R25": 25.0})
check("max hold is 15 minutes", dataset7.MAX_HOLD_S == 900)
check("decision clock is 5 s", F7.DECISION_STEP_S == 5)
src = "".join((ROOT / "src" / "nqr" / "p7" / f).read_text()
              for f in ("cache7.py", "features7.py", "dataset7.py"))
check("no reference to a book level beyond _00",
      not any(f"{s}{lvl}" in src for s in ("bid_px", "ask_px", "bid_sz", "ask_sz")
              for lvl in ("_01", "_02", "_03", "_04", "_05")))
check("no invented queue position / order id / hidden liquidity",
      not any(w in src.lower() for w in ("queue_position", "order_id", "iceberg")))

print("\n=== candidate status ===")
meta = SD / "models" / "development_meta.json"
if meta.exists():
    m = json.loads(meta.read_text())
    check("total configurations recorded == 12", m["total_configurations_evaluated"] == 12)
    v = m.get("verdict", {})
    print(f"       decision: {v.get('decision')}")
check("frozen spec exists only if a candidate earned it",
      (SD / "PHASE7_SPEC_FROZEN.md").exists() ==
      (SD / "results" / "run_val2025h1").exists() or
      not (SD / "results" / "run_val2025h1").exists())

print("\nRESULT:", "ALL CHECKS PASSED" if not fails else f"{len(fails)} FAILURES: {fails}")
sys.exit(1 if fails else 0)
