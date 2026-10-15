"""Phase-5 time / session / market-state diagnostics.

DIAGNOSTIC AND HYPOTHESIS GENERATION ONLY.  Nothing here may modify Phase 5;
the candidate was already selected and tested.  Everything is computed on the
UNCONDITIONAL decision population (no model), so it describes the market rather
than the model, and on DEVELOPMENT YEARS ONLY (2021-2023) unless labelled
CONTAMINATED.

The number of cells examined is reported so the reader can discount accordingly.
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import numpy as np
import polars as pl

from nqr.p5 import dataset5

OUT = ROOT / "strategies" / "larger_r" / "diagnostics"
OUT.mkdir(parents=True, exist_ok=True)
FRICTION = 1.0
TAG = "r4p0"                     # the selected scale; others in the CSV
BUCKET_LABELS = ["09:30-09:45", "09:45-10:00", "10:00-10:15", "10:15-10:30",
                 "10:30-10:45", "10:45-11:00", "11:00-11:15", "11:15-11:30"]


def netR(df, tag, side):
    p = df[f"{tag}_{side}_points"].to_numpy().astype(float)
    r = df[f"{tag}_R"].to_numpy().astype(float)
    return (p - FRICTION) / r


def cells(df, tag, col, labels=None):
    rows = []
    keys = sorted(df[col].unique().to_list())
    for k in keys:
        s = df.filter(pl.col(col) == k)
        if s.height < 200:
            continue
        L, S = netR(s, tag, "long"), netR(s, tag, "short")
        rows.append({
            "cell": (labels[int(k)] if labels and int(k) < len(labels) else str(k)),
            "n": s.height,
            "long_ER": float(np.nanmean(L)), "long_WR": float(np.nanmean(L > 0)),
            "short_ER": float(np.nanmean(S)), "short_WR": float(np.nanmean(S > 0)),
            "best_dir": "LONG" if np.nanmean(L) >= np.nanmean(S) else "SHORT",
            "best_ER": float(max(np.nanmean(L), np.nanmean(S))),
            "symmetry": float(np.nanmean(L) + np.nanmean(S)) / 2.0,
        })
    return pl.DataFrame(rows)


df = dataset5.load_split("dev")
df = df.with_columns(pl.col("trading_date").dt.year().alias("yr"))
u = dataset5.usable_mask(df, TAG)
df = df.filter(pl.Series(u))
print(f"development decision rows (2021-2023): {df.height:,}")

# ---- state bins, all from the frozen causal features ---------------------
def q4(col):
    return (pl.col(col).rank("ordinal") / pl.len() * 4).ceil().cast(pl.Int32)


df = df.with_columns(
    q4("atr1m").alias("vol_quartile"),
    q4("trades_per_s_60").alias("intensity_quartile"),
    q4("eff_60").alias("efficiency_quartile"),
    q4("delta_per_vol_60").alias("delta_quartile"),
    q4("vel_60_norm").alias("velocity_quartile"),
    (pl.col("dist_pdh_norm").abs() < 1.0).cast(pl.Int8).alias("near_pdh"),
    (pl.col("dist_pdl_norm").abs() < 1.0).cast(pl.Int8).alias("near_pdl"),
    (pl.col("dist_open_norm") > 0).cast(pl.Int8).alias("above_open"),
    q4("dist_open_norm").alias("dist_open_quartile"),
    pl.col("weekday").cast(pl.Int32).alias("weekday_f"),
)

GROUPS = [("bucket15", BUCKET_LABELS), ("vol_quartile", None), ("near_pdh", None),
          ("near_pdl", None), ("above_open", None), ("dist_open_quartile", None),
          ("velocity_quartile", None), ("efficiency_quartile", None),
          ("intensity_quartile", None), ("delta_quartile", None), ("weekday_f", None),
          ("yr", None)]

all_tabs, n_cells = {}, 0
for col, labels in GROUPS:
    t = cells(df, TAG, col, labels)
    if t.height == 0:
        continue
    t.write_csv(OUT / f"state_{col}.csv")
    all_tabs[col] = t.to_dicts()
    n_cells += t.height
    print(f"\n--- {col} ({t.height} cells) --- net R at 1.0pt, {TAG} = 4.0x ATR1m")
    print(f"{'cell':14s} {'n':>7s} {'longE[R]':>9s} {'longWR':>7s} {'shortE[R]':>10s} "
          f"{'shortWR':>8s} {'best':>6s} {'bestE[R]':>9s}")
    for r in t.iter_rows(named=True):
        print(f"{r['cell']:14s} {r['n']:7,d} {r['long_ER']:+9.4f} {r['long_WR']:7.4f} "
              f"{r['short_ER']:+10.4f} {r['short_WR']:8.4f} {r['best_dir']:>6s} "
              f"{r['best_ER']:+9.4f}")

# ---- the same, on the strategy's own executed trades (small n, for contrast) ----
summary = {"tag": TAG, "friction": FRICTION, "n_rows": df.height,
           "n_cells_examined": n_cells,
           "note": "DIAGNOSTIC ONLY - POST-HOC - REQUIRES NEW UNTOUCHED DATA",
           "tables": all_tabs}
(OUT / "state_diagnostics.json").write_text(json.dumps(summary, indent=2, default=str))
print(f"\n\nTOTAL CELLS EXAMINED: {n_cells}")
print("Every cell above is a POST-HOC observation on already-used data.")
print("None of it may modify Phase 5.  See FUTURE_HYPOTHESES.md.")
