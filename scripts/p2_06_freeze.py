"""Freeze the Phase-2 baseline: hash every file that can change a signal."""
import argparse, hashlib, json, sys, datetime as dt
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import yaml

FROZEN_FILES = [
    "strategies/impulse_exhaustion/config/baseline.yaml",
    "strategies/impulse_exhaustion/IMPULSE_EXHAUSTION_SPEC.md",
    "strategies/impulse_exhaustion/runner.py",
    "src/nqr/p2/cache2.py",
    "src/nqr/p2/signing.py",
    "src/nqr/p2/features.py",
    "src/nqr/p2/absorption.py",
    "src/nqr/p2/statemachine.py",
    "src/nqr/p2/controls.py",
    "src/nqr/holdout.py",
    "src/nqr/sessions/calendar.py",
    "src/nqr/data/contracts.py",
    "src/nqr/backtest/engine.py",
    "scripts/p2_01_build_cache.py",
    "scripts/p2_03_run.py",
]

ap = argparse.ArgumentParser()
ap.add_argument("--impl-version", default="1")
ap.add_argument("--count-check", default=None,
                help="path to a --count-only run_meta.json, recorded verbatim")
a = ap.parse_args()

digests, h = {}, hashlib.sha256()
for rel in FROZEN_FILES:
    b = (ROOT / rel).read_bytes()
    d = hashlib.sha256(b).hexdigest()
    digests[rel] = d
    h.update(rel.encode()); h.update(d.encode())
combined = h.hexdigest()
cfg = yaml.safe_load((ROOT / "strategies" / "impulse_exhaustion" / "config" / "baseline.yaml").read_text())
version_id = f"{cfg['spec_version']}.impl{a.impl_version}+{combined[:16]}"

sign = ROOT / "results" / "p2_signing_verification.json"
sign_summary = {}
if sign.exists():
    s = json.loads(sign.read_text())
    sign_summary = {k: s[k] for k in ("days_sampled", "total_trades", "total_unambiguous",
                                      "total_agree", "total_disagree",
                                      "overall_agreement_rate", "mean_inside_spread_frac",
                                      "native_unknown_frac")}
count_check = json.loads(Path(a.count_check).read_text()) if a.count_check else None

manifest = {"spec_version": cfg["spec_version"], "impl_version": a.impl_version,
            "frozen_id": version_id, "combined_sha256": combined,
            "frozen_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "signing_verification": sign_summary, "pre_freeze_count_check": count_check,
            "files": digests}
(ROOT / "results" / "p2_frozen_manifest.json").write_text(json.dumps(manifest, indent=2))

rows = "\n".join(f"| `{k}` | `{v}` |" for k, v in digests.items())
sig_md = ("\n".join(f"| {k} | {v} |" for k, v in sign_summary.items())
          if sign_summary else "| _not run_ | |")
cc = json.dumps(count_check, indent=2) if count_check else "not recorded"
body = f"""# IMPULSE_EXHAUSTION_SPEC_FROZEN.md

**Frozen baseline identifier**

    {version_id}

`spec_version` = `{cfg['spec_version']}` · implementation version `{a.impl_version}`
combined SHA-256 = `{combined}`
frozen at = `{manifest['frozen_utc']}`

Reproduce with `python scripts/p2_06_freeze.py`. The identifier is a SHA-256 over
the ordered `(path, file-sha256)` pairs below. If any of these files changes the
identifier changes, and the result is a **different hypothesis** that must be
named `ImpulseExhaustion_v2` and may **not** inherit 2024 as an untouched
validation set.

## Frozen file manifest

| file | sha256 |
|---|---|
{rows}

## Trade-signing verification (STEP 1), development days only

| metric | value |
|---|---|
{sig_md}

## Pre-freeze signal-count check

The specification was checked once on development for **signal count only**, to
confirm it is neither degenerate nor absurd. **No win rate, expectancy or P&L
was computed before the freeze.**

```
{cc}
```

## Freeze protocol

1. `IMPULSE_EXHAUSTION_SPEC.md` and `config/baseline.yaml` were completed before
   any P&L existed. Every threshold comes from a-priori reasoning about NQ tick
   size, NQ 1-minute range and the timescale of the hypothesis.
2. Exactly **one** absorption formula was written. No alternatives were coded,
   run or compared.
3. No parameter grid was swept. The brief's suggested regions
   (0.75-1.25 VU, 30-120 s) were collapsed to a single canonical value by
   reasoning, not by search.
4. Development (2021-2023) is for implementation verification and diagnostics.
   A weak year does not license a rule change.
5. Validation (2024) is run **exactly once** against this manifest.
6. Only a genuine implementation **bug** may be fixed; it must be documented,
   regression-tested, bump `impl_version`, and force a full rerun.

## Pre-registered PASS / FAIL gate (restated, unchanged)

2024 validation · 09:30-11:30 ET · 1R · 1.0 pt round-trip friction. **PASS**
requires all six: trades >= 100; net expectancy > 0 R; profit factor > 1.10;
win rate > 50 %; 95 % binomial CI lower bound > 50 %; one-sided binomial
p < 0.05. **PROMISING BUT INCONCLUSIVE** if expectancy is positive but a
significance or sample gate fails. **FAIL** otherwise.
"""
(ROOT / "strategies" / "impulse_exhaustion" / "IMPULSE_EXHAUSTION_SPEC_FROZEN.md").write_text(body)
print(version_id)
