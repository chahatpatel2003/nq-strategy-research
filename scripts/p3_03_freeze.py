"""Freeze the Phase-3 baseline: hash every file that can change a signal."""
import argparse, hashlib, json, sys, datetime as dt
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import yaml

FROZEN_FILES = [
    "strategies/directional_change/config/baseline.yaml",
    "strategies/directional_change/DIRECTIONAL_CHANGE_SPEC.md",
    "strategies/directional_change/runner.py",
    "src/nqr/p3/holdout3.py",
    "src/nqr/p3/cache3.py",
    "src/nqr/p3/dc_engine.py",
    "src/nqr/p3/strategies.py",
    "src/nqr/p3/fastpass.py",
    "src/nqr/p2/features.py",          # frozen upstream, reused read-only for VU
    "src/nqr/backtest/engine.py",
    "src/nqr/sessions/calendar.py",
    "src/nqr/data/contracts.py",
    "scripts/p3_01_events.py",
    "scripts/p3_04_run.py",
]

ap = argparse.ArgumentParser()
ap.add_argument("--impl-version", default="1")
ap.add_argument("--engine-audit", default=None)
a = ap.parse_args()

digests, h = {}, hashlib.sha256()
for rel in FROZEN_FILES:
    b = (ROOT / rel).read_bytes()
    d = hashlib.sha256(b).hexdigest()
    digests[rel] = d
    h.update(rel.encode()); h.update(d.encode())
combined = h.hexdigest()
cfg = yaml.safe_load((ROOT / "strategies" / "directional_change" /
                      "config" / "baseline.yaml").read_text())
vid = f"{cfg['spec_version']}.impl{a.impl_version}+{combined[:16]}"

audit = json.loads(Path(a.engine_audit).read_text()) if a.engine_audit else None
rows = "\n".join(f"| `{k}` | `{v}` |" for k, v in digests.items())
au = json.dumps(audit, indent=2) if audit else "not recorded"

manifest = {"spec_version": cfg["spec_version"], "impl_version": a.impl_version,
            "frozen_id": vid, "combined_sha256": combined,
            "frozen_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "theta_vu": cfg["event"]["theta_vu"],
            "beta_extension": cfg["strategies"]["dc_b"]["beta_extension"],
            "gamma_overshoot": cfg["strategies"]["dc_c"]["gamma_overshoot"],
            "pre_freeze_engine_audit": audit, "files": digests}
(ROOT / "results" / "p3_frozen_manifest.json").write_text(json.dumps(manifest, indent=2))

body = f"""# DIRECTIONAL_CHANGE_SPEC_FROZEN.md

**Frozen baseline identifier**

    {vid}

`spec_version` = `{cfg['spec_version']}` · implementation version `{a.impl_version}`
combined SHA-256 = `{combined}`
frozen at = `{manifest['frozen_utc']}`

Reproduce with `python scripts/p3_03_freeze.py`. The identifier is a SHA-256 over
the ordered `(path, file-sha256)` pairs below. If any of these files changes the
identifier changes and the result is a **different hypothesis**, which may not
inherit 2025-H2 as fresh validation.

## Frozen parameters

| parameter | value |
|---|---|
| `theta` | `{cfg['event']['theta_vu']} x VU`, floor `{cfg['event']['theta_floor_points']}` pt |
| VU | ATR14 of completed 1-minute bars, floor `{cfg['volatility']['vu_floor_points']}` pt |
| `theta` sampling | at run start (previous confirmation), held for the run |
| DC-B `beta` | `{cfg['strategies']['dc_b']['beta_extension']}` x theta extension |
| DC-C `gamma` | `{cfg['strategies']['dc_c']['gamma_overshoot']}` x theta prior overshoot |
| R | `= theta`, symmetric +-1R primary |
| entry latency | `{cfg['entry']['latency_ms']}` ms |
| primary window | `{cfg['reporting']['primary_window_et'][0]}-{cfg['reporting']['primary_window_et'][1]}` ET |
| primary friction | `{cfg['costs']['primary_friction_points']}` pt round trip |

## Frozen file manifest

| file | sha256 |
|---|---|
{rows}

## Pre-freeze engine audit (Phase 3A — event geometry only, NO P&L)

```
{au}
```

## Freeze protocol

1. `DIRECTIONAL_CHANGE_SPEC.md` and `config/baseline.yaml` were completed before
   any strategy P&L existed.
2. Phase 3A validated the **event engine only**: event counts, theta scale and
   randomly sampled DC-sequence charts. No win rate, expectancy or P&L of any
   kind was computed before this freeze.
3. `theta` was left at the brief's named `0.50 x VU`. The cost arithmetic it
   implies (a ~60 % gross win rate needed at 1.0 pt friction, given a median
   primary-window theta near 4.8 pt) was measured from event geometry alone and
   is disclosed in the spec **before** validation rather than used to move the
   design or the gate.
4. No parameter grid was searched. The theta sensitivity grid is a
   post-baseline diagnostic and cannot change the baseline.
5. 2024 is a contaminated diagnostic and can never satisfy a PASS criterion.
6. Fresh validation (2025-H2) is unlocked only after this freeze and run once.
7. Only a genuine implementation **bug** may be fixed: document, regression-test,
   bump `impl_version`, rerun everything.

## Pre-registered PASS gate (restated, unchanged)

Fresh validation 2025-07-01 .. 2025-12-31 · 09:30-11:30 ET · 1R · 1.0 pt
round-trip friction · **each family separately**. All six required: trades >= 100;
win rate > 50 %; 95 % CI lower bound > 50 %; net expectancy > 0 R; profit factor
> 1.10; one-sided binomial p < 0.05. **If no family passes, PHASE 3 = FAIL.**
Failing families are never combined into a composite.
"""
(ROOT / "strategies" / "directional_change" / "DIRECTIONAL_CHANGE_SPEC_FROZEN.md").write_text(body)
print(vid)
