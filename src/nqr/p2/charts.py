"""Phase-2 diagnostic charts: price + order flow + the full state machine trace."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import polars as pl

from nqr.sessions.calendar import ET

NS = 1_000_000_000


def _x(sec):
    return mdates.date2num([dt.datetime.fromtimestamp(int(s), tz=ET) for s in np.atleast_1d(sec)])


def plot_candidate(row: dict, g, out: Path, title_extra: str = "") -> None:
    """One page: price/BBO, aggressive volume, delta, efficiency, absorption."""
    lo = min(row["imp_start_ns"], row["signal_ns"]) // NS - 120
    hi = max(row["signal_ns"] // NS,
             (row.get("r1p0_exit_ns") or row["signal_ns"]) // NS) + 120
    m = (g.sec >= lo) & (g.sec <= hi)
    if m.sum() < 20:
        return
    sec = g.sec[m]
    x = _x(sec)
    fig, ax = plt.subplots(4, 1, figsize=(14, 11), sharex=True,
                           gridspec_kw={"height_ratios": [3, 1.1, 1.1, 1.1]})

    a0 = ax[0]
    a0.plot(x, g.close[m], lw=0.9, color="#222222", label="trade price (1s)")
    a0.fill_between(x, g.low[m], g.high[m], color="#888888", alpha=0.25, lw=0)
    if g.bbo_ok[m].any():
        a0.plot(x, np.where(g.bbo_ok[m], g.bbo_ask[m], np.nan), lw=0.6,
                color="#d73027", alpha=0.8, label="best ask")
        a0.plot(x, np.where(g.bbo_ok[m], g.bbo_bid[m], np.nan), lw=0.6,
                color="#1a9850", alpha=0.8, label="best bid")

    d = row["direction"]
    a0.axvspan(_x(row["imp_start_ns"] // NS)[0], _x(row["imp_end_ns"] // NS)[0],
               color="#4575b4", alpha=0.13, lw=0)
    a0.annotate("impulse", (_x(row["imp_end_ns"] // NS)[0], g.high[m].max()),
                fontsize=9, color="#4575b4", fontweight="bold")
    for k in (1, 2, 3):
        if f"leg{k}_ext_ns" not in row or row.get(f"leg{k}_ext_ns") is None:
            continue
        px = row[f"leg{k}_ext_price"]
        a0.plot(_x(row[f"leg{k}_ext_ns"] // NS), [px], marker="v" if d < 0 else "^",
                ms=9, color="#762a83", zorder=6)
        a0.annotate(f"H{k}" if d < 0 else f"L{k}",
                    (_x(row[f"leg{k}_ext_ns"] // NS)[0], px), fontsize=9,
                    fontweight="bold", color="#762a83",
                    textcoords="offset points", xytext=(4, 6 if d < 0 else -12))
        a0.axvline(_x(row[f"leg{k}_conf_ns"] // NS)[0], color="#762a83",
                   ls=":", lw=0.6, alpha=0.6)
    a0.axhline(row["ext_price"], color="#762a83", lw=1.2, ls="--",
               label=f"exhaustion extreme {row['ext_price']:.2f}")
    a0.axvline(_x(row["arm_ns"] // NS)[0], color="#f46d43", ls="--", lw=1.0)
    a0.annotate("ARMED", (_x(row["arm_ns"] // NS)[0], g.low[m].min()), fontsize=8,
                color="#f46d43", rotation=90, va="bottom")
    a0.axvline(_x(row["signal_ns"] // NS)[0], color="#000000", ls=":", lw=1.2)
    a0.annotate("failed continuation", (_x(row["signal_ns"] // NS)[0], g.low[m].min()),
                fontsize=8, rotation=90, va="bottom")
    if row.get("entry_price") is not None:
        a0.axhline(row["entry_price"], color="#000000", lw=1.1)
        a0.axhline(row["stop"], color="#d73027", lw=1.0, ls="--")
        if row.get("r1p0_target") is not None:
            a0.axhline(row["r1p0_target"], color="#1a9850", lw=1.0, ls="--")
        if row.get("r1p0_exit_ns"):
            a0.plot(_x(row["r1p0_exit_ns"] // NS), [row["r1p0_exit_price"]],
                    marker="X", ms=11, color="#000000", zorder=7)
            a0.annotate(f" exit {row['r1p0_outcome']}",
                        (_x(row["r1p0_exit_ns"] // NS)[0], row["r1p0_exit_price"]), fontsize=9)
    a0.legend(loc="upper left", fontsize=7.5, ncol=2)
    a0.set_ylabel("NQ points")
    a0.grid(alpha=0.15, lw=0.4)

    bv = np.diff(np.concatenate(([g.buy_cum[m][0]], g.buy_cum[m])))
    sv = np.diff(np.concatenate(([g.sell_cum[m][0]], g.sell_cum[m])))
    ax[1].bar(x, bv, width=1 / 86400, color="#1a9850", alpha=0.85, label="buy-initiated")
    ax[1].bar(x, -sv, width=1 / 86400, color="#d73027", alpha=0.85, label="sell-initiated")
    ax[1].set_ylabel("agg vol/s"); ax[1].legend(fontsize=7.5, loc="upper left")
    ax[1].grid(alpha=0.15, lw=0.4)

    ax[2].plot(x, np.cumsum(bv - sv), lw=1.0, color="#4575b4")
    ax[2].axhline(0, color="#999999", lw=0.6)
    ax[2].set_ylabel("cum delta"); ax[2].grid(alpha=0.15, lw=0.4)

    legs_k = [k for k in (1, 2, 3) if row.get(f"leg{k}_agg_vol") is not None]
    if legs_k:
        lx = [_x(row[f"leg{k}_ext_ns"] // NS)[0] for k in legs_k]
        ax[3].plot(lx, [row[f"leg{k}_efficiency"] for k in legs_k], "o-",
                   color="#762a83", label="efficiency (pts / agg contract)")
        ax3b = ax[3].twinx()
        ax3b.plot(lx, [row[f"leg{k}_absorption"] for k in legs_k], "s--",
                  color="#f46d43", label="absorption proxy")
        ax3b.set_ylabel("absorption", color="#f46d43")
        ax[3].set_ylabel("efficiency", color="#762a83")
        ax[3].legend(fontsize=7.5, loc="upper left")
    ax[3].grid(alpha=0.15, lw=0.4)
    ax[3].xaxis_date(tz=ET)
    ax[3].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S", tz=ET))

    side = "SHORT" if d < 0 else "LONG"
    hdr = (f"{row['trading_date']}  {row['symbol']}  {side}  |  impulse "
           f"{row['imp_displacement']:.1f}pt / {row['imp_seconds']}s "
           f"({row.get('imp_disp_vu') or float('nan'):.2f}xVU)  |  VU {row['vu']:.2f}  |  "
           f"absorption pct {row.get('absorption_pct') if row.get('absorption_pct') is not None else float('nan'):.3f}"
           f"  |  {row.get('status')}")
    if row.get("r1p0_points") is not None:
        hdr += f"  |  1R {row['r1p0_points']:+.2f} pt ({row['r1p0_R']:+.2f} R)"
    if row.get("skip_reason"):
        hdr += f"  |  skip: {row['skip_reason']}"
    fig.suptitle(hdr + title_extra, fontsize=9.5, y=0.995)
    fig.autofmt_xdate()
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    fig.savefig(out, dpi=105)
    plt.close(fig)
