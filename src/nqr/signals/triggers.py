"""Reversal-trigger candle definitions (2-minute bars).

Every definition is purely arithmetic - there is no discretionary "looks like"
component anywhere.  All three families are evaluated on every bar; the
strategy variants then select which families are eligible.

Notation for a bar: o,h,l,c ; rng = h-l ; body = |c-o| ;
upper wick = h-max(o,c) ; lower wick = min(o,c)-l.

ATR2M is the causal 20-bar average true range of the 2-minute series
(computed from bars strictly BEFORE the bar being classified).

Each detector returns, per bar index i:
    dir  : +1 bullish, -1 bearish, 0 none
    n    : number of bars in the completed pattern (i-n+1 .. i)
"""
from __future__ import annotations

import numpy as np

BULL, BEAR, NONE = 1, -1, 0


def atr2m(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int = 20) -> np.ndarray:
    """Causal ATR: value at i uses true ranges of bars i-n .. i-1 only."""
    pc = np.empty_like(close)
    pc[0] = close[0]
    pc[1:] = close[:-1]
    tr = np.maximum(high - low, np.maximum(np.abs(high - pc), np.abs(low - pc)))
    tr[0] = high[0] - low[0]
    out = np.full(len(tr), np.nan)
    if len(tr) <= n:
        return out
    csum = np.concatenate(([0.0], np.cumsum(tr)))
    # mean of tr[i-n : i]
    idx = np.arange(n, len(tr))
    out[idx] = (csum[idx] - csum[idx - n]) / n
    return out


def engulfing(o, h, l, c, atr, *, min_prev_body_atr_frac: float,
              min_cur_body_atr_frac: float) -> np.ndarray:
    """2-bar engulfing.  Current real body fully covers the previous real body."""
    n = len(o)
    out = np.zeros(n, dtype=np.int8)
    if n < 2:
        return out
    po, pc_ = o[:-1], c[:-1]
    co, cc = o[1:], c[1:]
    a = atr[1:]
    pbody = np.abs(pc_ - po)
    cbody = np.abs(cc - co)
    ok_size = (pbody >= min_prev_body_atr_frac * a) & (cbody >= min_cur_body_atr_frac * a) \
              & (cbody > pbody) & np.isfinite(a)
    bull = (pc_ < po) & (cc > co) & (co <= pc_) & (cc >= po) & ok_size
    bear = (pc_ > po) & (cc < co) & (co >= pc_) & (cc <= po) & ok_size
    out[1:][bull] = BULL
    out[1:][bear] = BEAR
    return out


def pin(o, h, l, c, atr, *, min_range_atr_frac: float, max_body_frac_of_range: float,
        min_dom_wick_frac_of_range: float, min_dom_wick_over_body: float,
        max_opp_wick_frac_of_range: float, min_close_location: float) -> np.ndarray:
    """1-bar pin bar / hammer / shooting star."""
    rng = h - l
    body = np.abs(c - o)
    up = h - np.maximum(o, c)
    dn = np.minimum(o, c) - l
    with np.errstate(divide="ignore", invalid="ignore"):
        clo = np.where(rng > 0, (c - l) / rng, 0.5)
    base = (rng >= min_range_atr_frac * atr) & (rng > 0) & np.isfinite(atr) \
           & (body <= max_body_frac_of_range * rng)
    bull = base & (dn >= min_dom_wick_frac_of_range * rng) & (dn >= min_dom_wick_over_body * body) \
           & (up <= max_opp_wick_frac_of_range * rng) & (clo >= min_close_location)
    bear = base & (up >= min_dom_wick_frac_of_range * rng) & (up >= min_dom_wick_over_body * body) \
           & (dn <= max_opp_wick_frac_of_range * rng) & ((1.0 - clo) >= min_close_location)
    out = np.zeros(len(o), dtype=np.int8)
    out[bull] = BULL
    out[bear] = BEAR
    return out


def star(o, h, l, c, atr, *, min_range1_atr_frac: float, min_body1_frac_of_range1: float,
         max_body2_over_body1: float, min_body3_frac_of_range3: float) -> np.ndarray:
    """3-bar morning / evening star (rejection cluster).

    bar1: decisive candle against the coming reversal
    bar2: small-bodied candle extending bar1's direction (the 'star')
    bar3: decisive candle closing back beyond the midpoint of bar1's real body
    """
    n = len(o)
    out = np.zeros(n, dtype=np.int8)
    if n < 3:
        return out
    o1, h1, l1, c1 = o[:-2], h[:-2], l[:-2], c[:-2]
    o2, h2, l2, c2 = o[1:-1], h[1:-1], l[1:-1], c[1:-1]
    o3, h3, l3, c3 = o[2:], h[2:], l[2:], c[2:]
    a = atr[2:]
    r1, b1 = h1 - l1, np.abs(c1 - o1)
    b2 = np.abs(c2 - o2)
    r3, b3 = h3 - l3, np.abs(c3 - o3)
    mid1 = (o1 + c1) / 2.0
    base = np.isfinite(a) & (r1 >= min_range1_atr_frac * a) & (r1 > 0) & (r3 > 0) \
           & (b1 >= min_body1_frac_of_range1 * r1) & (b2 <= max_body2_over_body1 * b1) \
           & (b3 >= min_body3_frac_of_range3 * r3)
    bull = base & (c1 < o1) & (l2 <= l1) & (np.maximum(o2, c2) < c1) \
           & (c3 > o3) & (c3 > mid1)
    bear = base & (c1 > o1) & (h2 >= h1) & (np.minimum(o2, c2) > c1) \
           & (c3 < o3) & (c3 < mid1)
    out[2:][bull] = BULL
    out[2:][bear] = BEAR
    return out


PATTERN_BARS = {"ENGULFING": 2, "PIN": 1, "STAR": 3}


def all_triggers(o, h, l, c, atr, cfg) -> dict[str, np.ndarray]:
    return {
        "ENGULFING": engulfing(o, h, l, c, atr, **cfg["engulfing"]),
        "PIN": pin(o, h, l, c, atr, **cfg["pin"]),
        "STAR": star(o, h, l, c, atr, **cfg["star"]),
    }
