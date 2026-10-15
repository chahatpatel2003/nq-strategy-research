"""Phase-5 chronological development.

    2021  fit preprocessor, control baseline, 6 models, 3 thresholds each
    2022  evaluate all 18 configurations, apply the selection criterion + Gate E
    2023  NOT TOUCHED HERE - see p5_03_run_split.py

Selection criterion (PHASE5_SEARCH_BUDGET S5, fixed before any outcome):
highest 2022 net expectancy in R at 1.0 pt friction over 09:30-11:30, subject to
>= 100 executed 2022 trades, ties broken on trade count.

Gate E (S6) additionally requires net E[R] > 0, PF > 1.05 and a positive
advantage over matched random.  Ranking first is NOT sufficient.
"""
import json, pickle, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import numpy as np
import polars as pl

from nqr.p4 import metrics4                    # frozen upstream, read-only
from nqr.p4.model4 import Preprocessor         # frozen upstream, read-only
from nqr.p5 import backtest5 as BT
from nqr.p5 import dataset5, model5
from nqr.p5 import holdout5 as H5
from nqr.p4.features4 import FEATURE_NAMES

OUT = ROOT / "strategies" / "larger_r" / "models"
OUT.mkdir(parents=True, exist_ok=True)
MIN_2022_TRADES = 100
FRICTION = 1.0

t0 = time.time()
df = dataset5.load_split("dev")
yr = np.array([d.year for d in df["trading_date"].to_list()])
assert set(np.unique(yr)) == {2021, 2022, 2023}
for d in (df["trading_date"].min(), df["trading_date"].max()):
    assert H5.period_of(d) in ("DISCOVERY_TRAIN", "SELECTION", "INTERNAL_TEST"), d
print(f"dev rows={df.height:,} days={df['trading_date'].n_unique()} "
      f"2021={int((yr==2021).sum()):,} 2022={int((yr==2022).sum()):,} "
      f"2023={int((yr==2023).sum()):,}  [{time.time()-t0:.0f}s]", flush=True)

X = dataset5.feature_matrix(df)
sec = df["sec_since_open"].to_numpy()
feat_ok = np.isfinite(X).all(axis=1) & (df["entry_ns"].to_numpy() > 0)
tr_all = (yr == 2021) & feat_ok
se_mask = (yr == 2022)

# ---- preprocessing fitted on 2021 ONLY (label-independent) ----------------
pre = Preprocessor.fit(X[tr_all], fit_on="train2021")
Xs = pre.transform(X)
print(f"scaler fitted on {pre.n_fit:,} 2021 rows only", flush=True)

df_se = df.filter(pl.Series(se_mask))
Xs_se, sec_se = Xs[se_mask], sec[se_mask]
n_days_2022 = df_se["trading_date"].n_unique()

models, thresholds, baselines, interps = {}, {}, {}, {}
rows, books = [], {}
for r_tag in dataset5.R_MULTS:
    u_all = dataset5.usable_mask(df, r_tag)
    tr = (yr == 2021) & u_all
    y_long = (df[f"{r_tag}_long_points"].to_numpy() > 0).astype(int)
    y_short = (df[f"{r_tag}_short_points"].to_numpy() > 0).astype(int)

    # ---- control baseline from TRAINING rows only ----
    base = model5.fit_baseline(sec[tr], y_long[tr], y_short[tr])
    baselines[r_tag] = base
    bl_tr, bs_tr = model5.baseline_vectors(base, sec[tr])
    bl_se, bs_se = model5.baseline_vectors(base, sec_se)
    print(f"\n[{r_tag}] train rows={int(tr.sum()):,}  "
          f"baseline long={base['overall_long']:.4f} short={base['overall_short']:.4f} "
          f"(theoretical 50% is NOT the null)", flush=True)

    for fam in model5.FAMILIES:
        t1 = time.time()
        est = model5.fit_model(fam, Xs[tr], y_long[tr])
        mk = f"{r_tag}:{fam}"
        models[mk] = est
        interps[mk] = model5.interpret(est, fam)
        p_tr = est.predict_proba(Xs[tr])[:, 1]
        s_tr, _ = model5.edge_and_direction(p_tr, bl_tr, bs_tr)
        thresholds[mk] = {q: model5.threshold_from_train(s_tr, q)
                          for q in model5.SELECTIVITY}
        print(f"  fit {mk:16s} acc={float(((p_tr>0.5).astype(int)==y_long[tr]).mean()):.4f} "
              f"tau={[round(v,5) for v in thresholds[mk].values()]} [{time.time()-t1:.0f}s]",
              flush=True)

        p_se = est.predict_proba(Xs_se)[:, 1]
        s_se, d_se = model5.edge_and_direction(p_se, bl_se, bs_se)
        u_se = u_all[se_mask]
        for q in model5.SELECTIVITY:
            cfg = model5.Config(r_tag, fam, q)
            tau = thresholds[mk][q]
            book = BT.run_strategy(df_se, r_tag, s_se, d_se, tau, u_se)
            acc = BT.accepted(book)
            m = metrics4.summarize(acc, FRICTION, n_days_available=n_days_2022) if acc.height else {}
            ctrl = BT.matched_controls(book, df_se, r_tag, u_se)
            cm = metrics4.summarize(ctrl, FRICTION, n_days_2022) if ctrl.height else {}
            adv = m.get("expectancy_R", float("nan")) - cm.get("expectancy_R", float("nan"))
            g0 = metrics4.summarize(acc, 0.0, n_days_2022) if acc.height else {}
            rows.append({
                "config": cfg.name, "r_tag": r_tag, "family": fam, "selectivity": q,
                "tau": tau, "n_candidates": book.height,
                "selection_rate": book.height / max(1, int(u_se.sum())),
                "n_trades": m.get("n_trades", 0),
                "trades_per_day": m.get("trades_per_day", float("nan")),
                "win_rate": m.get("win_rate", float("nan")),
                "expectancy_R": m.get("expectancy_R", float("nan")),
                "gross_expectancy_R": g0.get("expectancy_R", float("nan")),
                "profit_factor": m.get("profit_factor", float("nan")),
                "total_R": m.get("total_R", float("nan")),
                "median_hold_min": m.get("median_hold_min", float("nan")),
                "control_expectancy_R": cm.get("expectancy_R", float("nan")),
                "advantage_R": adv,
                "meets_min_trades": m.get("n_trades", 0) >= MIN_2022_TRADES,
                "gateE_expectancy": m.get("expectancy_R", -9) > 0,
                "gateE_pf": m.get("profit_factor", 0) > 1.05,
                "gateE_advantage": adv > 0,
            })
            books[cfg.name] = acc
            print(f"    {cfg.name:24s} n={m.get('n_trades',0):5d} "
                  f"({m.get('trades_per_day',float('nan')):4.1f}/d) "
                  f"WR={m.get('win_rate',float('nan')):.4f} "
                  f"E[R]={m.get('expectancy_R',float('nan')):+.4f} "
                  f"gross={g0.get('expectancy_R',float('nan')):+.4f} "
                  f"PF={m.get('profit_factor',float('nan')):.3f} "
                  f"adv={adv:+.4f}", flush=True)

