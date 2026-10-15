"""Phase-7 null tests.

N1  LABEL PERMUTATION -- permute the training target WITHIN trading days,
    preserving day structure and feature marginals, refit the exact same model,
    recompute thresholds by the same rule, and rescore 2022.  >= 50 permutations.

N2  TEMPORAL SHIFT -- pair each decision's FEATURES with the LABELS of the same
    time-of-day slot on a DIFFERENT trading day.  The marginal distribution of
    both features and outcomes is preserved; only the causal link is destroyed.

Neither may be used to tune anything.
"""
import json, pickle, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import numpy as np
import polars as pl

from nqr.p4 import metrics4
from nqr.p4.model4 import Preprocessor
from nqr.p7 import backtest7 as BT
from nqr.p7 import dataset7, model7

MODELS = ROOT / "strategies" / "orderbook_state" / "models"
OUT = ROOT / "strategies" / "orderbook_state" / "results"
OUT.mkdir(parents=True, exist_ok=True)
FR = 1.0
N_PERM = 50
SEED = 20260822

with open(MODELS / "production_model.pkl", "rb") as f:
    P = pickle.load(f)
TAG, FAM, Q = P["r_tag"], P["family"], P["selectivity"]
print(f"nulls for {P['config_name']}  ({N_PERM} permutations)")

df = dataset7.load_split("dev")
yr = np.array([d.year for d in df["trading_date"].to_list()])
X = dataset7.feature_matrix(df)
u = dataset7.usable_mask(df, TAG)
tr = (yr == 2021) & u
se = yr == 2022
y = df[f"{TAG}_y"].to_numpy().astype(int)
pre = Preprocessor.fit(X[tr], fit_on="train2021")
Xs = pre.transform(X)
df_se = df.filter(pl.Series(se))
u_se = u[se]
nd = df_se["trading_date"].n_unique()


def evaluate(est, thr):
    p = est.predict_proba(Xs[se])[:, 1]
    book = BT.run_strategy(df_se, TAG, model7.confidence(p), model7.direction_of(p),
                           thr, u_se)
    acc = BT.accepted(book)
    if acc.height == 0:
        return {"n_trades": 0, "expectancy_R": np.nan, "win_rate": np.nan}
    m = metrics4.summarize(acc, FR, n_days_available=nd)
    m["profit_factor_R"] = BT.pf_r(acc, FR)
    return m


est0 = model7.fit_model(FAM, Xs[tr], y[tr])
thr0 = model7.thresholds_from_train(est0.predict_proba(Xs[tr])[:, 1])[Q]
obs = evaluate(est0, thr0)
print(f"observed 2022: n={obs['n_trades']} WR={obs['win_rate']:.4f} "
      f"E[R]={obs['expectancy_R']:+.4f}")

# ---- N1 label permutation within trading days ----------------------------
days_tr = np.array(df.filter(pl.Series(tr))["trading_date"].to_list(), dtype=object)
blocks = {d: np.flatnonzero(days_tr == d) for d in np.unique(days_tr)}
y_tr = y[tr]
rng = np.random.default_rng(SEED)
rows, t0 = [], time.time()
for k in range(N_PERM):
    yp = y_tr.copy()
    for b in blocks.values():
        yp[b] = y_tr[b][rng.permutation(len(b))]
    e = model7.fit_model(FAM, Xs[tr], yp)
    th = model7.thresholds_from_train(e.predict_proba(Xs[tr])[:, 1])[Q]
    m = evaluate(e, th)
    rows.append({"rep": k, "tau": th, "n_trades": m["n_trades"],
                 "win_rate": m["win_rate"], "expectancy_R": m["expectancy_R"]})
    if k % 10 == 0:
        print(f"  perm {k:2d}: n={m['n_trades']:5d} E[R]={m['expectancy_R']:+.4f} "
              f"[{time.time()-t0:.0f}s]", flush=True)
perm = pl.DataFrame(rows)
perm.write_csv(OUT / "null_permutation.csv")
er = perm["expectancy_R"].to_numpy(); er = er[np.isfinite(er)]
wr = perm["win_rate"].to_numpy(); wr = wr[np.isfinite(wr)]

# ---- N2 temporal shift: features from day D, labels from the same slot on D' --
sec = df["sec_since_open"].to_numpy()
d_all = np.array(df["trading_date"].to_list(), dtype=object)
udays = np.unique(d_all)
shift_map = {d: udays[(i + 7) % len(udays)] for i, d in enumerate(udays)}   # fixed +7 days
key_to_row = {(d_all[i], sec[i]): i for i in range(len(sec))}
src = np.array([key_to_row.get((shift_map[d_all[i]], sec[i]), -1) for i in range(len(sec))])
have = src >= 0
y_shift = np.where(have, y[np.maximum(src, 0)], y)
tr_s = tr & have
e_s = model7.fit_model(FAM, Xs[tr_s], y_shift[tr_s])
th_s = model7.thresholds_from_train(e_s.predict_proba(Xs[tr_s])[:, 1])[Q]
shift = evaluate(e_s, th_s)

res = {"n_perm": N_PERM, "config": P["config_name"],
       "observed_2022": {k: obs.get(k) for k in ("n_trades", "win_rate", "expectancy_R",
                                                 "profit_factor_R")},
       "permutation": {"mean_ER": float(er.mean()), "sd_ER": float(er.std(ddof=1)),
                       "min_ER": float(er.min()), "max_ER": float(er.max()),
                       "mean_WR": float(wr.mean()), "sd_WR": float(wr.std(ddof=1)),
                       "p_null_ge_observed_ER": float((er >= obs["expectancy_R"]).mean()),
                       "p_null_ge_observed_WR": float((wr >= obs["win_rate"]).mean())},
       "temporal_shift": {"rows_shifted": int(have.sum()), "shift_days": 7,
                          "n_trades": shift["n_trades"],
                          "win_rate": shift["win_rate"],
                          "expectancy_R": shift["expectancy_R"],
                          "observed_minus_shift_ER":
                              obs["expectancy_R"] - shift["expectancy_R"]}}
(OUT / "nulls.json").write_text(json.dumps(res, indent=2, default=str))
print(json.dumps(res, indent=2, default=str))
