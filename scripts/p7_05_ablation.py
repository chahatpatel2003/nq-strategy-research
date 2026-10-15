"""Phase-7 incremental-MBP ablation: A0 full vs A1 quote-only vs A2 trades+context.

Each arm gets its OWN scaler fitted on 2021 with its own feature subset and its
OWN selectivity thresholds from 2021, so the comparison is apples-to-apples.
Same dates, same R, same model family, same selectivity level, same execution.

DIAGNOSTIC ONLY.  An ablation may never be promoted to the production candidate.
"""
import argparse, json, pickle, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import numpy as np
import polars as pl

from nqr.p4 import metrics4
from nqr.p4.model4 import Preprocessor
from nqr.p7 import backtest7 as BT
from nqr.p7 import dataset7, model7
from nqr.p7 import features7 as F7

MODELS = ROOT / "strategies" / "orderbook_state" / "models"
OUT = ROOT / "strategies" / "orderbook_state" / "results"
FR = 1.0

ap = argparse.ArgumentParser()
ap.add_argument("--split", default="itest2023",
                choices=["select2022", "itest2023", "contam2024", "val2025h1"])
ap.add_argument("--confirm", default="")
a = ap.parse_args()
if a.split == "val2025h1":
    from nqr.p7 import holdout7 as H7
    H7.unlock_phase7_validation(a.confirm)

with open(MODELS / "production_model.pkl", "rb") as f:
    P = pickle.load(f)
TAG, FAM, Q = P["r_tag"], P["family"], P["selectivity"]
atr_edges, spr_edges = P["atr_edges"], P["spread_edges"]
print(f"ablation of {P['config_name']} on {a.split}")

dev = dataset7.load_split("dev")
yr_d = np.array([d.year for d in dev["trading_date"].to_list()])
tgt = dataset7.load_split("dev" if a.split in ("select2022", "itest2023")
                          else a.split.replace("val2025h1", "val2025h1"))
year = {"select2022": 2022, "itest2023": 2023}.get(a.split)
if year:
    tgt = tgt.filter(pl.col("trading_date").dt.year() == year)
nd = tgt["trading_date"].n_unique()
u_tr_all = dataset7.usable_mask(dev, TAG) & (yr_d == 2021)
u_tg = dataset7.usable_mask(tgt, TAG)
y_tr = dev[f"{TAG}_y"].to_numpy().astype(int)

rows, books = [], {}
for name, names in F7.ABLATIONS.items():
    Xd = dataset7.feature_matrix(dev, names)
    Xt = dataset7.feature_matrix(tgt, names)
    ok = np.isfinite(Xd).all(axis=1) & u_tr_all
    pre = Preprocessor.fit(Xd[ok], fit_on="train2021")
    est = model7.fit_model(FAM, pre.transform(Xd[ok]), y_tr[ok])
    th = model7.thresholds_from_train(est.predict_proba(pre.transform(Xd[ok]))[:, 1])[Q]
    p = np.full(tgt.height, np.nan)
    m = u_tg & np.isfinite(Xt).all(axis=1)
    p[m] = est.predict_proba(pre.transform(Xt[m]))[:, 1]
    conf = np.where(np.isfinite(p), model7.confidence(p), -np.inf)
    dirn = model7.direction_of(np.nan_to_num(p, nan=0.5))
    book = BT.run_strategy(tgt, TAG, conf, dirn, th, m)
    acc = BT.accepted(book)
    st = metrics4.summarize(acc, FR, n_days_available=nd) if acc.height else {}
    g0 = metrics4.summarize(acc, 0.0, nd) if acc.height else {}
    ctrl = (BT.matched_controls(book, tgt, TAG, m, atr_edges, spr_edges, mode="cross_day")
            if acc.height else pl.DataFrame())
    cm = metrics4.summarize(ctrl, FR, nd) if ctrl.height else {}
    books[name] = acc
    rows.append({"arm": name, "n_features": len(names), "tau": th,
                 "n_trades": st.get("n_trades", 0), "win_rate": st.get("win_rate", np.nan),
                 "gross_ER": g0.get("expectancy_R", np.nan),
                 "net_ER": st.get("expectancy_R", np.nan),
                 "pf_r": BT.pf_r(acc, FR) if acc.height else np.nan,
                 "control_ER": cm.get("expectancy_R", np.nan),
                 "advantage_R": st.get("expectancy_R", np.nan) - cm.get("expectancy_R", np.nan)})
    print(f"  {name:20s} feats={len(names):3d} n={st.get('n_trades',0):5d} "
          f"WR={st.get('win_rate',np.nan):.4f} gross={g0.get('expectancy_R',np.nan):+.4f} "
          f"net={st.get('expectancy_R',np.nan):+.4f} "
          f"PF(R)={BT.pf_r(acc,FR) if acc.height else float('nan'):.3f}")

tab = pl.DataFrame(rows)
res = {"split": a.split, "config": P["config_name"], "arms": rows}
# the mandatory incremental-MBP test: full vs trades+context, day-block bootstrap
if books["A0_full"].height and books["A2_trades_context"].height:
    d = metrics4.block_bootstrap_diff(books["A0_full"], books["A2_trades_context"], FR,
                                      "expectancy_R")
    dw = metrics4.block_bootstrap_diff(books["A0_full"], books["A2_trades_context"], FR,
                                       "win_rate")
    res["incremental_mbp"] = {"expectancy_R": d, "win_rate": dw}
    print(f"\nINCREMENTAL MBP (A0 full - A2 trades+context): "
          f"{d['diff']:+.4f} R  CI95=[{d['ci95_lo']:+.4f}, {d['ci95_hi']:+.4f}]")
if books["A0_full"].height and books["A1_quote_only"].height:
    d1 = metrics4.block_bootstrap_diff(books["A0_full"], books["A1_quote_only"], FR,
                                       "expectancy_R")
    res["full_vs_quote_only"] = d1
    print(f"A0 full - A1 quote-only: {d1['diff']:+.4f} R "
          f"CI95=[{d1['ci95_lo']:+.4f}, {d1['ci95_hi']:+.4f}]")
d_out = OUT / f"run_{a.split}"; d_out.mkdir(parents=True, exist_ok=True)
tab.write_csv(d_out / "ablation.csv")
(d_out / "ablation.json").write_text(json.dumps(res, indent=2, default=str))
print(f"\nwrote {d_out}/ablation.*")
