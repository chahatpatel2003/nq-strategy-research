"""Pre-registered component ablation (DIAGNOSTIC ONLY).

A  impulse only                       -> entry at impulse confirmation
B  + aggression deterioration         -> entry when the third qualifying peak confirms
C  + absorption                       -> entry at the ARM moment
D  full baseline (+ failed continuation)

D is the strategy.  A/B/C exist to show which component carries information and
are never promoted.
"""
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import polars as pl
import yaml

from nqr.metrics.stats import compute
from nqr.p2.metrics2 import enrich

split = sys.argv[1] if len(sys.argv) > 1 else "dev"
cfg = yaml.safe_load((ROOT / "strategies" / "impulse_exhaustion" /
                      "config" / "baseline.yaml").read_text())
FR = cfg["costs"]["primary_friction_points"]
RES = ROOT / "strategies" / "impulse_exhaustion" / "results"

rows = []
for ab in ("A_impulse", "B_deterioration", "C_absorption", "D_full"):
    tag = f"{split}_{ab}"
    if not (RES / f"run_{tag}" / "run_meta.json").exists():
        print(f"running {tag} ...", flush=True)
        subprocess.run([sys.executable, str(ROOT / "scripts" / "p2_03_run.py"),
                        "--split", split, "--ablation", ab,
                        "--primary-target-only"], check=True,
                       stdout=subprocess.DEVNULL)
    p = RES / f"run_{tag}" / "trades.parquet"
    if not p.exists():
        rows.append({"variant": ab, "n_signals": 0}); continue
    t = enrich(pl.read_parquet(p))
    acc = t.filter(pl.col("status") == "ACCEPTED")
    for wcol, wlab in (("w_0930_1130", "09:30-11:30"), ("w_0930_1600", "09:30-16:00")):
        sub = acc.filter(pl.col(wcol))
        m = compute(sub, "r1p0", friction=FR)
        rows.append({"variant": ab, "window": wlab, "n_signals": t.height,
                     "n_trades": m.get("n_trades", 0), "win_rate": m.get("win_rate"),
                     "ci_lo": m.get("win_rate_ci95_lo"), "ci_hi": m.get("win_rate_ci95_hi"),
                     "expectancy_R": m.get("expectancy_R"),
                     "profit_factor": m.get("profit_factor"),
                     "total_points": m.get("total_points"),
                     "p_value": m.get("p_value_gt_breakeven")})
df = pl.DataFrame(rows, strict=False)
df.write_csv(RES / f"ablation_{split}.csv")
print(df.to_pandas().to_string(index=False))
