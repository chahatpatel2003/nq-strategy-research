"""Phase-4 visual diagnostics.

Six randomly drawn (seeded, never cherry-picked) galleries of 20 from the 2023
internal out-of-sample split:

    winners / losers / high-confidence no-trades / matched controls /
    false positives (confident and stopped out) / strong opposite-direction cases

Each panel shows the raw trade path from 5 minutes before the decision to the
exit, the decision point, the fill, the stop, the target, the realised outcome
and the state that produced the signal.
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

SD = ROOT / "strategies" / "state_discovery"
OUT = SD / "diagnostics"
SPLIT = "itest2023"
N = 20
SEED = 20260819
NS = F4.NS
PRE_S, POST_S = 300, 120
# the five features the frozen tree actually uses, plus two for context
SHOW = [("atr1m", "{:.1f}"), ("dist_pdh_norm", "{:+.1f}"),
        ("secs_since_low_300", "{:.0f}"), ("secs_since_high_300", "{:.0f}"),
        ("dist_open_norm", "{:+.1f}"), ("ret_norm_60", "{:+.2f}"),
        ("delta_per_vol_60", "{:+.2f}")]

d = SD / "results" / f"run_{SPLIT}"
trades = pl.read_parquet(d / "trades.parquet")
cands = pl.read_parquet(d / "candidates.parquet")
ctrl = pl.read_parquet(d / "controls_matched.parquet")
opp = pl.read_parquet(d / "controls_opposite.parquet")
with open(SD / "models" / "production_model.pkl", "rb") as f:
    tau = pickle.load(f)["tau"]

net = trades["net_1p0"].to_numpy()
edge_hi = np.quantile(trades["edge"].to_numpy(), 0.75)
opp_net = opp["net_1p0"].to_numpy()

gal = {
    "winners": trades.filter(pl.col("net_1p0") > 0),
    "losers": trades.filter(pl.col("net_1p0") < 0),
    "high_conf_no_trades": cands.filter((pl.col("status") == "SKIPPED")
                                        & (pl.col("edge") >= edge_hi)),
    "false_positives": trades.filter((pl.col("edge") >= edge_hi)
                                     & (pl.col("outcome") == "SL")),
    "matched_controls": ctrl,
    "strong_opposite": opp.with_columns(pl.Series("sn", opp_net))
                          .filter(pl.col("sn") > 0)
                          .join(trades.select(["decision_ts_ns", "net_1p0"])
                                .rename({"net_1p0": "strat_net"}),
                                on="decision_ts_ns", how="inner")
                          .filter(pl.col("strat_net") < 0),
}

rng = np.random.default_rng(SEED)
months = {}


def ticks_for(day):
    ym = f"{day.year:04d}-{day.month:02d}"
    if ym not in months:
        months[ym] = cache4.load_month(ym)
    m = months[ym]
    return m.filter(pl.col("trading_date") == day)


def panel(ax, row, kind):
    day = row["trading_date"]
    t = ticks_for(day)
    if t.height == 0:
        return False
    ts = t["ts_ns"].to_numpy(); px = t["px_ticks"].to_numpy() * F4.TICK
    dts = int(row["decision_ts_ns"])
    ex = int(row["exit_ns"]) if row.get("exit_ns") else dts + 60 * NS
    lo = np.searchsorted(ts, dts - PRE_S * NS)
    hi = np.searchsorted(ts, ex + POST_S * NS)
    if hi - lo < 5:
        return False
    x = (ts[lo:hi] - dts) / NS
    ax.plot(x, px[lo:hi], lw=0.7, color="#333")
    ax.axvline(0, color="#1f77b4", lw=1.0, ls="--")
    if row.get("entry_price"):
        e = float(row["entry_price"])
        ax.axhline(e, color="#1f77b4", lw=0.9)
        if row.get("stop") is not None:
            ax.axhline(float(row["stop"]), color="#d62728", lw=0.8, ls=":")
            ax.axhline(float(row["target"]), color="#2ca02c", lw=0.8, ls=":")
        if row.get("exit_ns"):
            ax.plot((ex - dts) / NS, float(row["exit_price"]), "o", ms=4,
                    color="#2ca02c" if row.get("net_1p0", 0) > 0 else "#d62728")
    bits = [f"{day} {row['side']}", f"score={row['score']:+.4f}"]
    if row.get("outcome"):
        bits.append(f"{row['outcome']} net={row.get('net_1p0', float('nan')):+.2f}pt "
                    f"({row.get('netR_1p0', float('nan')):+.2f}R)")
    else:
        bits.append(f"SKIP:{row.get('skip_reason')}")
    fv = [f"{k}={f.format(row[k])}" for k, f in SHOW if k in row and row[k] is not None]
    ax.set_title("\n".join([" | ".join(bits), "  ".join(fv[:4]), "  ".join(fv[4:])]),
                 fontsize=5.0, loc="left")
    ax.tick_params(labelsize=5)
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
        if k >= 20:
            break
        if panel(axes.flat[k], row, name):
            k += 1
    for j in range(k, 20):
        axes.flat[j].axis("off")
    fig.suptitle(f"Phase 4 - {name.replace('_',' ')} - random sample of {k} "
                 f"from {SPLIT} (seed {SEED}, not cherry-picked)", fontsize=10)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(OUT / f"{name}.png", dpi=110)
    plt.close(fig)
    print(f"  {name}: {k} panels from {frame.height} candidates")
print(f"wrote {OUT}")
