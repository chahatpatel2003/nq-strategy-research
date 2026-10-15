"""Phase-2 causality: quote alignment, event ordering, no future leakage."""
import numpy as np
import polars as pl
import pytest

from nqr.p2.signing import (BUY, SELL, UNKNOWN, causal_bbo_for_trades,
                            classify_from_bbo, verify_native_side)
from nqr.p2 import features as FT

NS = 1_000_000_000


def test_quote_used_is_strictly_before_the_trade():
    qt = np.array([10, 20, 30, 40], dtype=np.int64)
    bid = np.array([100, 101, 102, 103], dtype=np.int64)
    ask = np.array([102, 103, 104, 105], dtype=np.int64)
    tt = np.array([25, 30, 31, 5], dtype=np.int64)
    b, a = causal_bbo_for_trades(tt, qt, bid, ask)
    assert b.tolist() == [101, 101, 102, -1]      # t=30 must NOT see the t=30 quote
    assert a.tolist() == [103, 103, 104, -1]


def test_no_quote_yet_yields_unknown():
    qt = np.array([100], dtype=np.int64)
    b, a = causal_bbo_for_trades(np.array([50], dtype=np.int64), qt,
                                 np.array([1]), np.array([2]))
    assert b[0] == -1 and a[0] == -1
    assert classify_from_bbo(np.array([1]), b, a)[0] == UNKNOWN


def test_future_quotes_cannot_change_a_past_classification():
    """Appending later quotes must leave earlier classifications untouched."""
    qt = np.array([10, 20], dtype=np.int64)
    bid = np.array([100, 101], dtype=np.int64)
    ask = np.array([102, 103], dtype=np.int64)
    tt = np.array([15, 25], dtype=np.int64)
    px = np.array([102, 101], dtype=np.int64)
    r1 = classify_from_bbo(px, *causal_bbo_for_trades(tt, qt, bid, ask))
    qt2 = np.concatenate([qt, [30, 40]])
    bid2 = np.concatenate([bid, [200, 300]])
    ask2 = np.concatenate([ask, [201, 301]])
    r2 = classify_from_bbo(px, *causal_bbo_for_trades(tt, qt2, bid2, ask2))
    assert r1.tolist() == r2.tolist()


def test_quote_rule_boundaries():
    px = np.array([102, 103, 101, 100, 99], dtype=np.int64)
    bid = np.full(5, 100, dtype=np.int64)
    ask = np.full(5, 102, dtype=np.int64)
    got = classify_from_bbo(px, bid, ask).tolist()
    assert got == [BUY, BUY, UNKNOWN, SELL, SELL]


def test_inside_spread_is_unknown_not_guessed():
    px = np.array([101], dtype=np.int64)
    assert classify_from_bbo(px, np.array([100]), np.array([102]))[0] == UNKNOWN


# ------------------------------------------------------------ ATR / VU ----
def _minutes(n=40):
    return pl.DataFrame({
        "minute": np.arange(n, dtype=np.int64),
        "open": np.full(n, 100.0), "high": np.arange(n) * 0.0 + 110.0,
        "low": np.full(n, 100.0), "close": np.full(n, 105.0),
        "volume": np.full(n, 10, dtype=np.int64)})


def test_atr_excludes_the_current_minute():
    m = _minutes()
    a = FT.causal_atr_minutes(m, 14)
    assert np.isnan(a["atr_prev"].to_numpy()[:14]).all()
    m2 = m.with_columns(pl.when(pl.col("minute") >= 20).then(pl.lit(9999.0))
                        .otherwise(pl.col("high")).alias("high"))
    a2 = FT.causal_atr_minutes(m2, 14)
    assert a["atr_prev"][19] == pytest.approx(a2["atr_prev"][19])
    assert a["atr_prev"][20] == pytest.approx(a2["atr_prev"][20])


def test_vu_is_nan_during_warmup_so_no_signal_can_fire():
    m = _minutes()
    atr = FT.causal_atr_minutes(m, 14)
    sec = pl.DataFrame({"sec": np.arange(0, 40 * 60, 60, dtype=np.int64)})
    vu = FT.vu_per_second(sec, atr, floor_points=2.0)
    # NaN, not the floor: the state machine skips non-finite VU outright
    assert np.isnan(vu[:14]).all()
    assert np.isfinite(vu[20])


def test_vu_floor_applies_where_atr_is_defined():
    n = 40
    m = pl.DataFrame({"minute": np.arange(n, dtype=np.int64),
                      "open": np.full(n, 100.0), "high": np.full(n, 100.25),
                      "low": np.full(n, 100.0), "close": np.full(n, 100.0),
                      "volume": np.full(n, 10, dtype=np.int64)})
    atr = FT.causal_atr_minutes(m, 14)
    assert atr["atr_prev"][20] == pytest.approx(0.25)      # far below the floor
    sec = pl.DataFrame({"sec": np.arange(0, n * 60, 60, dtype=np.int64)})
    vu = FT.vu_per_second(sec, atr, floor_points=2.0)
    fin = np.isfinite(vu)
    assert fin.any() and (vu[fin] >= 2.0).all()


