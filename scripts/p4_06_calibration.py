"""Phase-4 calibration: does more model confidence mean more realised edge?

Two views, both on the frozen production model:

  ROW level   every usable decision row bucketed by the model's score.  Rows
              overlap heavily, so this is a shape diagnostic, not an inference.
  TRADE level the executed non-overlapping trades bucketed by |score|, with the
              matched-control expectancy beside them.
"""
import json, pickle, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import numpy as np
import polars as pl

from nqr.p4 import backtest4 as BT
from nqr.p4 import dataset4, metrics4, model4

SD = ROOT / "strategies" / "state_discovery"
OUT = SD / "results"
FRICTION = 1.0
SPLITS = [("train2021", "dev", 2021), ("select2022", "dev", 2022),
          ("itest2023", "dev", 2023), ("contam2024", "contam2024", None),
          ("contam2025h2", "contam2025h2", None)]

with open(SD / "models" / "production_model.pkl", "rb") as f:
    P = pickle.load(f)
pre, est, tau = P["pre"], P["est"], P["tau"]

rows, trade_rows = [], []
for name, ds, year in SPLITS:
    df = dataset4.load_split(ds, primary_only=True)
    if year:
        df = df.filter(pl.col("trading_date").dt.year() == year)
    u = dataset4.finite_mask(df)
    df = df.filter(pl.Series(u))
    X = dataset4.feature_matrix(df)
    s = model4.score_of(est, pre.transform(X))
    r = df["r_points"].to_numpy().astype(float)
    lp = df["long_points"].to_numpy().astype(float)
    sp = df["short_points"].to_numpy().astype(float)
    y = df["y"].to_numpy()
    took = np.where(s > 0, lp, sp)                    # points in the model's direction
    for v in np.unique(np.round(s, 6)):
        m = np.round(s, 6) == v
        rows.append({"split": name, "score": float(v), "pred_p_long": float(v + 0.5),
                     "n_rows": int(m.sum()), "traded": bool(abs(v) >= tau),
                     "actual_p_long_win": float(y[m].mean()),
                     "dir_gross_R": float((took[m] / r[m]).mean()),
                     "dir_net1_R": float(((took[m] - FRICTION) / r[m]).mean()),
                     "dir_net1_WR": float(((took[m] - FRICTION) > 0).mean())})

    # trade level, with the matched control beside it
    d = OUT / f"run_{name}"
    tp, cp = d / "trades.parquet", d / "controls_matched.parquet"
    if tp.exists():
        t = pl.read_parquet(tp)
        c = pl.read_parquet(cp) if cp.exists() else pl.DataFrame()
        edges = np.unique(np.round(t["edge"].to_numpy(), 6))
        for e in edges:
            sub = t.filter((pl.col("edge").round(6) == float(e)))
            if sub.height == 0:
                continue
            m = metrics4.summarize(sub, FRICTION)
            cm = {}
            if c.height:
                cs = c.filter(pl.col("trading_date").is_in(sub["trading_date"].unique()))
                cm = metrics4.summarize(cs, FRICTION) if cs.height else {}
            trade_rows.append({"split": name, "edge": float(e), "n_trades": m["n_trades"],
                               "win_rate": m["win_rate"], "expectancy_R": m["expectancy_R"],
                               "profit_factor": m["profit_factor"],
                               "control_expectancy_R": cm.get("expectancy_R", float("nan")),
                               "control_win_rate": cm.get("win_rate", float("nan")),
                               "edge_minus_control_R": m["expectancy_R"] - cm.get("expectancy_R", float("nan"))})

rt = pl.DataFrame(rows).sort(["split", "score"])
tt = pl.DataFrame(trade_rows).sort(["split", "edge"])
rt.write_csv(OUT / "calibration_rows.csv")
tt.write_csv(OUT / "calibration_trades.csv")

# monotonicity: does a higher |score| bucket really earn more?
mono = {}
for name, _, _ in SPLITS:
    sub = tt.filter(pl.col("split") == name).sort("edge")
    if sub.height >= 2:
        e = sub["edge"].to_numpy(); v = sub["expectancy_R"].to_numpy()
        ok = np.isfinite(v)
        mono[name] = {"n_buckets": int(ok.sum()),
                      "spearman_edge_vs_expectancy": float(
                          np.corrcoef(np.argsort(np.argsort(e[ok])),
                                      np.argsort(np.argsort(v[ok])))[0, 1]) if ok.sum() > 2 else None}
(OUT / "calibration.json").write_text(json.dumps(mono, indent=2))

print(rt.filter(pl.col("split") == "itest2023").to_pandas().to_string(index=False))
print()
print(tt.to_pandas().to_string(index=False))
print()
print(json.dumps(mono, indent=2))
