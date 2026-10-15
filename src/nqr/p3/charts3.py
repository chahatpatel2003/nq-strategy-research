"""Phase-3 diagnostic charts.

The chart is deliberately built so a lookahead mistake would be VISIBLE: the
confirmed extreme is drawn as a hollow marker at the time it printed, the solid
"signal" marker sits at the confirmation, and a shaded band spans the interval
during which the extreme existed but was NOT yet knowable.  An entry drawn
inside that band would be an obvious error.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

from nqr.sessions.calendar import ET

NS = 1_000_000_000
TICK = 0.25


def _x(ns):
    return mdates.date2num([dt.datetime.fromtimestamp(int(v) / NS, tz=ET)
                            for v in np.atleast_1d(ns)])


def plot_events(p, events, out: Path, lo_ns: int, hi_ns: int, title: str = "") -> None:
    """Raw DC sequence: tick path, running extremes, theta bands, confirmations."""
    m = (p.ts >= lo_ns) & (p.ts <= hi_ns)
    if m.sum() < 50:
        return
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.plot(_x(p.ts[m]), p.px_t[m] * TICK, lw=0.7, color="#222222", label="trade prints")
    evs = [e for e in events if lo_ns <= e.conf_ts <= hi_ns]
    for e in evs:
        c = "#d73027" if e.direction < 0 else "#1a9850"
        # the extreme, at the time it PRINTED - hollow: not yet knowable
        ax.plot(_x(e.ext_ts), [e.ext_price], marker="o", ms=8, mfc="none",
                mec=c, mew=1.6, zorder=6)
        # the confirmation - solid: this is the only tradeable moment
        ax.plot(_x(e.conf_ts), [e.conf_price], marker="v" if e.direction < 0 else "^",
                ms=9, color=c, zorder=7)
        ax.plot(_x([e.ext_ts, e.conf_ts]), [e.ext_price, e.conf_price],
                color=c, lw=0.8, ls="--", alpha=0.8, zorder=5)
        # the "not yet knowable" window
        ax.axvspan(_x(e.ext_ts)[0], _x(e.conf_ts)[0], color=c, alpha=0.07, lw=0)
        ax.hlines(e.trigger_price, _x(e.ext_ts)[0], _x(e.conf_ts)[0],
                  color=c, lw=0.8, ls=":", alpha=0.9)
    ax.plot([], [], "o", mfc="none", mec="#555555", label="extreme (printed, NOT yet knowable)")
    ax.plot([], [], "v", color="#555555", label="DC confirmation (signal exists here)")
    ax.plot([], [], ls=":", color="#555555", label="theta trigger level")
    ax.legend(loc="upper left", fontsize=8)
    ax.set_ylabel("NQ points")
    ax.grid(alpha=0.15, lw=0.4)
    ax.xaxis_date(tz=ET)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S", tz=ET))
    th = np.median([e.theta for e in evs]) if evs else float("nan")
    ax.set_title(f"{p.trading_date}  {p.symbol}  |  {len(evs)} DC events  |  "
                 f"median theta {th:.2f} pt {title}", fontsize=10)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    plt.close(fig)


def plot_trade(row: dict, p, events, out: Path) -> None:
    """One trade in event context: extreme, confirmation, entry, stop, target."""
    span = max(int(row["r1p0_exit_ns"] or row["signal_ns"]) - int(row["ext_ts"]), 60 * NS)
    lo = int(row["ext_ts"]) - max(span // 2, 60 * NS)
    hi = int(row.get("r1p0_exit_ns") or row["signal_ns"]) + max(span // 2, 60 * NS)
    m = (p.ts >= lo) & (p.ts <= hi)
    if m.sum() < 30:
        return
    d = int(row["direction"])
    c = "#d73027" if d < 0 else "#1a9850"
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.plot(_x(p.ts[m]), p.px_t[m] * TICK, lw=0.8, color="#222222")

    ax.plot(_x(row["ext_ts"]), [row["ext_price"]], marker="o", ms=10, mfc="none",
            mec=c, mew=2, zorder=7)
    ax.annotate("extreme\n(not yet knowable)", (_x(row["ext_ts"])[0], row["ext_price"]),
                textcoords="offset points", xytext=(-10, 14 if d < 0 else -32),
                fontsize=8, color=c, ha="center")
    ax.axvspan(_x(row["ext_ts"])[0], _x(row["conf_ts"])[0], color=c, alpha=0.10, lw=0)
    ref_lab = ("DC-B extension level" if row["family"] == "DC_B" else "theta trigger level")
    ax.axhline(row["ref_price"], color=c, lw=0.9, ls=":",
               label=f"{ref_lab} {row['ref_price']:.2f}")
    ax.axvline(_x(row["conf_ts"])[0], color=c, lw=1.3, ls="--")
    ax.annotate("DC confirmed", (_x(row["conf_ts"])[0], p.px_t[m].min() * TICK),
                rotation=90, va="bottom", fontsize=8, color=c)
    if row["signal_ns"] != row["conf_ts"]:
        ax.axvline(_x(row["signal_ns"])[0], color="#762a83", lw=1.2, ls="-.")
        ax.annotate("DC-B extension", (_x(row["signal_ns"])[0], p.px_t[m].min() * TICK),
                    rotation=90, va="bottom", fontsize=8, color="#762a83")
    if row.get("entry_price") is not None:
        ax.axhline(row["entry_price"], color="#000000", lw=1.2, label=f"entry {row['entry_price']:.2f}")
        ax.axhline(row["stop"], color="#d73027", lw=1.0, ls="--", label=f"stop {row['stop']:.2f}")
        tp = row["entry_price"] + d * row["r_points"]
        ax.axhline(tp, color="#1a9850", lw=1.0, ls="--", label=f"target {tp:.2f}")
        ax.plot(_x(row["entry_ns"]), [row["entry_price"]], marker="D", ms=8,
                color="#000000", zorder=8)
        if row.get("r1p0_exit_ns"):
            ax.plot(_x(row["r1p0_exit_ns"]), [row["r1p0_exit_price"]], marker="X",
                    ms=12, color="#000000", zorder=9)
            ax.annotate(f" exit {row['r1p0_outcome']}",
                        (_x(row["r1p0_exit_ns"])[0], row["r1p0_exit_price"]), fontsize=9)
    side = "SHORT" if d < 0 else "LONG"
    hdr = (f"{row['trading_date']}  {row['symbol']}  {row['family']}  {side}  |  "
           f"theta {row['theta']:.2f} (VU {row['vu']:.2f})  |  DC mag {row['dc_magnitude']:.2f}  |  "
           f"prev overshoot {row['prev_overshoot']:.2f} ({row['prev_overshoot_ratio']:.2f}x)")
    if row.get("r1p0_points") is not None:
        hdr += f"  |  1R {row['r1p0_points']:+.2f} pt ({row['r1p0_R']:+.2f} R)"
    if row.get("skip_reason"):
        hdr += f"  |  skip: {row['skip_reason']}"
    ax.set_title(hdr, fontsize=9)
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(alpha=0.15, lw=0.4)
    ax.set_ylabel("NQ points")
    ax.xaxis_date(tz=ET)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S", tz=ET))
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    plt.close(fig)
