"""Phase-6 entry-quality, time-within-context and half-hour diagnostics.

DIAGNOSTIC ONLY.  The candidate set was already rejected by the preregistered
gates; nothing here may modify Phase 6.
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import numpy as np
import polars as pl

from nqr.p4 import metrics4
from nqr.p6 import backtest6 as BT
from nqr.p6 import context6 as C6

RES = ROOT / "strategies" / "context_entry" / "results"
DIA = ROOT / "strategies" / "context_entry" / "diagnostics"
DIA.mkdir(parents=True, exist_ok=True)
P = ["train2021", "select2022", "itest2023", "contam2024", "contam2025h2"]
LAB = dict(zip(P, ["2021", "2022", "2023", "2024", "2025-H2"]))
FR = 1.0
BUCKET_LABEL = {0: "09:30-10:00", 1: "10:00-10:30", 2: "10:30-11:00", 3: "11:00-11:30"}


def load(s, b):
    p = RES / f"run_{s}" / f"book_{b}.parquet"
    return BT.accepted(pl.read_parquet(p)) if p.exists() else pl.DataFrame()


def pooled(b):
    return pl.concat([load(s, b) for s in P], how="diagonal")


def stat(t):
    if t.height == 0:
        return {}
    s = metrics4.summarize(t, FR)
    s["profit_factor_R"] = BT.pf_r(t, FR)
    s["gross_ER"] = metrics4.summarize(t, 0.0)["expectancy_R"]
    return s


out = {}
rnd = pooled("CONTROL_RANDOM")

# ---- 1. TIME WITHIN CONTEXT (on the random control: unbiased by mechanic) ----
print("=" * 92)
print("TIME WITHIN CONTEXT — outcome by wait between activation and entry")
print("  measured on CONTROL_RANDOM, so it is not confounded by any mechanic")
print("=" * 92)
bins = [(0, 300, "0-5 min"), (300, 600, "5-10"), (600, 900, "10-15"),
        (900, 1200, "15-20"), (1200, 10 ** 9, "20+")]
rows = []
w = rnd["wait_s"].to_numpy()
print(f"{'wait':10s} {'n':>6s} {'WR':>7s} {'gross':>9s} {'net E[R]':>9s} {'PF(R)':>7s} {'MAE pt':>8s}")
for lo, hi, lab in bins:
    sub = rnd.filter((pl.col("wait_s") >= lo) & (pl.col("wait_s") < hi))
    if sub.height < 30:
        continue
    s = stat(sub)
    rows.append({"bin": lab, **{k: s[k] for k in ("n_trades", "win_rate", "gross_ER",
                                                  "expectancy_R", "profit_factor_R",
                                                  "avg_MAE_points")}})
    print(f"{lab:10s} {s['n_trades']:6d} {s['win_rate']:7.4f} {s['gross_ER']:+9.4f} "
          f"{s['expectancy_R']:+9.4f} {s['profit_factor_R']:7.3f} {s['avg_MAE_points']:8.2f}")
out["time_within_context"] = rows
pl.DataFrame(rows).write_csv(DIA / "time_within_context.csv")

# ---- 2. HALF-HOUR BUCKET x DIRECTION -------------------------------------
print("\n" + "=" * 92)
print("HALF-HOUR CONTEXT BUCKET x DIRECTION  (CONTROL_RANDOM inside context)")
print("=" * 92)
rows = []
print(f"{'bucket':13s} {'side':6s} {'n':>6s} {'WR':>7s} {'gross':>9s} {'net E[R]':>9s} {'PF(R)':>7s}")
for b in range(4):
    for side in ("LONG", "SHORT"):
        sub = rnd.filter((pl.col("bucket") == b) & (pl.col("side") == side))
        if sub.height < 30:
            continue
        s = stat(sub)
        rows.append({"bucket": BUCKET_LABEL[b], "side": side,
                     **{k: s[k] for k in ("n_trades", "win_rate", "gross_ER",
                                          "expectancy_R", "profit_factor_R")}})
        print(f"{BUCKET_LABEL[b]:13s} {side:6s} {s['n_trades']:6d} {s['win_rate']:7.4f} "
              f"{s['gross_ER']:+9.4f} {s['expectancy_R']:+9.4f} {s['profit_factor_R']:7.3f}")
out["bucket_direction"] = rows
pl.DataFrame(rows).write_csv(DIA / "bucket_direction.csv")

# ---- 3. ENTRY QUALITY per mechanic ---------------------------------------
print("\n" + "=" * 92)
print("ENTRY QUALITY — what each mechanic actually buys")
print("=" * 92)
rows = []
print(f"{'method':18s} {'n':>5s} {'fill%':>6s} {'wait':>7s} {'improv R':>9s} {'pre-MAE R':>10s} "
      f"{'pre-MFE R':>10s} {'ctx age':>8s} {'left':>7s} {'MFE pt':>8s} {'MAE pt':>8s}")
n_ctx = sum(pl.read_parquet(RES / f"run_{s}" / "contexts.parquet").height for s in P)
for b in list(C6.ENTRY_METHODS) + ["CONTROL_IMMEDIATE"]:
    t = pooled(b)
    if t.height == 0:
        continue
    s = stat(t)
    r = t["r_points"].to_numpy()
    rec = {"method": b, "n": t.height, "fill_rate": t.height / n_ctx,
           "median_wait_min": float(np.median(t["wait_s"].to_numpy())) / 60,
           "mean_improve_R": float(t["entry_improvement_R"].mean()),
           "mean_pre_mae_R": float((t["pre_entry_mae"].to_numpy() / r).mean()),
           "mean_pre_mfe_R": float((t["pre_entry_mfe"].to_numpy() / r).mean()),
           "median_remaining_min": float(np.median(t["remaining_bucket_s"].to_numpy())) / 60,
           "avg_MFE_points": s["avg_MFE_points"], "avg_MAE_points": s["avg_MAE_points"],
           "win_rate": s["win_rate"], "expectancy_R": s["expectancy_R"]}
    rows.append(rec)
    print(f"{b:18s} {rec['n']:5d} {rec['fill_rate']:6.2f} {rec['median_wait_min']:6.1f}m "
          f"{rec['mean_improve_R']:+9.4f} {rec['mean_pre_mae_R']:10.4f} "
          f"{rec['mean_pre_mfe_R']:10.4f} {rec['median_wait_min']:7.1f}m "
          f"{rec['median_remaining_min']:6.1f}m {rec['avg_MFE_points']:8.2f} "
          f"{rec['avg_MAE_points']:8.2f}")
out["entry_quality"] = rows
pl.DataFrame(rows).write_csv(DIA / "entry_quality.csv")

# ---- 4. the adverse-selection decomposition ------------------------------
print("\n" + "=" * 92)
print("WHY THE PULLBACK ENTRIES DO NOT HELP — price improvement vs adverse selection")
print("=" * 92)
print(f"{'method':8s} {'price improvement':>18s} {'adverse excursion':>18s} {'net':>9s} "
      f"{'contexts entered':>17s}")
rows = []
for b in C6.ENTRY_METHODS:
    t = pooled(b)
    r = t["r_points"].to_numpy()
    imp = float(t["entry_improvement_R"].mean())
    mae = float((t["pre_entry_mae"].to_numpy() / r).mean())
    rows.append({"method": b, "improve_R": imp, "pre_mae_R": mae, "net": imp - mae,
                 "n": t.height, "fill_rate": t.height / n_ctx})
    print(f"{b:8s} {imp:+18.4f} {mae:18.4f} {imp-mae:+9.4f} "
          f"{t.height:8d} ({t.height/n_ctx:.0%})")
out["adverse_selection"] = rows
pl.DataFrame(rows).write_csv(DIA / "adverse_selection.csv")
print("\nA mechanic only gets a better price when the market has already moved against")
print("the context by MORE than the improvement it buys.")

out["n_contexts"] = n_ctx
out["note"] = "DIAGNOSTIC ONLY - POST-HOC - REQUIRES NEW UNTOUCHED DATA"
(DIA / "diagnostics.json").write_text(json.dumps(out, indent=2, default=str))
print(f"\nwrote {DIA}")
