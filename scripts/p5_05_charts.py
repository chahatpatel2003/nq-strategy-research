"""Phase-5 visual diagnostics: six seeded, non-cherry-picked galleries of 20.

Drawn from the pooled development trade log (2021-2023) so the samples are big
enough to be representative.
"""
import pickle, sys
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

SD = ROOT / "strategies" / "larger_r"
OUT = SD / "diagnostics" / "charts"
SPLITS = ["train2021", "select2022", "itest2023"]
N, SEED = 20, 20260820
NS = F4.NS
PRE_S, POST_S = 900, 300
SHOW = [("atr1m", "{:.1f}"), ("r_points", "{:.1f}"), ("dist_open_norm", "{:+.1f}"),
        ("dist_pdh_norm", "{:+.1f}"), ("ret_norm_300", "{:+.2f}"),
        ("delta_per_vol_60", "{:+.2f}"), ("eff_300", "{:.2f}")]

frames, cframes = [], []
for s in SPLITS:
    d = SD / "results" / f"run_{s}"
    if (d / "trades.parquet").exists():
        frames.append(pl.read_parquet(d / "trades.parquet").with_columns(pl.lit(s).alias("split")))
    if (d / "controls_matched.parquet").exists():
        cframes.append(pl.read_parquet(d / "controls_matched.parquet"))
trades = pl.concat(frames, how="diagonal")
ctrl = pl.concat(cframes, how="diagonal")
with open(SD / "models" / "production_model.pkl", "rb") as f:
    tau = pickle.load(f)["tau"]

hi_edge = float(np.quantile(trades["edge"].to_numpy(), 0.75))
gal = {
    "winners": trades.filter(pl.col("net_1p0") > 0),
    "losers": trades.filter(pl.col("net_1p0") < 0),
    "timeouts": trades.filter(pl.col("outcome") == "TIMEOUT"),
    "matched_controls": ctrl,
    "highest_confidence": trades.sort("edge", descending=True).head(60),
    "false_high_confidence": trades.filter((pl.col("edge") >= hi_edge)
                                           & (pl.col("net_1p0") < 0)),
}

rng = np.random.default_rng(SEED)
months: dict = {}


def ticks_for(day):
    ym = f"{day.year:04d}-{day.month:02d}"
    if ym not in months:
        months[ym] = cache4.load_month(ym)
    return months[ym].filter(pl.col("trading_date") == day)


def panel(ax, row):
    day = row["trading_date"]
    t = ticks_for(day)
    if t.height == 0:
        return False
    ts = t["ts_ns"].to_numpy(); px = t["px_ticks"].to_numpy() * F4.TICK
    dts = int(row["decision_ts_ns"]); ex = int(row["exit_ns"])
    lo = np.searchsorted(ts, dts - PRE_S * NS)
    hi = np.searchsorted(ts, ex + POST_S * NS)
    if hi - lo < 5:
        return False
    x = (ts[lo:hi] - dts) / 60.0 / NS
    ax.plot(x, px[lo:hi], lw=0.7, color="#333")
    ax.axvline(0, color="#1f77b4", lw=1.0, ls="--")
    e = float(row["entry_price"])
    ax.axhline(e, color="#1f77b4", lw=0.9)
    ax.axhline(float(row["stop"]), color="#d62728", lw=0.8, ls=":")
    ax.axhline(float(row["target"]), color="#2ca02c", lw=0.8, ls=":")
    ax.plot((ex - dts) / 60.0 / NS, float(row["exit_price"]), "o", ms=4,
            color="#2ca02c" if row["net_1p0"] > 0 else "#d62728")
    head = (f"{day} {row['side']} | edge={row['edge']:+.3f} | {row['outcome']} "
            f"net={row['net_1p0']:+.1f}pt ({row['netR_1p0']:+.2f}R) | "
            f"hold={row['hold_s']/60:.0f}m")
    fv = [f"{k}={f.format(row[k])}" for k, f in SHOW if k in row and row[k] is not None]
    ax.set_title("\n".join([head, "  ".join(fv[:4]), "  ".join(fv[4:])]),
                 fontsize=5.0, loc="left")
    ax.tick_params(labelsize=5)
    ax.set_xlabel("minutes from decision", fontsize=5)
    return True


OUT.mkdir(parents=True, exist_ok=True)
for name, frame in gal.items():
    if frame.height == 0:
        print(f"  {name}: empty"); continue
    take = rng.choice(frame.height, size=min(N, frame.height), replace=False)
    sample = frame[sorted(take.tolist())].sort("trading_date")
    fig, axes = plt.subplots(5, 4, figsize=(20, 17))
    k = 0
    for row in sample.iter_rows(named=True):
        if k >= N:
            break
        if panel(axes.flat[k], row):
            k += 1
    for j in range(k, N):
        axes.flat[j].axis("off")
    fig.suptitle(f"Phase 5 - {name.replace('_',' ')} - random sample of {k} from the pooled "
                 f"2021-2023 development log (seed {SEED}, not cherry-picked)", fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(OUT / f"{name}.png", dpi=110)
    plt.close(fig)
    print(f"  {name}: {k} panels from {frame.height} candidates")
print(f"wrote {OUT}")
