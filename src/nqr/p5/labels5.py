"""Phase-5 larger-R first passage.

Identical fill semantics to the frozen Phase-1/3/4 engine:

  stop    - stop-market, triggers on a print at or beyond the stop, fills there
  target  - resting limit, the tape must trade THROUGH by >= 1 tick
  entry   - first print at or after the decision timestamp + latency

ONE deliberate difference, fixed before any Phase-5 P&L (PHASE5_SPEC.md S9):

  timeout - Phase 4 exited at the last print BEFORE the cutoff, which is not
            executable: at that instant the cutoff had not yet arrived.  Phase 5
            exits at the FIRST print AT OR AFTER the timeout timestamp, which is
            what a real timeout order would get.  This is strictly the more
            conservative of the two.

`resolve_p5` therefore returns exactly what `nqr.p3.fastpass.resolve_fast`
returns whenever TP or SL is hit, and differs only on the TIMEOUT branch.
Asserted by tests/test_p5_labels.py.
"""
from __future__ import annotations

import numpy as np

from nqr.backtest.engine import Fill, TICK

_CHUNKS = (256, 2048, 16384, 131072)
TIMEOUT_MAX_WAIT_NS = 60 * 1_000_000_000     # abandon-to-last-print rail


def resolve_p5(ts: np.ndarray, px_ticks: np.ndarray, start_idx: int, end_ns: int,
               direction: int, tp: float, sl: float) -> Fill:
    """First passage of +/-R, else an executable timeout exit at/after ``end_ns``."""
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
                return Fill(int(ts[start_idx + i_tp]), tp, "TP")
            k = start_idx + i_sl
            return Fill(int(ts[k]), float(px_ticks[k]) * TICK, "SL")
        lo = hi
        if hi >= j:
            break

    # TIMEOUT: take the first print at or after the cutoff, not the last one before
    if j < len(ts) and int(ts[j]) - end_ns <= TIMEOUT_MAX_WAIT_NS:
        return Fill(int(ts[j]), float(px_ticks[j]) * TICK, "TIMEOUT")
    k = j - 1
    return Fill(int(ts[k]), float(px_ticks[k]) * TICK, "TIMEOUT")


def excursions_p5(ts: np.ndarray, px_ticks: np.ndarray, start_idx: int,
                  exit_ts_ns: int, direction: int, entry: float) -> tuple[float, float]:
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
