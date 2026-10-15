"""Phase-7 mandatory diagnostics, run AFTER the phase failed its 2022 gates.

No candidate was selected, so there is no production model.  These run on the
REFERENCE configuration -- the least-bad of the 12 on 2022 -- purely to answer
the central research question, and on the 2022 selection split only, so that
2023 is never opened.  Nothing here can rescue anything.

  1. INCREMENTAL-MBP ABLATION  A0 full (40) vs A1 quote-only (32) vs A2 trades+context (8)
  2. NULL N1  label permutation within training days, 50 refits
  3. NULL N2  temporal shift: features from day D paired with labels from D+7
  4. feature importance / grouped importance by family
"""
import json, sys, time
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

SD = ROOT / "strategies" / "orderbook_state"
OUT = SD / "results"; OUT.mkdir(parents=True, exist_ok=True)
FR = 1.0
N_PERM = 50
SEED = 20260822

sel = pl.read_parquet(SD / "models" / "selection_2022.parquet")
ref = sel.sort("net_ER", descending=True).row(0, named=True)
TAG, FAM, Q = ref["r_tag"], ref["family"], ref["selectivity"]
meta = json.loads((SD / "models" / "development_meta.json").read_text())
atr_edges = np.array(meta["atr_edges"]); spr_edges = np.array(meta["spread_edges"])
print(f"REFERENCE CONFIGURATION (least-bad of 12, NOT a candidate): {ref['config']}")
print(f"  2022: n={ref['n_trades']} net E[R]={ref['net_ER']:+.4f} PF(R)={ref['pf_r']:.3f}\n")

df = dataset7.load_split("dev")
yr = np.array([d.year for d in df["trading_date"].to_list()])
tr_mask, se_mask = yr == 2021, yr == 2022
u_all = dataset7.usable_mask(df, TAG)
y = df[f"{TAG}_y"].to_numpy().astype(int)
df_se = df.filter(pl.Series(se_mask))
u_se_all = u_all[se_mask]
nd = df_se["trading_date"].n_unique()


def evaluate(names, est, pre, thr, Xt_all):
    m = u_se_all & np.isfinite(Xt_all[se_mask]).all(axis=1)
    p = np.full(int(se_mask.sum()), np.nan)
    p[m] = est.predict_proba(pre.transform(Xt_all[se_mask][m]))[:, 1]
    conf = np.where(np.isfinite(p), model7.confidence(p), -np.inf)
    dirn = model7.direction_of(np.nan_to_num(p, nan=0.5))
    book = BT.run_strategy(df_se, TAG, conf, dirn, thr, m)
    acc = BT.accepted(book)
    return book, acc, m


# ---------------------------------------------- 1. incremental-MBP ablation
print("=" * 92)
print("1. INCREMENTAL-MBP ABLATION on 2022  (same dates, R, family, selectivity, execution)")
print("=" * 92)
rows, books = [], {}
for name, names in F7.ABLATIONS.items():
    Xa = dataset7.feature_matrix(df, names)
    ok = np.isfinite(Xa).all(axis=1) & tr_mask & u_all
    pre = Preprocessor.fit(Xa[ok], fit_on="train2021")
    est = model7.fit_model(FAM, pre.transform(Xa[ok]), y[ok])
    thr = model7.thresholds_from_train(est.predict_proba(pre.transform(Xa[ok]))[:, 1])[Q]
    book, acc, m = evaluate(names, est, pre, thr, Xa)
    st = metrics4.summarize(acc, FR, n_days_available=nd) if acc.height else {}
    g0 = metrics4.summarize(acc, 0.0, nd) if acc.height else {}
    ctrl = (BT.matched_controls(book, df_se, TAG, m, atr_edges, spr_edges, mode="cross_day")
            if acc.height else pl.DataFrame())
    cm = metrics4.summarize(ctrl, FR, nd) if ctrl.height else {}
    acc_tr = float(((est.predict_proba(pre.transform(Xa[ok]))[:, 1] >= 0.5).astype(int)
                    == y[ok]).mean())
    books[name] = acc
    rows.append({"arm": name, "n_features": len(names), "train_acc": acc_tr, "tau": thr,
                 "n_trades": st.get("n_trades", 0), "win_rate": st.get("win_rate", np.nan),
                 "gross_ER": g0.get("expectancy_R", np.nan),
                 "net_ER": st.get("expectancy_R", np.nan),
                 "pf_r": BT.pf_r(acc, FR) if acc.height else np.nan,
                 "control_ER": cm.get("expectancy_R", np.nan),
                 "advantage_R": st.get("expectancy_R", np.nan) - cm.get("expectancy_R", np.nan)})
    print(f"  {name:20s} feats={len(names):3d} train_acc={acc_tr:.4f} n={st.get('n_trades',0):5d} "
          f"WR={st.get('win_rate',np.nan):.4f} gross={g0.get('expectancy_R',np.nan):+.4f} "
          f"net={st.get('expectancy_R',np.nan):+.4f} "
          f"PF(R)={BT.pf_r(acc,FR) if acc.height else float('nan'):.3f} "
          f"adv={st.get('expectancy_R',np.nan)-cm.get('expectancy_R',np.nan):+.4f}")

