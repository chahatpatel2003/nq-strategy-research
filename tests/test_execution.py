import numpy as np
import pytest
from nqr.backtest.engine import TICK, find_entry, resolve, excursions

NS = 1_000_000_000


def tape(rows):
    ts = np.array([r[0] for r in rows], dtype=np.int64)
    px = np.array([int(round(r[1] / TICK)) for r in rows], dtype=np.int64)
    return ts, px


def test_entry_is_first_print_after_bar_close_plus_latency():
    ts, px = tape([(0, 100.0), (100 * 10**6, 100.5), (300 * 10**6, 101.0), (400 * 10**6, 101.5)])
    got = find_entry(ts, px, 250 * 10**6, 60 * NS)
    assert got is not None
    idx, t, p = got
    assert t == 300 * 10**6 and p == 101.0          # the 100 ms print is too early


def test_entry_abandoned_if_the_tape_goes_quiet():
    ts, px = tape([(0, 100.0), (10 * 60 * NS, 100.0)])
    assert find_entry(ts, px, 1 * NS, 60 * NS) is None


def test_tp_before_sl_inside_one_candle_is_decided_by_sequence():
    """Both levels are hit inside the same 2-minute window; order decides."""
    rows = [(0, 100.0), (1 * NS, 101.5), (2 * NS, 99.0)]     # TP side touched first
    ts, px = tape(rows)
    f = resolve(ts, px, 0, 10 * NS, +1, tp=101.0, sl=99.0)
    assert f.kind == "TP" and f.price == 101.0
    rows = [(0, 100.0), (1 * NS, 99.0), (2 * NS, 101.5)]     # SL side touched first
    ts, px = tape(rows)
    f = resolve(ts, px, 0, 10 * NS, +1, tp=101.0, sl=99.0)
    assert f.kind == "SL"


def test_limit_target_needs_a_trade_through_not_a_touch():
    ts, px = tape([(0, 100.0), (1 * NS, 101.0), (2 * NS, 101.0), (3 * NS, 99.0)])
    f = resolve(ts, px, 0, 10 * NS, +1, tp=101.0, sl=99.0)
    assert f.kind == "SL", "touching the limit must not count as a fill"
    ts, px = tape([(0, 100.0), (1 * NS, 101.25), (3 * NS, 99.0)])
    f = resolve(ts, px, 0, 10 * NS, +1, tp=101.0, sl=99.0)
    assert f.kind == "TP" and f.price == 101.0


def test_stop_fills_on_touch_at_the_print_price():
    ts, px = tape([(0, 100.0), (1 * NS, 98.5)])       # gapped straight through
    f = resolve(ts, px, 0, 10 * NS, +1, tp=101.0, sl=99.0)
    assert f.kind == "SL" and f.price == 98.5         # not 99.0 - we pay the print


def test_short_side_mirrors():
    ts, px = tape([(0, 100.0), (1 * NS, 98.75)])
    f = resolve(ts, px, 0, 10 * NS, -1, tp=99.0, sl=101.0)
    assert f.kind == "TP" and f.price == 99.0
    ts, px = tape([(0, 100.0), (1 * NS, 101.0)])
    f = resolve(ts, px, 0, 10 * NS, -1, tp=99.0, sl=101.0)
    assert f.kind == "SL"


def test_timeout_uses_last_print_before_the_cutoff():
    ts, px = tape([(0, 100.0), (1 * NS, 100.25), (2 * NS, 100.5), (20 * NS, 105.0)])
    f = resolve(ts, px, 0, 10 * NS, +1, tp=110.0, sl=90.0)
    assert f.kind == "TIMEOUT" and f.price == 100.5


def test_mfe_mae_from_raw_prints():
    ts, px = tape([(0, 100.0), (1 * NS, 103.0), (2 * NS, 97.0), (3 * NS, 101.0)])
    mfe, mae = excursions(ts, px, 0, 3 * NS, +1, 100.0)
    assert mfe == 3.0 and mae == 3.0
    mfe, mae = excursions(ts, px, 0, 3 * NS, -1, 100.0)
    assert mfe == 3.0 and mae == 3.0


def test_resolution_never_looks_past_the_cutoff():
    ts, px = tape([(0, 100.0), (1 * NS, 100.25), (30 * NS, 90.0)])
    f = resolve(ts, px, 0, 10 * NS, +1, tp=101.0, sl=99.0)
    assert f.kind == "TIMEOUT"
