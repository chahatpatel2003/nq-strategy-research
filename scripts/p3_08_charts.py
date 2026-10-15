"""Random per-family trade charts (20 winners + 20 losers each)."""
import argparse, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import numpy as np, polars as pl, yaml
from nqr.p3 import cache3, holdout3 as H3
from nqr.p3.charts3 import plot_trade
from nqr.p3.metrics3 import enrich
from strategies.directional_change.runner import build_day_path, run_day

ap = argparse.ArgumentParser()
ap.add_argument("--tag", required=True)
ap.add_argument("--n", type=int, default=20)
ap.add_argument("--seed", type=int, default=20260819)
ap.add_argument("--unlock-validation", action="store_true")
ap.add_argument("--config", default=str(ROOT / "strategies" / "directional_change" /
                                        "config" / "baseline.yaml"))
a = ap.parse_args()
if a.unlock_validation:
    H3.unlock_phase3_validation("I_AM_UNLOCKING_ONLY_2025_H2_FOR_PHASE3_VALIDATION")
cfg = yaml.safe_load(Path(a.config).read_text())
RUN = ROOT / "strategies" / "directional_change" / "results" / f"run_{a.tag}"
OUT = ROOT / "strategies" / "directional_change" / "diagnostics" / f"trades_{a.tag}"
rng = np.random.default_rng(a.seed)

picks = {}
for fam in ("DC_A", "DC_B", "DC_C"):
    p = RUN / f"trades_{fam}.parquet"
    if not p.exists():
        continue
    t = enrich(pl.read_parquet(p))
    acc = t.filter((pl.col("status") == "ACCEPTED") & pl.col("w_0930_1130"))
    for name, df in (("winners", acc.filter(pl.col("r1p0_points") > 0)),
                     ("losers", acc.filter(pl.col("r1p0_points") <= 0))):
        if df.height == 0:
            continue
        idx = rng.choice(df.height, size=min(a.n, df.height), replace=False)
        picks[f"{fam}_{name}"] = [df.row(int(i), named=True) for i in np.sort(idx)]

by_day = {}
for grp, rows in picks.items():
    for r in rows:
        by_day.setdefault(r["trading_date"], []).append((grp, r))

made = {k: 0 for k in picks}
cur_ym, month = None, None
for d in sorted(by_day):
    ym = f"{d.year:04d}-{d.month:02d}"
    if ym != cur_ym:
        month, cur_ym = cache3.load_month(ym), ym
    dp = build_day_path(month.filter(pl.col("trading_date") == d), cfg, d)
    if dp is None:
        continue
    evs, _ = run_day(dp, cfg)
    for grp, r in by_day[d]:
        out = OUT / grp
        out.mkdir(parents=True, exist_ok=True)
        try:
            plot_trade(r, dp, evs, out / f"{grp}_{d}_{r['signal_ns']}.png")
            made[grp] += 1
        except Exception as e:
            print(f"  chart failed {d} {grp}: {e}")
print(f"charts under {OUT}: {made}")
