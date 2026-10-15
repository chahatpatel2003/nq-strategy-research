"""Phase-7 causal top-of-book state vector.

40 registered features (hard cap 40).  Every one is a trailing aggregate closed
at the decision timestamp; nothing reads a quote, a trade or an aggregate stamped
after it.

GRID AND CAUSALITY
    The per-second book cache is expanded onto a dense 1-second grid over the
    09:00-12:00 ET band.  Grid index `i` is the second `[T0+i, T0+i+1)`.  A
    decision stamped `T0+i+1` reads `grid[i]`, so every input second has closed
    before it is used -- the same convention Phases 4-6 used and tested.
    Seconds with no book event carry the last known state forward (causal); the
    event-derived counters are zero there.

    Windows are 1 s, 5 s and 15 s, all trailing and closed at `i`.

ABLATION GROUPS (PHASE7_SPEC.md S12)
    A0  all 40
    A1  quote-only      : drops the 8 features that need trade volume (F8-F10)
    A2  trades+context  : drops the 32 features that need the book (F1-F7, F9, F10)
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from nqr.p2 import features as FT          # frozen upstream, read-only
from nqr.p4 import features4 as F4         # frozen upstream, read-only

TICK = 0.25
NS = 1_000_000_000
EPS = 1e-9

BOOK_BAND_START_ET = "09:00"
BOOK_BAND_END_ET = "12:00"
TRADE_BAND_START_ET = "08:00"        # longer, for ATR14 and its trailing percentile
TRADE_BAND_END_ET = "12:00"
SESSION_START_ET = "09:30"
SESSION_END_ET = "11:30"
DECISION_STEP_S = 5
WINDOWS = (1, 5, 15)
MAX_LOOKBACK_S = 15
ATR_LOOKBACK = 14
ATR_FLOOR = 2.0

FEATURE_NAMES: list[str] = (
    # F1 current BBO state (7)
    ["spread_ticks", "bid_sz", "ask_sz", "bbo_sz_total", "imb",
     "micro_off_ticks", "avg_ord_sz_bbo"] +
    # F2 imbalance persistence (4)
    ["imb_mean_5", "imb_mean_15", "imb_frac_pos_15", "imb_dev_1_15"] +
    # F3 microprice pressure (4)
    ["micro_off_mean_5", "micro_off_mean_15", "micro_press_persist_15",
     "micro_off_change_5"] +
    # F4 quote update intensity (4)
    ["quote_upd_per_s_5", "upd_asym_5", "bid_px_chg_per_s_15", "ask_px_chg_per_s_15"] +
    # F5 top-of-book OFI (3)
    ["ofi_1", "ofi_5", "ofi_15"] +
    # F6 size depletion / replenishment (4)
    ["bid_net_size_flow_5", "ask_net_size_flow_5", "repl_ratio_bid_15",
     "repl_ratio_ask_15"] +
    # F7 price-level step events (2)
    ["bid_step_asym_15", "ask_step_asym_15"] +
    # F8 trade aggression (4)
    ["trd_delta_5", "trd_delta_15", "trd_vol_rel_5", "avg_trd_sz_5"] +
    # F9 replenishment after aggression (2)
    ["ask_repl_per_buy_15", "bid_repl_per_sell_15"] +
    # F10 failure to advance (2)
    ["progress_per_signed_vol_15", "agg_vol_no_progress_15"] +
    # F11 minimal market context (4)
    ["atr1m_ticks", "atr_pct_rank", "secs_since_open", "ret_15s_norm"]
)

FAMILY_OF: dict[str, int] = {}
for _fam, _sl in ((1, slice(0, 7)), (2, slice(7, 11)), (3, slice(11, 15)),
                  (4, slice(15, 19)), (5, slice(19, 22)), (6, slice(22, 26)),
                  (7, slice(26, 28)), (8, slice(28, 32)), (9, slice(32, 34)),
                  (10, slice(34, 36)), (11, slice(36, 40))):
    for _n in FEATURE_NAMES[_sl]:
        FAMILY_OF[_n] = _fam

# features that require trade volume (drop for the quote-only ablation A1)
TRADE_DEPENDENT = [n for n in FEATURE_NAMES if FAMILY_OF[n] in (8, 9, 10)]
# features that require the order book (drop for the trades+context ablation A2)
BOOK_DEPENDENT = [n for n in FEATURE_NAMES if FAMILY_OF[n] in (1, 2, 3, 4, 5, 6, 7, 9, 10)]
ABLATIONS = {
    "A0_full": FEATURE_NAMES,
    "A1_quote_only": [n for n in FEATURE_NAMES if n not in TRADE_DEPENDENT],
    "A2_trades_context": [n for n in FEATURE_NAMES if n not in BOOK_DEPENDENT],
}


# ------------------------------------------------------------ helpers ----
def _roll_sum(a: np.ndarray, w: int) -> np.ndarray:
    c = np.concatenate(([0.0], np.cumsum(a, dtype=np.float64)))
    idx = np.arange(len(a))
    return c[idx + 1] - c[np.maximum(idx - w + 1, 0)]


def _roll_mean(a: np.ndarray, w: int) -> np.ndarray:
    idx = np.arange(len(a))
    n = np.minimum(idx + 1, w)
    return _roll_sum(a, w) / n


def _shift(a: np.ndarray, k: int, fill=np.nan) -> np.ndarray:
    out = np.full(len(a), fill, dtype=float)
    if k <= 0:
        out[:] = a
    elif k < len(a):
        out[k:] = a[:-k]
    return out


def et_sec(d: dt.date, hhmm: str) -> int:
    return F4.et_sec(d, hhmm)


# --------------------------------------------------------- book grid ----
_STATE = ("bid_px", "ask_px", "bid_sz", "ask_sz", "bid_ct", "ask_ct",
          "imb_last", "micro_last", "mid_last", "spread_last")
_FLOW = ("n_events", "imb_mean", "n_imb_pos", "n_imb_neg", "micro_off_mean",
         "spread_mean", "ofi", "b_inc", "b_dec", "a_inc", "a_dec",
         "n_b_up", "n_b_dn", "n_a_up", "n_a_dn", "n_b_upd", "n_a_upd",
         "n_add_b", "n_add_a", "n_can_b", "n_can_a",
         "trd_buy_vol", "trd_sell_vol", "trd_n")


def build_book_grid(day_book: pl.DataFrame, sec0: int, sec1: int,
                    min_rows: int = 600) -> dict | None:
    """Dense 1-second grid of book state and per-second event flow.

    State columns are forward-filled across event-less seconds (causal: the last
    known quote stays live).  Flow columns are zero in those seconds.
    """
    n = sec1 - sec0
    if n <= 0 or day_book.height < min_rows:
        return None
    sec = day_book["sec"].to_numpy().astype(np.int64)
    keep = (sec >= sec0) & (sec < sec1)
    if keep.sum() < min_rows:
        return None
    rel = (sec[keep] - sec0).astype(np.int64)
    g: dict = {"sec0": sec0, "n": n}
    present = np.zeros(n, dtype=bool)
    present[rel] = True
    g["present"] = present
    g["first_present"] = int(np.argmax(present))
    for c in _STATE:
        v = np.full(n, np.nan)
        v[rel] = day_book[c].to_numpy()[keep].astype(float)
        s = pl.Series(v).fill_nan(None).forward_fill().to_numpy()
        v = np.array(s, dtype=float)
        f0 = g["first_present"]
        v[:f0] = v[f0]                        # constant head; never decided on
        g[c] = v
    for c in _FLOW:
        v = np.zeros(n)
        raw = day_book[c].to_numpy()[keep].astype(float)
        v[rel] = np.nan_to_num(raw, nan=0.0)
        g[c] = v
    return g


def decision_indices(g: dict, d: dt.date, start_et: str = SESSION_START_ET,
                     end_et: str = SESSION_END_ET,
                     step_s: int = DECISION_STEP_S) -> np.ndarray:
    dec = np.arange(et_sec(d, start_et), et_sec(d, end_et), step_s, dtype=np.int64)
    idx = dec - g["sec0"] - 1
    return idx[(idx >= 0) & (idx < g["n"])]


def decision_ts_ns(g: dict, idx: np.ndarray) -> np.ndarray:
    return (g["sec0"] + idx + 1).astype(np.int64) * NS


# ---------------------------------------------------- the state matrix ----
def build_state_matrix(g: dict, d: dt.date, atr_by_sec: np.ndarray,
                       atr_rank_by_sec: np.ndarray) -> dict | None:
    """All 40 registered features on the whole second grid."""
    n, sec0 = g["n"], g["sec0"]
    F: dict[str, np.ndarray] = {}
    bs, as_ = g["bid_sz"], g["ask_sz"]
    tot = bs + as_
    mid, micro = g["mid_last"], g["micro_last"]
    spread = g["spread_last"]

    # ---- F1 current BBO state -------------------------------------------
    F["spread_ticks"] = spread / TICK
    F["bid_sz"] = bs
    F["ask_sz"] = as_
    F["bbo_sz_total"] = tot
    F["imb"] = g["imb_last"]
    F["micro_off_ticks"] = (micro - mid) / TICK
    F["avg_ord_sz_bbo"] = tot / np.maximum(g["bid_ct"] + g["ask_ct"], 1.0)

    # ---- F2 imbalance persistence ---------------------------------------
    ev = g["n_events"]
    imb_w = g["imb_mean"] * ev                      # event-weighted sum per second
    for w in (5, 15):
        F[f"imb_mean_{w}"] = _roll_sum(imb_w, w) / (_roll_sum(ev, w) + EPS)
    pos, neg = _roll_sum(g["n_imb_pos"], 15), _roll_sum(g["n_imb_neg"], 15)
    F["imb_frac_pos_15"] = pos / (pos + neg + EPS)
    F["imb_dev_1_15"] = F["imb"] - F["imb_mean_15"]

    # ---- F3 microprice pressure ------------------------------------------
    mo_w = g["micro_off_mean"] * ev
    for w in (5, 15):
        F[f"micro_off_mean_{w}"] = (_roll_sum(mo_w, w) / (_roll_sum(ev, w) + EPS)) / TICK
    sgn = np.sign(g["micro_off_mean"]) * (ev > 0)
    F["micro_press_persist_15"] = _roll_sum(sgn, 15) / (_roll_sum((ev > 0).astype(float), 15) + EPS)
    F["micro_off_change_5"] = F["micro_off_ticks"] - F["micro_off_mean_5"]

    # ---- F4 quote update intensity ---------------------------------------
    bu5, au5 = _roll_sum(g["n_b_upd"], 5), _roll_sum(g["n_a_upd"], 5)
    F["quote_upd_per_s_5"] = (bu5 + au5) / 5.0
    F["upd_asym_5"] = (bu5 - au5) / (bu5 + au5 + EPS)
    F["bid_px_chg_per_s_15"] = (_roll_sum(g["n_b_up"], 15) + _roll_sum(g["n_b_dn"], 15)) / 15.0
    F["ask_px_chg_per_s_15"] = (_roll_sum(g["n_a_up"], 15) + _roll_sum(g["n_a_dn"], 15)) / 15.0

    # ---- F5 OFI, normalised by the trailing liquidity scale ---------------
    scale = _roll_mean(tot, 15) + EPS
    for w in WINDOWS:
        F[f"ofi_{w}"] = _roll_sum(g["ofi"], w) / scale

    # ---- F6 size depletion / replenishment -------------------------------
    F["bid_net_size_flow_5"] = (_roll_sum(g["b_inc"], 5) - _roll_sum(g["b_dec"], 5)) / scale
    F["ask_net_size_flow_5"] = (_roll_sum(g["a_inc"], 5) - _roll_sum(g["a_dec"], 5)) / scale
    F["repl_ratio_bid_15"] = _roll_sum(g["b_inc"], 15) / (_roll_sum(g["b_dec"], 15) + EPS)
    F["repl_ratio_ask_15"] = _roll_sum(g["a_inc"], 15) / (_roll_sum(g["a_dec"], 15) + EPS)

    # ---- F7 price-level step asymmetry ------------------------------------
    bup, bdn = _roll_sum(g["n_b_up"], 15), _roll_sum(g["n_b_dn"], 15)
    aup, adn = _roll_sum(g["n_a_up"], 15), _roll_sum(g["n_a_dn"], 15)
    F["bid_step_asym_15"] = (bup - bdn) / (bup + bdn + EPS)
    F["ask_step_asym_15"] = (aup - adn) / (aup + adn + EPS)

    # ---- F8 trade aggression ----------------------------------------------
    for w in (5, 15):
        b, s = _roll_sum(g["trd_buy_vol"], w), _roll_sum(g["trd_sell_vol"], w)
        F[f"trd_delta_{w}"] = (b - s) / (b + s + EPS)
    v5 = _roll_sum(g["trd_buy_vol"] + g["trd_sell_vol"], 5) / 5.0
    v15 = _roll_mean(g["trd_buy_vol"] + g["trd_sell_vol"], 15)
    F["trd_vol_rel_5"] = v5 / (v15 + EPS)
    F["avg_trd_sz_5"] = (v5 * 5.0) / (_roll_sum(g["trd_n"], 5) + EPS)

    # ---- F9 replenishment after aggression ---------------------------------
    buy15 = _roll_sum(g["trd_buy_vol"], 15)
    sell15 = _roll_sum(g["trd_sell_vol"], 15)
    F["ask_repl_per_buy_15"] = _roll_sum(g["a_inc"], 15) / (buy15 + 1.0)
    F["bid_repl_per_sell_15"] = _roll_sum(g["b_inc"], 15) / (sell15 + 1.0)

    # ---- F10 failure to advance -------------------------------------------
    dmid_ticks = (mid - _shift(mid, 15, fill=mid[0])) / TICK
    signed = buy15 - sell15
    F["progress_per_signed_vol_15"] = dmid_ticks / (np.abs(signed) + 1.0)
    F["agg_vol_no_progress_15"] = (buy15 + sell15) / (np.abs(dmid_ticks) + 1.0)

    # ---- F11 minimal market context ---------------------------------------
    atr = atr_by_sec
    F["atr1m_ticks"] = atr / TICK
    F["atr_pct_rank"] = atr_rank_by_sec
    i_open = et_sec(d, SESSION_START_ET) - sec0 - 1
    F["secs_since_open"] = ((np.arange(n) + 1) - (i_open + 1)).astype(float)
    F["ret_15s_norm"] = (mid - _shift(mid, 15, fill=mid[0])) / (atr + EPS)

    missing = set(FEATURE_NAMES) - set(F)
    extra = set(F) - set(FEATURE_NAMES)
    if missing or extra:
        raise AssertionError(f"feature set mismatch: missing={missing} extra={extra}")
    X = np.column_stack([np.asarray(F[k], dtype=np.float64) for k in FEATURE_NAMES])
    return {"X": X, "i_open": i_open, "mid": mid, "atr": atr}


def microprice(bid_px, ask_px, bid_sz, ask_sz):
    """Standard top-of-book microprice: each price weighted by the OPPOSITE size.

        micro = (ask * bid_sz + bid * ask_sz) / (bid_sz + ask_sz)

    A heavy bid pushes the microprice UP toward the ask.  Unit tested.
    """
    return (ask_px * bid_sz + bid_px * ask_sz) / (bid_sz + ask_sz)


def ofi_event(pb, qb, pa, qa, lpb, lqb, lpa, lqa):
    """Cont-Kukanov-Stoikov top-of-book order-flow imbalance for one transition.

    Mirrors the SQL in `cache7.BOOK_SQL` exactly; both are unit tested against
    the same six transition cases.
    """
    if pb > lpb:
        b = qb
    elif pb == lpb:
        b = qb - lqb
    else:
        b = -lqb
    if pa < lpa:
        a = -qa
    elif pa == lpa:
        a = -(qa - lqa)
    else:
        a = lqa
    return b + a