res = {"reference_config": ref["config"], "note": "NO CANDIDATE WAS SELECTED - diagnostics only",
       "ablation": rows}
if books["A0_full"].height and books["A2_trades_context"].height:
    d = metrics4.block_bootstrap_diff(books["A0_full"], books["A2_trades_context"], FR, "expectancy_R")
    dw = metrics4.block_bootstrap_diff(books["A0_full"], books["A2_trades_context"], FR, "win_rate")
    res["incremental_mbp"] = {"expectancy_R": d, "win_rate": dw}
    print(f"\n  INCREMENTAL MBP  (A0 full - A2 trades+context): {d['diff']:+.4f} R  "
          f"CI95=[{d['ci95_lo']:+.4f}, {d['ci95_hi']:+.4f}]  "
          f"{'excludes 0' if d['ci95_lo']>0 or d['ci95_hi']<0 else 'CONTAINS 0'}")
if books["A0_full"].height and books["A1_quote_only"].height:
    d1 = metrics4.block_bootstrap_diff(books["A0_full"], books["A1_quote_only"], FR, "expectancy_R")
    res["full_vs_quote_only"] = d1
    print(f"  A0 full - A1 quote-only: {d1['diff']:+.4f} R "
          f"CI95=[{d1['ci95_lo']:+.4f}, {d1['ci95_hi']:+.4f}]")

# ------------------------------------------------------------- 2/3. nulls
print("\n" + "=" * 92)
print(f"2. NULL N1 - label permutation within training days ({N_PERM} refits)")
print("=" * 92)
X = dataset7.feature_matrix(df)
tr = tr_mask & u_all
pre0 = Preprocessor.fit(X[tr], fit_on="train2021")
Xs = pre0.transform(X)
est0 = model7.fit_model(FAM, Xs[tr], y[tr])
thr0 = model7.thresholds_from_train(est0.predict_proba(Xs[tr])[:, 1])[Q]
_, acc0, _ = evaluate(F7.FEATURE_NAMES, est0, pre0, thr0, X)
obs = metrics4.summarize(acc0, FR, nd)
print(f"  observed 2022: n={obs['n_trades']} WR={obs['win_rate']:.4f} E[R]={obs['expectancy_R']:+.4f}")

days_tr = np.array(df.filter(pl.Series(tr))["trading_date"].to_list(), dtype=object)
blocks = [np.flatnonzero(days_tr == d) for d in np.unique(days_tr)]
y_tr = y[tr]
rng = np.random.default_rng(SEED)
perm_rows, t0 = [], time.time()
for k in range(N_PERM):
    yp = y_tr.copy()
    for b in blocks:
        yp[b] = y_tr[b][rng.permutation(len(b))]
    e = model7.fit_model(FAM, Xs[tr], yp)
    th = model7.thresholds_from_train(e.predict_proba(Xs[tr])[:, 1])[Q]
    _, a, _ = evaluate(F7.FEATURE_NAMES, e, pre0, th, X)
    m = metrics4.summarize(a, FR, nd) if a.height else {}
    perm_rows.append({"rep": k, "n_trades": m.get("n_trades", 0),
                      "win_rate": m.get("win_rate", np.nan),
                      "expectancy_R": m.get("expectancy_R", np.nan)})
    if k % 10 == 0:
        print(f"    perm {k:2d}: n={m.get('n_trades',0):5d} "
              f"E[R]={m.get('expectancy_R',np.nan):+.4f}  [{time.time()-t0:.0f}s]", flush=True)
perm = pl.DataFrame(perm_rows); perm.write_csv(OUT / "null_permutation.csv")
er = perm["expectancy_R"].to_numpy(); er = er[np.isfinite(er)]
wr = perm["win_rate"].to_numpy(); wr = wr[np.isfinite(wr)]
res["null_permutation"] = {
    "n_perm": N_PERM, "observed_ER": obs["expectancy_R"], "observed_WR": obs["win_rate"],
    "null_mean_ER": float(er.mean()), "null_sd_ER": float(er.std(ddof=1)),
    "null_min_ER": float(er.min()), "null_max_ER": float(er.max()),
    "null_mean_WR": float(wr.mean()),
    "p_null_ge_observed_ER": float((er >= obs["expectancy_R"]).mean()),
    "p_null_ge_observed_WR": float((wr >= obs["win_rate"]).mean())}
