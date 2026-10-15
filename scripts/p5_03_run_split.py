"""Run the selected Phase-5 candidate over one split.

    python scripts/p5_03_run_split.py --split train2021
    python scripts/p5_03_run_split.py --split itest2023
    python scripts/p5_03_run_split.py --split contam2024
    python scripts/p5_03_run_split.py --split contam2025h2
    python scripts/p5_03_run_split.py --split val2026q1 --confirm <phrase>
"""
import argparse, json, pickle, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import numpy as np
import polars as pl

from nqr.p4 import metrics4                    # frozen upstream, read-only
from nqr.p4.features4 import FEATURE_NAMES
from nqr.p5 import backtest5 as BT
from nqr.p5 import dataset5, model5
from nqr.p5 import holdout5 as H5


def pf_r(t, friction: float) -> float:
    """Profit factor in R units.

    `metrics4.summarize` reports PF on POINTS while expectancy is in R.  With a
    volatility-scaled R those two can disagree in sign, because a large-R trade
    contributes more points but the same +/-1R.  Phase 5 sizes risk per trade,
    so the R-consistent figure is the one the gates mean.
    """
    if t.height == 0:
        return float("nan")
    r = (t["points"].to_numpy().astype(float) - friction) / t["r_points"].to_numpy().astype(float)
    gp, gl = float(r[r > 0].sum()), float(-r[r < 0].sum())
    return gp / gl if gl > 0 else float("inf")


MODELS = ROOT / "strategies" / "larger_r" / "models"
OUT = ROOT / "strategies" / "larger_r" / "results"
FRICTION = 1.0
WINDOWS = {"0930_1130": (0, 7200), "0930_1030": (0, 3600), "1030_1130": (3600, 7200)}
DATASET_OF = {"train2021": "dev", "select2022": "dev", "itest2023": "dev", "dev": "dev",
              "contam2024": "contam2024", "contam2025h2": "contam2025h2",
              "val2026q1": "val2026q1"}

ap = argparse.ArgumentParser()
ap.add_argument("--split", choices=list(DATASET_OF), required=True)
ap.add_argument("--confirm", default="")
a = ap.parse_args()
if a.split == "val2026q1":
    H5.unlock_phase5_validation(a.confirm)
    print("*** FRESH VALIDATION - 2026-Q1 - ONE SHOT ***")
if a.split in ("contam2024", "contam2025h2"):
    print("*** CONTAMINATED DIAGNOSTIC - NOT VALIDATION ***")

start, end = H5.SPLITS[a.split]
H5.assert_range_allowed(start, end, f"--split {a.split}")

with open(MODELS / "production_model.pkl", "rb") as f:
    P = pickle.load(f)
pre, est, tau = P["pre"], P["est"], P["tau"]
r_tag, fam, base = P["r_tag"], P["family"], P["baseline"]
assert pre.fit_on == "train2021", "the scaler must be the 2021-only one"
assert base["n_fit"] > 0
print(f"candidate: {P['config_name']}  R={dataset5.R_MULTS[r_tag]}xATR1m  tau={tau:.6f}")

t0 = time.time()
df = dataset5.load_split(DATASET_OF[a.split])
df = df.filter((pl.col("trading_date") >= start) & (pl.col("trading_date") <= end))
assert df.height, "no rows for this split"
assert df["trading_date"].min() >= start and df["trading_date"].max() <= end
for d in (df["trading_date"].min(), df["trading_date"].max()):
    H5.assert_date_allowed(d, "split row")

usable = dataset5.usable_mask(df, r_tag)
X = dataset5.feature_matrix(df)
sec = df["sec_since_open"].to_numpy()
p = np.full(df.height, np.nan)
p[usable] = est.predict_proba(pre.transform(X[usable]))[:, 1]
bl, bs = model5.baseline_vectors(base, sec)
score, direction = model5.edge_and_direction(p, bl, bs)
score = np.where(np.isfinite(p), score, -np.inf)
n_days = df["trading_date"].n_unique()
print(f"rows={df.height:,} usable={int(usable.sum()):,} days={n_days}  [{time.time()-t0:.0f}s]",
      flush=True)

d_out = OUT / f"run_{a.split}"; d_out.mkdir(parents=True, exist_ok=True)
res = {"split": a.split, "start": str(start), "end": str(end),
       "config": P["config_name"], "r_tag": r_tag, "r_mult": dataset5.R_MULTS[r_tag],
       "family": fam, "tau": tau, "selectivity": P["selectivity"],
       "friction_primary": FRICTION,
       "is_contaminated": a.split in ("contam2024", "contam2025h2"),
       "is_fresh_validation": a.split == "val2026q1",
       "n_rows": df.height, "n_usable": int(usable.sum()), "n_days": n_days}

windows = {}
for wname, (lo, hi) in WINDOWS.items():
    m = (sec >= lo) & (sec < hi)
    sub = df.filter(pl.Series(m))
    nd = sub["trading_date"].n_unique()
    book = BT.run_strategy(sub, r_tag, score[m], direction[m], tau, usable[m])
    acc = BT.accepted(book)
    st = metrics4.summarize(acc, FRICTION, n_days_available=nd) if acc.height else {}
    if st:
        st["profit_factor_R"] = pf_r(acc, FRICTION)
        st["profit_factor_points"] = st["profit_factor"]
    windows[wname] = st
    if wname == "0930_1130":
        pbook, psub, pmask, pdays = book, sub, m, nd
    print(f"  {wname}: cand={book.height:5d} trades={st.get('n_trades',0):5d} "
          f"WR={st.get('win_rate',float('nan')):.4f} "
          f"E[R]={st.get('expectancy_R',float('nan')):+.4f} "
          f"PF(R)={st.get('profit_factor_R',float('nan')):.3f}", flush=True)
