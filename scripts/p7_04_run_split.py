"""Run the selected Phase-7 candidate, unchanged, over one split.

    python scripts/p7_04_run_split.py --split itest2023
    python scripts/p7_04_run_split.py --split contam2024
    python scripts/p7_04_run_split.py --split val2025h1 --confirm <phrase>
"""
import argparse, json, pickle, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import numpy as np
import polars as pl

from nqr.p4 import metrics4
from nqr.p7 import backtest7 as BT
from nqr.p7 import dataset7, model7
from nqr.p7 import features7 as F7
from nqr.p7 import holdout7 as H7

MODELS = ROOT / "strategies" / "orderbook_state" / "models"
OUT = ROOT / "strategies" / "orderbook_state" / "results"
FR = 1.0
DATASET_OF = {"train2021": "dev", "select2022": "dev", "itest2023": "dev",
              "contam2024": "contam2024", "val2025h1": "val2025h1"}
WINDOWS = {"0930_1130": (0, 7200), "0930_1030": (0, 3600), "1030_1130": (3600, 7200)}

ap = argparse.ArgumentParser()
ap.add_argument("--split", choices=list(DATASET_OF), required=True)
ap.add_argument("--confirm", default="")
a = ap.parse_args()
if a.split == "val2025h1":
    H7.unlock_phase7_validation(a.confirm)
    print("*** FRESH MBP-1 VALIDATION - 2025-H1 - ONE SHOT ***")
if a.split == "contam2024":
    print("*** CONTAMINATED DIAGNOSTIC - NOT VALIDATION ***")

start, end = H7.SPLITS[a.split]
H7.assert_range_allowed(start, end, f"--split {a.split}")

with open(MODELS / "production_model.pkl", "rb") as f:
    P = pickle.load(f)
pre, est, tau, TAG, FAM = P["pre"], P["est"], P["tau"], P["r_tag"], P["family"]
atr_edges, spr_edges = P["atr_edges"], P["spread_edges"]
assert pre.fit_on == "train2021", "the scaler must be the 2021-only one"
print(f"candidate: {P['config_name']}  R={dataset7.R_POINTS[TAG]}pt  tau={tau:.6f}")

t0 = time.time()
df = dataset7.load_split(DATASET_OF[a.split])
df = df.filter((pl.col("trading_date") >= start) & (pl.col("trading_date") <= end))
assert df.height, "no rows for this split"
for d in (df["trading_date"].min(), df["trading_date"].max()):
    H7.assert_date_allowed(d, "split row")
u = dataset7.usable_mask(df, TAG)
X = dataset7.feature_matrix(df)
p = np.full(df.height, np.nan)
p[u] = est.predict_proba(pre.transform(X[u]))[:, 1]
conf = np.where(np.isfinite(p), model7.confidence(p), -np.inf)
direction = model7.direction_of(np.nan_to_num(p, nan=0.5))
sec = df["sec_since_open"].to_numpy()
nd = df["trading_date"].n_unique()
print(f"rows={df.height:,} usable={int(u.sum()):,} days={nd}  [{time.time()-t0:.0f}s]", flush=True)

d_out = OUT / f"run_{a.split}"; d_out.mkdir(parents=True, exist_ok=True)
res = {"split": a.split, "start": str(start), "end": str(end),
       "config": P["config_name"], "r_tag": TAG, "r_points": dataset7.R_POINTS[TAG],
       "family": FAM, "tau": tau, "selectivity": P["selectivity"],
       "friction_primary": FR, "is_contaminated": a.split == "contam2024",
       "is_fresh_validation": a.split == "val2025h1",
       "n_rows": df.height, "n_usable": int(u.sum()), "n_days": nd}

windows = {}
for w, (lo, hi) in WINDOWS.items():
    m = (sec >= lo) & (sec < hi)
    sub = df.filter(pl.Series(m))
    ndw = sub["trading_date"].n_unique()
    book = BT.run_strategy(sub, TAG, conf[m], direction[m], tau, u[m])
    acc = BT.accepted(book)
    st = metrics4.summarize(acc, FR, n_days_available=ndw) if acc.height else {}
    if st:
        st["profit_factor_R"] = BT.pf_r(acc, FR)
        st["profit_factor_points"] = st["profit_factor"]
    windows[w] = st
    if w == "0930_1130":
        pbook, psub, pmask, pdays = book, sub, m, ndw
    print(f"  {w}: cand={book.height:5d} trades={st.get('n_trades',0):5d} "
          f"WR={st.get('win_rate',np.nan):.4f} E[R]={st.get('expectancy_R',np.nan):+.4f} "
          f"PF(R)={st.get('profit_factor_R',np.nan):.3f}", flush=True)
