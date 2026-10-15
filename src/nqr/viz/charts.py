"""Diagnostic charts: 2-minute candles with the level, A, B, C, trigger, entry, SL, TP."""
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


def _candles(ax, bars: pl.DataFrame):
    x = mdates.date2num([dt.datetime.fromtimestamp(t / NS, tz=ET) for t in bars["bar_ns"]])
    w = (2 / (24 * 60)) * 0.7
    o = bars["open"].to_numpy(); h = bars["high"].to_numpy()
    l = bars["low"].to_numpy(); c = bars["close"].to_numpy()
    up = c >= o
    ax.vlines(x, l, h, color="#555555", linewidth=0.6, zorder=2)
    for m, col in ((up, "#1a9850"), (~up, "#d73027")):
        if m.any():
            ax.bar(x[m], np.maximum(np.abs(c - o)[m], 1e-9), bottom=np.minimum(o, c)[m],
                   width=w, color=col, edgecolor=col, linewidth=0.4, zorder=3)
    ax.xaxis_date(tz=ET)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=ET))


def _mark(ax, ns, price, label, color, dy=0):
    x = mdates.date2num(dt.datetime.fromtimestamp(ns / NS, tz=ET))
    ax.plot([x], [price], marker="o", ms=7, color=color, zorder=6,
            markeredgecolor="white", markeredgewidth=0.8)
    ax.annotate(label, (x, price), textcoords="offset points", xytext=(6, 8 + dy),
                fontsize=9, fontweight="bold", color=color, zorder=7)


def plot_trade(row: dict, bars: pl.DataFrame, out: Path, title_extra: str = "") -> None:
    pad = 25 * 2 * 60 * NS
    lo_ns = min(row["a_ns"], row["signal_ns"]) - pad
    hi_ns = max(row["signal_ns"], row.get("r1_exit_ns") or row["signal_ns"]) + pad
    w = bars.filter((pl.col("bar_ns") >= lo_ns - 2 * 60 * NS) & (pl.col("bar_ns") <= hi_ns))
    if w.height < 3:
        return
    fig, ax = plt.subplots(figsize=(13, 6.5))
    _candles(ax, w)
    ax.axhline(row["level"], color="#2166ac", lw=1.6, ls="-", zorder=4,
               label=f"{row['family']} {row['level']:.2f}")
    ax.axhspan(row["level"] - row["tolerance"], row["level"] + row["tolerance"],
               color="#2166ac", alpha=0.10, zorder=1)
    _mark(ax, row["a_ns"], row["level"], "A", "#2166ac")
    _mark(ax, row["b_ns"], row["b_price"], "B", "#762a83")
    _mark(ax, row["c_ns"], row["c_price"], "C", "#1b7837")
    xs = mdates.date2num([dt.datetime.fromtimestamp(n / NS, tz=ET)
                          for n in (row["a_ns"], row["b_ns"], row["c_ns"])])
    ax.plot(xs, [row["level"], row["b_price"], row["c_price"]], color="#999999",
            lw=1.2, ls="--", zorder=5)
    sig_x = mdates.date2num(dt.datetime.fromtimestamp(row["signal_ns"] / NS, tz=ET))
    ax.axvline(sig_x, color="#f46d43", lw=1.2, ls=":", zorder=4)
    ax.annotate(f"{row['trigger_type']}\ntrigger close", (sig_x, row["trig_c"]),
                textcoords="offset points", xytext=(6, -28), fontsize=8, color="#f46d43")
    if row.get("entry_price") is not None and row.get("r1_exit_ns") is not None:
        ax.axhline(row["entry_price"], color="#000000", lw=1.1, zorder=4)
        ax.axhline(row["stop"], color="#d73027", lw=1.1, ls="--", zorder=4)
        if row.get("r1_target") is not None:
            ax.axhline(row["r1_target"], color="#1a9850", lw=1.1, ls="--", zorder=4)
        ex = mdates.date2num(dt.datetime.fromtimestamp(row["r1_exit_ns"] / NS, tz=ET))
        ax.plot([ex], [row["r1_exit_price"]], marker="X", ms=11, color="#000000", zorder=7)
        ax.annotate(f"exit {row['r1_outcome']}", (ex, row["r1_exit_price"]),
                    textcoords="offset points", xytext=(6, 6), fontsize=9)
    side = "LONG" if row["direction"] > 0 else "SHORT"
    st = row.get("status")
    hdr = (f"{row['trading_date']}  {row['symbol']}  {side}  {row['family']}  "
           f"{row['trigger_type']}  |  ratio {row['time_ratio']:.2f}x  "
           f"AB {row['ab_dist']:.1f}pt/{row['ab_ns']/6e10:.0f}m  "
           f"BC {row['bc_dist']:.1f}pt/{row['bc_ns']/6e10:.0f}m  |  {st}")
    if row.get("r1_points") is not None:
        hdr += f"  |  1R result {row['r1_points']:+.2f} pt ({row['r1_R']:+.2f} R)"
    if row.get("skip_reason"):
        hdr += f"  |  skip: {row['skip_reason']}"
    ax.set_title(hdr + title_extra, fontsize=9.5)
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(alpha=0.18, lw=0.5)
    ax.set_ylabel("NQ points")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    plt.close(fig)
