"""Apply the PRE-REGISTERED Phase-2 verdict rule.  Arithmetic only."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import polars as pl
import yaml

from nqr import paths
from nqr.metrics.stats import compute
from nqr.p2.metrics2 import enrich, window_report

cfg = yaml.safe_load((ROOT / "strategies" / "impulse_exhaustion" /
                      "config" / "baseline.yaml").read_text())
V = cfg["verdict"]
man = json.loads((paths.RESULTS_DIR / "p2_frozen_manifest.json").read_text())
RUN = ROOT / "strategies" / "impulse_exhaustion" / "results" / "run_val"

t = enrich(pl.read_parquet(RUN / "trades.parquet"))
acc = t.filter((pl.col("status") == "ACCEPTED") & pl.col("w_0930_1130"))
diag = pl.read_parquet(RUN / "daily_diag.parquet")
m = window_report(acc, "r1p0", V["friction_points"], diag.height)

checks = {
    f"trades >= {V['min_trades']}": (m.get("n_trades", 0) >= V["min_trades"], m.get("n_trades", 0)),
    "net expectancy > 0 R": (m.get("expectancy_R", -1) > V["min_expectancy_r"],
                             round(m.get("expectancy_R", float('nan')), 4)),
    f"profit factor > {V['min_profit_factor']}": (m.get("profit_factor", 0) > V["min_profit_factor"],
                                                  round(m.get("profit_factor", float('nan')), 4)),
    f"win rate > {V['min_win_rate']}": (m.get("win_rate", 0) > V["min_win_rate"],
                                        round(m.get("win_rate", float('nan')), 4)),
    f"95% CI lower bound > {V['ci_lower_gt']}": (m.get("win_rate_ci95_lo", 0) > V["ci_lower_gt"],
                                                 round(m.get("win_rate_ci95_lo", float('nan')), 4)),
    f"binomial p < {V['binomial_p_lt']}": (m.get("p_value_gt_breakeven", 1) < V["binomial_p_lt"],
                                           round(m.get("p_value_gt_breakeven", float('nan')), 4)),
}
all_pass = all(v[0] for v in checks.values())
pos_exp = m.get("expectancy_R", -1) > 0 and m.get("profit_factor", 0) > 1.0
verdict = "PASS" if all_pass else ("PROMISING BUT INCONCLUSIVE" if pos_exp else "FAIL")

out = {"frozen_id": man["frozen_id"], "split": "validation 2024",
       "hypothesis": f"window={V['window']} target={V['target']} "
                     f"friction={V['friction_points']} pt round trip",
       "metrics": {k: m.get(k) for k in
                   ("n_trades", "wins", "losses", "win_rate", "win_rate_ci95_lo",
                    "win_rate_ci95_hi", "p_value_gt_breakeven", "expectancy_R",
                    "median_R", "expectancy_points", "profit_factor", "total_points",
                    "max_drawdown_R", "max_drawdown_R_daily", "longest_loss_streak",
                    "t_stat_R", "trades_per_day_mean", "pct_profitable_days",
                    "worst_day_R", "daily_R_p05")},
       "gate_checks": {k: {"pass": bool(v[0]), "value": v[1]} for k, v in checks.items()},
       "verdict": verdict}
(paths.RESULTS_DIR / "p2_verdict.json").write_text(json.dumps(out, indent=2, default=str))
print(json.dumps(out, indent=2, default=str))
