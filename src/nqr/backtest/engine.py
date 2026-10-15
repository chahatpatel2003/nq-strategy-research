"""Trade resolution from RAW trade prints.

Nothing here ever infers an outcome from 2-minute OHLC.  Entry, target and
stop are all resolved against the chronological tick stream.

Fill model (frozen):

  ENTRY   market order sent when the trigger bar closes.  Filled at the first
          print with ts_event >= trigger_bar_end + latency_ms.  This is a
          pessimistic-but-honest model: we pay whatever trades next, we do not
          get the trigger bar's close.

  STOP    stop-market.  Triggered by the first print at or beyond the stop
          price; filled at that print.  (Additional adverse slippage is
          covered by the round-trip friction sweep.)

  TARGET  resting limit.  A touch is NOT a fill: the tape must trade THROUGH
          the limit by at least one tick before we consider ourselves filled,
          which is the conservative treatment of queue position.

  TIMEOUT if neither is reached, exit at the last print before 17:00 ET.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

TICK = 0.25


@dataclass
class Fill:
    ts_ns: int
    price: float
    kind: str          # TP | SL | TIMEOUT | NO_DATA


def find_entry(ts: np.ndarray, px_ticks: np.ndarray, after_ns: int,
               max_wait_ns: int) -> tuple[int, int, float] | None:
    """First print at/after ``after_ns``.  Returns (idx, ts_ns, price)."""
    i = int(np.searchsorted(ts, after_ns, side="left"))
    if i >= len(ts):
        return None
    if ts[i] - after_ns > max_wait_ns:
        return None
    return i, int(ts[i]), float(px_ticks[i]) * TICK


def resolve(ts: np.ndarray, px_ticks: np.ndarray, start_idx: int, end_ns: int,
            direction: int, tp: float, sl: float) -> Fill:
    """Walk the tape from ``start_idx`` and report which of TP / SL happens first.

    Both levels are compared on the exact integer tick grid, so there is no
    floating-point ambiguity about "touched".
    """
    stop_t = int(np.round(sl / TICK))
    # limit fill requires trading THROUGH the target by one tick
    tp_t = int(np.round(tp / TICK)) + (1 if direction > 0 else -1)

    j = int(np.searchsorted(ts, end_ns, side="right"))
    seg = px_ticks[start_idx:j]
    if seg.size == 0:
        return Fill(end_ns, float(px_ticks[start_idx]) * TICK, "NO_DATA")

    if direction > 0:
        hit_tp = seg >= tp_t
        hit_sl = seg <= stop_t
    else:
        hit_tp = seg <= tp_t
        hit_sl = seg >= stop_t

    i_tp = int(np.argmax(hit_tp)) if hit_tp.any() else -1
    i_sl = int(np.argmax(hit_sl)) if hit_sl.any() else -1

    if i_tp < 0 and i_sl < 0:
        k = start_idx + seg.size - 1
        return Fill(int(ts[k]), float(px_ticks[k]) * TICK, "TIMEOUT")
    if i_sl < 0 or (0 <= i_tp <= i_sl):
        # a single print cannot be on both sides of the entry, so ties cannot
        # occur; ordering is decided purely by tape sequence.
        k = start_idx + i_tp
        return Fill(int(ts[k]), tp, "TP")
    k = start_idx + i_sl
    return Fill(int(ts[k]), float(px_ticks[k]) * TICK, "SL")


def excursions(ts: np.ndarray, px_ticks: np.ndarray, start_idx: int, exit_ts_ns: int,
               direction: int, entry: float) -> tuple[float, float]:
    """(MFE, MAE) in points over the realised holding period, from raw prints."""
    j = int(np.searchsorted(ts, exit_ts_ns, side="right"))
    seg = px_ticks[start_idx:j]
    if seg.size == 0:
        return 0.0, 0.0
    hi = float(seg.max()) * TICK
    lo = float(seg.min()) * TICK
    if direction > 0:
        return hi - entry, entry - lo
    return entry - lo, hi - entry
