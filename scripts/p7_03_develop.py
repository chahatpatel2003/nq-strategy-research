"""Phase-7 chronological development.

    2021  TRAIN   fit scaler, 4 models, selectivity quantiles, control quartile edges
    2022  SELECT  evaluate all 12 configurations, apply gates G1-G6, select <= 1
    2023  NOT TOUCHED HERE - see p7_04_run_split.py

Selection among survivors (SEARCH_BUDGET S8): highest TRADING-DAY MEDIAN
advantage vs matched random -- not raw per-trade expectancy.  This is the direct
correction of the Phase-5 defect.
"""
import json, pickle, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import numpy as np
import polars as pl

from nqr.p4 import metrics4                      # frozen upstream, read-only
from nqr.p4.model4 import Preprocessor           # frozen upstream, read-only
from nqr.p7 import backtest7 as BT
from nqr.p7 import dataset7, model7
from nqr.p7 import features7 as F7
from nqr.p7 import holdout7 as H7

OUT = ROOT / "strategies" / "orderbook_state" / "models"
OUT.mkdir(parents=True, exist_ok=True)
FR = 1.0
MIN_2022_TRADES = 200


def day_median_advantage(a: pl.DataFrame, b: pl.DataFrame, friction=FR) -> float:
    """Median across trading days of (strategy daily mean R - control daily mean R)."""
    if a.height == 0 or b.height == 0:
        return float("nan")
    def per_day(t):
        r = (t["points"].to_numpy().astype(float) - friction) / t["r_points"].to_numpy().astype(float)
        d = np.array(t["trading_date"].to_list(), dtype=object)
        u, inv = np.unique(d, return_inverse=True)
        return dict(zip(u, np.bincount(inv, weights=r) / np.bincount(inv)))
    A, B = per_day(a), per_day(b)
    both = [A[k] - B[k] for k in A if k in B]
    return float(np.median(both)) if both else float("nan")


t0 = time.time()
df = dataset7.load_split("dev")
yr = np.array([d.year for d in df["trading_date"].to_list()])
assert set(np.unique(yr)) == {2021, 2022, 2023}
for d in (df["trading_date"].min(), df["trading_date"].max()):
    assert H7.period_of(d) in ("TRAIN", "SELECT", "ITEST"), d
print(f"dev rows={df.height:,} days={df['trading_date'].n_unique()} "
      f"2021={int((yr==2021).sum()):,} 2022={int((yr==2022).sum()):,} "
      f"2023={int((yr==2023).sum()):,}  [{time.time()-t0:.0f}s]", flush=True)

X = dataset7.feature_matrix(df)
feat_ok = np.isfinite(X).all(axis=1) & (df["entry_ns"].to_numpy() > 0)
tr_all = (yr == 2021) & feat_ok
se_mask = yr == 2022

pre = Preprocessor.fit(X[tr_all], fit_on="train2021")
Xs = pre.transform(X)
print(f"scaler fitted on {pre.n_fit:,} 2021 rows only", flush=True)

# control matching quartile edges -- 2021 TRAINING rows only, then frozen
atr_edges = BT._quartile_edges(df["atr1m_ticks"].to_numpy().astype(float)[tr_all])
spr_edges = BT._quartile_edges(df["spread_ticks"].to_numpy().astype(float)[tr_all])
print(f"control quartile edges (2021 only)  ATR {np.round(atr_edges,2)}  "
      f"spread {np.round(spr_edges,2)}")

df_se = df.filter(pl.Series(se_mask))
Xs_se = Xs[se_mask]
n_days_2022 = df_se["trading_date"].n_unique()

