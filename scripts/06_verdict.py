"""Apply the PRE-REGISTERED verdict rule.  No judgement, only arithmetic."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import polars as pl
import yaml

from nqr import paths
from nqr.metrics.stats import compute

cfg = yaml.safe_load((ROOT / "config" / "fast_slow_baseline.yaml").read_text())
frozen = json.loads((paths.RESULTS_DIR / "frozen_manifest.json").read_text())

VARIANT, TAG, FRICTION = "ANY", "r1", 1.0
GATES = dict(min_trades=100, ci_lo_gt=0.50, pf_gt=1.10, p_lt=0.05)

t = pl.read_parquet(paths.RESULTS_DIR / "fast_slow_val" / f"trades_{VARIANT}.parquet")
acc = t.filter(pl.col("status") == "ACCEPTED")
m = compute(acc, TAG, friction=FRICTION)

checks = {
    "n_trades >= 100": (m["n_trades"] >= GATES["min_trades"], m["n_trades"]),
    "win-rate 95% CI low > 0.50": (m["win_rate_ci95_lo"] > GATES["ci_lo_gt"], round(m["win_rate_ci95_lo"], 4)),
    "expectancy_R > 0": (m["expectancy_R"] > 0, round(m["expectancy_R"], 4)),
    "profit factor > 1.10": (m["profit_factor"] > GATES["pf_gt"], round(m["profit_factor"], 4)),
    "binomial p < 0.05": (m["p_value_gt_breakeven"] < GATES["p_lt"], round(m["p_value_gt_breakeven"], 4)),
    "CI high >= break-even": (m["win_rate_ci95_hi"] >= m["breakeven_win_rate"], round(m["win_rate_ci95_hi"], 4)),
}
if m["expectancy_R"] <= 0 or not checks["CI high >= break-even"][0]:
    verdict = "FAIL"
elif all(v[0] for k, v in checks.items() if k != "CI high >= break-even"):
    verdict = "PASS"
else:
    verdict = "PROMISING BUT INCONCLUSIVE"

out = {"frozen_id": frozen["frozen_id"], "split": "validation 2024",
       "hypothesis": f"variant={VARIANT} target=1R friction={FRICTION} pt round trip",
       "metrics": {k: m[k] for k in ("n_trades", "wins", "losses", "win_rate",
                                     "win_rate_ci95_lo", "win_rate_ci95_hi",
                                     "breakeven_win_rate", "p_value_gt_breakeven",
                                     "expectancy_R", "expectancy_points",
                                     "profit_factor", "total_points",
                                     "max_drawdown_R", "t_stat_R")},
       "gate_checks": {k: {"pass": bool(v[0]), "value": v[1]} for k, v in checks.items()},
       "verdict": verdict}
(paths.RESULTS_DIR / "verdict.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
