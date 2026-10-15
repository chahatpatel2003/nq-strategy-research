"""Phase-6 development analysis: is the causal context real, and does any of the
six entry mechanics beat random timing inside it?

Applies the preregistered gates in PHASE6_SEARCH_BUDGET.md S6 in order.
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import numpy as np
import polars as pl

from nqr.p4 import metrics4
from nqr.p5.dataset5 import FRICTIONS
from nqr.p6 import backtest6 as BT
from nqr.p6 import context6 as C6

RES = ROOT / "strategies" / "context_entry" / "results"
OUT = ROOT / "strategies" / "context_entry" / "models"
OUT.mkdir(parents=True, exist_ok=True)
PERIODS = ["train2021", "select2022", "itest2023", "contam2024", "contam2025h2"]
LAB = {"train2021": "2021", "select2022": "2022", "itest2023": "2023",
       "contam2024": "2024", "contam2025h2": "2025-H2"}
FR = 1.0
MIN_TRADES = 300
BOOKS = list(C6.ENTRY_METHODS) + [f"CONTROL_{c}" for c in C6.CONTROLS]


def load(split, book):
    p = RES / f"run_{split}" / f"book_{book}.parquet"
    return BT.accepted(pl.read_parquet(p)) if p.exists() else pl.DataFrame()


def m(t, fr=FR):
    if t.height == 0:
        return {}
    s = metrics4.summarize(t, fr)
    s["profit_factor_R"] = BT.pf_r(t, fr)
    return s


data = {b: {p: load(p, b) for p in PERIODS} for b in BOOKS}
pooled = {b: pl.concat([v for v in data[b].values() if v.height], how="diagonal")
          for b in BOOKS}
ctx = {p: pl.read_parquet(RES / f"run_{p}" / "contexts.parquet") for p in PERIODS}
n_ctx = {p: ctx[p].height for p in PERIODS}

# ============================================================ 1. is context real?
print("=" * 96)
print("STEP 1 — IS THE CAUSAL CONTEXT ITSELF REAL?")
print("  random minute INSIDE an activated context   vs   random minute in a")
print("  no-context bucket on the same day, same direction distribution, same R")
print("=" * 96)
print(f"{'period':10s} {'contexts':>9s} | {'IN-CONTEXT':>11s} {'n':>6s} {'WR':>7s} | "
      f"{'NON-CONTEXT':>12s} {'n':>6s} {'WR':>7s} | {'diff':>8s} {'95% day-block CI':>22s}")
ctx_real = {}
for p in PERIODS:
    a, b = data["CONTROL_RANDOM"][p], data["CONTROL_NONCONTEXT"][p]
    ma, mb = m(a), m(b)
    d = metrics4.block_bootstrap_diff(a, b, FR, "expectancy_R") if a.height and b.height else {}
    ctx_real[p] = {"in": ma, "non": mb, "diff": d}
    print(f"{LAB[p]:10s} {n_ctx[p]:9d} | {ma['expectancy_R']:+11.4f} {ma['n_trades']:6d} "
          f"{ma['win_rate']:7.4f} | {mb['expectancy_R']:+12.4f} {mb['n_trades']:6d} "
          f"{mb['win_rate']:7.4f} | {d['diff']:+8.4f} "
          f"[{d['ci95_lo']:+.4f},{d['ci95_hi']:+.4f}]")
pa, pb = pooled["CONTROL_RANDOM"], pooled["CONTROL_NONCONTEXT"]
mpa, mpb = m(pa), m(pb)
dp = metrics4.block_bootstrap_diff(pa, pb, FR, "expectancy_R")
dpw = metrics4.block_bootstrap_diff(pa, pb, FR, "win_rate")
print("-" * 96)
print(f"{'POOLED':10s} {sum(n_ctx.values()):9d} | {mpa['expectancy_R']:+11.4f} {mpa['n_trades']:6d} "
      f"{mpa['win_rate']:7.4f} | {mpb['expectancy_R']:+12.4f} {mpb['n_trades']:6d} "
      f"{mpb['win_rate']:7.4f} | {dp['diff']:+8.4f} [{dp['ci95_lo']:+.4f},{dp['ci95_hi']:+.4f}]")
print(f"\n  in-context gross (0.0pt) E[R] = {m(pa,0.0)['expectancy_R']:+.4f}   "
      f"PF(R) = {mpa['profit_factor_R']:.3f}")
print(f"  WR difference {dpw['diff']:+.4f}  CI [{dpw['ci95_lo']:+.4f},{dpw['ci95_hi']:+.4f}]")
ctx_positive = mpa["expectancy_R"] > 0
ctx_beats_non = dp["ci95_lo"] > 0
print(f"\n  context E[R] > 0 ................ {ctx_positive}")
print(f"  context beats non-context (CI>0)  {ctx_beats_non}")

# ================================================ 2. entry mechanics vs random
print("\n" + "=" * 96)
print("STEP 2 — DOES ANY ENTRY MECHANIC BEAT RANDOM TIMING INSIDE THE SAME CONTEXT?")
print("=" * 96)
rows = []
for b in list(C6.ENTRY_METHODS) + ["CONTROL_IMMEDIATE"]:
    per = {}
    for p in PERIODS:
        per[p] = m(data[b][p])
    tot = m(pooled[b])
    gross = m(pooled[b], 0.0)
    adv = [per[p].get("expectancy_R", np.nan) -
           m(data["CONTROL_RANDOM"][p]).get("expectancy_R", np.nan) for p in PERIODS]
    d = metrics4.block_bootstrap_diff(pooled[b], pooled["CONTROL_RANDOM"], FR, "expectancy_R")
    dw = metrics4.block_bootstrap_diff(pooled[b], pooled["CONTROL_RANDOM"], FR, "win_rate")
    n_pos = sum(1 for p in PERIODS if per[p].get("expectancy_R", -9) > 0)
    rows.append({
        "book": b, "n_trades": tot.get("n_trades", 0),
        "win_rate": tot.get("win_rate", np.nan),
        "gross_ER": gross.get("expectancy_R", np.nan),
        "net_ER": tot.get("expectancy_R", np.nan),
        "pf_r": tot.get("profit_factor_R", np.nan),
        "periods_positive": n_pos,
        "median_advantage": float(np.nanmedian(adv)),
        "adv_diff": d["diff"], "adv_lo": d["ci95_lo"], "adv_hi": d["ci95_hi"],
        "wr_diff": dw["diff"], "wr_lo": dw["ci95_lo"], "wr_hi": dw["ci95_hi"],
        "max_dd_R": tot.get("max_drawdown_R", np.nan),
        "median_hold_min": tot.get("median_hold_min", np.nan),
        "mean_entry_improv_R": float(BT.accepted(pooled[b])["entry_improvement_R"].mean()),
        "median_wait_min": float(np.median(pooled[b]["wait_s"].to_numpy())) / 60.0,
        **{f"ER_{LAB[p]}": per[p].get("expectancy_R", np.nan) for p in PERIODS},
        **{f"n_{LAB[p]}": per[p].get("n_trades", 0) for p in PERIODS},
    })
tab = pl.DataFrame(rows)
print(f"{'book':18s} {'n':>5s} {'WR':>7s} {'gross':>8s} {'net E[R]':>9s} {'PF(R)':>7s} "
      f"{'per+':>5s} {'medAdv':>8s} {'adv':>8s} {'95% CI':>20s} {'wait':>6s} {'improv':>8s}")
for r in tab.iter_rows(named=True):
    print(f"{r['book']:18s} {r['n_trades']:5d} {r['win_rate']:7.4f} {r['gross_ER']:+8.4f} "
          f"{r['net_ER']:+9.4f} {r['pf_r']:7.3f} {r['periods_positive']:4d}/5 "
          f"{r['median_advantage']:+8.4f} {r['adv_diff']:+8.4f} "
          f"[{r['adv_lo']:+.4f},{r['adv_hi']:+.4f}] {r['median_wait_min']:5.1f}m "
          f"{r['mean_entry_improv_R']:+8.4f}")
print(f"\n{'CONTROL_RANDOM':18s} {mpa['n_trades']:5d} {mpa['win_rate']:7.4f} "
      f"{m(pa,0.0)['expectancy_R']:+8.4f} {mpa['expectancy_R']:+9.4f} "
      f"{mpa['profit_factor_R']:7.3f}   ---   (the primary null)")

print("\nper-period net E[R] at 1.0pt:")
print(f"{'book':18s}" + "".join(f"{LAB[p]:>11s}" for p in PERIODS))
for r in tab.iter_rows(named=True):
    print(f"{r['book']:18s}" + "".join(f"{r['ER_'+LAB[p]]:+11.4f}" for p in PERIODS))
print(f"{'CONTROL_RANDOM':18s}" + "".join(
    f"{m(data['CONTROL_RANDOM'][p])['expectancy_R']:+11.4f}" for p in PERIODS))

# ==================================================================== 3. gates
print("\n" + "=" * 96)
print("STEP 3 — PREREGISTERED DEVELOPMENT GATES (PHASE6_SEARCH_BUDGET S6)")
print("=" * 96)
print(f"{'method':8s} {'G1 n>=300':>12s} {'G2 4/5 +ve':>12s} {'G2 comb>0':>11s} "
      f"{'G3 PF(R)>1.10':>15s} {'G4 CI_lo>0':>14s} {'ELIGIBLE':>10s}")
gates = {}
for r in tab.filter(pl.col("book").is_in(list(C6.ENTRY_METHODS))).iter_rows(named=True):
    g1 = r["n_trades"] >= MIN_TRADES
    g2a = r["periods_positive"] >= 4
    g2b = r["net_ER"] > 0
    g3 = r["pf_r"] > 1.10
    g4 = r["adv_lo"] > 0
    ok = all([g1, g2a, g2b, g3, g4])
    gates[r["book"]] = {"G1": g1, "G2_periods": g2a, "G2_combined": g2b, "G3": g3,
                        "G4": g4, "eligible": ok, "n": r["n_trades"],
                        "periods_positive": r["periods_positive"],
                        "net_ER": r["net_ER"], "pf_r": r["pf_r"],
                        "adv_lo": r["adv_lo"], "median_advantage": r["median_advantage"]}
    print(f"{r['book']:8s} {str(g1)+' ('+str(r['n_trades'])+')':>12s} "
          f"{str(g2a)+' ('+str(r['periods_positive'])+'/5)':>12s} "
          f"{str(g2b):>11s} {str(g3)+' ('+f'{r['pf_r']:.2f}'+')':>15s} "
          f"{str(g4)+' ('+f'{r['adv_lo']:+.3f}'+')':>14s} {str(ok):>10s}")

elig = [k for k, v in gates.items() if v["eligible"]]
print(f"\nTOTAL ENTRY CONFIGURATIONS EVALUATED: {len(C6.ENTRY_METHODS)} (budget 6)")
print(f"ELIGIBLE: {elig if elig else 'NONE'}")
verdict = {"context_positive": bool(ctx_positive), "context_beats_noncontext": bool(ctx_beats_non),
           "context_pooled": {k: mpa.get(k) for k in ("n_trades", "win_rate", "expectancy_R",
                                                      "profit_factor_R")},
           "noncontext_pooled": {k: mpb.get(k) for k in ("n_trades", "win_rate", "expectancy_R")},
           "context_vs_noncontext": dp, "context_vs_noncontext_wr": dpw,
           "gates": gates, "eligible": elig,
           "total_configurations_evaluated": len(C6.ENTRY_METHODS)}
if not elig:
    verdict["decision"] = ("PHASE 6 FAILS BEFORE VALIDATION - no entry mechanic passed the "
                           "preregistered development gates; 2026-Q1 stays sealed.")
    print("\n*** NO ENTRY MECHANIC PASSED THE DEVELOPMENT GATES ***")
    print("    PHASE 6 FAILS BEFORE VALIDATION. 2026-Q1 STAYS SEALED.")
else:
    best = max(elig, key=lambda k: (gates[k]["median_advantage"], gates[k]["n"]))
    verdict["selected"] = best
    verdict["decision"] = f"candidate {best} proceeds to freeze"
    print(f"\nSELECTED (highest median per-period advantage vs CONTROL_RANDOM): {best}")
tab.write_csv(OUT / "entry_comparison.csv")
tab.write_parquet(OUT / "entry_comparison.parquet")
(OUT / "development_verdict.json").write_text(json.dumps(verdict, indent=2, default=str))
(OUT / "context_reality.json").write_text(json.dumps(ctx_real, indent=2, default=str))
