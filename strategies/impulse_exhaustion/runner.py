"""Phase-2 day runner: features -> state machine -> tick-resolved trades.

Reuses the Phase-1 execution engine verbatim (`nqr.backtest.engine`), so entry
sequencing, trade-through limit fills, touch-fill stops and MFE/MAE are exactly
the machinery already validated in Phase 1.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np
import polars as pl

from nqr.backtest.engine import TICK, find_entry, resolve, excursions
from nqr.p2 import features as FT
from nqr.p2.absorption import TrailingPercentile
from nqr.p2.statemachine import Candidate, Leg, build_legs, run_direction
from nqr.sessions.calendar import to_utc

NS = 1_000_000_000


@dataclass
class DayGrid:
    trading_date: dt.date
    symbol: str
    sec: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    traded: np.ndarray
    vu: np.ndarray
    buy_cum: np.ndarray
    sell_cum: np.ndarray
    bbo_ask: np.ndarray
    bbo_bid: np.ndarray
    bbo_ask_open: np.ndarray
    bbo_ask_hi: np.ndarray
    bbo_bid_open: np.ndarray
    bbo_bid_lo: np.ndarray
    bbo_bid_sz: np.ndarray
    bbo_ask_sz: np.ndarray
    bbo_events: np.ndarray
    bbo_ask_churn: np.ndarray
    bbo_ask_persist: np.ndarray
    bbo_spread: np.ndarray
    bbo_ok: np.ndarray


def _et_sec(d: dt.date, hhmm: str) -> int:
    h, m = (int(x) for x in hhmm.split(":"))
    return int(to_utc(d, dt.time(h, m)).timestamp())


def build_day_grid(day_ticks: pl.DataFrame, day_bbo: pl.DataFrame, cfg: dict,
                   d: dt.date) -> DayGrid | None:
    """Dense 1-second grid over the cached band, with all causal features."""
    if day_ticks.height == 0:
        return None
    s0 = _et_sec(d, cfg["data"]["band_start_et"])
    s1 = _et_sec(d, cfg["data"]["band_end_et"])
    sb = FT.second_bars(day_ticks)
    grid = FT.densify_seconds(sb, s0, s1)
    minutes = FT.minute_bars_from_seconds(grid)
    atr = FT.causal_atr_minutes(minutes, cfg["volatility"]["atr_minutes"])
    vu = FT.vu_per_second(grid, atr, cfg["volatility"]["vu_floor_points"])

    buy = grid["buy_vol"].to_numpy().astype(np.float64)
    sell = grid["sell_vol"].to_numpy().astype(np.float64)

    # ---- BBO joined onto the same grid, forward filled from the PAST only ----
    n = grid.height
    ask = np.full(n, np.nan); bid = np.full(n, np.nan)
    ask_o = np.full(n, np.nan); ask_h = np.full(n, np.nan)
    bid_o = np.full(n, np.nan); bid_l = np.full(n, np.nan)
    ask_sz = np.zeros(n); bid_sz = np.zeros(n)
    ev = np.zeros(n); churn = np.zeros(n); spr = np.full(n, np.nan)
    persist = np.zeros(n)
    if day_bbo.height:
        b = pl.DataFrame({"sec": grid["sec"]}).join(day_bbo, on="sec", how="left")
        ask = (b["ask_last"].cast(pl.Float64) * TICK).forward_fill().to_numpy()
        bid = (b["bid_last"].cast(pl.Float64) * TICK).forward_fill().to_numpy()
        ask_o = (b["ask_first"].cast(pl.Float64) * TICK).forward_fill().to_numpy()
        ask_h = (b["ask_max"].cast(pl.Float64) * TICK).forward_fill().to_numpy()
        bid_o = (b["bid_first"].cast(pl.Float64) * TICK).forward_fill().to_numpy()
        bid_l = (b["bid_min"].cast(pl.Float64) * TICK).forward_fill().to_numpy()
        ask_sz = b["ask_sz_last"].cast(pl.Float64).forward_fill().fill_null(0).to_numpy()
        bid_sz = b["bid_sz_last"].cast(pl.Float64).forward_fill().fill_null(0).to_numpy()
        ev = b["n_events"].fill_null(0).to_numpy().astype(float)
        # best-price churn WITHIN the second, and persistence ACROSS seconds -
        # both derived from columns that exist; neither looks forward.
        churn = (b["ask_max"].cast(pl.Float64) - b["ask_min"].cast(pl.Float64)) \
            .fill_null(0).to_numpy().astype(float)
        al = b["ask_last"].cast(pl.Float64).forward_fill()
        persist = (al == al.shift(1)).fill_null(False).to_numpy().astype(float)
        spr = b["spread_ticks_mean"].forward_fill().to_numpy()
    ok = np.isfinite(ask) & np.isfinite(bid) & np.isfinite(ask_o) & np.isfinite(bid_o)
    ask = np.where(ok, ask, 0.0); bid = np.where(ok, bid, 0.0)
    ask_o = np.where(ok, ask_o, 0.0); ask_h = np.where(ok, ask_h, 0.0)
    bid_o = np.where(ok, bid_o, 0.0); bid_l = np.where(ok, bid_l, 0.0)

    return DayGrid(d, day_ticks["symbol"][0], grid["sec"].to_numpy(),
                   grid["high"].to_numpy(), grid["low"].to_numpy(),
                   grid["close"].to_numpy(), grid["traded"].to_numpy(),
                   vu, np.cumsum(buy), np.cumsum(sell), ask, bid,
                   ask_o, ask_h, bid_o, bid_l, bid_sz, ask_sz,
                   ev, churn, persist, spr, ok)


def run_day(g: DayGrid, cfg: dict, hist: dict[int, TrailingPercentile],
            entry_stage: str = "FAILED_CONTINUATION") -> tuple[list, list, dict]:
    """Both directions for one day.  `hist` persists ACROSS days (rolling)."""
    theta = np.maximum(cfg["extension"]["dc_theta_vu"] * g.vu,
                       cfg["extension"]["dc_theta_min_points"])
    dcs = FT.directional_changes(g.high, g.low, g.close, theta, g.traded)
    start_idx = int(np.searchsorted(g.sec, _et_sec(g.trading_date,
                                                   cfg["data"]["engine_start_et"])))
    # absorption reference legs must themselves be RTH legs (session-matched)
    rth_lo = _et_sec(g.trading_date, cfg["data"]["signal_start_et"])
    rth_hi = _et_sec(g.trading_date, cfg["data"]["signal_end_et"])
    eligible = (g.sec >= rth_lo) & (g.sec < rth_hi)
    cands, rejects = [], []
    legs_by_dir = {}
    for direction in (-1, 1):
        s = -direction
        legs = build_legs(dcs, s, g.buy_cum, g.sell_cum,
                          g.bbo_ask_open, g.bbo_ask_hi,
                          g.bbo_bid_open, g.bbo_bid_lo, g.bbo_ok, hist[direction],
                          eligible)
        legs_by_dir[direction] = legs
        c, r = run_direction(direction, cfg, high=g.high, low=g.low, traded=g.traded,
                             vu=g.vu, sec=g.sec, legs_all=legs,
                             trading_date=g.trading_date, symbol=g.symbol,
                             engine_start_idx=start_idx, entry_stage=entry_stage)
        cands.extend(c); rejects.extend(r)
    cands.sort(key=lambda c: (c.signal_idx, c.direction))
    diag = {"n_dc": len(dcs), "n_legs_short": len(legs_by_dir[-1]),
            "n_legs_long": len(legs_by_dir[1])}
    return cands, rejects, diag


def simulate_day(cands: list[Candidate], g: DayGrid, ts: np.ndarray, px: np.ndarray,
                 cfg: dict, primary_only: bool = False) -> list[dict]:
    """Turn signals into tick-resolved trades under one-position-at-a-time."""
    E, S, T, C = cfg["entry"], cfg["stop"], cfg["targets"], cfg["costs"]
    lat = int(E["latency_ms"]) * 1_000_000
    max_wait = int(E["max_wait_ms"]) * 1_000_000
    sig_lo = _et_sec(g.trading_date, cfg["data"]["signal_start_et"])
    sig_hi = _et_sec(g.trading_date, cfg["data"]["signal_end_et"])
    hard = _et_sec(g.trading_date, cfg["targets"]["hard_exit_et"]) * NS
    rows: list[dict] = []
    busy_until = -1

    for c in cands:
        i = c.signal_idx
        sig_ns = int((g.sec[i] + 1) * NS)          # the 1-second bar CLOSES at sec+1
        rec = _base_row(c, g, sig_ns)
        if not (sig_lo <= g.sec[i] < sig_hi):
            rec["status"], rec["skip_reason"] = "SKIPPED", "OUTSIDE_RTH"
            rows.append(rec); continue
        if sig_ns < busy_until:
            rec["status"], rec["skip_reason"] = "SKIPPED", "SKIPPED_OVERLAP"
            rows.append(rec); continue
        ent = find_entry(ts, px, sig_ns + lat, max_wait)
        if ent is None:
            rec["status"], rec["skip_reason"] = "SKIPPED", "NO_ENTRY_PRINT"
            rows.append(rec); continue
        eidx, ets, epx = ent
        # the window is defined on when the ENTRY becomes executable, so a signal
        # that only fills after the RTH cutoff is not traded at all
        if ets // NS >= sig_hi:
            rec["status"], rec["skip_reason"] = "SKIPPED", "OUTSIDE_RTH"
            rec.update(entry_ns=ets, entry_price=epx)
            rows.append(rec); continue
        stop = c.ext_price + (S["ticks"] * TICK) * (-c.direction)
        r = (epx - stop) * c.direction
        rec.update(entry_ns=ets, entry_price=epx, stop=stop, r_points=r,
                   entry_slippage=(epx - float(g.close[i])) * c.direction)
        if r < S["min_r_points"] or r < S["min_r_vu"] * c.vu:
            rec["status"], rec["skip_reason"] = "SKIPPED", "R_TOO_SMALL"
            rows.append(rec); continue
        if r > S["max_r_vu"] * c.vu:
            rec["status"], rec["skip_reason"] = "SKIPPED", "R_TOO_LARGE"
            rows.append(rec); continue
        end_ns = min(hard, ets + int(T["max_hold_seconds"]) * NS)
        mults = [T["primary_r"]] if primary_only else [T["primary_r"]] + list(T["diagnostic_r"])
        for mult in mults:
            tag = "r" + str(mult).replace(".", "p")
            tp = epx + c.direction * mult * r
            f = resolve(ts, px, eidx, end_ns, c.direction, tp, stop)
            mfe, mae = excursions(ts, px, eidx, f.ts_ns, c.direction, epx)
            pts = (f.price - epx) * c.direction
            rec[f"{tag}_target"] = tp
            rec[f"{tag}_outcome"] = f.kind
            rec[f"{tag}_exit_ns"] = f.ts_ns
            rec[f"{tag}_exit_price"] = f.price
            rec[f"{tag}_points"] = pts
            rec[f"{tag}_R"] = pts / r if r > 0 else 0.0
            rec[f"{tag}_mfe"] = mfe
            rec[f"{tag}_mae"] = mae
            rec[f"{tag}_hold_s"] = (f.ts_ns - ets) / NS
            for fr in C["round_trip_points_grid"]:
                rec[f"{tag}_net_{str(fr).replace('.', 'p')}"] = pts - fr
        rec["status"], rec["skip_reason"] = "ACCEPTED", None
        busy_until = rec["r1p0_exit_ns"]
        rows.append(rec)
    return rows


def _base_row(c: Candidate, g: DayGrid, sig_ns: int) -> dict:
    L = c.legs
    last = L[-1] if L else None
    row = dict(trading_date=c.trading_date, symbol=c.symbol, direction=c.direction,
               side="LONG" if c.direction > 0 else "SHORT",
               imp_start_ns=int(g.sec[c.imp_start_idx]) * NS,
               imp_end_ns=int(g.sec[c.imp_end_idx]) * NS,
               imp_seconds=c.imp_seconds, imp_displacement=c.imp_displacement,
               vu=c.vu, imp_disp_vu=c.imp_displacement / c.vu if c.vu else None,
               ext_price=c.ext_price, ext_ns=int(g.sec[c.ext_idx]) * NS,
               arm_ns=int(g.sec[c.arm_idx]) * NS, signal_ns=sig_ns,
               signal_price=float(g.close[c.signal_idx]),
               absorption=last.absorption if last else None,
               absorption_pct=last.absorption_pct if last else None,
               n_legs=len(L),
               bbo_spread_ticks=float(g.bbo_spread[c.ext_idx]) if np.isfinite(g.bbo_spread[c.ext_idx]) else None,
               bbo_imbalance=_imb(g, c.ext_idx),
               bbo_ask_churn_ticks=float(g.bbo_ask_churn[c.ext_idx]),
               bbo_ask_persist=float(g.bbo_ask_persist[c.ext_idx]),
               bbo_events=float(g.bbo_events[c.ext_idx]),
               entry_ns=None, entry_price=None, stop=None, r_points=None,
               entry_slippage=None, status=None, skip_reason=None)
    for k, lg in enumerate(L, start=1):
        row[f"leg{k}_ext_ns"] = int(g.sec[lg.ext_idx]) * NS
        row[f"leg{k}_conf_ns"] = int(g.sec[lg.conf_idx]) * NS
        row[f"leg{k}_ext_price"] = lg.ext_price
        row[f"leg{k}_start_price"] = lg.start_price
        row[f"leg{k}_agg_vol"] = lg.agg_vol
        row[f"leg{k}_progress"] = lg.progress
        row[f"leg{k}_efficiency"] = lg.efficiency
        row[f"leg{k}_bbo_adv_ticks"] = lg.bbo_advance_ticks
        row[f"leg{k}_absorption"] = lg.absorption
    row["agg_drop_ratio"] = (L[-1].agg_vol / L[0].agg_vol) if L and L[0].agg_vol else None
    row["eff_drop_ratio"] = (L[-1].efficiency / L[0].efficiency) if L and L[0].efficiency else None
    return row


def _imb(g: DayGrid, i: int) -> float | None:
    tot = g.bbo_bid_sz[i] + g.bbo_ask_sz[i]
    return float((g.bbo_bid_sz[i] - g.bbo_ask_sz[i]) / tot) if tot > 0 else None