# --------------------------------------------------------- second bars ----
def _ticks(rows, d=None):
    import datetime as dt
    d = d or dt.date(2023, 5, 10)
    return pl.DataFrame({"trading_date": [d] * len(rows), "symbol": ["NQM3"] * len(rows),
                         "ts_ns": [r[0] for r in rows], "px_ticks": [r[1] for r in rows],
                         "size": [r[2] for r in rows], "side_raw": [r[3] for r in rows],
                         "row_seq": list(range(len(rows)))},
                        schema_overrides={"px_ticks": pl.Int32, "size": pl.Int32,
                                          "side_raw": pl.Int32})


def test_second_bar_signed_volume():
    t0 = 1_683_000_000 * NS
    b = FT.second_bars(_ticks([(t0, 100, 3, 1), (t0 + 5, 104, 2, -1),
                              (t0 + 9, 97, 1, 0), (t0 + NS - 1, 101, 4, 1)]))
    assert b.height == 1
    r = b.row(0, named=True)
    assert r["buy_vol"] == 7 and r["sell_vol"] == 2 and r["unk_vol"] == 1
    assert r["delta"] == 5 and r["volume"] == 10
    assert (r["open"], r["high"], r["low"], r["close"]) == (25.0, 26.0, 24.25, 25.25)


def test_second_bar_boundary_is_half_open():
    t0 = 1_683_000_000 * NS
    b = FT.second_bars(_ticks([(t0, 100, 1, 1), (t0 + NS - 1, 110, 1, 1),
                               (t0 + NS, 120, 1, 1)])).sort("sec")
    assert b.height == 2 and b["close"][0] == 27.5 and b["open"][1] == 30.0


def test_densify_forward_fills_only_from_the_past():
    t0 = 1_683_000_000
    b = FT.second_bars(_ticks([(t0 * NS, 100, 1, 1), ((t0 + 3) * NS, 120, 1, 1)]))
    g = FT.densify_seconds(b, t0 - 2, t0 + 5)
    c = g["close"].to_numpy()
    assert np.isnan(c[0]) and np.isnan(c[1])         # nothing known before the first print
    assert c[2] == 25.0 and c[3] == 25.0 and c[4] == 25.0
    assert c[5] == 30.0
    assert g["traded"].to_list() == [False, False, True, False, False, True, False]
    assert g["volume"].sum() == 2


# --------------------------------------- signing decision-rule regression ----
def test_verify_native_side_counts_agreement_correctly():
    import datetime as dt
    ticks = pl.DataFrame({
        "trading_date": [dt.date(2023, 5, 10)] * 5,
        "symbol": ["NQM3"] * 5,
        # t=15 sees the t=10 quote (bid 100, ask 102 in ticks)
        "ts_ns": [15, 16, 17, 18, 5],
        "px_ticks": [102, 100, 101, 103, 102],
        "size": [1] * 5,
        "side_raw": [1, -1, 1, -1, 1],      # 4th disagrees, 5th has no quote yet
        "row_seq": list(range(5))},
        schema_overrides={"px_ticks": pl.Int32, "size": pl.Int32, "side_raw": pl.Int32})
    quotes = pl.DataFrame({"ts_ns": [10], "bid_t": [100], "ask_t": [102]})
    r = verify_native_side(ticks, quotes)
    assert r["n_with_quote"] == 4               # the t=5 trade has no prior quote
    assert r["n_unambiguous"] == 3              # 101 is inside the spread
    assert r["n_agree"] == 2 and r["n_disagree"] == 1
    assert r["agreement_rate"] == pytest.approx(2 / 3)
    assert r["n_inside_spread"] == 1


def test_unknown_trades_are_excluded_from_signed_volume():
    import datetime as dt
    t0 = 1_700_000_000 * NS
    b = FT.second_bars(pl.DataFrame({
        "trading_date": [dt.date(2023, 5, 10)] * 3, "symbol": ["NQM3"] * 3,
        "ts_ns": [t0, t0 + 1, t0 + 2], "px_ticks": [400, 400, 400],
        "size": [5, 7, 11], "side_raw": [1, -1, 0], "row_seq": [0, 1, 2]},
        schema_overrides={"px_ticks": pl.Int32, "size": pl.Int32, "side_raw": pl.Int32}))
    r = b.row(0, named=True)
    assert r["buy_vol"] == 5 and r["sell_vol"] == 7 and r["unk_vol"] == 11
    assert r["delta"] == -2                     # unknown contributes to neither side
    assert r["volume"] == 23
