"""Phase-4 causal state vector.

Every feature is a trailing aggregate closed at the decision timestamp `t`.
Nothing here reads a price, a trade or an aggregate stamped after `t`.

Implementation note on causality: features are computed on a dense 1-second
grid where index `i` corresponds to the second `[T0+i, T0+i+1)`.  A window
"ending at i" therefore covers seconds `i-h+1 .. i`, all of which have CLOSED.
Decision timestamps are taken at the START of second `i+1`, i.e. the engine
acts on `grid[i]` at wall-clock `T0+i+1`, so even the second containing the
decision has finished before its own features are used.

RECOVERY NOTE (see reports/PHASE4_START_INTEGRITY.md)
-----------------------------------------------------
The first write of this module was cut off mid-file by the macOS Desktop
permission failure.  What survived was the docstring, `FEATURE_NAMES`, the
rolling helpers, `build_grid` and `causal_atr`; the state-matrix builder was
missing entirely.  The module was completed from `FEATURE_REGISTRY.md`, which
was already on disk and is unchanged.  Two defects in the surviving fragment
were repaired, both pure implementation bugs, neither a change of strategy:

  1. `build_grid` seeded `high`/`low` with NaN and then used
     `np.maximum.at` / `np.minimum.at`.  `np.maximum(nan, x) is nan`, so every
     second's high and low would have come out NaN.  Now seeded with -/+inf.
  2. `open`/`close` were assigned with duplicate fancy indices and relied on
     "last write wins", which NumPy does not guarantee.  Now resolved with an
     explicit first/last-of-run index, which is deterministic.

The registered feature universe is untouched: 55 features, exactly the names
and formulas in FEATURE_REGISTRY.md.
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from nqr.p2 import features as FT          # frozen upstream, read-only
from nqr.p3.dc_engine import detect_events  # frozen upstream, read-only
from nqr.sessions.calendar import to_utc    # frozen upstream, read-only

TICK = 0.25
NS = 1_000_000_000
EPS = 1e-9

RET_HORIZONS = (5, 15, 30, 60, 120, 300)

# ---- fixed clock / band (SEARCH_BUDGET.md: exactly one decision clock) ----
BAND_START_ET = "08:00"        # warm-up head room, matches the p2 tick cache
BAND_END_ET = "16:15"
SESSION_START_ET = "09:30"     # official Phase-4 session start
SESSION_END_ET = "11:30"       # official Phase-4 session end
DIAG_END_ET = "16:00"          # extended diagnostic window end
DECISION_STEP_S = 5
OR_END_ET = "10:00"            # opening range completes here

ATR_LOOKBACK = 14
ATR_FLOOR = 2.0                # points, == Phase-2/3 VU floor
R_ATR_MULT = 0.50
R_FLOOR = 1.0
R_CAP = 25.0
THETA_VU = 0.50                # frozen Phase-3 DC threshold
THETA_FLOOR = 1.00
PCT_RANK_MINUTES = 120
MAX_LOOKBACK_S = 1800          # longest second-grid window used by any feature

FEATURE_NAMES: list[str] = (
    [f"ret_norm_{h}" for h in RET_HORIZONS] + ["eff_60", "eff_300"] +
    ["vel_15_norm", "vel_60_norm", "vel_ratio_15_60", "accel_15_60", "persist_60"] +
    ["atr1m", "rv_60_norm", "rv_300_norm", "vol_ratio_60_300", "range_60_norm",
     "atr_pct_rank", "vol_expansion"] +
    ["dist_high_300_norm", "dist_low_300_norm", "dist_high_1800_norm",
     "dist_low_1800_norm", "n_new_highs_300", "n_new_lows_300", "pullback_depth",
     "secs_since_high_300", "secs_since_low_300"] +
    ["trades_per_s_60", "vol_per_s_60", "avg_trade_size_60", "max_trade_size_60_rel",
     "intensity_ratio_60_300", "volume_ratio_60_300"] +
    ["delta_60_norm", "delta_300_norm", "delta_per_vol_60", "delta_per_vol_300",
     "cum_delta_norm", "delta_accel"] +
    ["secs_since_open", "is_second_hour", "weekday"] +
    ["dist_open_norm", "dist_vwap_norm", "dist_pdh_norm", "dist_pdl_norm",
     "dist_or30_hi_norm", "dist_or30_lo_norm"] +
    ["last_dc_dir", "last_dc_mag_norm", "last_overshoot_norm", "prev2_dc_dir",
     "secs_since_last_dc"]
)

FAMILY_OF = {}
for _fam, _names in (
    (1, FEATURE_NAMES[0:8]), (2, FEATURE_NAMES[8:13]), (3, FEATURE_NAMES[13:20]),
    (4, FEATURE_NAMES[20:29]), (5, FEATURE_NAMES[29:35]), (6, FEATURE_NAMES[35:41]),
    (7, FEATURE_NAMES[41:44]), (8, FEATURE_NAMES[44:50]), (9, FEATURE_NAMES[50:55]),
):
    for _n in _names:
        FAMILY_OF[_n] = _fam


# ------------------------------------------------------------ helpers ----
def _roll_sum(a: np.ndarray, w: int) -> np.ndarray:
    """Trailing sum over the w samples ending at (and including) each index."""
    c = np.concatenate(([0.0], np.cumsum(a, dtype=np.float64)))
    idx = np.arange(len(a))
    lo = np.maximum(idx - w + 1, 0)
    return c[idx + 1] - c[lo]


def _roll_max(a: np.ndarray, w: int) -> np.ndarray:
    return pl.Series(a).rolling_max(window_size=w, min_samples=1).to_numpy()


def _roll_min(a: np.ndarray, w: int) -> np.ndarray:
    return pl.Series(a).rolling_min(window_size=w, min_samples=1).to_numpy()


def _shift(a: np.ndarray, k: int, fill=np.nan) -> np.ndarray:
    out = np.full(len(a), fill, dtype=float)
    if k <= 0:
        out[:] = a
    elif k < len(a):
        out[k:] = a[:-k]
    return out


def _secs_since_extreme(a: np.ndarray, w: int, want_max: bool) -> np.ndarray:
    """Seconds since the trailing-window extreme was last set (0 = right now)."""
    ext = _roll_max(a, w) if want_max else _roll_min(a, w)
    at_ext = np.isclose(a, ext)
    idx = np.arange(len(a))
    last = np.where(at_ext, idx, -1)
    last = np.maximum.accumulate(last)
    return np.where(last >= 0, idx - last, float(w)).astype(float)


def _safe_div(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return a / (np.abs(b) + EPS) * np.sign(np.where(b == 0, 1.0, b))


def et_sec(d: dt.date, hhmm: str) -> int:
    """Epoch second of an ET wall-clock time on Globex trading date ``d``."""
    h, m = (int(x) for x in hhmm.split(":"))
    return int(to_utc(d, dt.time(h, m)).timestamp())


# ------------------------------------------------------------- grid ----
def build_grid(day: pl.DataFrame, band_start_s: int, band_end_s: int) -> dict | None:
    """Dense 1-second grid of trade aggregates for one trading day.

    ``day`` must be sorted by (ts_ns, row_seq) and hold a single front contract.
    """
    if day.height < 500:
        return None
    ts = day["ts_ns"].to_numpy()
    px_t = day["px_ticks"].to_numpy().astype(np.int64)
    size = day["size"].to_numpy().astype(np.float64)
    side = day["side_raw"].to_numpy().astype(np.int64) if "side_raw" in day.columns \
        else np.zeros(len(ts), dtype=np.int64)

    sec = ts // NS
    n = band_end_s - band_start_s
    if n <= 0:
        return None
    rel = (sec - band_start_s).astype(np.int64)
    keep = (rel >= 0) & (rel < n)
    if keep.sum() < 500:
        return None
    rel, px_k, sz_k, sd_k = rel[keep], px_t[keep], size[keep], side[keep]
    ts_k = ts[keep]
    pxp = px_k * TICK

    # -inf / +inf seeds: np.maximum(nan, x) is nan, so a NaN seed would wipe
    # out every high/low.  See the recovery note in the module docstring.
    high = np.full(n, -np.inf)
    low = np.full(n, np.inf)
    np.maximum.at(high, rel, pxp)
    np.minimum.at(low, rel, pxp)

    # first / last print of each second, resolved deterministically (rel is
    # non-decreasing because the tick frame is sorted by (ts_ns, row_seq)).
    newrun = np.empty(len(rel), dtype=bool)
    newrun[0] = True
    np.not_equal(rel[1:], rel[:-1], out=newrun[1:])
    first_i = np.flatnonzero(newrun)
    last_i = np.concatenate((first_i[1:] - 1, [len(rel) - 1]))
    openp = np.full(n, np.nan)
    close = np.full(n, np.nan)
    openp[rel[first_i]] = pxp[first_i]
    close[rel[last_i]] = pxp[last_i]

    vol = np.zeros(n); cnt = np.zeros(n); pxvol = np.zeros(n)
    buy = np.zeros(n); sell = np.zeros(n); mx = np.zeros(n)
    np.add.at(vol, rel, sz_k)
    np.add.at(cnt, rel, 1.0)
    np.add.at(pxvol, rel, pxp * sz_k)
    np.add.at(buy, rel, np.where(sd_k > 0, sz_k, 0.0))
    np.add.at(sell, rel, np.where(sd_k < 0, sz_k, 0.0))
    np.maximum.at(mx, rel, sz_k)

    traded = cnt > 0
    f0 = int(np.argmax(traded))                     # first traded second
    # NOTE: polars treats np.nan as a VALUE, not a null, so the NaN seeds must be
    # converted to nulls before forward_fill or the fill is a silent no-op.
    c = np.array(pl.Series(close).fill_nan(None).forward_fill().to_numpy(), dtype=float)
    # Constant-fill the pre-first-print head so that cumulative sums do not
    # propagate NaN across the whole day.  Nothing may be decided there: the
    # caller asserts every decision index is >= f0 + MAX_LOOKBACK_S.
    c[:f0] = c[f0]
    high = np.where(traded, high, c)
    low = np.where(traded, low, c)
    openp = np.where(traded, openp, c)
    return {"sec0": band_start_s, "n": n, "close": c, "high": high, "low": low,
            "open": openp, "vol": vol, "cnt": cnt, "buy": buy, "sell": sell,
            "pxvol": pxvol, "maxsz": mx, "traded": traded, "first_traded": f0,
            "ts": ts_k, "px_t": px_k, "size": sz_k, "side": sd_k}


def _minute_bars(g: dict) -> tuple[np.ndarray, pl.DataFrame]:
    """(absolute minute per grid second, completed 1-minute OHLC of traded minutes)."""
    minute = ((np.arange(g["n"]) + g["sec0"]) // 60)
    m = (pl.DataFrame({"minute": minute, "o": g["open"], "h": g["high"],
                       "l": g["low"], "c": g["close"], "tr": g["traded"]})
         .filter(pl.col("tr"))
         .group_by("minute")
         .agg(pl.col("o").first().alias("open"), pl.col("h").max().alias("high"),
              pl.col("l").min().alias("low"), pl.col("c").last().alias("close"))
         .sort("minute"))
    return minute, m


def causal_atr(g: dict, lookback: int = ATR_LOOKBACK,
               floor: float = ATR_FLOOR) -> tuple[np.ndarray, pl.DataFrame]:
    """ATR14 of COMPLETED 1-minute bars, broadcast onto the second grid.

    Untraded minutes carry the last published ATR forward, which uses only
    past completed minutes and never a future one.
    """
    minute, m = _minute_bars(g)
    if m.height < lookback + 2:
        return np.full(g["n"], np.nan), pl.DataFrame(
            {"minute": [], "atr_prev": []}, schema={"minute": pl.Int64, "atr_prev": pl.Float64})
    atr = FT.causal_atr_minutes(m, lookback)
    grid_min = pl.DataFrame({"minute": np.arange(int(minute[0]), int(minute[-1]) + 1)})
    filled = (grid_min.join(atr, on="minute", how="left").sort("minute")
              .with_columns(pl.col("atr_prev").forward_fill()))
    amap = dict(zip(filled["minute"].to_list(), filled["atr_prev"].to_list()))
    v = np.array([amap.get(int(x), np.nan) for x in minute], dtype=float)
    return np.maximum(v, floor), atr


def r_from_atr(atr: np.ndarray) -> np.ndarray:
    """SEARCH_BUDGET.md: R = 0.50 x ATR14(completed 1-min), floor 1.0, cap 25.0."""
    return np.clip(R_ATR_MULT * atr, R_FLOOR, R_CAP)


def _atr_pct_rank(minute: np.ndarray, atr: pl.DataFrame, n: int) -> np.ndarray:
    """Trailing within-day percentile of atr1m over the strictly prior 120 min.

    Computed at MINUTE resolution (atr1m is constant inside a minute) and then
    broadcast, which is both exact and cheap.
    """
    out = np.full(n, np.nan)
    if atr.height == 0:
        return out
    mins = atr["minute"].to_numpy().astype(np.int64)
    vals = atr["atr_prev"].to_numpy().astype(float)
    rank = np.full(len(mins), np.nan)
    for k in range(len(mins)):
        if not np.isfinite(vals[k]):
            continue
        lo = np.searchsorted(mins, mins[k] - PCT_RANK_MINUTES, side="left")
        prior = vals[lo:k]
        prior = prior[np.isfinite(prior)]
        if prior.size == 0:
            continue
        rank[k] = float((prior <= vals[k]).mean())
    rmap = dict(zip(mins.tolist(), rank.tolist()))
    # carry the last published rank forward across untraded minutes (causal)
    last = np.nan
    per_min = {}
    for mm in range(int(minute[0]), int(minute[-1]) + 1):
        if mm in rmap and np.isfinite(rmap[mm]):
            last = rmap[mm]
        per_min[mm] = last
    return np.array([per_min.get(int(x), np.nan) for x in minute], dtype=float)


# --------------------------------------------------- DC event context ----
def _dc_events(g: dict, atr_sec: np.ndarray) -> list:
    """Confirmed DC events for the day, from the FROZEN Phase-3 engine.

    The compressed price path and the theta schedule are rebuilt exactly as
    `strategies/directional_change/runner.build_day_path` does; equivalence is
    asserted by tests/test_p4_features.py::
    test_dc_context_matches_the_frozen_phase3_runner.
    """
    ts, px_t = g["ts"], g["px_t"]
    n = g["n"]
    sec_of = (ts // NS - g["sec0"]).astype(np.int64)
    vu_tick = atr_sec[np.clip(sec_of, 0, n - 1)]
    theta_tick = np.maximum(THETA_VU * vu_tick, THETA_FLOOR)

    keep = np.empty(len(px_t), dtype=bool)
    keep[0] = True
    np.not_equal(px_t[1:], px_t[:-1], out=keep[1:])
    ci = np.flatnonzero(keep)
    if len(ci) < 4:
        return []
    cum_tr = np.arange(1, len(px_t) + 1, dtype=np.int64)[ci]
    cum_vo = np.cumsum(g["size"])[ci]
    fin = np.flatnonzero(np.isfinite(vu_tick[ci]))
    if fin.size == 0:
        return []
    return detect_events(px_t[ci].astype(np.float64) * TICK, ts[ci], theta_tick[ci],
                         vu_tick[ci], cum_tr, cum_vo, start_i=int(fin[0]))


_dc_events_for_test = _dc_events


def dc_context(g: dict, atr_sec: np.ndarray) -> dict:
    """Family-9 state variables broadcast onto the second grid."""
    n = g["n"]
    evs = _dc_events(g, atr_sec)
    if not evs:
        return _empty_dc(n)

    conf_sec = np.array([e.conf_ts // NS - g["sec0"] for e in evs], dtype=np.int64)
    direction = np.array([e.direction for e in evs], dtype=float)
    mag = np.array([e.dc_magnitude for e in evs], dtype=float)
    prev_os = np.array([e.prev_overshoot for e in evs], dtype=float)

    # event k is KNOWN from second conf_sec[k] onward (its confirmation closed
    # inside that second); grid index i may use events with conf_sec <= i.
    idx = np.arange(n)
    k = np.searchsorted(conf_sec, idx, side="right") - 1        # last known event
    has = k >= 0
    kk = np.clip(k, 0, len(evs) - 1)
    k2 = np.clip(k - 1, 0, len(evs) - 1)
    return {
        "last_dc_dir": np.where(has, direction[kk], 0.0),
        "last_dc_mag": np.where(has, mag[kk], np.nan),
        "last_overshoot": np.where(has, prev_os[kk], np.nan),
        "prev2_dc_dir": np.where(k >= 1, direction[k2], 0.0),
        "secs_since_last_dc": np.where(has, idx - conf_sec[kk], 3600.0).astype(float),
        "n_events": len(evs),
    }


def _empty_dc(n: int) -> dict:
    return {"last_dc_dir": np.zeros(n), "last_dc_mag": np.full(n, np.nan),
            "last_overshoot": np.full(n, np.nan), "prev2_dc_dir": np.zeros(n),
            "secs_since_last_dc": np.full(n, 3600.0), "n_events": 0}


# --------------------------------------------------- the state matrix ----
def build_state_matrix(g: dict, d: dt.date, pdh: float, pdl: float) -> dict | None:
    """All 55 registered features on the whole second grid.

    Returns a dict with 'X' (n_grid x 55, float64, FEATURE_NAMES order), 'atr',
    'r_points' and the anchor indices.  Decision-row selection is the caller's
    job (`decision_indices`).
    """
    n, sec0 = g["n"], g["sec0"]
    c, hi, lo = g["close"], g["high"], g["low"]
    vol, cnt, buy, sell = g["vol"], g["cnt"], g["buy"], g["sell"]

    atr, atr_min = causal_atr(g)
    minute = ((np.arange(n) + sec0) // 60)
    dc_ = np.diff(c, prepend=c[0])
    adc = np.abs(dc_)

    i_open = et_sec(d, SESSION_START_ET) - sec0 - 1        # grid index of 09:29:59
    i_or_end = et_sec(d, OR_END_ET) - sec0 - 1            # grid index of 09:59:59
    if not (0 <= i_open < n and 0 < i_or_end < n):
        return None
    if g["first_traded"] + MAX_LOOKBACK_S > i_open:
        return None                                       # not enough warm-up tape

    F: dict[str, np.ndarray] = {}

    # ---- family 1: returns / displacement -------------------------------
    for h in RET_HORIZONS:
        F[f"ret_norm_{h}"] = (c - _shift(c, h)) / (atr * np.sqrt(h / 60.0))
    for h in (60, 300):
        F[f"eff_{h}"] = np.abs(c - _shift(c, h)) / (_roll_sum(adc, h) + EPS)

    # ---- family 2: velocity / acceleration ------------------------------
    v15 = (c - _shift(c, 15)) / 15.0 / (atr / 60.0)
    v60 = (c - _shift(c, 60)) / 60.0 / (atr / 60.0)
    F["vel_15_norm"] = v15
    F["vel_60_norm"] = v60
    F["vel_ratio_15_60"] = v15 / (np.abs(v60) + EPS)
    F["accel_15_60"] = v15 - v60
    nup = _roll_sum((dc_ > 0).astype(float), 60)
    ndn = _roll_sum((dc_ < 0).astype(float), 60)
    s60 = np.sign(c - _shift(c, 60))
    agree = np.where(s60 > 0, nup, np.where(s60 < 0, ndn, 0.0))
    nz = nup + ndn
    frac = np.where(nz > 0, agree / np.maximum(nz, 1.0), 0.5)
    F["persist_60"] = np.where(s60 == 0, 0.0, 2.0 * frac - 1.0)

    # ---- family 3: volatility / range -----------------------------------
    rv60 = np.sqrt(_roll_sum(dc_ ** 2, 60))
    rv300 = np.sqrt(_roll_sum(dc_ ** 2, 300))
    F["atr1m"] = atr
    F["rv_60_norm"] = rv60 / atr
    F["rv_300_norm"] = rv300 / (atr * np.sqrt(5.0))
    F["vol_ratio_60_300"] = rv60 * np.sqrt(5.0) / (rv300 + EPS)
    F["range_60_norm"] = (_roll_max(c, 60) - _roll_min(c, 60)) / atr
    F["atr_pct_rank"] = _atr_pct_rank(minute, atr_min, n)
    F["vol_expansion"] = atr / (_shift(atr, 1200) + EPS)

    # ---- family 4: micro price structure --------------------------------
    mx300, mn300 = _roll_max(c, 300), _roll_min(c, 300)
    mx1800, mn1800 = _roll_max(c, 1800), _roll_min(c, 1800)
    F["dist_high_300_norm"] = (mx300 - c) / atr
    F["dist_low_300_norm"] = (c - mn300) / atr
    F["dist_high_1800_norm"] = (mx1800 - c) / atr
    F["dist_low_1800_norm"] = (c - mn1800) / atr
    new_hi = (c > _shift(mx300, 1, fill=np.inf)).astype(float)
    new_lo = (c < _shift(mn300, 1, fill=-np.inf)).astype(float)
    F["n_new_highs_300"] = _roll_sum(new_hi, 300)
    F["n_new_lows_300"] = _roll_sum(new_lo, 300)
    F["pullback_depth"] = (mx300 - c) / (mx300 - mn300 + EPS)
    F["secs_since_high_300"] = _secs_since_extreme(c, 300, True)
    F["secs_since_low_300"] = _secs_since_extreme(c, 300, False)

    # ---- family 5: trade intensity --------------------------------------
    cnt60, cnt300 = _roll_sum(cnt, 60), _roll_sum(cnt, 300)
    vol60, vol300 = _roll_sum(vol, 60), _roll_sum(vol, 300)
    tps60, tps300 = cnt60 / 60.0, cnt300 / 300.0
    vps60, vps300 = vol60 / 60.0, vol300 / 300.0
    mean_sz300 = vol300 / np.maximum(cnt300, 1.0)
    F["trades_per_s_60"] = tps60
    F["vol_per_s_60"] = vps60
    F["avg_trade_size_60"] = vol60 / np.maximum(cnt60, 1.0)
    F["max_trade_size_60_rel"] = _roll_max(g["maxsz"], 60) / (mean_sz300 + EPS)
    F["intensity_ratio_60_300"] = tps60 / (tps300 + EPS)
    F["volume_ratio_60_300"] = vps60 / (vps300 + EPS)

    # ---- family 6: trade side / delta -----------------------------------
    sgn = buy - sell
    d60, d300 = _roll_sum(sgn, 60), _roll_sum(sgn, 300)
    sv60, sv300 = _roll_sum(buy + sell, 60), _roll_sum(buy + sell, 300)
    F["delta_60_norm"] = d60 / (vol300 / 5.0 + EPS)          # / trailing mean 60s volume
    F["delta_300_norm"] = d300 / (_roll_sum(vol, 1500) / 5.0 + EPS)  # mirror at 300s
    F["delta_per_vol_60"] = d60 / (sv60 + EPS)
    F["delta_per_vol_300"] = d300 / (sv300 + EPS)
    cum_sgn = np.cumsum(sgn); cum_vol = np.cumsum(vol)
    base = i_open                                            # cumulate from 09:30:00
    cd = (cum_sgn - cum_sgn[base]) / (cum_vol - cum_vol[base] + EPS)
    F["cum_delta_norm"] = np.where(np.arange(n) > base, cd, 0.0)
    F["delta_accel"] = F["delta_per_vol_60"] - F["delta_per_vol_300"]

    # ---- family 7: time / session ---------------------------------------
    # value at grid index i is stamped for the decision at wall-clock i+1
    sso = (np.arange(n) + 1) - (i_open + 1)
    F["secs_since_open"] = sso.astype(float)
    F["is_second_hour"] = (sso >= 3600).astype(float)
    F["weekday"] = np.full(n, float(d.weekday()))

    # ---- family 8: objective location ------------------------------------
    F["dist_open_norm"] = (c - c[i_open]) / atr
    cum_pv = np.cumsum(g["pxvol"])
    rth_vol = cum_vol - cum_vol[base]
    vwap = np.where(rth_vol > 0, (cum_pv - cum_pv[base]) / np.maximum(rth_vol, EPS), c)
    F["dist_vwap_norm"] = np.where(np.arange(n) > base, (c - vwap) / atr, 0.0)
    F["dist_pdh_norm"] = (c - pdh) / atr if np.isfinite(pdh) else np.full(n, np.nan)
    F["dist_pdl_norm"] = (c - pdl) / atr if np.isfinite(pdl) else np.full(n, np.nan)
    or_hi = float(np.max(hi[base + 1:i_or_end + 1]))
    or_lo = float(np.min(lo[base + 1:i_or_end + 1]))
    after_or = np.arange(n) >= i_or_end
    F["dist_or30_hi_norm"] = np.where(after_or, (c - or_hi) / atr, 0.0)
    F["dist_or30_lo_norm"] = np.where(after_or, (c - or_lo) / atr, 0.0)

    # ---- family 9: event sequence ----------------------------------------
    dcx = dc_context(g, atr)
    F["last_dc_dir"] = dcx["last_dc_dir"]
    F["last_dc_mag_norm"] = dcx["last_dc_mag"] / atr
    F["last_overshoot_norm"] = dcx["last_overshoot"] / atr
    F["prev2_dc_dir"] = dcx["prev2_dc_dir"]
    F["secs_since_last_dc"] = np.minimum(dcx["secs_since_last_dc"], 3600.0)

    missing = set(FEATURE_NAMES) - set(F)
    extra = set(F) - set(FEATURE_NAMES)
    if missing or extra:
        raise AssertionError(f"feature set mismatch: missing={missing} extra={extra}")

    X = np.column_stack([np.asarray(F[k], dtype=np.float64) for k in FEATURE_NAMES])
    return {"X": X, "atr": atr, "r_points": r_from_atr(atr), "close": c,
            "i_open": i_open, "i_or_end": i_or_end, "n_dc_events": dcx["n_events"],
            "or_hi": or_hi, "or_lo": or_lo}


def decision_indices(g: dict, d: dt.date, start_et: str = SESSION_START_ET,
                     end_et: str = DIAG_END_ET, step_s: int = DECISION_STEP_S) -> np.ndarray:
    """Grid indices whose decision timestamp lies on the fixed 5-second clock.

    Decision timestamp of grid index i is (sec0 + i + 1); the clock is anchored
    on the session open, so the first decision is exactly at ``start_et``.
    """
    t0 = et_sec(d, start_et)
    t1 = et_sec(d, end_et)
    dec = np.arange(t0, t1, step_s, dtype=np.int64)
    idx = dec - g["sec0"] - 1
    return idx[(idx >= 0) & (idx < g["n"])]


def decision_ts_ns(g: dict, idx: np.ndarray) -> np.ndarray:
    return (g["sec0"] + idx + 1).astype(np.int64) * NS