print(f"  null E[R] {er.mean():+.4f} +/- {er.std(ddof=1):.4f}  range [{er.min():+.4f}, {er.max():+.4f}]")
print(f"  p(null >= observed) E[R] = {res['null_permutation']['p_null_ge_observed_ER']:.3f}  "
      f"WR = {res['null_permutation']['p_null_ge_observed_WR']:.3f}")

print("\n" + "=" * 92)
print("3. NULL N2 - temporal shift (features from day D, labels from D+7)")
print("=" * 92)
sec = df["sec_since_open"].to_numpy()
d_all = np.array(df["trading_date"].to_list(), dtype=object)
udays = np.unique(d_all)
shift = {d: udays[(i + 7) % len(udays)] for i, d in enumerate(udays)}
key = {(d_all[i], int(sec[i])): i for i in range(len(sec))}
src = np.array([key.get((shift[d_all[i]], int(sec[i])), -1) for i in range(len(sec))])
have = src >= 0
y_sh = np.where(have, y[np.maximum(src, 0)], y)
tr_s = tr & have
e_s = model7.fit_model(FAM, Xs[tr_s], y_sh[tr_s])
th_s = model7.thresholds_from_train(e_s.predict_proba(Xs[tr_s])[:, 1])[Q]
_, a_s, _ = evaluate(F7.FEATURE_NAMES, e_s, pre0, th_s, X)
ms = metrics4.summarize(a_s, FR, nd) if a_s.height else {}
res["null_temporal_shift"] = {"rows_shifted": int(have.sum()), "shift_trading_days": 7,
                              "n_trades": ms.get("n_trades", 0),
                              "win_rate": ms.get("win_rate", np.nan),
                              "expectancy_R": ms.get("expectancy_R", np.nan),
                              "observed_minus_shift": obs["expectancy_R"] - ms.get("expectancy_R", np.nan)}
print(f"  shifted {int(have.sum()):,} rows  n={ms.get('n_trades',0)} "
      f"WR={ms.get('win_rate',np.nan):.4f} E[R]={ms.get('expectancy_R',np.nan):+.4f}")
print(f"  observed - shifted = {obs['expectancy_R'] - ms.get('expectancy_R', np.nan):+.4f} R")

# ------------------------------------------------- 4. feature importance
print("\n" + "=" * 92)
print("4. FEATURE IMPORTANCE (reference configuration)")
print("=" * 92)
interp = model7.interpret(est0, FAM)
if interp["kind"] == "logistic":
    coefs = interp["coefficients"]
    print(f"  elastic-net logistic, {interp['n_nonzero']}/40 non-zero coefficients")
    for n, v in interp["top15"]:
        print(f"    {n:26s} {v:+.5f}   (family {F7.FAMILY_OF[n]})")
    grp = {}
    for n, v in coefs.items():
        grp.setdefault(F7.FAMILY_OF[n], []).append(abs(v))
    tot = sum(sum(v) for v in grp.values())
    FAMNAME = {1: "BBO state", 2: "imbalance persistence", 3: "microprice pressure",
               4: "quote update intensity", 5: "OFI", 6: "size decrease/increase",
               7: "price-level steps", 8: "trade aggression",
               9: "replenishment after aggression", 10: "failure to advance",
               11: "minimal context"}
    print("\n  grouped |coefficient| share by family:")
    gs = {}
    for f in sorted(grp):
        s = sum(grp[f]); gs[FAMNAME[f]] = s / tot
        print(f"    {f:2d} {FAMNAME[f]:32s} n={len(grp[f]):2d}  mean|coef|={np.mean(grp[f]):.5f}  "
              f"share={s/tot:6.1%}")
    mbp = sum(gs[FAMNAME[f]] for f in (1,2,3,4,5,6,7))
    print(f"\n    pure book families (1-7): {mbp:.1%} of total |coefficient| mass")
    res["feature_importance"] = {"kind": "logistic", "top15": interp["top15"],
                                 "family_share": gs, "book_share_1_7": mbp}
else:
    res["feature_importance"] = interp
(SD / "models" / "interpretation_reference.json").write_text(json.dumps(interp, indent=2))
pl.DataFrame(rows).write_csv(OUT / "ablation.csv")
(OUT / "diagnostics.json").write_text(json.dumps(res, indent=2, default=str))
print(f"\nwrote {OUT}/diagnostics.json")
