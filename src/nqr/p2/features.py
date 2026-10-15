"""Phase-2 causal feature construction.

Everything here is trailing-only.  A value stamped at second `t` may depend on
events with `ts_event <= t_end` and on nothing later.  There are no centred
windows, no backward fills and no full-day statistics.
"""
from __future__ import annotations

import numpy as np
import polars as pl

TICK = 0.25
NS = 1_000_000_000


# --------------------------------------------------------------- 1s bars ----
def second_bars(ticks: pl.DataFrame) -> pl.DataFrame:
    """One row per traded second.  Signed volume comes from the aggressor code.

    open/close use exact source order (`row_seq`), so a multi-fill sweep sharing
    one `ts_event` resolves deterministically.
    """
    if ticks.height == 0:
        return pl.DataFrame(schema=SEC_SCHEMA)
    df = ticks.with_columns((pl.col("ts_ns") // NS).alias("sec"))
    out = (
        df.group_by(["trading_date", "symbol", "sec"])
          .agg(
              pl.col("px_ticks").first().alias("o_t"),
              pl.col("px_ticks").max().alias("h_t"),
              pl.col("px_ticks").min().alias("l_t"),
              pl.col("px_ticks").last().alias("c_t"),
              pl.col("size").sum().alias("volume"),
              pl.len().alias("trades"),
              pl.col("size").filter(pl.col("side_raw") == 1).sum().alias("buy_vol"),
              pl.col("size").filter(pl.col("side_raw") == -1).sum().alias("sell_vol"),
              pl.col("size").filter(pl.col("side_raw") == 0).sum().alias("unk_vol"),
              pl.col("size").max().alias("max_trade_size"),
              pl.col("ts_ns").min().alias("first_ts_ns"),
              pl.col("ts_ns").max().alias("last_ts_ns"),
          )
          .sort("sec")
    )
    return out.with_columns(
        (pl.col("o_t") * TICK).alias("open"), (pl.col("h_t") * TICK).alias("high"),
        (pl.col("l_t") * TICK).alias("low"), (pl.col("c_t") * TICK).alias("close"),
        (pl.col("buy_vol") - pl.col("sell_vol")).alias("delta"),
    ).drop(["o_t", "h_t", "l_t", "c_t"])


SEC_SCHEMA = {
    "trading_date": pl.Date, "symbol": pl.String, "sec": pl.Int64,
    "volume": pl.Int64, "trades": pl.UInt32, "buy_vol": pl.Int64,
    "sell_vol": pl.Int64, "unk_vol": pl.Int64, "max_trade_size": pl.Int32,
    "first_ts_ns": pl.Int64, "last_ts_ns": pl.Int64,
    "open": pl.Float64, "high": pl.Float64, "low": pl.Float64,
    "close": pl.Float64, "delta": pl.Int64,
}


def densify_seconds(sec_bars: pl.DataFrame, sec_start: int, sec_end: int) -> pl.DataFrame:
    """Expand to one row per second in [sec_start, sec_end).

    Untraded seconds carry zero volume and forward-filled prices.  The forward
    fill only ever propagates the PAST close, never a future one.
    """
    grid = pl.DataFrame({"sec": np.arange(sec_start, sec_end, dtype=np.int64)})
    j = grid.join(sec_bars, on="sec", how="left").sort("sec")
    j = j.with_columns(pl.col("close").forward_fill().alias("ffill_close"))
    return j.with_columns(
        pl.col("open").fill_null(pl.col("ffill_close")),
        pl.col("high").fill_null(pl.col("ffill_close")),
        pl.col("low").fill_null(pl.col("ffill_close")),
        pl.col("close").fill_null(pl.col("ffill_close")),
        pl.col("volume").fill_null(0), pl.col("trades").fill_null(0),
        pl.col("buy_vol").fill_null(0), pl.col("sell_vol").fill_null(0),
        pl.col("unk_vol").fill_null(0), pl.col("delta").fill_null(0),
        pl.col("max_trade_size").fill_null(0),
        (pl.col("volume").fill_null(0) > 0).alias("traded"),
    ).drop("ffill_close")


# ------------------------------------------------------------ minute ATR ----
def minute_bars_from_seconds(sec: pl.DataFrame) -> pl.DataFrame:
    d = sec.filter(pl.col("traded")).with_columns((pl.col("sec") // 60).alias("minute"))
    return (d.group_by("minute")
             .agg(pl.col("open").first().alias("open"), pl.col("high").max().alias("high"),
                  pl.col("low").min().alias("low"), pl.col("close").last().alias("close"),
                  pl.col("volume").sum().alias("volume"))
             .sort("minute"))


def causal_atr_minutes(minutes: pl.DataFrame, n: int = 14) -> pl.DataFrame:
    """ATR of COMPLETED minutes.  The value published for minute m uses minutes
    m-n .. m-1 only, so the in-progress minute cannot leak its own range."""
    h = minutes["high"].to_numpy(); l = minutes["low"].to_numpy(); c = minutes["close"].to_numpy()
    pc = np.empty_like(c); pc[0] = c[0]; pc[1:] = c[:-1]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    tr[0] = h[0] - l[0]
    out = np.full(len(tr), np.nan)
    if len(tr) > n:
        cs = np.concatenate(([0.0], np.cumsum(tr)))
        idx = np.arange(n, len(tr))
        out[idx] = (cs[idx] - cs[idx - n]) / n
    return minutes.select("minute").with_columns(pl.Series("atr_prev", out))


def vu_per_second(sec: pl.DataFrame, minutes_atr: pl.DataFrame, floor_points: float) -> np.ndarray:
    """VU at second t = ATR14 of the completed minutes strictly before t's minute.

    Implemented by mapping second -> its own minute and reading `atr_prev`,
    which by construction excludes the current minute.
    """
    m = (sec.select("sec").with_columns((pl.col("sec") // 60).alias("minute"))
            .join(minutes_atr, on="minute", how="left"))
    v = m["atr_prev"].to_numpy().astype(float)
    # NaN propagates through np.maximum by design: during the ATR warm-up VU is
    # undefined and the state machine refuses to act on a non-finite VU.
    return np.maximum(v, floor_points)


# ------------------------------------------------- directional-change events ----
def directional_changes(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                        theta: np.ndarray, traded: np.ndarray) -> list[dict]:
    """Causal directional-change (DC) tracker.

    While tracking a peak the running maximum is extended; once price retraces
    `theta` from it the peak is CONFIRMED.  A confirmed extreme is published at
    the index where the retracement completed - never at the index where the
    extreme itself printed.

    Two deliberate conservatism choices, both frozen:

    * Confirmation requires ``conf_idx > ext_idx``.  Within one second we cannot
      know whether the high or the low printed first, so a second that both sets
      a new extreme and appears to retrace from it does NOT confirm; the
      confirmation waits for a strictly later second.  This can only ever DELAY
      information, never advance it.
    * The tracker starts undecided and adopts a direction only when the first
      `theta` move resolves it, so no direction is assumed at the open.

    Returns dicts with:
        kind        'PEAK' | 'TROUGH'
        ext_idx     index at which the extreme printed
        ext_price   the extreme price
        conf_idx    index at which it became causally known
        start_idx   index of the previous confirmed opposite extreme (leg start)
        start_price price of that previous extreme
    """
    n = len(high)
    out: list[dict] = []
    if n == 0:
        return out
    first = int(np.argmax(traded)) if traded.any() else -1
    if first < 0:
        return out

    mode = 0                                  # 0 undecided, +1 peak-tracking, -1 trough
    hi_p, hi_i = high[first], first           # running max while undecided / peak mode
    lo_p, lo_i = low[first], first            # running min while undecided / trough mode
    prev_i, prev_p = first, float(close[first])

    for i in range(first, n):
        if not traded[i]:
            continue
        th = theta[i]
        if mode == 0:
            if high[i] > hi_p:
                hi_p, hi_i = high[i], i
            if low[i] < lo_p:
                lo_p, lo_i = low[i], i
            if i > hi_i and low[i] <= hi_p - th:
                mode = 1                       # resolve as peak-tracking, confirm below
            elif i > lo_i and high[i] >= lo_p + th:
                mode = -1
            else:
                continue
        if mode == 1:
            if high[i] > hi_p:
                hi_p, hi_i = high[i], i
            if i > hi_i and low[i] <= hi_p - th:
                out.append(dict(kind="PEAK", ext_idx=hi_i, ext_price=float(hi_p),
                                conf_idx=i, start_idx=prev_i, start_price=float(prev_p)))
                prev_i, prev_p = hi_i, float(hi_p)
                mode, lo_p, lo_i = -1, low[i], i
        elif mode == -1:
            if low[i] < lo_p:
                lo_p, lo_i = low[i], i
            if i > lo_i and high[i] >= lo_p + th:
                out.append(dict(kind="TROUGH", ext_idx=lo_i, ext_price=float(lo_p),
                                conf_idx=i, start_idx=prev_i, start_price=float(prev_p)))
                prev_i, prev_p = lo_i, float(lo_p)
                mode, hi_p, hi_i = 1, high[i], i
    return out


def rolling_min(a: np.ndarray, w: int) -> np.ndarray:
    """Trailing minimum over the w samples ending at (and including) each index."""
    return pl.Series(a).rolling_min(window_size=w, min_samples=1).to_numpy()


def rolling_max(a: np.ndarray, w: int) -> np.ndarray:
    return pl.Series(a).rolling_max(window_size=w, min_samples=1).to_numpy()
