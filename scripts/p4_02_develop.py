"""Phase-4 chronological development.

    2021  fit the 6 preregistered models        (DISCOVERY_TRAIN)
    2022  evaluate all 18 configurations, pick  (SELECTION)
    2023  NOT TOUCHED HERE - see p4_03_itest.py (INTERNAL_TEST)

The selection criterion is fixed in SEARCH_BUDGET.md S4 and PREREG A13:
highest 2022 net expectancy in R at 1.0 pt friction over 09:30-11:30, subject
to >= 200 executed 2022 trades, ties broken on trade count.  Nothing else
participates.
"""
import json, pickle, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import numpy as np
import polars as pl

from nqr.p4 import backtest4 as BT
from nqr.p4 import dataset4, metrics4, model4
from nqr.p4 import holdout4 as H4
from nqr.p4.features4 import FEATURE_NAMES

OUT = ROOT / "strategies" / "state_discovery" / "models"
OUT.mkdir(parents=True, exist_ok=True)
MIN_2022_TRADES = 200
FRICTION = 1.0

t0 = time.time()
print("loading dev state dataset (09:30-11:30 only) ...", flush=True)
df = dataset4.load_split("dev", primary_only=True)
usable_all = dataset4.finite_mask(df)
yr = np.array([d.year for d in df["trading_date"].to_list()])
print(f"  rows={df.height:,}  usable={usable_all.sum():,}  "
      f"2021={int((yr==2021).sum()):,} 2022={int((yr==2022).sum()):,} "
      f"2023={int((yr==2023).sum()):,}  [{time.time()-t0:.0f}s]", flush=True)

# ---- guard: development may only ever see 2021-2023 -----------------------
for d in (df["trading_date"].min(), df["trading_date"].max()):
    assert H4.period_of(d) in ("DISCOVERY_TRAIN", "SELECTION", "INTERNAL_TEST"), d
assert set(np.unique(yr)) == {2021, 2022, 2023}

tr = (yr == 2021) & usable_all
se = (yr == 2022) & usable_all
X = dataset4.feature_matrix(df)
y = df["y"].to_numpy().astype(int)

# ---- preprocessing fitted on 2021 ONLY -----------------------------------
pre = model4.Preprocessor.fit(X[tr], fit_on="train2021")
Xs_tr = pre.transform(X[tr])
Xs_all = pre.transform(X)
print(f"scaler fitted on {pre.n_fit:,} 2021 rows only  [{time.time()-t0:.0f}s]", flush=True)

# ---- fit the 6 models on 2021 --------------------------------------------
models, thresholds, train_scores = {}, {}, {}
for mk in model4.model_keys():
    t1 = time.time()
    est = model4.fit_model(mk, Xs_tr, y[tr])
    s_tr = model4.score_of(est, Xs_tr)
    models[mk] = est
    train_scores[mk] = s_tr
    thresholds[mk] = {q: model4.threshold_from_train(s_tr, q)
                      for q in model4.THRESHOLD_QUANTILES}
    acc = float(((s_tr > 0).astype(int) == y[tr]).mean())
    print(f"  fit {mk:18s} train_acc={acc:.4f} "
          f"tau={[round(v,5) for v in thresholds[mk].values()]}  [{time.time()-t1:.0f}s]",
          flush=True)

# ---- evaluate all 18 configurations on 2022 ONLY --------------------------
df_se = df.filter(pl.Series(se))
u_se = usable_all[se]
n_days_2022 = df_se["trading_date"].n_unique()
print(f"\nSELECTION on 2022: {df_se.height:,} rows, {n_days_2022} days", flush=True)

rows, books = [], {}
for cfg in model4.enumerate_configs():
    s_se = model4.score_of(models[cfg.model_key], Xs_all[se])
    tau = thresholds[cfg.model_key][cfg.threshold_q]
    tr_book = BT.run_strategy(df_se, s_se, tau, u_se)
    acc_b = BT.accepted(tr_book)
    m = metrics4.summarize(acc_b, FRICTION, n_days_available=n_days_2022) if acc_b.height else {}
    n_cand = tr_book.height
    rows.append({"config": cfg.name, "family": cfg.family, "hyper": cfg.hyper,
                 "threshold_q": cfg.threshold_q, "tau": tau,
                 "n_candidates": n_cand,
                 "selection_rate": n_cand / max(1, int(u_se.sum())),
                 "n_trades": m.get("n_trades", 0),
                 "win_rate": m.get("win_rate", float("nan")),
                 "expectancy_R": m.get("expectancy_R", float("nan")),
                 "total_R": m.get("total_R", float("nan")),
                 "profit_factor": m.get("profit_factor", float("nan")),
                 "trades_per_day": m.get("trades_per_day", float("nan")),
                 "meets_min_trades": m.get("n_trades", 0) >= MIN_2022_TRADES})
    books[cfg.name] = acc_b
    print(f"  {cfg.name:26s} cand={n_cand:6d} trades={m.get('n_trades',0):5d} "
          f"WR={m.get('win_rate',float('nan')):.4f} "
          f"E[R]={m.get('expectancy_R',float('nan')):+.4f} "
          f"PF={m.get('profit_factor',float('nan')):.3f}", flush=True)

tab = pl.DataFrame(rows)
tab.write_parquet(OUT / "selection_2022.parquet")

# ---- the single preregistered selection rule ------------------------------
elig = tab.filter(pl.col("meets_min_trades") & pl.col("expectancy_R").is_not_nan())
shortfall = elig.height == 0
if shortfall:
    print(f"\n!! no configuration reached {MIN_2022_TRADES} 2022 trades - "
          "falling back to the highest-frequency configuration (SEARCH_BUDGET S4)")
    elig = tab.sort(["n_trades"], descending=True)
    winner = elig.row(0, named=True)
else:
    elig = elig.sort(["expectancy_R", "n_trades"], descending=[True, True])
    winner = elig.row(0, named=True)

print(f"\nSELECTED: {winner['config']}  "
      f"2022 E[R]={winner['expectancy_R']:+.4f} n={winner['n_trades']}")

wk = f"{winner['family']}:{winner['hyper']}"
interp = model4.interpret(models[wk], wk)
payload = {"preprocessor": pre.to_dict(), "model_key": wk,
           "threshold_q": winner["threshold_q"], "tau": winner["tau"],
           "config_name": winner["config"], "features": list(FEATURE_NAMES),
           "selection": {k: winner[k] for k in
                         ("n_trades", "win_rate", "expectancy_R", "total_R",
                          "profit_factor", "selection_rate")},
           "min_trades_shortfall": bool(shortfall),
           "total_configurations_evaluated": len(rows),
           "friction": FRICTION}
(OUT / "production_meta.json").write_text(json.dumps(payload, indent=2, default=str))
(OUT / "interpretation.json").write_text(json.dumps(interp, indent=2))
with open(OUT / "production_model.pkl", "wb") as f:
    pickle.dump({"pre": pre, "model_key": wk, "est": models[wk],
                 "tau": winner["tau"], "threshold_q": winner["threshold_q"]}, f)
with open(OUT / "all_models.pkl", "wb") as f:
    pickle.dump({"pre": pre, "models": models, "thresholds": thresholds}, f)
print(f"\nTOTAL CONFIGURATIONS EVALUATED: {len(rows)}  (budget {model4.MAX_CONFIGS})")
print(f"done in {time.time()-t0:.0f}s")