models, thresholds, interps, rows, books = {}, {}, {}, [], {}
for r_tag in dataset7.R_POINTS:
    u_all = dataset7.usable_mask(df, r_tag)
    tr = (yr == 2021) & u_all
    y = df[f"{r_tag}_y"].to_numpy().astype(int)
    base = float(y[tr].mean())
    print(f"\n[{r_tag}] train rows={int(tr.sum()):,}  P(UP) base rate={base:.4f} "
          f"(theoretical 50% is NOT the null)", flush=True)
    for fam in model7.FAMILIES:
        t1 = time.time()
        est = model7.fit_model(fam, Xs[tr], y[tr])
        mk = f"{r_tag}:{fam}"
        models[mk] = est
        interps[mk] = model7.interpret(est, fam)
        p_tr = est.predict_proba(Xs[tr])[:, 1]
        thresholds[mk] = model7.thresholds_from_train(p_tr)
        acc_tr = float(((p_tr >= 0.5).astype(int) == y[tr]).mean())
        print(f"  fit {mk:16s} train_acc={acc_tr:.4f} "
              f"tau={[round(v,5) for v in thresholds[mk].values()]}  [{time.time()-t1:.0f}s]",
              flush=True)

        p_se = est.predict_proba(Xs_se)[:, 1]
        conf_se = model7.confidence(p_se)
        dir_se = model7.direction_of(p_se)
        u_se = u_all[se_mask]
        for q in model7.SELECTIVITY:
            cfg = model7.Config(r_tag, fam, q)
            tau = thresholds[mk][q]
            book = BT.run_strategy(df_se, r_tag, conf_se, dir_se, tau, u_se)
            acc = BT.accepted(book)
            m = metrics4.summarize(acc, FR, n_days_available=n_days_2022) if acc.height else {}
            g0 = metrics4.summarize(acc, 0.0, n_days_2022) if acc.height else {}
            ctrl = (BT.matched_controls(book, df_se, r_tag, u_se, atr_edges, spr_edges,
                                        mode="cross_day") if acc.height else pl.DataFrame())
            cm = metrics4.summarize(ctrl, FR, n_days_2022) if ctrl.height else {}
            adv = m.get("expectancy_R", np.nan) - cm.get("expectancy_R", np.nan)
            dma = day_median_advantage(acc, ctrl) if ctrl.height else np.nan
            g1 = m.get("n_trades", 0) >= MIN_2022_TRADES
            g2 = m.get("expectancy_R", -9) > 0
            g3 = BT.pf_r(acc, FR) > 1.10 if acc.height else False
            g4 = adv > 0 if np.isfinite(adv) else False
            g5 = g4
            g6 = g0.get("expectancy_R", -9) > 0
            rows.append({
                "config": cfg.name, "r_tag": r_tag, "family": fam, "selectivity": q,
                "tau": tau, "n_candidates": book.height, "n_trades": m.get("n_trades", 0),
                "trades_per_day": m.get("trades_per_day", np.nan),
                "win_rate": m.get("win_rate", np.nan),
                "gross_ER": g0.get("expectancy_R", np.nan),
                "net_ER": m.get("expectancy_R", np.nan),
                "pf_r": BT.pf_r(acc, FR) if acc.height else np.nan,
                "max_dd_R": m.get("max_drawdown_R", np.nan),
                "control_n": cm.get("n_trades", 0),
                "control_ER": cm.get("expectancy_R", np.nan),
                "advantage_R": adv, "day_median_advantage": dma,
                "G1": g1, "G2": g2, "G3": g3, "G4": g4, "G5": g5, "G6": g6,
                "eligible": all([g1, g2, g3, g4, g5, g6])})
            books[cfg.name] = acc
            print(f"    {cfg.name:22s} n={m.get('n_trades',0):5d} "
                  f"({m.get('trades_per_day',np.nan):5.2f}/d) "
                  f"WR={m.get('win_rate',np.nan):.4f} "
                  f"gross={g0.get('expectancy_R',np.nan):+.4f} "
                  f"net={m.get('expectancy_R',np.nan):+.4f} "
                  f"PF(R)={BT.pf_r(acc,FR) if acc.height else float('nan'):.3f} "
                  f"adv={adv:+.4f} dayMedAdv={dma:+.4f} "
                  f"{'ELIGIBLE' if all([g1,g2,g3,g4,g5,g6]) else ''}", flush=True)

tab = pl.DataFrame(rows)
tab.write_parquet(OUT / "selection_2022.parquet")
tab.write_csv(OUT / "selection_2022.csv")
elig = tab.filter(pl.col("eligible"))
print("\n" + "=" * 90)
print(f"TOTAL CONFIGURATIONS EVALUATED: {tab.height}  (budget {model7.MAX_CONFIGS})")
print(f"eligible after G1-G6: {elig.height}/12")

payload = {"friction": FR, "min_2022_trades": MIN_2022_TRADES,
           "total_configurations_evaluated": tab.height,
           "preprocessor": pre.to_dict(),
           "atr_edges": atr_edges.tolist(), "spread_edges": spr_edges.tolist(),
           "thresholds": {k: {str(q): v for q, v in d.items()} for k, d in thresholds.items()},
           "features": list(F7.FEATURE_NAMES)}
if elig.height == 0:
    best = tab.sort("net_ER", descending=True).row(0, named=True)
    payload["verdict"] = {"eligible": [], "selected": None,
                          "best_config": best["config"], "best_net_ER": best["net_ER"],
                          "decision": "PHASE 7 FAILS BEFORE 2023 - no configuration passed "
                                      "the 2022 gates; 2025-H1 stays sealed."}
    print("\n*** NO CONFIGURATION PASSED THE 2022 GATES ***")
    print(f"    best was {best['config']} at net E[R]={best['net_ER']:+.4f}, "
          f"PF(R)={best['pf_r']:.3f}, adv={best['advantage_R']:+.4f}")
    print("    PHASE 7 FAILS BEFORE 2023. 2025-H1 STAYS SEALED.")
else:
    rank = elig.sort(["day_median_advantage", "n_trades"], descending=[True, True])
    w = rank.row(0, named=True)
    payload["verdict"] = {"eligible": elig["config"].to_list(), "selected": w["config"],
                          "decision": "candidate proceeds to the 2023 internal OOS test"}
    payload["winner"] = w
    mk = f"{w['r_tag']}:{w['family']}"
    with open(OUT / "production_model.pkl", "wb") as f:
        pickle.dump({"pre": pre, "r_tag": w["r_tag"], "family": w["family"],
                     "est": models[mk], "tau": w["tau"], "selectivity": w["selectivity"],
                     "config_name": w["config"], "atr_edges": atr_edges,
                     "spread_edges": spr_edges}, f)
    (OUT / "interpretation.json").write_text(json.dumps(interps[mk], indent=2))
    print(f"\nSELECTED (highest trading-day median advantage): {w['config']}")
    print(f"  2022 n={w['n_trades']} net E[R]={w['net_ER']:+.4f} PF(R)={w['pf_r']:.3f} "
          f"dayMedAdv={w['day_median_advantage']:+.4f}")

(OUT / "development_meta.json").write_text(json.dumps(payload, indent=2, default=str))
(OUT / "interpretation_all.json").write_text(json.dumps(interps, indent=2))
with open(OUT / "all_models.pkl", "wb") as f:
    pickle.dump({"pre": pre, "models": models, "thresholds": thresholds,
                 "atr_edges": atr_edges, "spread_edges": spr_edges}, f)
print(f"done in {time.time()-t0:.0f}s")
