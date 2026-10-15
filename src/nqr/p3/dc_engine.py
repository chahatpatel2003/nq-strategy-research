"""Causal directional-change (DC) event engine, reconstructed tick by tick.

An UP run tracks the running high.  When a trade prints at or below
``high - theta`` a **DOWNWARD directional-change event is CONFIRMED**, and the
extreme that is confirmed is the prior high.  A DOWN run mirrors this.

THE CENTRAL CAUSALITY RULE
--------------------------
The extreme printed at ``ext_ts`` is NOT known to be an extreme until the
threshold is crossed at ``conf_ts``.  Every event therefore carries both
timestamps, and **the signal does not exist until ``conf_ts``**.  Nothing in
this module ever stamps a tradeable moment at ``ext_ts``; the strategies key
exclusively off ``conf_idx`` / ``conf_ts``.

Overshoot
---------
After a downward DC confirms at price ``conf_px``, price may keep falling.  The
low it eventually reaches is the extreme that the NEXT (upward) DC will confirm.
The overshoot of event *k* is therefore ``|ext_price(k+1) - conf_price(k)|`` and
is only fully known once event *k+1* confirms.  It is stored on event *k* for
diagnostics, and a strategy may only use it where it is already known - which is
why DC-C keys off the *previous* event's overshoot, complete by construction.

theta
-----
``theta`` is sampled once, at the instant the current run begins (that is, at
the confirmation of the previous event), and held constant for the whole run.
A threshold that drifted mid-run would make "did price move theta from the
extreme?" ambiguous.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np

TICK = 0.25
UP, DOWN, UNDECIDED = 1, -1, 0


@dataclass
class DCEvent:
    seq: int                    # index within the day, 0-based
    direction: int              # +1 upward DC (confirmed a low), -1 downward DC
    theta: float                # threshold that governed the run just ended
    vu: float                   # volatility unit at run start
    ext_idx: int                # tick index of the confirmed extreme
    ext_ts: int                 # ... and its ts_event (NOT tradeable)
    ext_price: float
    conf_idx: int               # tick index where the threshold was crossed
    conf_ts: int                # ... the moment the event becomes KNOWN
    conf_price: float           # the confirming print
    trigger_price: float        # ext_price -/+ theta: the theoretical level
    dc_magnitude: float         # |conf_price - ext_price|
    run_start_idx: int          # previous confirmation (start of the run)
    run_start_ts: int
    run_start_price: float
    prev_overshoot: float       # overshoot of the PREVIOUS event (known now)
    prev_overshoot_ratio: float # prev_overshoot / theta
    prev_direction: int
    prev_dc_magnitude: float
    n_trades: int               # over the run  (run_start -> conf)
    volume: float
    event_ns: int               # conf_ts - run_start_ts
    total_move: float           # |ext_price - run_start_price| (the run itself)
    total_move_ns: int          # ext_ts - run_start_ts
    velocity: float             # total_move / seconds  (points per second)
    # filled in when the NEXT event confirms:
    overshoot: float = float("nan")
    overshoot_ns: int = -1
    overshoot_ratio: float = float("nan")
    overshoot_ext_idx: int = -1
    overshoot_ext_ts: int = -1
    overshoot_ext_price: float = float("nan")


def detect_events(px: np.ndarray, ts: np.ndarray, theta_at: np.ndarray,
                  vu_at: np.ndarray, cum_trades: np.ndarray, cum_vol: np.ndarray,
                  start_i: int = 0) -> list[DCEvent]:
    """Walk one day's tick path and emit confirmed DC events.

    ``px`` is in POINTS (float) and is expected to be the compressed
    price-change path; ``theta_at``/``vu_at`` are aligned per-tick arrays;
    ``cum_trades``/``cum_vol`` are inclusive cumulative counts on the same index
    so that per-run aggregates are exact O(1) differences.
    """
    n = len(px)
    out: list[DCEvent] = []
    if n <= start_i + 1:
        return out

    mode = UNDECIDED
    hi_px, hi_i = px[start_i], start_i
    lo_px, lo_i = px[start_i], start_i
    run_i = start_i                       # run start = previous confirmation
    theta = float(theta_at[start_i])
    vu = float(vu_at[start_i])
    prev_dir = 0
    prev_mag = float("nan")
    seq = 0

    for i in range(start_i, n):
        p = px[i]
        if mode == UNDECIDED:
            if p > hi_px:
                hi_px, hi_i = p, i
            if p < lo_px:
                lo_px, lo_i = p, i
            if p <= hi_px - theta and hi_i < i:
                mode = UP                 # we were in an UP run; resolve below
            elif p >= lo_px + theta and lo_i < i:
                mode = DOWN
            else:
                continue

        if mode == UP:
            if p > hi_px:
                hi_px, hi_i = p, i
                continue
            if p > hi_px - theta or hi_i >= i:
                continue
            ev = _make(seq, -1, theta, vu, hi_i, hi_px, i, p, hi_px - theta,
                       run_i, px, ts, cum_trades, cum_vol, prev_dir, prev_mag)
        else:
            if p < lo_px:
                lo_px, lo_i = p, i
                continue
            if p < lo_px + theta or lo_i >= i:
                continue
            ev = _make(seq, +1, theta, vu, lo_i, lo_px, i, p, lo_px + theta,
                       run_i, px, ts, cum_trades, cum_vol, prev_dir, prev_mag)

        # close the PREVIOUS event's overshoot: it ran from that event's
        # confirmation to the extreme this event has just confirmed
        if out:
            prev = out[-1]
            prev.overshoot_ext_idx = ev.ext_idx
            prev.overshoot_ext_ts = ev.ext_ts
            prev.overshoot_ext_price = ev.ext_price
            prev.overshoot = abs(ev.ext_price - prev.conf_price)
            prev.overshoot_ns = int(ev.ext_ts - prev.conf_ts)
            prev.overshoot_ratio = prev.overshoot / prev.theta if prev.theta > 0 else float("nan")

        out.append(ev)
        seq += 1
        prev_dir, prev_mag = ev.direction, ev.dc_magnitude
        # start the next run at this confirmation; resample theta HERE
        run_i = i
        theta = float(theta_at[i])
        vu = float(vu_at[i])
        if ev.direction < 0:
            mode, lo_px, lo_i = DOWN, p, i
        else:
            mode, hi_px, hi_i = UP, p, i

    # the last event's overshoot never completes within the day: left as NaN so
    # no strategy can accidentally consume an unfinished measurement
    return out


def _make(seq, direction, theta, vu, ext_i, ext_px, conf_i, conf_px, trig_px,
          run_i, px, ts, cum_trades, cum_vol, prev_dir, prev_mag) -> DCEvent:
    ext_ts = int(ts[ext_i]); conf_ts = int(ts[conf_i]); run_ts = int(ts[run_i])
    move_ns = max(int(ext_ts - run_ts), 0)
    total_move = abs(float(ext_px) - float(px[run_i]))
    # IDENTITY, used by DC-C: for seq > 0 the run that just ended started at the
    # PREVIOUS event's confirmation, so this run's magnitude IS that event's
    # completed overshoot - and it is fully known right now, at conf_ts.
    prev_os = total_move if seq > 0 else float("nan")
    return DCEvent(
        seq=seq, direction=int(direction), theta=float(theta), vu=float(vu),
        ext_idx=int(ext_i), ext_ts=ext_ts, ext_price=float(ext_px),
        conf_idx=int(conf_i), conf_ts=conf_ts, conf_price=float(conf_px),
        trigger_price=float(trig_px),
        dc_magnitude=abs(float(conf_px) - float(ext_px)),
        run_start_idx=int(run_i), run_start_ts=run_ts,
        run_start_price=float(px[run_i]),
        prev_overshoot=float(prev_os),
        prev_overshoot_ratio=(float(prev_os) / theta) if theta > 0 else float("nan"),
        prev_direction=int(prev_dir), prev_dc_magnitude=float(prev_mag),
        n_trades=int(cum_trades[conf_i] - cum_trades[run_i]),
        volume=float(cum_vol[conf_i] - cum_vol[run_i]),
        event_ns=int(conf_ts - run_ts),
        total_move=total_move, total_move_ns=move_ns,
        velocity=(total_move / (move_ns / 1e9)) if move_ns > 0 else float("nan"),
    )


def events_to_rows(evs: list[DCEvent]) -> list[dict]:
    return [asdict(e) for e in evs]
