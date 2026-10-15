"""Freeze the baseline: hash every file that can change a signal, and emit
FAST_SLOW_SPEC_FROZEN.md with the resulting version identifier."""
import hashlib, json, sys, datetime as dt
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import yaml

FROZEN_FILES = [
    "config/fast_slow_baseline.yaml",
    "src/nqr/holdout.py",
    "src/nqr/paths.py",
    "src/nqr/sessions/calendar.py",
    "src/nqr/data/contracts.py",
    "src/nqr/data/cache.py",
    "src/nqr/levels/build.py",
    "src/nqr/signals/triggers.py",
    "src/nqr/signals/fast_slow.py",
    "src/nqr/backtest/engine.py",
    "src/nqr/execution/simulate.py",
    "strategies/fast_slow/runner.py",
    "scripts/01_build_cache.py",
    "scripts/02_run_fast_slow.py",
]

digests = {}
h = hashlib.sha256()
for rel in FROZEN_FILES:
    p = ROOT / rel
    b = p.read_bytes()
    d = hashlib.sha256(b).hexdigest()
    digests[rel] = d
    h.update(rel.encode())
    h.update(d.encode())
combined = h.hexdigest()
cfg = yaml.safe_load((ROOT / "config" / "fast_slow_baseline.yaml").read_text())
version_id = f"{cfg['spec_version']}+{combined[:16]}"

manifest = {"spec_version": cfg["spec_version"], "frozen_id": version_id,
            "combined_sha256": combined, "frozen_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "files": digests}
(ROOT / "results" / "frozen_manifest.json").write_text(json.dumps(manifest, indent=2))

rows = "\n".join(f"| `{k}` | `{v}` |" for k, v in digests.items())
body = f"""# FAST_SLOW_SPEC_FROZEN.md

**Frozen baseline identifier**

    {version_id}

`spec_version` = `{cfg['spec_version']}`
combined SHA-256 = `{combined}`
frozen at = `{manifest['frozen_utc']}`

Reproduce with `python scripts/05_freeze.py`; the identifier is a SHA-256 over
the ordered `(path, file-sha256)` pairs below. If any of these files changes,
the identifier changes and the result is a **different hypothesis** that must be
named `FastSlow_v2` and evaluated separately.

## Frozen file manifest

| file | sha256 |
|---|---|
{rows}

## Freeze protocol actually followed

1. `FAST_SLOW_SPEC.md` and `config/fast_slow_baseline.yaml` were written **before
   any strategy P&L existed**. Every threshold in them comes from *a priori*
   reasoning about NQ tick size, NQ daily range and 2-minute bar granularity.
2. Development (2021-2023) was used **only** to verify the implementation: the
   trade log was audited for causality, stop/target arithmetic, fill-price
   consistency and MFE/MAE coherence, and randomly-sampled charts were checked
   against raw bars.
3. Two implementation defects were found and fixed during development, neither
   of which is a strategy parameter:
   * an Int8 overflow in the polars session-label expression (`dt.hour()` returns
     Int8, so `18*60` wrapped) - every bar was mislabelled `ASIA`;
   * the tick cache was not explicitly sorted by `ts_event`, which would have
     broken `searchsorted` on the ~1-in-3-million source rows whose `ts_event`
     ordering differs from `ts_recv` ordering.
   A regression test now covers each.
4. **No strategy parameter was altered after development results were seen.**
   The only post-result code edits were to the charting helper (handling
   `None` exit timestamps for skipped rows) and the addition of extra
   diagnostic columns to the rejected-pattern log. Neither can change a signal;
   the development run was re-executed after both and reproduced identical
   counts.
5. Validation (2024) was executed **once**, with this frozen configuration.

## The complete rule set

The full mechanical specification is `FAST_SLOW_SPEC.md`, whose SHA-256 is
recorded here as well for completeness:

    FAST_SLOW_SPEC.md  {hashlib.sha256((ROOT / 'FAST_SLOW_SPEC.md').read_bytes()).hexdigest()}

A second programmer needs `FAST_SLOW_SPEC.md` plus the frozen YAML to
reimplement this from scratch; the source files above are the reference
implementation of it.

## Pre-registered verdict rule (restated, unchanged)

Applied to the primary hypothesis - variant `ANY`, target `1R` - on the 2024
validation split at **1.0 point** round-trip friction:

* **PASS** - win-rate 95% CI lower bound > 0.50 AND expectancy > 0 AND profit
  factor > 1.10 AND one-sided binomial p < 0.05 against a 50% break-even AND
  at least 100 trades.
* **PROMISING BUT INCONCLUSIVE** - point-estimate expectancy > 0 but any of the
  above gates fails.
* **FAIL** - expectancy <= 0 at 1.0 point friction, or the 95% CI upper bound
  lies below the break-even win rate.
"""
(ROOT / "FAST_SLOW_SPEC_FROZEN.md").write_text(body)
print(version_id)