res["windows"] = windows

acc = BT.accepted(pbook)
u_p = u[pmask]
pbook.write_parquet(d_out / "signals.parquet")
if acc.height:
    feats = psub.select(["decision_ts_ns"] + F7.FEATURE_NAMES)
    acc.join(feats, on="decision_ts_ns", how="left").write_parquet(d_out / "trades.parquet")
    acc.write_csv(d_out / "trades.csv")
    fs = {}
    for fr in dataset7.FRICTIONS:
        m_ = metrics4.summarize(acc, fr, pdays)
        m_["profit_factor_R"] = BT.pf_r(acc, fr)
        fs[str(fr)] = m_
    res["friction_sweep"] = fs
res["skip_reasons"] = (pbook.filter(pl.col("status") == "SKIPPED")
                       .group_by("skip_reason").len().to_dicts() if pbook.height else [])

for mode in ("cross_day", "same_day_forward"):
    c = BT.matched_controls(pbook, psub, TAG, u_p, atr_edges, spr_edges, mode=mode)
    if c.height:
        c.write_parquet(d_out / f"control_{mode}.parquet")
        res[f"control_{mode}"] = metrics4.summarize(c, FR, pdays)
        res[f"control_{mode}"]["profit_factor_R"] = BT.pf_r(c, FR)
        res[f"vs_{mode}"] = {s: metrics4.block_bootstrap_diff(acc, c, FR, s)
                             for s in ("expectancy_R", "win_rate", "expectancy_points")}
    print(f"  control[{mode}]: n={c.height} "
          f"E[R]={res.get(f'control_{mode}',{}).get('expectancy_R',np.nan):+.4f}")

opp = BT.opposite_direction(pbook, psub, TAG)
if opp.height:
    opp.write_parquet(d_out / "control_opposite.parquet")
    res["control_opposite"] = metrics4.summarize(opp, FR, pdays)
    res["control_opposite"]["profit_factor_R"] = BT.pf_r(opp, FR)
    res["vs_opposite"] = {s: metrics4.block_bootstrap_diff(acc, opp, FR, s)
                          for s in ("expectancy_R", "win_rate")}
if acc.height:
    res["strategy_ci"] = {s: metrics4.block_bootstrap_ci(acc, FR, s)
                          for s in ("expectancy_R", "win_rate")}
    res["concentration"] = metrics4.weekly_concentration(acc, FR)
    sg = acc.with_columns(
        pl.col("trading_date").dt.month().alias("month"),
        pl.col("trading_date").dt.weekday().alias("weekday"),
        pl.when(pl.col("sec_since_open") < 3600).then(pl.lit("hour1"))
          .otherwise(pl.lit("hour2")).alias("hour"),
        (pl.col("sec_since_open") // 900).alias("bucket15m"),
        pl.col("side").alias("dir_label"),
        (pl.col("atr1m_ticks").rank("ordinal") / pl.len() * 4).ceil().cast(pl.Int32).alias("vol_q"),
        (pl.col("spread_ticks").rank("ordinal") / pl.len() * 4).ceil().cast(pl.Int32).alias("spread_q"),
        (pl.col("score").rank("ordinal") / pl.len() * 4).ceil().cast(pl.Int32).alias("conf_q"))
    tabs = {}
    for col in ("month", "weekday", "hour", "bucket15m", "dir_label", "vol_q",
                "spread_q", "conf_q"):
        tb = metrics4.by_group(sg, col, FR)
        if tb.height:
            tb.write_csv(d_out / f"by_{col}.csv")
            tabs[col] = tb.to_dicts()
    res["subgroups"] = tabs

(d_out / "results.json").write_text(json.dumps(res, indent=2, default=str))
w = res["windows"]["0930_1130"]
print(f"\n[{a.split}] 09:30-11:30 @1.0pt : n={w.get('n_trades',0)} "
      f"({w.get('trades_per_day',np.nan):.2f}/day) WR={w.get('win_rate',np.nan):.4f} "
      f"E[R]={w.get('expectancy_R',np.nan):+.4f} PF(R)={w.get('profit_factor_R',np.nan):.3f}")
if "friction_sweep" in res:
    print(f"  gross (0.0pt): {res['friction_sweep']['0.0']['expectancy_R']:+.4f}")
for mode in ("cross_day", "same_day_forward"):
    if f"vs_{mode}" in res:
        v = res[f"vs_{mode}"]["expectancy_R"]
        print(f"  vs matched random [{mode}]: d={v['diff']:+.4f} "
              f"CI95=[{v['ci95_lo']:+.4f}, {v['ci95_hi']:+.4f}]")
print(f"done in {time.time()-t0:.0f}s")
