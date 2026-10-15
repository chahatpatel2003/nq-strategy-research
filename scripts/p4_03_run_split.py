"""Run the selected Phase-4 production strategy over one split.

    python scripts/p4_03_run_split.py --split train2021
    python scripts/p4_03_run_split.py --split select2022
    python scripts/p4_03_run_split.py --split itest2023
    python scripts/p4_03_run_split.py --split contam2024
    python scripts/p4_03_run_split.py --split contam2025h2
    python scripts/p4_03_run_split.py --split val2026q1 --confirm <phrase>

Produces, for every split identically: the trade log, matched-random controls,
the opposite-direction control, the shuffled-direction null, prop-firm metrics,
day-block bootstrap CIs, window diagnostics and subgroup tables.
"""
import argparse, json, pickle, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import numpy as np
import polars as pl

from nqr.p4 import backtest4 as BT
from nqr.p4 import dataset4, metrics4, model4
from nqr.p4 import holdout4 as H4
from nqr.p4.features4 import FEATURE_NAMES

MODELS = ROOT / "strategies" / "state_discovery" / "models"
OUT = ROOT / "strategies" / "state_discovery" / "results"
FRICTION = 1.0
WINDOWS = {"0930_1130": (0, 7200), "0930_1030": (0, 3600), "1030_1130": (3600, 7200),
           "0930_1200": (0, 9000), "0930_1600": (0, 23400)}
DATASET_OF = {"train2021": "dev", "select2022": "dev", "itest2023": "dev", "dev": "dev",
              "contam2024": "contam2024", "contam2025h2": "contam2025h2",
              "val2026q1": "val2026q1"}

ap = argparse.ArgumentParser()
ap.add_argument("--split", choices=list(DATASET_OF), required=True)
ap.add_argument("--confirm", default="")
a = ap.parse_args()
if a.split == "val2026q1":
    H4.unlock_phase4_validation(a.confirm)
    print("*** FRESH VALIDATION - 2026-Q1 - ONE SHOT ***")
if a.split in ("contam2024", "contam2025h2"):
    print("*** CONTAMINATED DIAGNOSTIC - NOT VALIDATION ***")

start, end = H4.SPLITS[a.split]
H4.assert_range_allowed(start, end, f"--split {a.split}")

with open(MODELS / "production_model.pkl", "rb") as f:
    P = pickle.load(f)
pre, est, tau, mk = P["pre"], P["est"], P["tau"], P["model_key"]
assert pre.fit_on == "train2021", "the scaler must be the 2021-only one"
print(f"production model: {mk}  tau={tau:.6f}  (top {int(P['threshold_q']*100)}%)")

t0 = time.time()
df = dataset4.load_split(DATASET_OF[a.split], primary_only=False)
df = df.filter((pl.col("trading_date") >= start) & (pl.col("trading_date") <= end))
assert df.height, "no rows for this split"
assert df["trading_date"].min() >= start and df["trading_date"].max() <= end
for d in (df["trading_date"].min(), df["trading_date"].max()):
    H4.assert_date_allowed(d, "split row")
usable = dataset4.finite_mask(df)
X = dataset4.feature_matrix(df)
score = np.full(df.height, np.nan)
score[usable] = model4.score_of(est, pre.transform(X[usable]))
sec = df["sec_since_open"].to_numpy()
print(f"rows={df.height:,} usable={int(usable.sum()):,} "
      f"days={df['trading_date'].n_unique()}  [{time.time()-t0:.0f}s]", flush=True)

d_out = OUT / f"run_{a.split}"
d_out.mkdir(parents=True, exist_ok=True)
res = {"split": a.split, "start": str(start), "end": str(end),
       "model_key": mk, "tau": tau, "threshold_q": P["threshold_q"],
       "friction_primary": FRICTION,
       "is_contaminated": a.split in ("contam2024", "contam2025h2"),
       "is_fresh_validation": a.split == "val2026q1",
       "n_rows": df.height, "n_usable": int(usable.sum()),
       "n_days": int(df["trading_date"].n_unique())}

windows = {}
for wname, (lo, hi) in WINDOWS.items():
    m = (sec >= lo) & (sec < hi)
    sub = df.filter(pl.Series(m))
    nd = sub["trading_date"].n_unique()
    book = BT.run_strategy(sub, score[m], tau, usable[m])
    acc = BT.accepted(book)
    stats = metrics4.summarize(acc, FRICTION, n_days_available=nd) if acc.height else {}
    windows[wname] = stats
    if wname == "0930_1130":
        primary_book, primary_sub, primary_mask, primary_days = book, sub, m, nd
    print(f"  {wname}: cand={book.height:6d} trades={stats.get('n_trades',0):5d} "
          f"WR={stats.get('win_rate',float('nan')):.4f} "
          f"E[R]={stats.get('expectancy_R',float('nan')):+.4f} "
          f"PF={stats.get('profit_factor',float('nan')):.3f}", flush=True)
res["windows"] = windows

