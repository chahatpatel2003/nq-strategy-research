"""Null control C4 — randomised feature/target relationship.

PREREG A12.  Permute the training target WITHIN trading-day blocks (so feature
marginals and the day structure survive, and only the feature->target link is
destroyed), refit the FROZEN production configuration, recalibrate tau by the
same A7 procedure, and recompute the 2022 selection statistic.  Repeating this
gives the null distribution for the number that chose the production model.

Uses development data only.  Nothing here can change the frozen strategy.
"""
import json, pickle, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import numpy as np
import polars as pl

from nqr.p4 import backtest4 as BT
from nqr.p4 import dataset4, metrics4, model4

OUT = ROOT / "strategies" / "state_discovery" / "results"
OUT.mkdir(parents=True, exist_ok=True)
N_REP = 20
FRICTION = 1.0
SEED = 20260819

with open(ROOT / "strategies" / "state_discovery" / "models" / "production_model.pkl", "rb") as f:
    P = pickle.load(f)
mk, q_thr = P["model_key"], P["threshold_q"]
print(f"C4 null for the frozen configuration {mk} top{int(q_thr*100)}  ({N_REP} reps)")

df = dataset4.load_split("dev", primary_only=True)
usable = dataset4.finite_mask(df)
yr = np.array([d.year for d in df["trading_date"].to_list()])
tr = (yr == 2021) & usable
se = (yr == 2022)
X = dataset4.feature_matrix(df)
y = df["y"].to_numpy().astype(int)

df_se = df.filter(pl.Series(se))
u_se = usable[se]
n_days_2022 = df_se["trading_date"].n_unique()

# the observed statistic, recomputed here so the comparison is like-for-like
pre = model4.Preprocessor.fit(X[tr], "train2021")
Xs_tr = pre.transform(X[tr]); Xs_se = pre.transform(X[se])
est = model4.fit_model(mk, Xs_tr, y[tr])
tau = model4.threshold_from_train(model4.score_of(est, Xs_tr), q_thr)
obs_acc = BT.accepted(BT.run_strategy(df_se, model4.score_of(est, Xs_se), tau, u_se))
obs = metrics4.summarize(obs_acc, FRICTION, n_days_2022)
print(f"observed 2022: n={obs['n_trades']} WR={obs['win_rate']:.4f} "
      f"E[R]={obs['expectancy_R']:+.4f}")

# day blocks of the 2021 training partition
tr_days = np.array(df.filter(pl.Series(tr))["trading_date"].to_list(), dtype=object)
uniq_days = np.unique(tr_days)
blocks = {d: np.flatnonzero(tr_days == d) for d in uniq_days}
y_tr = y[tr]

rng = np.random.default_rng(SEED)
rows = []
t0 = time.time()
for rep in range(N_REP):
    yp = y_tr.copy()
    for d in uniq_days:                     # permute inside each trading day
        b = blocks[d]
        yp[b] = y_tr[b][rng.permutation(len(b))]
    e = model4.fit_model(mk, Xs_tr, yp)
    tau_r = model4.threshold_from_train(model4.score_of(e, Xs_tr), q_thr)
    acc = BT.accepted(BT.run_strategy(df_se, model4.score_of(e, Xs_se), tau_r, u_se))
    m = metrics4.summarize(acc, FRICTION, n_days_2022) if acc.height else {}
    rows.append({"rep": rep, "tau": tau_r, "n_trades": m.get("n_trades", 0),
                 "win_rate": m.get("win_rate", float("nan")),
                 "expectancy_R": m.get("expectancy_R", float("nan")),
                 "profit_factor": m.get("profit_factor", float("nan"))})
    print(f"  rep {rep:2d}: n={m.get('n_trades',0):6d} "
          f"WR={m.get('win_rate',float('nan')):.4f} "
          f"E[R]={m.get('expectancy_R',float('nan')):+.4f}  [{time.time()-t0:.0f}s]", flush=True)

tab = pl.DataFrame(rows)
tab.write_csv(OUT / "null_c4_permuted_target.csv")
er = tab["expectancy_R"].to_numpy(); wr = tab["win_rate"].to_numpy()
er = er[np.isfinite(er)]; wr = wr[np.isfinite(wr)]
res = {"n_rep": N_REP, "model_key": mk, "threshold_q": q_thr,
       "observed_2022": {k: obs.get(k) for k in ("n_trades", "win_rate", "expectancy_R",
                                                 "profit_factor")},
       "null_expectancy_R_mean": float(er.mean()), "null_expectancy_R_sd": float(er.std(ddof=1)),
       "null_expectancy_R_min": float(er.min()), "null_expectancy_R_max": float(er.max()),
       "null_win_rate_mean": float(wr.mean()), "null_win_rate_sd": float(wr.std(ddof=1)),
       "p_null_ge_observed_ER": float((er >= obs["expectancy_R"]).mean()),
       "p_null_ge_observed_WR": float((wr >= obs["win_rate"]).mean())}
(OUT / "null_c4.json").write_text(json.dumps(res, indent=2))
print(json.dumps(res, indent=2))
