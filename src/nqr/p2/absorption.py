"""Absorption PROXY.

MBP-1 gives only the top of book, so individual-order queue position and hidden
liquidity are NOT observable.  Nothing here claims to measure them, and nothing
here claims to observe anyone's intent.  What is measured is a purely
observable quantity:

    how much aggressive volume was spent, per tick of best-price advance,
    during the final push into the extreme.

    absorption_raw = aggressive_volume_in_direction
                     / max(best_price_advance_in_ticks, 1)

For a bullish (short-candidate) leg the numerator is buyer-initiated volume and
the denominator is the advance of the best ASK across the leg; for a bearish
leg it is seller-initiated volume over the decline of the best BID.  Using the
BBO rather than traded prices is deliberate: the hypothesis is about aggression
failing to move the *quote*.

The raw number scales with volume regime, so it is compared against a strictly
trailing empirical distribution: the previous ``history`` observations of
absorption_raw taken from same-direction DC legs that finished BEFORE the
current one.  No global, full-sample or full-day percentile is ever used.
"""
from __future__ import annotations

from collections import deque

import numpy as np


class TrailingPercentile:
    """Rolling window of the last ``maxlen`` completed observations.

    ``rank(x)`` returns the fraction of stored observations strictly below x.
    ``ready()`` is False until ``min_obs`` observations exist, and while it is
    False no candidate may qualify - the strategy simply does not trade until
    it has seen enough history.
    """

    def __init__(self, maxlen: int, min_obs: int):
        self.buf: deque[float] = deque(maxlen=maxlen)
        self.min_obs = min_obs

    def ready(self) -> bool:
        return len(self.buf) >= self.min_obs

    def rank(self, x: float) -> float:
        if not self.buf:
            return float("nan")
        a = np.fromiter(self.buf, dtype=float)
        return float((a < x).mean())

    def push(self, x: float) -> None:
        if np.isfinite(x):
            self.buf.append(float(x))

    def __len__(self) -> int:
        return len(self.buf)


def absorption_raw(agg_volume: float, best_price_advance_ticks: float) -> float:
    """Aggressive contracts spent per tick of best-price advance."""
    return float(agg_volume) / max(float(best_price_advance_ticks), 1.0)
