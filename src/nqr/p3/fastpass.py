"""Chunked first-passage resolution.

Phase 3 generates one to two orders of magnitude more trades than Phases 1-2,
and `nqr.backtest.engine.resolve` scans the whole remaining tape for every
trade.  This module returns **exactly the same answer** by scanning in growing
chunks and stopping at the first hit; `tests/test_p3_fastpass.py` asserts
equality against the frozen engine on randomised inputs.

The fill semantics are unchanged and are the Phase-1 rules:
  * stop-market  - triggers on a print at or beyond the stop, fills at that print
  * resting limit- needs the tape to trade THROUGH the level by >= 1 tick,
                   fills at the limit price (a touch is NOT a fill)
  * timeout      - last print before the cutoff
"""
from __future__ import annotations

import numpy as np

from nqr.backtest.engine import Fill, TICK

_CHUNKS = (256, 2048, 16384, 131072)


def resolve_fast(ts: np.ndarray, px_ticks: np.ndarray, start_idx: int, end_ns: int,
                 direction: int, tp: float, sl: float) -> Fill:
    stop_t = int(np.round(sl / TICK))
    tp_t = int(np.round(tp / TICK)) + (1 if direction > 0 else -1)
    j = int(np.searchsorted(ts, end_ns, side="right"))
    if j <= start_idx:
        return Fill(end_ns, float(px_ticks[start_idx]) * TICK, "NO_DATA")

    lo = start_idx
    for width in _CHUNKS + (j - start_idx,):
        hi = min(start_idx + width, j)
        if hi <= lo and hi < j:
            continue
        seg = px_ticks[start_idx:hi]
        if direction > 0:
            hit_tp = seg >= tp_t
            hit_sl = seg <= stop_t
        else:
            hit_tp = seg <= tp_t
            hit_sl = seg >= stop_t
        any_tp, any_sl = hit_tp.any(), hit_sl.any()
        if any_tp or any_sl:
            i_tp = int(np.argmax(hit_tp)) if any_tp else -1
            i_sl = int(np.argmax(hit_sl)) if any_sl else -1
            if i_sl < 0 or (0 <= i_tp <= i_sl):
                k = start_idx + i_tp
                return Fill(int(ts[k]), tp, "TP")
            k = start_idx + i_sl
            return Fill(int(ts[k]), float(px_ticks[k]) * TICK, "SL")
        lo = hi
        if hi >= j:
            break
    k = j - 1
    return Fill(int(ts[k]), float(px_ticks[k]) * TICK, "TIMEOUT")


def excursions_fast(ts: np.ndarray, px_ticks: np.ndarray, start_idx: int,
                    exit_ts_ns: int, direction: int, entry: float) -> tuple[float, float]:
    j = int(np.searchsorted(ts, exit_ts_ns, side="right"))
    seg = px_ticks[start_idx:j]
    if seg.size == 0:
        return 0.0, 0.0
    hi = float(seg.max()) * TICK
    lo = float(seg.min()) * TICK
    if direction > 0:
        return hi - entry, entry - lo
    return entry - lo, hi - entry
