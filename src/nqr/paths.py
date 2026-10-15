"""Project paths + data discovery (read-only access to the T9 research drive)."""
from __future__ import annotations

import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
CACHE_DIR = PROJECT_ROOT / "data_cache"
RESULTS_DIR = PROJECT_ROOT / "results"
REPORTS_DIR = PROJECT_ROOT / "reports"
LOGS_DIR = PROJECT_ROOT / "logs"

for _d in (CACHE_DIR, RESULTS_DIR, REPORTS_DIR, LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

DRIVE_CANDIDATES = ["/Volumes/T9"]
_HALF_RE = re.compile(r"^(\d{4})_H([12])\.parquet$")


def find_drive() -> Path:
    for c in DRIVE_CANDIDATES:
        p = Path(c)
        if p.is_dir():
            return p
    raise FileNotFoundError("Samsung T9 drive not mounted at /Volumes/T9")


def find_dataset_dir(kind: str) -> Path:
    """Locate the 'trades' or 'mbp1' folder without hard-coding the layout."""
    assert kind in ("trades", "mbp1")
    drive = find_drive()
    hits: list[Path] = []
    for root, dirs, files in os.walk(drive):
        dirs[:] = [d for d in dirs if not d.startswith((".", "$")) and d != "System Volume Information"]
        base = os.path.basename(root).lower().replace("-", "").replace("_", "")
        if base == kind.replace("-", "").replace("_", ""):
            if any(_HALF_RE.match(f) for f in files):
                hits.append(Path(root))
    if not hits:
        raise FileNotFoundError(f"No '{kind}' folder with YYYY_H[12].parquet files under {drive}")
    hits.sort(key=lambda p: len(str(p)))
    return hits[0]


def half_files(kind: str = "trades") -> dict[str, Path]:
    """Map '2021_H1' -> Path for every half-year file present."""
    d = find_dataset_dir(kind)
    out = {}
    for f in sorted(os.listdir(d)):
        m = _HALF_RE.match(f)
        if m:
            out[f[:-8]] = d / f
    return out


def allowed_half_files(kind: str = "trades") -> dict[str, Path]:
    """Only halves that contain NO data on/after the holdout start."""
    from nqr.holdout import HOLDOUT_START, is_unlocked

    out = {}
    for key, p in half_files(kind).items():
        year, half = int(key[:4]), int(key[-1])
        # A half-year file's earliest Globex trading day is ~1 day before the
        # nominal period start; its last day is the period end.
        end_year = year
        if not is_unlocked() and end_year >= HOLDOUT_START.year:
            continue
        out[key] = p
    return out
