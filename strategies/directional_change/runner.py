"""Phase-3 day runner: ticks -> causal DC events -> family signals -> trades."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np
import polars as pl

from nqr.backtest.engine import TICK, find_entry
from nqr.p2 import features as FT           # frozen, read-only reuse
from nqr.p3.dc_engine import detect_events
from nqr.p3.fastpass import excursions_fast, resolve_fast
from nqr.p3.strategies import FAMILIES, build_signals
from nqr.sessions.calendar import to_utc

NS = 1_000_000_000


@dataclass
class DayPath:
    trading_date: dt.date
    symbol: str
    ts: np.ndarray            # FULL tick stream (for entries and first passage)
    px_t: np.ndarray          # ... in integer ticks
    c_ts: np.ndarray          # COMPRESSED price-change path
    c_px: np.ndarray          # ... in points
    c_idx: np.ndarray         # original index of each compressed point
    c_theta: np.ndarray
    c_vu: np.ndarray
    c_cum_trades: np.ndarray
    c_cum_vol: np.ndarray
    engine_start: int         # index on the compressed path


def et_sec(d: dt.date, hhmm: str) -> int:
    h, m = (int(x) for x in hhmm.split(":"))
    return int(to_utc(d, dt.time(h, m)).timestamp())


def build_day_path(day: pl.DataFrame, cfg: dict, d: dt.date) -> DayPath | None:
    """Compress the tick path and attach a causal VU / theta to every point.

    Compression keeps the FIRST print at each new price.  That is exact for the
    DC engine - running extremes and threshold crossings depend only on the
    sequence of distinct prices - and it keeps the EARLIEST timestamp at which
    each price was reached, so confirmations are never late.
    """
    if day.height < 100:
        return None
    ts = day["ts_ns"].to_numpy()
    px_t = day["px_ticks"].to_numpy().astype(np.int64)
    size = day["size"].to_numpy().astype(np.float64)

    # ---- causal VU: ATR14 of COMPLETED 1-minute bars (frozen Phase-2 code) ----
    minute = ts // (60 * NS)
    mdf = (pl.DataFrame({"minute": minute, "px": px_t.astype(np.float64) * TICK})
             .group_by("minute")
             .agg(pl.col("px").first().alias("open"), pl.col("px").max().alias("high"),
                  pl.col("px").min().alias("low"), pl.col("px").last().alias("close"))
             .sort("minute"))
    atr = FT.causal_atr_minutes(mdf, cfg["volatility"]["atr_minutes"])
    amap = dict(zip(atr["minute"].to_list(), atr["atr_prev"].to_list()))
    vu_full = np.array([amap.get(int(m), np.nan) for m in minute], dtype=float)
    vu_full = np.maximum(vu_full, cfg["volatility"]["vu_floor_points"])
    theta_full = np.maximum(cfg["event"]["theta_vu"] * vu_full,
                            cfg["event"]["theta_floor_points"])

    keep = np.empty(len(px_t), dtype=bool)
    keep[0] = True
    np.not_equal(px_t[1:], px_t[:-1], out=keep[1:])
    ci = np.flatnonzero(keep)

    cum_tr = np.arange(1, len(px_t) + 1, dtype=np.int64)
    cum_vo = np.cumsum(size)

    first_ok = np.flatnonzero(np.isfinite(vu_full[ci]))
    if first_ok.size == 0:
        return None
    eng_lo = et_sec(d, cfg["data"]["engine_start_et"]) * NS
    start = max(int(first_ok[0]), int(np.searchsorted(ts[ci], eng_lo)))
    if start >= len(ci) - 2:
        return None

    return DayPath(d, day["symbol"][0], ts, px_t,
                   ts[ci], px_t[ci].astype(np.float64) * TICK, ci,
                   theta_full[ci], vu_full[ci], cum_tr[ci], cum_vo[ci], start)


def run_day(p: DayPath, cfg: dict):
    evs = detect_events(p.c_px, p.c_ts, p.c_theta, p.c_vu,
                        p.c_cum_trades, p.c_cum_vol, start_i=p.engine_start)
    sigs = build_signals(evs, p.c_px, p.c_ts, cfg)
    return evs, sigs


def simulate(sigs: list, p: DayPath, cfg: dict) -> list[dict]:
    """One family's book: one open position at a time, tick-exact first passage."""
    E, R, T, C = cfg["entry"], cfg["risk"], cfg["targets"], cfg["costs"]
    lat = int(E["latency_ms"]) * 1_000_000
    max_wait = int(E["max_wait_ms"]) * 1_000_000
    sig_lo = et_sec(p.trading_date, cfg["data"]["signal_start_et"])
    sig_hi = et_sec(p.trading_date, cfg["data"]["signal_end_et"])
    hard = et_sec(p.trading_date, T["hard_exit_et"]) * NS
    tags = target_tags(cfg)
    fricts = list(C["round_trip_points_grid"])
    rows: list[dict] = []
    busy_until = -1

    for s in sorted(sigs, key=lambda x: (x.signal_ts, x.event_seq)):
        rec = _row(s, p, tags, fricts)
        if not (sig_lo <= s.signal_ts // NS < sig_hi):
            rec["status"], rec["skip_reason"] = "SKIPPED", "OUTSIDE_RTH"
            rows.append(rec); continue
        if s.signal_ts < busy_until:
            rec["status"], rec["skip_reason"] = "SKIPPED", "SKIPPED_OVERLAP"
            rows.append(rec); continue
        r = float(s.theta)
        if not (R["min_r_points"] <= r <= R["max_r_points"]):
            rec["status"], rec["skip_reason"] = "SKIPPED", "R_OUT_OF_RANGE"
            rows.append(rec); continue
        ent = find_entry(p.ts, p.px_t, s.signal_ts + lat, max_wait)
        if ent is None:
            rec["status"], rec["skip_reason"] = "SKIPPED", "NO_ENTRY_PRINT"
            rows.append(rec); continue
        eidx, ets, epx = ent
        if ets // NS >= sig_hi:
            rec["status"], rec["skip_reason"] = "SKIPPED", "OUTSIDE_RTH"
            rec.update(entry_ns=ets, entry_price=epx)
            rows.append(rec); continue
        d = s.direction
        stop = epx - d * r
        # Phase-1/2 convention: POSITIVE slippage is ADVERSE.
        # long  -> paying more than the reference is adverse
        # short -> selling below the reference is adverse
        rec.update(entry_ns=ets, entry_price=epx, stop=stop, r_points=r,
                   entry_slippage=(epx - s.ref_price) * d,
                   signal_to_entry_pts=(epx - s.signal_price) * d)
        end_ns = min(hard, ets + int(T["max_hold_seconds"]) * NS)
        for mult in [T["primary_r"]] + list(T["diagnostic_r"]):
            tag = "r" + str(mult).replace(".", "p")
            tp = epx + d * mult * r
            f = resolve_fast(p.ts, p.px_t, eidx, end_ns, d, tp, stop)
            mfe, mae = excursions_fast(p.ts, p.px_t, eidx, f.ts_ns, d, epx)
            pts = (f.price - epx) * d
            rec[f"{tag}_outcome"] = f.kind
            rec[f"{tag}_exit_ns"] = f.ts_ns
            rec[f"{tag}_exit_price"] = f.price
            rec[f"{tag}_points"] = pts
            rec[f"{tag}_R"] = pts / r
            rec[f"{tag}_mfe"] = mfe
            rec[f"{tag}_mae"] = mae
            rec[f"{tag}_hold_s"] = (f.ts_ns - ets) / NS
            for fr in C["round_trip_points_grid"]:
                rec[f"{tag}_net_{str(fr).replace('.', 'p')}"] = pts - fr
        rec["status"], rec["skip_reason"] = "ACCEPTED", None
        busy_until = rec["r1p0_exit_ns"]
        rows.append(rec)
    return rows


def target_tags(cfg: dict) -> list[str]:
    T = cfg["targets"]
    return ["r" + str(m).replace(".", "p")
            for m in [T["primary_r"]] + list(T["diagnostic_r"])]


def _row(s, p: DayPath, tags: list[str], fricts: list[float]) -> dict:
    """Every row carries an IDENTICAL key set so the parquet schema is stable and
    polars never has to infer a type from an all-null prefix of skipped rows."""
    row = dict(
        trading_date=p.trading_date, symbol=p.symbol, family=s.family,
        event_seq=s.event_seq, direction=s.direction,
        side="LONG" if s.direction > 0 else "SHORT",
        theta=s.theta, vu=s.vu,
        ext_ts=s.ext_ts, ext_price=s.ext_price,
        conf_ts=s.conf_ts, conf_price=s.conf_price, ref_price=s.ref_price,
        signal_ns=s.signal_ts, signal_price=s.signal_price,
        dc_magnitude=s.dc_magnitude, total_move=s.total_move,
        prev_overshoot=s.prev_overshoot, prev_overshoot_ratio=s.prev_overshoot_ratio,
        event_ns=s.event_ns, n_trades=s.n_trades, volume=s.volume,
        velocity=s.velocity, prev_direction=s.prev_direction,
        entry_ns=None, entry_price=None, stop=None, r_points=None,
        entry_slippage=None, signal_to_entry_pts=None,
        status=None, skip_reason=None)
    for t in tags:
        row[f"{t}_outcome"] = None
        row[f"{t}_exit_ns"] = None
        row[f"{t}_exit_price"] = None
        row[f"{t}_points"] = None
        row[f"{t}_R"] = None
        row[f"{t}_mfe"] = None
        row[f"{t}_mae"] = None
        row[f"{t}_hold_s"] = None
        for fr in fricts:
            row[f"{t}_net_{str(fr).replace('.', 'p')}"] = None
    return row


P3_SCHEMA_OVERRIDES = {
    "entry_ns": "Int64", "entry_price": "Float64", "stop": "Float64",
    "r_points": "Float64", "entry_slippage": "Float64",
    "signal_to_entry_pts": "Float64", "skip_reason": "String",
}
