"""Phase-6 causal context activation and the six entry mechanics.

CONTEXT (frozen, PHASE6_SPEC S4)
    Inside each 30-minute bucket of 09:30-11:30 ET, the FIRST decision timestamp
    whose Phase-5 edge score clears the frozen tau activates the context.  Its
    predicted direction is LOCKED for the remainder of that bucket; later model
    flips do not change it.  At most ONE context per bucket.  If no qualifying
    signal occurs, there is no context.

    Nothing about a context depends on anything after its activation timestamp:
    not the bucket's selection, not the direction, not R, not the reference
    price.  This is the whole point of Phase 6 -- see CONTEXT_CAUSALITY_AUDIT.md
    for what went wrong with the Phase-5 decomposition.

ENTRIES (frozen, PHASE6_SEARCH_BUDGET -- exactly six, no others)
    E1  enter 5 minutes after activation
    E2  enter 10 minutes after activation
    E3  enter after a 0.25R adverse excursion from the activation price
    E4  enter after a 0.50R adverse excursion
    E5  E3 plus a 0.125R resumption off the causal running extreme
    E6  E4 plus a 0.125R resumption off the causal running extreme

Every mechanic may only trigger between activation and the end of its own
bucket, and every fill is the first realistically executable print after the
trigger becomes known.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np

from nqr.p4 import features4 as F4

NS = F4.NS
TICK = F4.TICK
LATENCY_NS = 250 * 1_000_000            # identical to Phases 1-5
BUCKET_S = 1800
N_BUCKETS = 4
E1_DELAY_S = 300
E2_DELAY_S = 600
E3_PULLBACK_R = 0.25
E4_PULLBACK_R = 0.50
RESUME_R = 0.125
ENTRY_METHODS = ("E1", "E2", "E3", "E4", "E5", "E6")
CONTROLS = ("IMMEDIATE", "RANDOM", "NONCONTEXT")


@dataclass
class Context:
    trading_date: dt.date
    symbol: str
    bucket: int                 # 0..3
    activation_ts: int          # ns, the decision timestamp that qualified
    direction: int              # +1 / -1, LOCKED for the bucket
    score: float
    r_points: float             # Phase-5 r4p0 R, locked at activation
    bucket_end_ts: int          # ns, exclusive
    act_idx: int                # tape index of the activation reference fill
    act_ts: int                 # ns of that fill
    act_price: float            # the reference price for E3-E6, == IMMEDIATE's fill
    n_qualifying: int           # how many rows in the bucket cleared tau
    sec_since_open: int


def bucket_bounds(d: dt.date, b: int) -> tuple[int, int]:
    t0 = F4.et_sec(d, F4.SESSION_START_ET)
    return t0 + b * BUCKET_S, t0 + (b + 1) * BUCKET_S


def _fill(ts: np.ndarray, px: np.ndarray, trigger_ns: int, bucket_end_ns: int,
          max_wait_ns: int = 60 * NS) -> tuple[int, int, float] | None:
    """First realistically executable print after a trigger becomes known.

    Latency is applied to every mechanic and every control identically, so the
    comparison between them is exact.  The fill must land before bucket end.
    """
    i = int(np.searchsorted(ts, trigger_ns + LATENCY_NS, side="left"))
    if i >= len(ts):
        return None
    if ts[i] - (trigger_ns + LATENCY_NS) > max_wait_ns:
        return None
    if ts[i] >= bucket_end_ns:
        return None
    return i, int(ts[i]), float(px[i]) * TICK


def build_contexts(day: dt.date, symbol: str, dec_ts: np.ndarray, sec_open: np.ndarray,
                   score: np.ndarray, direction: np.ndarray, r_pts: np.ndarray,
                   ok: np.ndarray, tau: float, ts: np.ndarray,
                   px: np.ndarray) -> list[Context]:
    """One causal context per 30-minute bucket, or none."""
    out: list[Context] = []
    for b in range(N_BUCKETS):
        b0, b1 = bucket_bounds(day, b)
        m = (sec_open >= (b0 - F4.et_sec(day, F4.SESSION_START_ET))) & \
            (sec_open < (b1 - F4.et_sec(day, F4.SESSION_START_ET)))
        idx = np.flatnonzero(m & ok & (score >= tau))
        if idx.size == 0:
            continue
        i = int(idx[0])                                   # FIRST qualifying signal
        act_ns = int(dec_ts[i])
        f = _fill(ts, px, act_ns, b1 * NS)
        if f is None:
            continue
        out.append(Context(
            trading_date=day, symbol=symbol, bucket=b, activation_ts=act_ns,
            direction=int(direction[i]), score=float(score[i]),
            r_points=float(r_pts[i]), bucket_end_ts=b1 * NS,
            act_idx=f[0], act_ts=f[1], act_price=f[2],
            n_qualifying=int(idx.size), sec_since_open=int(sec_open[i])))
    return out


# ------------------------------------------------------- entry mechanics ----
def _window(ts: np.ndarray, c: Context) -> tuple[int, int]:
    return c.act_idx, int(np.searchsorted(ts, c.bucket_end_ts, side="left"))


def entry_delay(ts, px, c: Context, delay_s: int):
    trig = c.activation_ts + delay_s * NS
    if trig >= c.bucket_end_ts:
        return None
    f = _fill(ts, px, trig, c.bucket_end_ts)
    return None if f is None else (trig, *f)


def entry_pullback(ts, px, c: Context, frac: float):
    """First print at or beyond `frac` x R adverse to the activation price."""
    i0, i1 = _window(ts, c)
    if i1 <= i0:
        return None
    seg = px[i0:i1] * TICK
    lvl = c.act_price - c.direction * frac * c.r_points
    hit = (seg <= lvl) if c.direction > 0 else (seg >= lvl)
    if not hit.any():
        return None
    j = i0 + int(np.argmax(hit))
    f = _fill(ts, px, int(ts[j]), c.bucket_end_ts)
    return None if f is None else (int(ts[j]), *f)


def entry_pullback_resume(ts, px, c: Context, frac: float, resume: float = RESUME_R):
    """Adverse excursion of `frac` x R, then a `resume` x R recovery measured
    from the CAUSAL running extreme -- the extreme known so far, never the
    eventual one."""
    i0, i1 = _window(ts, c)
    if i1 <= i0:
        return None
    seg = px[i0:i1] * TICK
    lvl = c.act_price - c.direction * frac * c.r_points
    hit = (seg <= lvl) if c.direction > 0 else (seg >= lvl)
    if not hit.any():
        return None
    j = int(np.argmax(hit))                       # relative to i0
    tail = seg[j:]
    need = resume * c.r_points
    if c.direction > 0:
        run = np.minimum.accumulate(tail)         # running low SO FAR
        rec = tail >= run + need
    else:
        run = np.maximum.accumulate(tail)         # running high SO FAR
        rec = tail <= run - need
    if not rec.any():
        return None
    k = i0 + j + int(np.argmax(rec))
    f = _fill(ts, px, int(ts[k]), c.bucket_end_ts)
    return None if f is None else (int(ts[k]), *f)


def entry_of(method: str, ts, px, c: Context):
    if method == "E1":
        return entry_delay(ts, px, c, E1_DELAY_S)
    if method == "E2":
        return entry_delay(ts, px, c, E2_DELAY_S)
    if method == "E3":
        return entry_pullback(ts, px, c, E3_PULLBACK_R)
    if method == "E4":
        return entry_pullback(ts, px, c, E4_PULLBACK_R)
    if method == "E5":
        return entry_pullback_resume(ts, px, c, E3_PULLBACK_R)
    if method == "E6":
        return entry_pullback_resume(ts, px, c, E4_PULLBACK_R)
    raise ValueError(f"unknown entry method {method!r}: the budget fixes exactly six")


# ------------------------------------------------------------- controls ----
def entry_immediate(ts, px, c: Context):
    """CONTROL_IMMEDIATE: the activation reference fill itself."""
    return (c.activation_ts, c.act_idx, c.act_ts, c.act_price)


def random_minutes(c: Context, rng: np.random.Generator, k: int) -> list[int]:
    """Decision-grid minutes available at or after activation, inside the bucket.

    This is the direct causal analogue of Phase 5's 'random minute in the
    bucket' -- except it can never precede the activation that supplied the
    direction, which is exactly what Phase 5 got wrong.
    """
    mins = np.arange(c.activation_ts, c.bucket_end_ts, 60 * NS, dtype=np.int64)
    if mins.size == 0:
        return []
    take = rng.choice(mins.size, size=min(k, mins.size), replace=False)
    return sorted(int(mins[i]) for i in take)


def entry_at(ts, px, c: Context, trigger_ns: int):
    f = _fill(ts, px, trigger_ns, c.bucket_end_ts)
    return None if f is None else (trigger_ns, *f)