res["windows"] = windows

acc = BT.accepted(pbook)
u_p = usable[pmask]
pbook.write_parquet(d_out / "candidates.parquet")
if acc.height:
    feats = psub.select(["decision_ts_ns"] + FEATURE_NAMES)
    acc.join(feats, on="decision_ts_ns", how="left").write_parquet(d_out / "trades.parquet")
    acc.write_csv(d_out / "trades.csv")
if acc.height:
    fs = {}
    for fr in dataset5.FRICTIONS:
        m = metrics4.summarize(acc, fr, pdays)
        m["profit_factor_R"] = pf_r(acc, fr)
        fs[str(fr)] = m
    res["friction_sweep"] = fs
else:
    res["friction_sweep"] = {}
res["skip_reasons"] = (pbook.filter(pl.col("status") == "SKIPPED")
                       .group_by("skip_reason").len().to_dicts() if pbook.height else [])

ctrl = BT.matched_controls(pbook, psub, r_tag, u_p)
opp = BT.opposite_direction(pbook, psub, r_tag)
if ctrl.height:
    ctrl.write_parquet(d_out / "controls_matched.parquet")
if opp.height:
    opp.write_parquet(d_out / "controls_opposite.parquet")
res["matched_control"] = metrics4.summarize(ctrl, FRICTION, pdays) if ctrl.height else {}
if ctrl.height:
    res["matched_control"]["profit_factor_R"] = pf_r(ctrl, FRICTION)
res["opposite_control"] = metrics4.summarize(opp, FRICTION, pdays) if opp.height else {}
if opp.height:
    res["opposite_control"]["profit_factor_R"] = pf_r(opp, FRICTION)
if acc.height and ctrl.height:
    res["vs_matched"] = {s: metrics4.block_bootstrap_diff(acc, ctrl, FRICTION, s)
                         for s in ("expectancy_R", "win_rate", "expectancy_points")}
if acc.height and opp.height:
    res["vs_opposite"] = {s: metrics4.block_bootstrap_diff(acc, opp, FRICTION, s)
                          for s in ("expectancy_R", "win_rate")}
if acc.height:
    res["strategy_ci"] = {s: metrics4.block_bootstrap_ci(acc, FRICTION, s)
                          for s in ("expectancy_R", "win_rate")}
    res["concentration"] = metrics4.weekly_concentration(acc, FRICTION)
    sg = acc.with_columns(
        pl.col("trading_date").dt.month().alias("month"),
        pl.col("trading_date").dt.weekday().alias("weekday"),
        pl.when(pl.col("sec_since_open") < 3600).then(pl.lit("hour1"))
          .otherwise(pl.lit("hour2")).alias("hour"),
        pl.col("side").alias("dir_label"),
        pl.col("bucket15").alias("bucket15"),
        (pl.col("atr1m").rank("ordinal") / pl.len() * 4).ceil().cast(pl.Int32).alias("vol_quartile"),
        (pl.col("r_points").rank("ordinal") / pl.len() * 4).ceil().cast(pl.Int32).alias("r_quartile"),
        (pl.col("edge").rank("ordinal") / pl.len() * 4).ceil().cast(pl.Int32).alias("edge_quartile"))
    tabs = {}
    for col in ("month", "weekday", "hour", "dir_label", "bucket15",
                "vol_quartile", "r_quartile", "edge_quartile"):
        tb = metrics4.by_group(sg, col, FRICTION)
        if tb.height:
            tb.write_csv(d_out / f"by_{col}.csv")
            tabs[col] = tb.to_dicts()
    res["subgroups"] = tabs

(d_out / "results.json").write_text(json.dumps(res, indent=2, default=str))
w = res["windows"]["0930_1130"]
print(f"\n[{a.split}] 09:30-11:30 @1.0pt : n={w.get('n_trades',0)} "
      f"({w.get('trades_per_day',float('nan')):.2f}/day) "
      f"WR={w.get('win_rate',float('nan')):.4f} E[R]={w.get('expectancy_R',float('nan')):+.4f} "
      f"PF(R)={w.get('profit_factor_R',float('nan')):.3f} "
      f"PF(pts)={w.get('profit_factor_points',float('nan')):.3f}")
if res["friction_sweep"]:
    print(f"  gross (0.0pt): E[R]={res['friction_sweep']['0.0']['expectancy_R']:+.4f}")
if "vs_matched" in res:
    v, ww = res["vs_matched"]["expectancy_R"], res["vs_matched"]["win_rate"]
    print(f"  vs matched random: dE[R]={v['diff']:+.4f} CI95=[{v['ci95_lo']:+.4f}, {v['ci95_hi']:+.4f}]"
          f"  dWR={ww['diff']:+.4f} CI95=[{ww['ci95_lo']:+.4f}, {ww['ci95_hi']:+.4f}]")
print(f"done in {time.time()-t0:.0f}s")
