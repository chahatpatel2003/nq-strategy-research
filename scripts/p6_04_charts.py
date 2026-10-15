"""Phase-6 visual diagnostics: seeded, non-cherry-picked galleries of 20."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import polars as pl

from nqr.p4 import cache4
from nqr.p4 import features4 as F4
from nqr.p6 import backtest6 as BT
from nqr.p6 import context6 as C6

RES = ROOT / "strategies" / "context_entry" / "results"
OUT = ROOT / "strategies" / "context_entry" / "diagnostics" / "charts"
OUT.mkdir(parents=True, exist_ok=True)
P = ["train2021", "select2022", "itest2023", "contam2024", "contam2025h2"]
NS = F4.NS
N, SEED = 20, 20260821
COLS = {"E1": "#ff7f0e", "E2": "#8c564b", "E3": "#2ca02c", "E4": "#d62728",
        "E5": "#9467bd", "E6": "#e377c2"}


def load(b):
    fr = [pl.read_parquet(RES / f"run_{s}" / f"book_{b}.parquet")
          for s in P if (RES / f"run_{s}" / f"book_{b}.parquet").exists()]
    return BT.accepted(pl.concat(fr, how="diagonal")) if fr else pl.DataFrame()


ctxs = pl.concat([pl.read_parquet(RES / f"run_{s}" / "contexts.parquet") for s in P],
                 how="diagonal")
books = {b: load(b) for b in list(C6.ENTRY_METHODS) + ["CONTROL_IMMEDIATE", "CONTROL_RANDOM"]}
months: dict = {}


def ticks_for(day):
    ym = f"{day.year:04d}-{day.month:02d}"
    if ym not in months:
        months[ym] = cache4.load_month(ym)
    return months[ym].filter(pl.col("trading_date") == day)


def ctx_panel(ax, c):
    day = c["trading_date"]
    t = ticks_for(day)
    if t.height == 0:
        return False
    ts = t["ts_ns"].to_numpy(); px = t["px_ticks"].to_numpy() * F4.TICK
    a = int(c["activation_ts"])
    b1 = a + int(c["bucket_remaining_s"]) * NS
    lo = np.searchsorted(ts, a - 600 * NS); hi = np.searchsorted(ts, b1 + 1800 * NS)
    if hi - lo < 5:
        return False
    x = (ts[lo:hi] - a) / 60.0 / NS
    ax.plot(x, px[lo:hi], lw=0.7, color="#333")
    ax.axvline(0, color="#1f77b4", lw=1.2, ls="--")
    ax.axvline((b1 - a) / 60.0 / NS, color="#999", lw=0.8, ls="-.")
    d = c["direction"]; R = c["r_points"]; P0 = c["act_price"]
    ax.axhline(P0, color="#1f77b4", lw=0.9)
    ax.axhline(P0 - d * 0.25 * R, color="#2ca02c", lw=0.6, ls=":")
    ax.axhline(P0 - d * 0.50 * R, color="#d62728", lw=0.6, ls=":")
    hits = []
    for m in C6.ENTRY_METHODS:
        bk = books[m]
        r = bk.filter((pl.col("trading_date") == day) & (pl.col("bucket") == c["bucket"]))
        if r.height:
            e = r.row(0, named=True)
            ax.plot((e["entry_ns"] - a) / 60.0 / NS, e["entry_price"], "v", ms=5,
                    color=COLS[m])
            hits.append(f"{m}{e['netR_1p0']:+.2f}")
    ax.set_title(f"{day} {c['side']} b{c['bucket']} R={R:.0f}pt | " + " ".join(hits),
                 fontsize=5.2, loc="left")
    ax.tick_params(labelsize=5)
    ax.set_xlabel("minutes from context activation", fontsize=5)
    return True


def trade_panel(ax, row):
    day = row["trading_date"]
    t = ticks_for(day)
    if t.height == 0:
        return False
    ts = t["ts_ns"].to_numpy(); px = t["px_ticks"].to_numpy() * F4.TICK
    a = int(row["activation_ts"]); ex = int(row["exit_ns"])
    lo = np.searchsorted(ts, a - 600 * NS); hi = np.searchsorted(ts, ex + 600 * NS)
    if hi - lo < 5:
        return False
    x = (ts[lo:hi] - a) / 60.0 / NS
    ax.plot(x, px[lo:hi], lw=0.7, color="#333")
    ax.axvline(0, color="#1f77b4", lw=1.2, ls="--")
    ax.axhline(row["act_price"], color="#1f77b4", lw=0.8, ls="-")
    ax.axhline(row["entry_price"], color="#000", lw=0.9)
    ax.axhline(row["stop"], color="#d62728", lw=0.8, ls=":")
    ax.axhline(row["target"], color="#2ca02c", lw=0.8, ls=":")
    ax.plot((int(row["entry_ns"]) - a) / 60.0 / NS, row["entry_price"], "v", ms=5,
            color="#1f77b4")
    ax.plot((ex - a) / 60.0 / NS, row["exit_price"], "o", ms=4,
            color="#2ca02c" if row["net_1p0"] > 0 else "#d62728")
    ax.set_title(f"{day} {row['side']} b{row['bucket']} | {row['outcome']} "
                 f"{row['netR_1p0']:+.2f}R | wait {row['wait_s']/60:.1f}m "
                 f"improv {row['entry_improvement_R']:+.2f}R | hold {row['hold_s']/60:.0f}m",
                 fontsize=5.2, loc="left")
    ax.tick_params(labelsize=5)
    ax.set_xlabel("minutes from context activation", fontsize=5)
    return True


rng = np.random.default_rng(SEED)
e3 = books["E3"]
entered = set(zip(e3["trading_date"].to_list(), e3["bucket"].to_list()))
no_entry = ctxs.filter(~pl.struct(["trading_date", "bucket"]).map_elements(
    lambda r: (r["trading_date"], r["bucket"]) in entered, return_dtype=pl.Boolean))

GAL = [("contexts_all_mechanics", ctxs, ctx_panel),
       ("E3_winners", e3.filter(pl.col("net_1p0") > 0), trade_panel),
       ("E3_losers", e3.filter(pl.col("net_1p0") < 0), trade_panel),
       ("E3_timeouts", e3.filter(pl.col("outcome") == "TIMEOUT"), trade_panel),
       ("contexts_no_pullback", no_entry, ctx_panel),
       ("control_random", books["CONTROL_RANDOM"], trade_panel)]

for name, frame, fn in GAL:
    if frame.height == 0:
        print(f"  {name}: empty"); continue
    take = rng.choice(frame.height, size=min(N, frame.height), replace=False)
    sample = frame[sorted(take.tolist())].sort("trading_date")
    fig, axes = plt.subplots(5, 4, figsize=(20, 17))
    k = 0
    for row in sample.iter_rows(named=True):
        if k >= N:
            break
        if fn(axes.flat[k], row):
            k += 1
    for j in range(k, N):
        axes.flat[j].axis("off")
    fig.suptitle(f"Phase 6 — {name.replace('_',' ')} — random sample of {k} from the pooled "
                 f"2021–2025-H2 development log (seed {SEED}, not cherry-picked)", fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(OUT / f"{name}.png", dpi=110)
    plt.close(fig)
    print(f"  {name}: {k} panels from {frame.height} candidates")
print(f"wrote {OUT}")
