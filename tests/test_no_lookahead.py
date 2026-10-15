"""Integration test: a signal must be reproducible from a bar series that is
TRUNCATED at the moment the signal became knowable.

If any part of detection peeked at a future bar, truncating the series would
change or delete the signal.
"""
import datetime as dt
from pathlib import Path
import sys

import numpy as np
import polars as pl
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nqr.levels.build import build_level_segments, daily_atr, day_extremes, session_extremes
from nqr.signals import triggers as TG
from strategies.fast_slow.runner import VARIANTS, find_candidates, select_variant

BARS = ROOT / "data_cache" / "bars" / "bars_2m.parquet"
pytestmark = pytest.mark.skipif(not BARS.exists(), reason="run scripts/01_build_cache.py first")


@pytest.fixture(scope="module")
def world():
    cfg = yaml.safe_load((ROOT / "config" / "fast_slow_baseline.yaml").read_text())
    bars = pl.read_parquet(BARS).sort("bar_ns")
    se = session_extremes(bars.filter(pl.col("session") != "HALT"))
    de = day_extremes(bars)
    atr = daily_atr(de, 20)
    dates = sorted(bars["trading_date"].unique().to_list())
    segs = build_level_segments(dates, se, de, atr, min_session_bars=30,
                                tol_atr_frac=0.02, tol_min=1.0, tol_max=20.0, dedup_mult=1.0)
    sb = {}
    for s in segs:
        sb.setdefault(s.trading_date, []).append(s)
    amap = {r["trading_date"]: r["atr20_prev"] for r in atr.iter_rows(named=True)}
    return cfg, bars, sb, amap


def _run_day(cfg, bars, segs, a20, d):
    o = bars["open"].to_numpy(); h = bars["high"].to_numpy()
    l = bars["low"].to_numpy(); c = bars["close"].to_numpy()
    bns = bars["bar_ns"].to_numpy()
    tc = np.array([x.toordinal() for x in bars["trading_date"].to_list()])
    a2 = TG.atr2m(h, l, c, cfg["trigger"]["atr2m_lookback"])
    trig = TG.all_triggers(o, h, l, c, a2, cfg["trigger"])
    idx = np.flatnonzero(tc == d.toordinal())
    g0, g1 = int(idx[0]), int(idx[-1]) + 1
    cands, _ = find_candidates(bars[g0:g1], segs, cfg, trig, g0, bns, tc, o, h, l, c, float(a20))
    return select_variant(cands, VARIANTS["ANY"], cfg["trigger"]["precedence"])


def test_signals_survive_truncation_at_the_signal_bar(world):
    cfg, bars, sb, amap = world
    trades = pl.read_parquet(ROOT / "results" / "fast_slow_dev" / "trades_ANY.parquet")
    sample = trades.filter(pl.col("status") == "ACCEPTED").head(400).sample(
        n=25, seed=7, with_replacement=False)
    checked = 0
    for row in sample.iter_rows(named=True):
        d = row["trading_date"]
        # keep only bars that had CLOSED by the moment the signal was published
        cut = bars.filter(pl.col("bar_end_ns") <= row["signal_ns"])
        got = _run_day(cfg, cut, sb[d], amap[d], d)
        keys = {(g.family, round(g.level, 4), g.a_ns, g.b_ns, g.c_ns, g.signal_ns,
                 g.trigger_type, round(g.stop, 4)) for g in got}
        want = (row["family"], round(row["level"], 4), row["a_ns"], row["b_ns"],
                row["c_ns"], row["signal_ns"], row["trigger_type"], round(row["stop"], 4))
        assert want in keys, f"signal on {d} not reproducible from truncated history"
        checked += 1
    assert checked == 25


def test_no_signal_uses_a_bar_that_had_not_closed(world):
    """Every A/B/C/trigger timestamp is a bar END, and the signal is the last of them."""
    trades = pl.read_parquet(ROOT / "results" / "fast_slow_dev" / "trades_ANY.parquet")
    step = 120_000_000_000
    for col in ("a_ns", "b_ns", "c_ns", "signal_ns"):
        assert (trades[col] % step == 0).all(), f"{col} is not on a bar boundary"
    assert (trades["signal_ns"] >= trades["c_ns"]).all()
    assert (trades["c_ns"] > trades["b_ns"]).all()
    assert (trades["b_ns"] > trades["a_ns"]).all()
    acc = trades.filter(pl.col("status") == "ACCEPTED")
    assert (acc["entry_ns"] >= acc["signal_ns"] + 250_000_000).all()
    assert (acc["r1_exit_ns"] >= acc["entry_ns"]).all()
    assert (acc["r2_exit_ns"] >= acc["entry_ns"]).all()


def test_levels_never_come_from_the_future(world):
    cfg, bars, sb, amap = world
    trades = pl.read_parquet(ROOT / "results" / "fast_slow_dev" / "trades_ANY.parquet")
    segs = {(s.trading_date, s.family, round(s.price, 4)): s
            for day in sb.values() for s in day}
    for row in trades.head(500).iter_rows(named=True):
        s = segs[(row["trading_date"], row["family"], round(row["level"], 4))]
        assert s.valid_from_ns <= row["a_ns"], "pattern started before its level existed"
        assert s.source_date <= row["trading_date"]