tab = pl.DataFrame(rows)
tab = tab.with_columns((pl.col("gateE_expectancy") & pl.col("gateE_pf")
                        & pl.col("gateE_advantage")).alias("gateE_pass"))
tab.write_parquet(OUT / "selection_2022.parquet")
tab.write_csv(OUT / "selection_2022.csv")

elig = tab.filter(pl.col("meets_min_trades") & pl.col("expectancy_R").is_not_nan())
ranked = elig.sort(["expectancy_R", "n_trades"], descending=[True, True])
print("\n" + "=" * 78)
print(f"TOTAL CONFIGURATIONS EVALUATED: {tab.height}  (budget {model5.MAX_CONFIGS})")
print(f"configurations clearing the {MIN_2022_TRADES}-trade minimum: {elig.height}/18")
print(f"configurations passing Gate E (E[R]>0, PF>1.05, adv>0): "
      f"{int(tab['gateE_pass'].sum())}/18")

if ranked.height == 0 or int(tab["gateE_pass"].sum()) == 0:
    winner = ranked.row(0, named=True) if ranked.height else None
    verdict = {"gateE_pass": False, "n_gateE": int(tab["gateE_pass"].sum()),
               "best_config": winner["config"] if winner else None,
               "best_expectancy_R": winner["expectancy_R"] if winner else None,
               "decision": "PHASE 5 FAILS BEFORE VALIDATION - no configuration "
                           "passed Gate E on 2022; 2026-Q1 stays sealed."}
    print("\n*** NO CONFIGURATION PASSED GATE E ***")
    if winner:
        print(f"    best was {winner['config']} at E[R]={winner['expectancy_R']:+.4f}, "
              f"PF={winner['profit_factor']:.3f}, adv={winner['advantage_R']:+.4f}")
    print("    PHASE 5 FAILS BEFORE VALIDATION. 2026-Q1 stays sealed.")
else:
    ok = ranked.filter(pl.col("gateE_pass"))
    winner = ok.row(0, named=True)
    verdict = {"gateE_pass": True, "n_gateE": int(tab["gateE_pass"].sum()),
               "best_config": winner["config"],
               "best_expectancy_R": winner["expectancy_R"],
               "decision": "candidate proceeds to the 2023 internal OOS test (Gate F)"}
    print(f"\nSELECTED: {winner['config']}  2022 E[R]={winner['expectancy_R']:+.4f} "
          f"n={winner['n_trades']} PF={winner['profit_factor']:.3f} "
          f"adv={winner['advantage_R']:+.4f}")

payload = {"spec_version": "largerr-1.0.0", "friction": FRICTION,
           "total_configurations_evaluated": tab.height,
           "min_2022_trades": MIN_2022_TRADES,
           "preprocessor": pre.to_dict(), "baselines": baselines,
           "thresholds": {k: {str(q): v for q, v in d.items()} for k, d in thresholds.items()},
           "features": list(FEATURE_NAMES), "verdict": verdict,
           "winner": (winner if verdict["gateE_pass"] else None)}
(OUT / "development_meta.json").write_text(json.dumps(payload, indent=2, default=str))
(OUT / "interpretation_all.json").write_text(json.dumps(interps, indent=2))
with open(OUT / "all_models.pkl", "wb") as f:
    pickle.dump({"pre": pre, "models": models, "thresholds": thresholds,
                 "baselines": baselines}, f)
if verdict["gateE_pass"]:
    wk = f"{winner['r_tag']}:{winner['family']}"
    with open(OUT / "production_model.pkl", "wb") as f:
        pickle.dump({"pre": pre, "r_tag": winner["r_tag"], "family": winner["family"],
                     "est": models[wk], "tau": winner["tau"],
                     "selectivity": winner["selectivity"],
                     "baseline": baselines[winner["r_tag"]],
                     "config_name": winner["config"]}, f)
    (OUT / "interpretation.json").write_text(json.dumps(interps[wk], indent=2))
print(f"done in {time.time()-t0:.0f}s")