# --------------------------------------------------- primary-window detail ----
acc = BT.accepted(primary_book)
u_p = usable[primary_mask]
primary_book.write_parquet(d_out / "candidates.parquet")
if acc.height:
    feats = primary_sub.select(["decision_ts_ns"] + FEATURE_NAMES)
    acc.join(feats, on="decision_ts_ns", how="left").write_parquet(d_out / "trades.parquet")
    acc.write_csv(d_out / "trades.csv")

res["friction_sweep"] = {str(fr): metrics4.summarize(acc, fr, primary_days)
                         for fr in dataset4.FRICTIONS} if acc.height else {}
res["skip_reasons"] = (primary_book.filter(pl.col("status") == "SKIPPED")
                       .group_by("skip_reason").len().to_dicts()
                       if primary_book.height else [])

# --------------------------------------------------------------- controls ----
ctrl = BT.matched_controls(primary_book, primary_sub, u_p)
opp = BT.opposite_direction(primary_book, primary_sub, u_p)
if ctrl.height:
    ctrl.write_parquet(d_out / "controls_matched.parquet")
if opp.height:
    opp.write_parquet(d_out / "controls_opposite.parquet")
res["matched_control"] = metrics4.summarize(ctrl, FRICTION, primary_days) if ctrl.height else {}
res["opposite_control"] = metrics4.summarize(opp, FRICTION, primary_days) if opp.height else {}

if acc.height and ctrl.height:
    res["vs_matched"] = {
        "expectancy_R": metrics4.block_bootstrap_diff(acc, ctrl, FRICTION, "expectancy_R"),
        "win_rate": metrics4.block_bootstrap_diff(acc, ctrl, FRICTION, "win_rate"),
        "expectancy_points": metrics4.block_bootstrap_diff(acc, ctrl, FRICTION, "expectancy_points"),
    }
if acc.height and opp.height:
    res["vs_opposite"] = {
        "expectancy_R": metrics4.block_bootstrap_diff(acc, opp, FRICTION, "expectancy_R"),
        "win_rate": metrics4.block_bootstrap_diff(acc, opp, FRICTION, "win_rate"),
    }
if acc.height:
    res["strategy_ci"] = {
        "expectancy_R": metrics4.block_bootstrap_ci(acc, FRICTION, "expectancy_R"),
        "win_rate": metrics4.block_bootstrap_ci(acc, FRICTION, "win_rate"),
    }
    null3 = BT.shuffled_direction_null(primary_book, primary_sub, u_p, n_rep=1000)
    res["null_c3_shuffled_direction"] = {
        "n_rep": null3["n_rep"], "long_frac": null3["long_frac"],
        "null_wr_mean": float(null3["null_win_rate"].mean()),
        "null_wr_p95": float(np.quantile(null3["null_win_rate"], 0.95)),
        "null_ER_mean": float(null3["null_expectancy_R"].mean()),
        "null_ER_p95": float(np.quantile(null3["null_expectancy_R"], 0.95)),
        "strategy_wr": res["windows"]["0930_1130"]["win_rate"],
        "strategy_ER": res["windows"]["0930_1130"]["expectancy_R"],
        "p_strategy_ER_under_null": float(
            (null3["null_expectancy_R"] >= res["windows"]["0930_1130"]["expectancy_R"]).mean()),
    }
    res["concentration"] = metrics4.weekly_concentration(acc, FRICTION)

    # ---------------------------------------------------------- subgroups ----
    sg = acc.with_columns(
        pl.col("trading_date").dt.month().alias("month"),
        pl.col("trading_date").dt.weekday().alias("weekday"),
        pl.when(pl.col("sec_since_open") < 3600).then(pl.lit("hour1"))
          .otherwise(pl.lit("hour2")).alias("hour"),
        pl.col("side").alias("dir_label"),
        (pl.col("r_points").rank("ordinal") / pl.len() * 4).ceil().cast(pl.Int32).alias("r_quartile"),
        (pl.col("edge").rank("ordinal") / pl.len() * 4).ceil().cast(pl.Int32).alias("edge_quartile"),
    )
    tabs = {}
    for col in ("month", "weekday", "hour", "dir_label", "r_quartile", "edge_quartile"):
        tb = metrics4.by_group(sg, col, FRICTION)
        if tb.height:
            tb.write_csv(d_out / f"by_{col}.csv")
            tabs[col] = tb.to_dicts()
    res["subgroups"] = tabs

(d_out / "results.json").write_text(json.dumps(res, indent=2, default=str))
p = res["windows"]["0930_1130"]
print(f"\n[{a.split}] 09:30-11:30 @1.0pt : n={p.get('n_trades',0)} "
      f"WR={p.get('win_rate',float('nan')):.4f} E[R]={p.get('expectancy_R',float('nan')):+.4f} "
      f"PF={p.get('profit_factor',float('nan')):.3f}")
if "vs_matched" in res:
    v = res["vs_matched"]["expectancy_R"]
    w = res["vs_matched"]["win_rate"]
    print(f"  vs matched random: dE[R]={v['diff']:+.4f} "
          f"CI95=[{v['ci95_lo']:+.4f}, {v['ci95_hi']:+.4f}]  "
          f"dWR={w['diff']:+.4f} CI95=[{w['ci95_lo']:+.4f}, {w['ci95_hi']:+.4f}]")
print(f"done in {time.time()-t0:.0f}s")
