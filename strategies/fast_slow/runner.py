"""Fast-Slow strategy runner.

Pipeline per Globex trading day:
  level segments  ->  A/B/C detection  ->  reversal trigger  ->  candidate
  signal  ->  precedence + concurrency  ->  tick-resolved entry/exit.

Four variants share one candidate set, differing only in which trigger
families are eligible:  ENGULFING, PIN, STAR, ANY.  ANY is the pre-registered
primary hypothesis.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import polars as pl

from nqr.backtest.engine import TICK, find_entry, resolve, excursions
from nqr.levels.build import PRIORITY, LevelSegment
from nqr.sessions.calendar import ET, day_bounds_utc, to_utc
from nqr.signals import triggers as TG
from nqr.signals.fast_slow import detect_abc, time_ratio_bucket

NS = 1_000_000_000
VARIANTS = {
    "ENGULFING": ("ENGULFING",),
    "PIN": ("PIN",),
    "STAR": ("STAR",),
    "ANY": ("ENGULFING", "PIN", "STAR"),
}


def select_variant(cands: list["Candidate"], eligible: tuple[str, ...],
                   precedence: list[str]) -> list["Candidate"]:
    """One signal per A-B-C pattern: earliest trigger bar, then family precedence."""
    rank = {f: i for i, f in enumerate(precedence)}
    best: dict[tuple, "Candidate"] = {}
    for cd in cands:
        if cd.trigger_type not in eligible:
            continue
        key = (cd.trading_date, cd.family, cd.level, cd.a_ns, cd.b_ns, cd.c_ns)
        cur = best.get(key)
        if cur is None or (cd.trigger_idx, rank[cd.trigger_type]) < (cur.trigger_idx, rank[cur.trigger_type]):
            best[key] = cd
    return sorted(best.values(), key=order_key)


@dataclass
class Candidate:
    trading_date: dt.date
    symbol: str
    family: str
    level: float
    tolerance: float
    direction: int
    a_ns: int
    b_ns: int
    c_ns: int
    a_price: float
    b_price: float
    c_price: float
    ab_dist: float
    bc_dist: float
    ab_ns: int
    bc_ns: int
    time_ratio: float
    dist_ratio: float
    trigger_type: str
    trigger_idx: int
    trigger_n_bars: int
    signal_ns: int              # trigger bar END = moment the signal is knowable
    trig_o: float
    trig_h: float
    trig_l: float
    trig_c: float
    pattern_high: float
    pattern_low: float
    stop: float
    max_r_allowed: float | None = None


def _contiguous(bar_ns: np.ndarray, tdate_code: np.ndarray, i: int, nbars: int, step: int) -> bool:
    if i - nbars + 1 < 0:
        return False
    for k in range(i - nbars + 2, i + 1):
        if bar_ns[k] - bar_ns[k - 1] != step:
            return False
        if tdate_code[k] != tdate_code[k - 1]:
            return False
    return True


def find_candidates(day_bars: pl.DataFrame, segs: list[LevelSegment], cfg: dict,
                    trig: dict[str, np.ndarray], gidx0: int,
                    bar_ns_all: np.ndarray, tdate_code: np.ndarray,
                    o: np.ndarray, h: np.ndarray, l: np.ndarray, c: np.ndarray,
                    atr20_prev: float) -> tuple[list[Candidate], list[dict]]:
    """gidx0 = index of the day's first bar inside the global arrays."""
    step = cfg["data"]["bar_minutes"] * 60 * NS
    P = cfg["pattern"]
    T = cfg["trigger"]
    S = cfg["stop"]
    min_ab = max(P["min_ab_points_atr_frac"] * atr20_prev, P["min_ab_points_floor"])
    n_day = day_bars.height
    bar_ns = bar_ns_all[gidx0:gidx0 + n_day]
    bar_end = bar_ns + step
    sym = day_bars["symbol"][0]
    d = day_bars["trading_date"][0]

    cands: list[Candidate] = []
    rejects: list[dict] = []
    for seg in segs:
        m = (bar_end > seg.valid_from_ns) & (bar_end <= seg.valid_to_ns)
        if m.sum() < 4:
            continue
        idx = np.flatnonzero(m)
        s0, s1 = int(idx[0]), int(idx[-1]) + 1
        sh, slo, sbe = h[gidx0 + s0:gidx0 + s1], l[gidx0 + s0:gidx0 + s1], bar_end[s0:s1]
        abcs = detect_abc(sh, slo, sbe, seg.price, seg.tolerance,
                          min_ab_dist=min_ab, min_ab_bars=P["min_ab_bars"],
                          max_ab_bars=P["max_ab_bars"], max_bc_bars=P["max_bc_bars"],
                          time_ratio_min=P["time_ratio_min"],
                          dist_ratio_min=P["bc_ab_distance_ratio_min"],
                          dist_ratio_max=P["bc_ab_distance_ratio_max"],
                          step_ns=step, keep_rejects=True)
        for ab in abcs:
            base = dict(trading_date=d, symbol=sym, family=seg.family, level=seg.price,
                        tolerance=seg.tolerance, direction=ab.direction,
                        ab_dist=ab.ab_dist, bc_dist=ab.bc_dist,
                        ab_ns=ab.ab_ns, bc_ns=ab.bc_ns,
                        time_ratio=ab.time_ratio, dist_ratio=ab.dist_ratio,
                        a_ns=int(bar_end[s0 + ab.a_idx]), b_ns=int(bar_end[s0 + ab.b_idx]),
                        c_ns=int(sbe[ab.c_idx]), a_price=ab.a_price,
                        b_price=ab.b_price, c_price=ab.c_price,
                        signal_ns=int(sbe[ab.c_idx]), trigger_type="NONE",
                        trig_o=float(o[gidx0 + s0 + ab.c_idx]),
                        trig_h=float(h[gidx0 + s0 + ab.c_idx]),
                        trig_l=float(l[gidx0 + s0 + ab.c_idx]),
                        trig_c=float(c[gidx0 + s0 + ab.c_idx]),
                        status="REJECTED")
            if ab.reject is not None:
                rejects.append({**base, "skip_reason": ab.reject})
                continue
            gA, gB, gC = gidx0 + s0 + ab.a_idx, gidx0 + s0 + ab.b_idx, gidx0 + s0 + ab.c_idx
            hits: dict[str, Candidate] = {}
            dead = False
            for t in range(gC, min(gC + T["window_bars"], gidx0 + s1)):
                # level must still be holding at this point in the window
                if ab.direction > 0:
                    run = float(l[gC:t + 1].min())
                    bc_run = ab.b_price - run
                else:
                    run = float(h[gC:t + 1].max())
                    bc_run = run - ab.b_price
                if ab.ab_dist <= 0 or bc_run / ab.ab_dist > P["bc_ab_distance_ratio_max"]:
                    dead = True
                    break
                for fam in T["families"]:
                    if fam in hits or trig[fam][t] != ab.direction:
                        continue
                    nb = TG.PATTERN_BARS[fam]
                    if not _contiguous(bar_ns_all, tdate_code, t, nb, step):
                        continue
                    p0 = t - nb + 1
                    if p0 <= gB:
                        continue
                    p_hi = float(h[p0:t + 1].max())
                    p_lo = float(l[p0:t + 1].min())
                    # the trigger pattern itself must reach the level zone
                    if ab.direction > 0 and p_lo > seg.price + seg.tolerance:
                        continue
                    if ab.direction < 0 and p_hi < seg.price - seg.tolerance:
                        continue
                    stop = (p_lo - S["ticks"] * TICK) if ab.direction > 0 else (p_hi + S["ticks"] * TICK)
                    hits[fam] = Candidate(
                        trading_date=d, symbol=sym, family=seg.family, level=seg.price,
                        tolerance=seg.tolerance, direction=ab.direction,
                        a_ns=int(bar_end[s0 + ab.a_idx]), b_ns=int(bar_end[s0 + ab.b_idx]),
                        c_ns=int(bar_end[s0 + ab.c_idx]),
                        a_price=ab.a_price, b_price=ab.b_price, c_price=ab.c_price,
                        ab_dist=ab.ab_dist, bc_dist=ab.bc_dist, ab_ns=ab.ab_ns, bc_ns=ab.bc_ns,
                        time_ratio=ab.time_ratio, dist_ratio=ab.dist_ratio,
                        trigger_type=fam, trigger_idx=t, trigger_n_bars=nb,
                        signal_ns=int(bar_ns_all[t] + step),
                        trig_o=float(o[t]), trig_h=float(h[t]), trig_l=float(l[t]),
                        trig_c=float(c[t]), pattern_high=p_hi, pattern_low=p_lo, stop=stop,
                        max_r_allowed=float(S["max_r_atr_frac"] * atr20_prev))
            if not hits:
                rejects.append({**base, "skip_reason": "LEVEL_BROKEN" if dead else "NO_TRIGGER"})
            else:
                cands.extend(hits.values())
    return cands, rejects


def order_key(cd: Candidate) -> tuple:
    return (cd.signal_ns, PRIORITY[cd.family], abs(cd.level - cd.trig_c), cd.family, cd.level)
