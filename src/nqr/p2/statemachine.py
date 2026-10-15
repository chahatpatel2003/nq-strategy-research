"""Impulse-exhaustion / absorption reversal state machine.

Deterministic, symmetric for LONG and SHORT, one candidate per direction at a
time, stepping over a dense 1-second event grid.  Every quantity consumed at
second `i` is computed from seconds <= i.

    IDLE -> IMPULSE -> EXHAUSTION_WATCH -> ARMED -> (SIGNAL | ABANDON) -> COOLDOWN

`direction` is the direction of the eventual TRADE: -1 SHORT (after a bullish
impulse), +1 LONG (after a bearish impulse).  `s = -direction` is the impulse
direction, and every comparison is written once and signed by `s`, so the two
sides are literally the same code path.

Absorption history is built in a separate, strictly streaming pass
(`build_legs`) so that a leg's percentile is always computed against legs that
were CONFIRMED STRICTLY EARLIER, and the current leg is only added to the
history after its own rank has been taken.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import polars as pl

from nqr.p2.absorption import TrailingPercentile, absorption_raw

TICK = 0.25
SHORT, LONG = -1, 1
STATES = ("IDLE", "IMPULSE", "EXHAUSTION_WATCH", "ARMED")


@dataclass
class Leg:
    """One extension attempt: previous confirmed opposite extreme -> new extreme."""
    start_idx: int
    ext_idx: int
    conf_idx: int
    start_price: float
    ext_price: float
    agg_vol: float                # aggressive volume in the impulse direction
    progress: float               # |ext - start| in points
    bbo_advance_ticks: float
    absorption: float
    absorption_pct: float         # rank vs STRICTLY earlier legs; nan while warming
    hist_ready: bool

    @property
    def efficiency(self) -> float:
        return self.progress / max(self.agg_vol, 1.0)


@dataclass
class Candidate:
    direction: int
    trading_date: Any
    symbol: str
    imp_start_idx: int
    imp_end_idx: int
    imp_displacement: float
    imp_seconds: int
    vu: float
    legs: list[Leg]
    ext_price: float
    ext_idx: int
    arm_idx: int
    signal_idx: int | None = None


def nonincreasing(x: list[float], tol: float, drop: float) -> bool:
    """Frozen deterioration test.

    Each successive value may tick UP by at most `tol` (noise tolerance) and the
    final value must sit at least `drop` below the first (economic significance).
    """
    for a, b in zip(x, x[1:]):
        if b > a * (1.0 + tol):
            return False
    return x[-1] <= x[0] * (1.0 - drop)


def build_legs(dcs: list[dict], s: int, buy_cum: np.ndarray, sell_cum: np.ndarray,
               ask_open: np.ndarray, ask_hi: np.ndarray,
               bid_open: np.ndarray, bid_lo: np.ndarray,
               bbo_ok: np.ndarray, hist: TrailingPercentile,
               eligible: np.ndarray | None = None) -> list[Leg]:
    """Confirmed DC extremes in the impulse direction -> Legs, in confirmation order.

    `hist` is a persistent rolling window that survives across days.  For each
    leg the rank is taken BEFORE the leg is pushed, so a leg never contributes
    to its own reference distribution.

    `eligible` marks the seconds whose legs may take part in the reference
    distribution, keeping the comparison session-matched: an RTH leg is ranked
    only against other RTH legs.  A leg whose extreme falls outside the eligible
    band is still measured and reported, but is neither ranked nor pushed, so it
    can never qualify (`hist_ready` is False).
    """
    want = "PEAK" if s > 0 else "TROUGH"
    out: list[Leg] = []
    for dc in dcs:
        if dc["kind"] != want:
            continue
        i0, i1 = dc["start_idx"], dc["ext_idx"]
        if i1 <= i0 or not (bbo_ok[i0] and bbo_ok[i1]):
            continue
        cum = buy_cum if s > 0 else sell_cum
        agg = float(cum[i1] - cum[i0])
        progress = abs(float(dc["ext_price"]) - float(dc["start_price"]))
        # best-price advance across the leg, measured on within-second extremes:
        # the leg-start reference is the FIRST quote of the starting second and
        # the running extreme is the max/min quote seen in any second of the leg.
        if s > 0:
            adv = (float(ask_hi[i0:i1 + 1].max()) - float(ask_open[i0])) / TICK
        else:
            adv = (float(bid_open[i0]) - float(bid_lo[i0:i1 + 1].min())) / TICK
        raw = absorption_raw(agg, adv)
        elig = True if eligible is None else bool(eligible[i1])
        ready = hist.ready() and elig
        pct = hist.rank(raw) if ready else float("nan")
        if elig:
            hist.push(raw)                  # push AFTER ranking - never self-referential
        out.append(Leg(i0, i1, dc["conf_idx"], float(dc["start_price"]),
                       float(dc["ext_price"]), agg, progress, adv, raw, pct, ready))
    return out


def check_exhaustion(legs: list[Leg], D: dict, A: dict,
                     stage: str = "FAILED_CONTINUATION") -> tuple[bool, str]:
    """Gate set for the extension sequence.

    ``stage`` only relaxes gates for the pre-registered ablation: stage
    ``DETERIORATION`` stops before the absorption test.  The baseline runs the
    full set.
    """
    if D["require_volume"] and not nonincreasing([l.agg_vol for l in legs],
                                                 D["step_tolerance"], D["overall_drop"]):
        return False, "NO_VOLUME_DETERIORATION"
    if D["require_efficiency"] and not nonincreasing([l.efficiency for l in legs],
                                                     D["step_tolerance"], D["overall_drop"]):
        return False, "NO_EFFICIENCY_DETERIORATION"
    if stage == "DETERIORATION":
        return True, ""
    if not legs[-1].hist_ready:
        return False, "ABSORPTION_HISTORY_WARMUP"
    if legs[-1].absorption_pct < float(A["percentile_min"]):
        return False, "ABSORPTION_TOO_LOW"
    return True, ""


ENTRY_STAGES = ("IMPULSE", "DETERIORATION", "ABSORPTION", "FAILED_CONTINUATION")


def run_direction(direction: int, cfg: dict, *, high: np.ndarray, low: np.ndarray,
                  traded: np.ndarray, vu: np.ndarray, sec: np.ndarray,
                  legs_all: list[Leg], trading_date, symbol,
                  engine_start_idx: int,
                  entry_stage: str = "FAILED_CONTINUATION",
                  ) -> tuple[list[Candidate], list[dict]]:
    """Walk one direction over one day's dense second grid.

    ``entry_stage`` exists solely for the pre-registered component ablation.
    The BASELINE is always ``FAILED_CONTINUATION``; the earlier stages signal at
    the moment their own condition set is first satisfied, which is what
    "impulse only" / "impulse + deterioration" / "+ absorption" mean.
    """
    assert entry_stage in ENTRY_STAGES
    s = -direction
    I, E, D, A, F, C = (cfg["impulse"], cfg["extension"], cfg["deterioration"],
                        cfg["absorption"], cfg["failed_continuation"], cfg["cooldown"])
    W = int(I["max_seconds"])
    n = len(high)
    out: list[Candidate] = []
    rejects: list[dict] = []

    roll_lo = pl.Series(low).rolling_min(window_size=W, min_samples=1).to_numpy()
    roll_hi = pl.Series(high).rolling_max(window_size=W, min_samples=1).to_numpy()

    legs_by_conf: dict[int, list[Leg]] = {}
    for lg in legs_all:
        legs_by_conf.setdefault(lg.conf_idx, []).append(lg)

    state = "IDLE"
    cand: Candidate | None = None
    legs: list[Leg] = []
    imp_start = imp_end = -1
    imp_disp = 0.0
    cooldown_until = -10 ** 9
    last_imp_end = -1

    def close_candidate(why: str, at: int):
        nonlocal state, cand, legs, cooldown_until
        rejects.append(_rej(direction, trading_date, symbol, imp_start, imp_end,
                            imp_disp, legs, why, int(sec[at]),
                            vu[imp_end] if imp_end >= 0 else np.nan))
        state, cand, legs = "IDLE", None, []
        cooldown_until = int(sec[at]) + int(C["min_seconds_after_candidate"])

    for i in range(max(engine_start_idx, 0), n):
        if not traded[i]:
            continue
        v = vu[i]
        if not np.isfinite(v):
            continue

        # ------------------------------------------------ ARMED: await the failure
        if state == "ARMED":
            assert cand is not None
            if (sec[i] - sec[cand.arm_idx]) > int(F["arm_max_seconds"]):
                close_candidate("ARM_TIMEOUT", i)
                continue
            beyond = (high[i] > cand.ext_price) if s > 0 else (low[i] < cand.ext_price)
            if beyond and F["cancel_on_new_extreme"]:
                # a fresh extreme re-opens evaluation; keep the leg history
                rejects.append(_rej(direction, trading_date, symbol, imp_start, imp_end,
                                    imp_disp, legs, "NEW_EXTREME_WHILE_ARMED",
                                    int(sec[i]), cand.vu))
                state, cand = "EXHAUSTION_WATCH", None
            else:
                move = (cand.ext_price - low[i]) if s > 0 else (high[i] - cand.ext_price)
                if move >= float(F["reversal_vu"]) * cand.vu:
                    cand.signal_idx = i
                    out.append(cand)
                    state, cand, legs = "IDLE", None, []
                    cooldown_until = int(sec[i]) + int(C["min_seconds_after_candidate"])
                    continue

        # -------------------------------------- collect confirmed extension legs
        if state in ("IMPULSE", "EXHAUSTION_WATCH") and i in legs_by_conf:
            for lg in legs_by_conf[i]:
                if lg.ext_idx < imp_start:
                    continue
                if legs:
                    better = (lg.ext_price > legs[-1].ext_price) if s > 0 \
                        else (lg.ext_price < legs[-1].ext_price)
                    if not better:
                        close_candidate("NOT_A_NEW_EXTREME", i)
                        break
                legs.append(lg)
                if (sec[lg.ext_idx] - sec[imp_start]) > int(E["max_seconds_from_impulse"]):
                    close_candidate("EXTENSION_TOO_SLOW", i)
                    break
                k = int(E["n_attempts"])
                if len(legs) >= k:
                    use = legs[-k:]
                    ok, why = check_exhaustion(use, D, A, stage=entry_stage)
                    if ok:
                        cand = Candidate(direction, trading_date, symbol, imp_start,
                                         imp_end, imp_disp,
                                         int(sec[imp_end] - sec[imp_start]),
                                         float(vu[imp_end]), list(use),
                                         use[-1].ext_price, use[-1].ext_idx, i)
                        if entry_stage in ("DETERIORATION", "ABSORPTION"):
                            cand.signal_idx = i               # ablations B and C
                            out.append(cand)
                            state, cand, legs = "IDLE", None, []
                            cooldown_until = int(sec[i]) + int(C["min_seconds_after_candidate"])
                            break
                        state = "ARMED"
                    else:
                        rejects.append(_rej(direction, trading_date, symbol, imp_start,
                                            imp_end, imp_disp, use, why, int(sec[i]),
                                            vu[imp_end]))
                        state = "EXHAUSTION_WATCH"
            if state == "IDLE":
                continue

        # ------------------------------------------------------ IDLE: find impulse
        if state == "IDLE":
            if sec[i] < cooldown_until:
                continue
            disp = (high[i] - roll_lo[i]) if s > 0 else (roll_hi[i] - low[i])
            if disp < max(float(I["displacement_vu"]) * v, float(I["min_points"])):
                continue
            j0 = max(0, i - W + 1)
            k = j0 + (int(np.argmin(low[j0:i + 1])) if s > 0 else int(np.argmax(high[j0:i + 1])))
            if C["require_fresh_impulse"] and last_imp_end >= 0 and k <= last_imp_end:
                continue
            imp_start, imp_end, imp_disp = k, i, float(disp)
            last_imp_end = i
            legs, state = [], "IMPULSE"
            if entry_stage == "IMPULSE":                     # ablation A
                c = Candidate(direction, trading_date, symbol, imp_start, imp_end,
                              imp_disp, int(sec[imp_end] - sec[imp_start]), float(v),
                              [], float(high[i] if s > 0 else low[i]), i, i)
                c.signal_idx = i
                out.append(c)
                state, legs = "IDLE", []
                cooldown_until = int(sec[i]) + int(C["min_seconds_after_candidate"])

    if cand is not None:
        rejects.append(_rej(direction, trading_date, symbol, imp_start, imp_end, imp_disp,
                            legs, "END_OF_SESSION", int(sec[n - 1]), cand.vu))
    return out, rejects


def _rej(direction, trading_date, symbol, i0, i1, disp, legs, why, at_sec, vu) -> dict:
    last = legs[-1] if legs else None
    return dict(direction=direction, trading_date=trading_date, symbol=symbol,
                imp_start_idx=int(i0), imp_end_idx=int(i1),
                imp_displacement=float(disp), vu=float(vu) if np.isfinite(vu) else None,
                n_legs=len(legs), reject_reason=why, at_sec=int(at_sec),
                absorption=float(last.absorption) if last else None,
                absorption_pct=float(last.absorption_pct) if last else None)
