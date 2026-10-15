"""The three pre-registered Phase-3 hypotheses.

All three key exclusively off a DC event's ``conf_idx`` / ``conf_ts`` - the
moment the threshold was actually crossed.  None of them ever references
``ext_idx`` as a tradeable moment, because the extreme is not known to be an
extreme until the confirmation.

  DC-A  enter in the new DC direction at the confirmation itself.
        "does a confirmed directional change keep going?"

  DC-B  after the confirmation, wait for the move to EXTEND a further
        beta * theta beyond the confirming print, then join it in the same
        direction, provided the extension happens before the opposite DC
        confirms.  "is joining an extending overshoot better than catching
        the turn?"

  DC-C  DC-A restricted to confirmations whose just-completed run extended at
        least gamma * theta - i.e. the PREVIOUS event's overshoot was unusually
        large.  That quantity is complete and known at this confirmation
        (see dc_engine: overshoot(k) == total_move(k+1)).
        "does an unusually extended overshoot revert harder?"

DC-C is by construction a SUBSET of DC-A and is reported as such; it is a
conditioned hypothesis, not an independent one.

Every family uses the same risk geometry: R = theta of the event, symmetric
+1R / -1R first passage.  The stop is a pure distance from the entry, never a
historical extreme, so nothing about it requires hindsight.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

FAMILIES = ("DC_A", "DC_B", "DC_C")


@dataclass
class Signal:
    family: str
    event_seq: int
    direction: int            # +1 long, -1 short  (== the DC direction)
    theta: float
    vu: float
    signal_idx: int           # index on the COMPRESSED path
    signal_ts: int            # moment the signal becomes knowable
    signal_price: float       # the print that made it knowable
    ref_price: float          # theoretical level (trigger price)
    ext_price: float
    ext_ts: int
    conf_ts: int
    conf_price: float
    prev_overshoot: float
    prev_overshoot_ratio: float
    dc_magnitude: float
    total_move: float
    event_ns: int
    n_trades: int
    volume: float
    velocity: float
    prev_direction: int


def _base(fam, ev, sig_idx, sig_ts, sig_px, ref_px) -> Signal:
    return Signal(
        family=fam, event_seq=ev.seq, direction=ev.direction, theta=ev.theta, vu=ev.vu,
        signal_idx=int(sig_idx), signal_ts=int(sig_ts), signal_price=float(sig_px),
        ref_price=float(ref_px), ext_price=ev.ext_price, ext_ts=ev.ext_ts,
        conf_ts=ev.conf_ts, conf_price=ev.conf_price,
        prev_overshoot=ev.prev_overshoot, prev_overshoot_ratio=ev.prev_overshoot_ratio,
        dc_magnitude=ev.dc_magnitude, total_move=ev.total_move, event_ns=ev.event_ns,
        n_trades=ev.n_trades, volume=ev.volume, velocity=ev.velocity,
        prev_direction=ev.prev_direction)


def signals_dc_a(events: list) -> list[Signal]:
    return [_base("DC_A", ev, ev.conf_idx, ev.conf_ts, ev.conf_price, ev.trigger_price)
            for ev in events]


def signals_dc_c(events: list, gamma: float) -> list[Signal]:
    out = []
    for ev in events:
        os_ = ev.prev_overshoot
        if np.isfinite(os_) and ev.theta > 0 and os_ >= gamma * ev.theta:
            out.append(_base("DC_C", ev, ev.conf_idx, ev.conf_ts, ev.conf_price,
                             ev.trigger_price))
    return out


def signals_dc_b(events: list, px: np.ndarray, ts: np.ndarray, beta: float) -> list[Signal]:
    """Join the overshoot once it extends beta*theta beyond the confirming print.

    The search window runs from the confirmation up to (but excluding) the next
    event's confirmation, so a single event can produce at most one DC-B signal
    and the trigger can never be attributed to a later event.
    """
    out = []
    for k, ev in enumerate(events):
        lo = ev.conf_idx + 1
        hi = events[k + 1].conf_idx if k + 1 < len(events) else len(px)
        if lo >= hi:
            continue
        d = ev.direction
        level = ev.conf_price + d * beta * ev.theta
        seg = px[lo:hi]
        hit = (seg >= level) if d > 0 else (seg <= level)
        if not hit.any():
            continue
        j = lo + int(np.argmax(hit))
        out.append(_base("DC_B", ev, j, ts[j], px[j], level))
    return out


def build_signals(events: list, px: np.ndarray, ts: np.ndarray,
                  cfg: dict) -> dict[str, list[Signal]]:
    S = cfg["strategies"]
    return {
        "DC_A": signals_dc_a(events),
        "DC_B": signals_dc_b(events, px, ts, float(S["dc_b"]["beta_extension"])),
        "DC_C": signals_dc_c(events, float(S["dc_c"]["gamma_overshoot"])),
    }
