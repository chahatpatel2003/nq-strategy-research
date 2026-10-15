"""Turn ranked candidates into tick-resolved trades under the baseline
portfolio rule (one open Fast-Slow position at a time)."""
from __future__ import annotations

import datetime as dt

import numpy as np

from nqr.backtest.engine import TICK, find_entry, resolve, excursions

NS = 1_000_000_000


def simulate_day(cands, ts: np.ndarray, px: np.ndarray, day_end_ns: int,
                 timeout_ns: int, cfg: dict) -> list[dict]:
    """cands must already be sorted by ``order_key``."""
    E, S, T = cfg["entry"], cfg["stop"], cfg["targets"]
    lat = int(E["latency_ms"]) * 1_000_000
    max_wait = int(E["max_wait_ms"]) * 1_000_000
    max_r_abs = None
    rows: list[dict] = []
    busy_until = -1

    for cd in cands:
        rec = _base_row(cd)
        if cd.signal_ns < busy_until:
            rec["status"], rec["skip_reason"] = "SKIPPED", "CONCURRENT_POSITION"
            rows.append(rec)
            continue
        ent = find_entry(ts, px, cd.signal_ns + lat, max_wait)
        if ent is None:
            rec["status"], rec["skip_reason"] = "SKIPPED", "NO_ENTRY_PRINT"
            rows.append(rec)
            continue
        eidx, ets, epx = ent
        r = (epx - cd.stop) * cd.direction
        if r < S["min_r_points"]:
            rec["status"], rec["skip_reason"] = "SKIPPED", "R_TOO_SMALL"
            rec.update(entry_ns=ets, entry_price=epx, r_points=r)
            rows.append(rec)
            continue
        if rec["max_r_allowed"] is not None and r > rec["max_r_allowed"]:
            rec["status"], rec["skip_reason"] = "SKIPPED", "R_TOO_LARGE"
            rec.update(entry_ns=ets, entry_price=epx, r_points=r)
            rows.append(rec)
            continue

        rec.update(entry_ns=ets, entry_price=epx, r_points=r,
                   entry_slippage=(epx - cd.trig_c) * cd.direction)
        hard_end = min(day_end_ns, timeout_ns)
        for tag, mult in (("r1", T["primary_r"]), ("r2", T["secondary_r"])):
            tp = epx + cd.direction * mult * r
            f = resolve(ts, px, eidx, hard_end, cd.direction, tp, cd.stop)
            mfe, mae = excursions(ts, px, eidx, f.ts_ns, cd.direction, epx)
            pts = (f.price - epx) * cd.direction
            rec[f"{tag}_target"] = tp
            rec[f"{tag}_outcome"] = f.kind
            rec[f"{tag}_exit_ns"] = f.ts_ns
            rec[f"{tag}_exit_price"] = f.price
            rec[f"{tag}_points"] = pts
            rec[f"{tag}_R"] = pts / r if r > 0 else 0.0
            rec[f"{tag}_mfe"] = mfe
            rec[f"{tag}_mae"] = mae
            rec[f"{tag}_hold_s"] = (f.ts_ns - ets) / NS
        rec["status"], rec["skip_reason"] = "ACCEPTED", None
        # concurrency is governed by the PRIMARY (1R) book
        busy_until = rec["r1_exit_ns"]
        rows.append(rec)
    return rows


def _base_row(cd) -> dict:
    return {
        "trading_date": cd.trading_date, "symbol": cd.symbol, "family": cd.family,
        "level": cd.level, "tolerance": cd.tolerance, "direction": cd.direction,
        "a_ns": cd.a_ns, "b_ns": cd.b_ns, "c_ns": cd.c_ns,
        "a_price": cd.a_price, "b_price": cd.b_price, "c_price": cd.c_price,
        "ab_dist": cd.ab_dist, "bc_dist": cd.bc_dist,
        "ab_ns": cd.ab_ns, "bc_ns": cd.bc_ns,
        "time_ratio": cd.time_ratio, "dist_ratio": cd.dist_ratio,
        "trigger_type": cd.trigger_type, "trigger_n_bars": cd.trigger_n_bars,
        "trig_o": cd.trig_o, "trig_h": cd.trig_h, "trig_l": cd.trig_l, "trig_c": cd.trig_c,
        "pattern_high": cd.pattern_high, "pattern_low": cd.pattern_low,
        "signal_ns": cd.signal_ns, "stop": cd.stop,
        "entry_ns": None, "entry_price": None, "r_points": None, "entry_slippage": None,
        "max_r_allowed": cd.max_r_allowed,
        "status": None, "skip_reason": None,
    }
