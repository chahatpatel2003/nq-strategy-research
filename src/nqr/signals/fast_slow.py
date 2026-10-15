"""Fast-Slow A-B-C pattern detection.

Deterministic, no hand labelling, no visual judgement.

Within one level segment (a constant level price L valid over [t0,t1)):

  touch(i)  <=>  low_i - tol <= L <= high_i + tol

  A  = the LAST bar of a contiguous touch cluster, i.e. the final bar in
       contact with the level before price departs.
  B  = the extreme of the excursion that follows A, measured over the bars
       strictly between A and the next touch.
  C  = the FIRST bar after B that touches the level again.

Because C is defined as the first return, every departure/return cycle yields
at most ONE (A,B,C) candidate: the deduplication is structural, not a filter.

Direction: an excursion ABOVE the level returns down onto support -> LONG.
An excursion BELOW the level returns up into resistance -> SHORT.
Trade direction therefore equals the sign of the A->B leg, exactly as the
published pattern describes ("trade the reversal of the slow return").
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np

NS_PER_MIN = 60_000_000_000


@dataclass
class ABC:
    a_idx: int
    b_idx: int
    c_idx: int
    direction: int          # +1 long, -1 short
    level: float
    tolerance: float
    a_price: float
    b_price: float
    c_price: float
    ab_dist: float
    bc_dist: float
    ab_ns: int
    bc_ns: int
    time_ratio: float
    dist_ratio: float
    reject: str | None = None


def detect_abc(high: np.ndarray, low: np.ndarray, bar_end_ns: np.ndarray,
               level: float, tol: float, *,
               min_ab_dist: float, min_ab_bars: int, max_ab_bars: int,
               max_bc_bars: int, time_ratio_min: float,
               dist_ratio_min: float, dist_ratio_max: float,
               step_ns: int = 120_000_000_000,
               keep_rejects: bool = False) -> list[ABC]:
    """Scan one level segment.  ``high/low/bar_end_ns`` are that segment's bars."""
    n = len(high)
    out: list[ABC] = []
    if n < 4:
        return out
    touch = (low - tol <= level) & (level <= high + tol)
    above = low > level + tol
    below = high < level - tol

    i = 0
    while i < n:
        if not touch[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and touch[j + 1]:
            j += 1
        a_idx = j
        k = a_idx + 1
        if k >= n:
            break
        c = k
        while c < n and not touch[c]:
            c += 1
        if c >= n:
            break                                  # never returned inside this segment
        c_idx = c
        sl = slice(a_idx + 1, c_idx)
        m = c_idx - a_idx - 1
        if m <= 0:
            i = c_idx
            continue

        if above[sl].all():
            direction = 1
            b_off = int(np.argmax(high[sl]))
            b_price = float(high[sl][b_off])
            c_price = float(low[c_idx])
        elif below[sl].all():
            direction = -1
            b_off = int(np.argmin(low[sl]))
            b_price = float(low[sl][b_off])
            c_price = float(high[c_idx])
        else:
            i = c_idx                               # excursion straddled the level
            continue
        b_idx = a_idx + 1 + b_off

        ab_dist = abs(b_price - level)
        bc_dist = abs(c_price - b_price)
        ab_ns = int(bar_end_ns[b_idx] - bar_end_ns[a_idx])
        bc_ns = int(bar_end_ns[c_idx] - bar_end_ns[b_idx])
        # measured in *wall-clock* bar widths so that missing (untraded)
        # intervals cannot make a slow leg look fast
        ab_bars = ab_ns / step_ns
        bc_bars = bc_ns / step_ns
        tr = (bc_ns / ab_ns) if ab_ns > 0 else 0.0
        dr = (bc_dist / ab_dist) if ab_dist > 0 else 0.0

        why = None
        if ab_bars < min_ab_bars:
            why = "AB_TOO_FEW_BARS"
        elif ab_bars > max_ab_bars:
            why = "AB_TOO_MANY_BARS"
        elif bc_bars > max_bc_bars:
            why = "BC_TOO_MANY_BARS"
        elif ab_dist < min_ab_dist:
            why = "AB_MOVE_TOO_SMALL"
        elif tr < time_ratio_min:
            why = "TIME_RATIO_TOO_LOW"
        elif not (dist_ratio_min <= dr <= dist_ratio_max):
            why = "DIST_RATIO_OUT_OF_RANGE"

        if why is None or keep_rejects:
            out.append(ABC(a_idx, b_idx, c_idx, direction, float(level), float(tol),
                           float(level), b_price, c_price, float(ab_dist), float(bc_dist),
                           ab_ns, bc_ns, float(tr), float(dr), why))
        i = c_idx
    return out


def time_ratio_bucket(tr: float) -> str:
    if tr < 2.0:
        return "<2.0"
    if tr < 2.5:
        return "2.0-2.5"
    if tr < 3.0:
        return "2.5-3.0"
    return ">=3.0"
