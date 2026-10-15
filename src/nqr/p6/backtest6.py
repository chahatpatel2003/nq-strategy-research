"""Phase-6 backtest: one causal context per bucket, six entry mechanics, three controls.

Trade geometry is the FROZEN Phase-5 `r4p0` architecture, reused unchanged:
R = 4.0 x ATR14(completed 1-min) locked at context activation, 1R target /
1R stop hung off the realised entry price, 60-minute maximum hold, executable
timeout (first print at or after the cutoff), hard 16:00 ET rail.

Nothing here re-optimises R, RR, the horizon, the session or the direction
model.  Only WHEN and AT WHAT PRICE the position is opened.
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from nqr.p4 import features4 as F4
from nqr.p5.dataset5 import FRICTIONS, MAX_HOLD_S, PRIMARY_FRICTION
from nqr.p5.labels5 import excursions_p5, resolve_p5
from nqr.p6.context6 import (CONTROLS, ENTRY_METHODS, Context, entry_at, entry_immediate,
                             entry_of, random_minutes)

NS = F4.NS
TICK = F4.TICK
HARD_EXIT_ET = "16:00"
RANDOM_PER_CONTEXT = 10
OUTCOME_NAME = {"TP": "TP", "SL": "SL", "TIMEOUT": "TIMEOUT", "NO_DATA": "NO_DATA"}


def _pre_entry_excursion(px: np.ndarray, i0: int, i1: int, ref: float, d: int):
    """MFE / MAE between context activation and the entry fill, in points."""
    if i1 <= i0:
        return 0.0, 0.0
    seg = px[i0:i1 + 1] * TICK
    hi, lo = float(seg.max()), float(seg.min())
    return ((hi - ref, ref - lo) if d > 0 else (ref - lo, hi - ref))


def _trade(c: Context, method: str, trig_ns: int, eidx: int, ets: int, epx: float,
           ts: np.ndarray, px: np.ndarray, hard_ns: int) -> dict:
    d, r = c.direction, c.r_points
    end_ns = min(hard_ns, ets + MAX_HOLD_S * NS)
    f = resolve_p5(ts, px, eidx, end_ns, d, epx + d * r, epx - d * r)
    mfe, mae = excursions_p5(ts, px, eidx, f.ts_ns, d, epx)
    pts = (f.price - epx) * d
    pre_mfe, pre_mae = _pre_entry_excursion(px, c.act_idx, eidx, c.act_price, d)
    rec = {
        "trading_date": c.trading_date, "symbol": c.symbol, "bucket": c.bucket,
        "method": method, "direction": d, "side": "LONG" if d > 0 else "SHORT",
        "score": c.score, "activation_ts": c.activation_ts, "act_price": c.act_price,
        "sec_since_open": c.sec_since_open,
        "trigger_ts": int(trig_ns), "entry_ns": int(ets), "entry_price": float(epx),
        "r_points": float(r), "stop": float(epx - d * r), "target": float(epx + d * r),
        "wait_s": (ets - c.activation_ts) / NS,
        "remaining_bucket_s": (c.bucket_end_ts - ets) / NS,
        # positive = a better fill than entering immediately at activation
        "entry_improvement_pt": (c.act_price - epx) * d,
        "entry_improvement_R": (c.act_price - epx) * d / r,
        "pre_entry_mfe": pre_mfe, "pre_entry_mae": pre_mae,
        "outcome": OUTCOME_NAME[f.kind], "exit_ns": int(f.ts_ns),
        "exit_price": float(f.price), "points": float(pts), "R": float(pts / r),
        "mfe": float(mfe), "mae": float(mae), "hold_s": (f.ts_ns - ets) / NS,
        "friction_over_r": PRIMARY_FRICTION / r,
    }
    for fr in FRICTIONS:
        k = str(fr).replace(".", "p")
        rec[f"net_{k}"] = pts - fr
        rec[f"netR_{k}"] = (pts - fr) / r
    return rec


def _skip(c: Context, method: str, reason: str) -> dict:
    return {"trading_date": c.trading_date, "symbol": c.symbol, "bucket": c.bucket,
            "method": method, "direction": c.direction,
            "side": "LONG" if c.direction > 0 else "SHORT", "score": c.score,
            "activation_ts": c.activation_ts, "act_price": c.act_price,
            "sec_since_open": c.sec_since_open,
            "status": "SKIPPED", "skip_reason": reason}


def run_day(day: dt.date, contexts: list[Context], ts: np.ndarray, px: np.ndarray,
            rng: np.random.Generator, noncontext_buckets: list[int],
            dir_pool: np.ndarray) -> dict:
    """All six methods, the three controls and the context log for one day."""
    hard_ns = F4.et_sec(day, HARD_EXIT_ET) * NS
    out = {m: [] for m in ENTRY_METHODS}
    out.update({f"CONTROL_{c}": [] for c in CONTROLS})
    ctx_rows = []
    busy = {m: -1 for m in list(ENTRY_METHODS) + ["CONTROL_IMMEDIATE"]}

    for c in contexts:
        ctx_rows.append({
            "trading_date": c.trading_date, "symbol": c.symbol, "bucket": c.bucket,
            "activation_ts": c.activation_ts, "sec_since_open": c.sec_since_open,
            "direction": c.direction, "side": "LONG" if c.direction > 0 else "SHORT",
            "score": c.score, "r_points": c.r_points, "act_price": c.act_price,
            "n_qualifying": c.n_qualifying,
            "bucket_remaining_s": (c.bucket_end_ts - c.activation_ts) / NS})

        # ---- the six entry mechanics, each its own one-position book ----
        for m in ENTRY_METHODS:
            e = entry_of(m, ts, px, c)
            if e is None:
                out[m].append(_skip(c, m, "NO_ENTRY_IN_BUCKET")); continue
            trig, eidx, ets, epx = e
            if ets < busy[m]:
                out[m].append(_skip(c, m, "SKIPPED_OVERLAP")); continue
            rec = _trade(c, m, trig, eidx, ets, epx, ts, px, hard_ns)
            rec.update(status="ACCEPTED", skip_reason=None)
            busy[m] = rec["exit_ns"]
            out[m].append(rec)

        # ---- CONTROL_IMMEDIATE (also one position at a time) ----
        trig, eidx, ets, epx = entry_immediate(ts, px, c)
        if ets >= busy["CONTROL_IMMEDIATE"]:
            rec = _trade(c, "CONTROL_IMMEDIATE", trig, eidx, ets, epx, ts, px, hard_ns)
            rec.update(status="ACCEPTED", skip_reason=None)
            busy["CONTROL_IMMEDIATE"] = rec["exit_ns"]
            out["CONTROL_IMMEDIATE"].append(rec)
        else:
            out["CONTROL_IMMEDIATE"].append(_skip(c, "CONTROL_IMMEDIATE", "SKIPPED_OVERLAP"))

        # ---- CONTROL_RANDOM: independent entries, causal, after activation ----
        for t_ns in random_minutes(c, rng, RANDOM_PER_CONTEXT):
            e = entry_at(ts, px, c, t_ns)
            if e is None:
                continue
            trig, eidx, ets, epx = e
            rec = _trade(c, "CONTROL_RANDOM", trig, eidx, ets, epx, ts, px, hard_ns)
            rec.update(status="ACCEPTED", skip_reason=None)
            out["CONTROL_RANDOM"].append(rec)

        # ---- CONTROL_NONCONTEXT: same day, a bucket with NO context ----
        if noncontext_buckets:
            b = int(rng.choice(noncontext_buckets))
            from nqr.p6.context6 import bucket_bounds
            b0, b1 = bucket_bounds(day, b)
            d = int(rng.choice(dir_pool)) if dir_pool.size else c.direction
            shadow = Context(day, c.symbol, b, b0 * NS, d, 0.0, c.r_points, b1 * NS,
                             0, 0, 0.0, 0, b0 - F4.et_sec(day, F4.SESSION_START_ET))
            f0 = entry_at(ts, px, shadow, b0 * NS)
            if f0 is not None:
                shadow.act_idx, shadow.act_ts, shadow.act_price = f0[1], f0[2], f0[3]
                for t_ns in random_minutes(shadow, rng, RANDOM_PER_CONTEXT):
                    e = entry_at(ts, px, shadow, t_ns)
                    if e is None:
                        continue
                    trig, eidx, ets, epx = e
                    rec = _trade(shadow, "CONTROL_NONCONTEXT", trig, eidx, ets, epx,
                                 ts, px, hard_ns)
                    rec.update(status="ACCEPTED", skip_reason=None)
                    out["CONTROL_NONCONTEXT"].append(rec)
    return {"books": out, "contexts": ctx_rows}


SCHEMA = {"trading_date": pl.Date, "symbol": pl.String, "outcome": pl.String,
          "skip_reason": pl.String, "status": pl.String, "exit_ns": pl.Int64,
          "entry_ns": pl.Int64, "trigger_ts": pl.Int64, "activation_ts": pl.Int64}


def frame(rows: list[dict]) -> pl.DataFrame:
    if not rows:
        return pl.DataFrame()
    keys: list[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    full = [{k: r.get(k) for k in keys} for r in rows]
    ov = {k: v for k, v in SCHEMA.items() if k in keys}
    for c in ("points", "R", "mfe", "mae", "hold_s", "exit_price", "entry_price",
              "wait_s", "entry_improvement_pt", "entry_improvement_R",
              "pre_entry_mfe", "pre_entry_mae", "remaining_bucket_s"):
        if c in keys:
            ov[c] = pl.Float64
    for fr in FRICTIONS:
        k = str(fr).replace(".", "p")
        for pre in ("net_", "netR_"):
            if pre + k in keys:
                ov[pre + k] = pl.Float64
    return pl.DataFrame(full, strict=False, schema_overrides=ov)


def accepted(t: pl.DataFrame) -> pl.DataFrame:
    return t if t.height == 0 else t.filter(pl.col("status") == "ACCEPTED")


def pf_r(t: pl.DataFrame, friction: float) -> float:
    """Profit factor in R units -- PF(R).  Phase 5 established that the
    points-based figure can disagree in sign under a volatility-scaled R."""
    if t.height == 0:
        return float("nan")
    r = (t["points"].to_numpy().astype(float) - friction) / t["r_points"].to_numpy().astype(float)
    gp, gl = float(r[r > 0].sum()), float(-r[r < 0].sum())
    return gp / gl if gl > 0 else float("inf")
