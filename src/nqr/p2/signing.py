"""Trade aggressor classification and its verification.

Databento's GLBX.MDP3 `trades` schema carries a native `side` field.  Phase 2
does NOT assume what it means.  ``verify_native_side`` reconstructs the causal
top of book from MBP-1 and measures, on unambiguous trades only, whether

    side == 'B'  <=>  trade printed at or above the prevailing ASK
    side == 'A'  <=>  trade printed at or below the prevailing BID

CAUSALITY.  For a trade at ``ts_event = t`` the BBO used is the last MBP-1
top-of-book state with ``ts_event < t`` - STRICTLY before.  A book update
stamped at the same nanosecond as the trade is the book *after* that trade (or
is ordering-ambiguous with it), so it is excluded.  This can only make the quote
staler, never fresher, and it makes quote lookahead structurally impossible.
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

TICK = 0.25

BUY, SELL, UNKNOWN = 1, -1, 0


def causal_bbo_for_trades(trade_ts: np.ndarray, quote_ts: np.ndarray,
                          bid_t: np.ndarray, ask_t: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Latest quote STRICTLY before each trade.  -1 where no quote exists yet."""
    idx = np.searchsorted(quote_ts, trade_ts, side="left") - 1
    ok = idx >= 0
    b = np.where(ok, bid_t[np.clip(idx, 0, None)], -1)
    a = np.where(ok, ask_t[np.clip(idx, 0, None)], -1)
    return b, a


def classify_from_bbo(px_t: np.ndarray, bid_t: np.ndarray, ask_t: np.ndarray) -> np.ndarray:
    """Lee-Ready style quote rule, no tick-rule fallback (inside stays UNKNOWN)."""
    out = np.zeros(len(px_t), dtype=np.int8)
    have = (bid_t >= 0) & (ask_t >= 0)
    out[have & (px_t >= ask_t)] = BUY
    out[have & (px_t <= bid_t)] = SELL
    return out


def verify_native_side(ticks: pl.DataFrame, quotes: pl.DataFrame) -> dict:
    """Compare the native `side_raw` against the causal quote rule.

    ``quotes`` needs columns ts_ns, bid_t, ask_t sorted by ts_ns.
    """
    if ticks.height == 0 or quotes.height == 0:
        return {"n": 0}
    tt = ticks["ts_ns"].to_numpy()
    px = ticks["px_ticks"].to_numpy().astype(np.int64)
    native = ticks["side_raw"].to_numpy().astype(np.int8)
    qt = quotes["ts_ns"].to_numpy()
    qb = quotes["bid_t"].to_numpy().astype(np.int64)
    qa = quotes["ask_t"].to_numpy().astype(np.int64)
    b, a = causal_bbo_for_trades(tt, qt, qb, qa)
    rule = classify_from_bbo(px, b, a)

    have = (b >= 0) & (a >= 0)
    unamb = have & (rule != UNKNOWN)
    agree = unamb & (rule == native)
    disagree = unamb & (rule != native) & (native != UNKNOWN)
    native_unknown = unamb & (native == UNKNOWN)
    inside = have & (rule == UNKNOWN)
    return {
        "n": int(len(tt)),
        "n_with_quote": int(have.sum()),
        "n_unambiguous": int(unamb.sum()),
        "n_agree": int(agree.sum()),
        "n_disagree": int(disagree.sum()),
        "n_native_unknown_on_unambiguous": int(native_unknown.sum()),
        "agreement_rate": float(agree.sum() / max(unamb.sum(), 1)),
        "n_inside_spread": int(inside.sum()),
        "inside_spread_frac": float(inside.sum() / max(have.sum(), 1)),
        "native_unknown_frac": float((native == UNKNOWN).mean()),
        "native_buy_frac": float((native == BUY).mean()),
        "native_sell_frac": float((native == SELL).mean()),
    }
