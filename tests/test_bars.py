import datetime as dt
import numpy as np
import polars as pl
from nqr.data.cache import build_bars_from_ticks

NS = 1_000_000_000
BAR = 120 * NS


def _ticks(rows):
    return pl.DataFrame(
        {"trading_date": [dt.date(2023, 5, 10)] * len(rows),
         "symbol": ["NQM3"] * len(rows),
         "ts_ns": [r[0] for r in rows],
         "px_ticks": [r[1] for r in rows],
         "size": [r[2] for r in rows],
         "row_seq": list(range(len(rows)))},
        schema_overrides={"px_ticks": pl.Int32, "size": pl.Int32})


def test_ohlcv_exact():
    t0 = 1_683_000_000 * NS
    t0 -= t0 % BAR
    rows = [(t0 + 1, 100, 3), (t0 + 5 * NS, 104, 1), (t0 + 9 * NS, 97, 2),
            (t0 + 119 * NS, 101, 4)]
    b = build_bars_from_ticks(_ticks(rows))
    assert b.height == 1
    r = b.row(0, named=True)
    assert (r["open"], r["high"], r["low"], r["close"]) == (25.0, 26.0, 24.25, 25.25)
    assert r["volume"] == 10 and r["trades"] == 4
    assert r["bar_end_ns"] - r["bar_ns"] == BAR


def test_bar_boundary_is_half_open():
    t0 = 1_683_000_000 * NS
    t0 -= t0 % BAR
    rows = [(t0, 100, 1), (t0 + BAR - 1, 110, 1), (t0 + BAR, 120, 1)]
    b = build_bars_from_ticks(_ticks(rows)).sort("bar_ns")
    assert b.height == 2
    # the print exactly ON the boundary starts the NEXT bar
    assert b["close"][0] == 27.5 and b["open"][1] == 30.0


def test_no_bar_for_empty_interval():
    t0 = 1_683_000_000 * NS
    t0 -= t0 % BAR
    rows = [(t0, 100, 1), (t0 + 3 * BAR, 100, 1)]
    b = build_bars_from_ticks(_ticks(rows))
    assert b.height == 2                      # the two empty intervals produce nothing


def test_open_close_follow_source_order_not_timestamp_ties():
    t0 = 1_683_000_000 * NS
    t0 -= t0 % BAR
    # three fills of one sweep sharing an identical ts_event
    rows = [(t0 + NS, 100, 1), (t0 + NS, 102, 1), (t0 + NS, 105, 1)]
    b = build_bars_from_ticks(_ticks(rows))
    assert b["open"][0] == 25.0 and b["close"][0] == 26.25


def test_epoch_alignment_matches_even_et_minutes():
    from nqr.sessions.calendar import to_utc
    for d, t in [(dt.date(2024, 1, 15), dt.time(9, 30)), (dt.date(2024, 7, 15), dt.time(9, 30))]:
        ns = int(to_utc(d, t).timestamp() * NS)
        assert ns % BAR == 0
