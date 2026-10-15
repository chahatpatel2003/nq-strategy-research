"""Apply the PRE-REGISTERED Phase-3 verdict rule.  Arithmetic only."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import polars as pl
import yaml

from nqr import paths
from nqr.p3.metrics3 import enrich, window_report

cfg = yaml.safe_load((ROOT / "strategies" / "directional_change" /
                      "config" / "baseline.yaml").read_text())
V = cfg["verdict"]
man = json.loads((paths.RESULTS_DIR / "p3_frozen_manifest.json").read_text())
RUN = ROOT / "strategies" / "directional_change" / "results" / "run_val2025h2"
meta = json.loads((RUN / "run_meta.json").read_text())
assert meta["is_fresh_validation"], "verdict must be computed on the fresh validation split"

out = {"frozen_id": man["frozen_id"], "split": "fresh validation 2025-07-01..2025-12-31",
       "hypothesis": f"window={V['window']} target={V['target']} "
                     f"friction={V['friction_points']} pt round trip, per family",
       "families": {}, "n_families_tested": 0}
any_pass = False
any_promising = False

for fam in ("DC_A", "DC_B", "DC_C"):
    p = RUN / f"trades_{fam}.parquet"
    if not p.exists():
        continue
    t = enrich(pl.read_parquet(p))
    acc = t.filter((pl.col("status") == "ACCEPTED") & pl.col("w_0930_1130"))
    m = window_report(acc, "r1p0", V["friction_points"], meta["trading_days"])
    checks = {
        f"trades >= {V['min_trades']}": (m.get("n_trades", 0) >= V["min_trades"], m.get("n_trades", 0)),
        f"win rate > {V['min_win_rate']}": (m.get("win_rate", 0) > V["min_win_rate"],
                                            round(m.get("win_rate", float('nan')), 4)),
        f"95% CI lower bound > {V['ci_lower_gt']}": (m.get("win_rate_ci95_lo", 0) > V["ci_lower_gt"],
                                                     round(m.get("win_rate_ci95_lo", float('nan')), 4)),
        "net expectancy > 0 R": (m.get("expectancy_R", -1) > V["min_expectancy_r"],
                                 round(m.get("expectancy_R", float('nan')), 4)),
        f"profit factor > {V['min_profit_factor']}": (m.get("profit_factor", 0) > V["min_profit_factor"],
                                                      round(m.get("profit_factor", float('nan')), 4)),
        f"binomial p < {V['binomial_p_lt']}": (m.get("p_value_gt_breakeven", 1) < V["binomial_p_lt"],
                                               round(m.get("p_value_gt_breakeven", float('nan')), 4)),
    }
    passed = all(v[0] for v in checks.values())
    promising = (m.get("expectancy_R", -1) > 0 and m.get("profit_factor", 0) > 1.0)
    any_pass |= passed
    any_promising |= promising
    out["n_families_tested"] += 1
    out["families"][fam] = {
        "metrics": {k: m.get(k) for k in
                    ("n_trades", "wins", "losses", "win_rate", "win_rate_ci95_lo",
                     "win_rate_ci95_hi", "p_value_gt_breakeven", "expectancy_R",
                     "median_R", "expectancy_points", "profit_factor", "total_points",
                     "breakeven_wr_at_friction", "max_drawdown_R",
                     "max_drawdown_R_daily", "longest_loss_streak", "t_stat_R",
                     "trades_per_day_mean", "pct_profitable_days", "worst_day_R")},
        "gate_checks": {k: {"pass": bool(v[0]), "value": v[1]} for k, v in checks.items()},
        "family_verdict": "PASS" if passed else ("PROMISING BUT INCONCLUSIVE" if promising else "FAIL"),
    }

out["multiplicity_note"] = (
    f"{out['n_families_tested']} families were tested; a Bonferroni-adjusted "
    f"threshold would be {V['binomial_p_lt'] / max(out['n_families_tested'], 1):.4f}. "
    "The gate is applied exactly as pre-registered; this is reported for context only.")
out["verdict"] = "PASS" if any_pass else ("PROMISING BUT INCONCLUSIVE" if any_promising else "FAIL")
out["composite_note"] = ("Families are evaluated separately and are never combined "
                         "into a composite to manufacture a pass.")
(paths.RESULTS_DIR / "p3_verdict.json").write_text(json.dumps(out, indent=2, default=str))
print(json.dumps(out, indent=2, default=str))
