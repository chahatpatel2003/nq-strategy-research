"""Fingerprint the Phase-5 artifacts so Phase 6 can assert they never change.

Phase 5 has no frozen manifest of its own -- its candidate was rejected at Gate F
and never frozen -- so this records the hashes Phase 6 depends on.
"""
import datetime as dt, hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

FILES = ["src/nqr/p5/holdout5.py", "src/nqr/p5/labels5.py", "src/nqr/p5/dataset5.py",
         "src/nqr/p5/model5.py", "src/nqr/p5/backtest5.py",
         "strategies/larger_r/PHASE5_SPEC.md",
         "strategies/larger_r/PHASE5_SEARCH_BUDGET.md",
         "strategies/larger_r/PHASE5_FEATURE_REGISTRY.md",
         "strategies/larger_r/PHASE5_VERDICT.md",
         "strategies/larger_r/models/production_model.pkl",
         "strategies/larger_r/models/development_meta.json"]
files = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in FILES}
h = hashlib.sha256()
for k, v in files.items():
    h.update(k.encode()); h.update(v.encode())
out = {"phase": 5, "note": "Phase 5 was never frozen (candidate rejected at Gate F); "
                           "this pins the artifacts Phase 6 reuses read-only.",
       "combined_sha256": h.hexdigest(), "recorded_utc": dt.datetime.now(dt.UTC).isoformat(),
       "files": files}
(ROOT / "results" / "p5_artifact_manifest.json").write_text(json.dumps(out, indent=2))
print(f"phase-5 artifact fingerprint: {h.hexdigest()[:16]}  ({len(files)} files)")
