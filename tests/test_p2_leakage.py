"""Automated lookahead / leakage checks for Phase 2.

These are the mechanised half of reports/PHASE2_LEAKAGE_AUDIT.md.
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

from nqr.holdout import HOLDOUT_START, sql_date_guard
from nqr.p2 import cache2, features as FT
from nqr.p2.absorption import TrailingPercentile
from nqr.p2.statemachine import build_legs

CFG = yaml.safe_load((ROOT / "strategies" / "impulse_exhaustion" /
                      "config" / "baseline.yaml").read_text())
NS = 1_000_000_000


# ---------------------------------------------------- 1. trailing windows ----
def test_rolling_min_is_trailing_only():
    a = np.arange(10, dtype=float)
    r = FT.rolling_min(a, 3)
    assert r[0] == 0 and r[2] == 0 and r[5] == 3
    b = a.copy(); b[6:] = -100
    assert FT.rolling_min(b, 3)[5] == r[5]        # future change cannot alter the past


def test_rolling_max_is_trailing_only():
    a = np.arange(10, dtype=float)
    r = FT.rolling_max(a, 3)
    b = a.copy(); b[6:] = 1e6
    assert FT.rolling_max(b, 3)[5] == r[5]


# ------------------------------------------------- 2. trailing percentile ----
def test_percentile_uses_past_observations_only():
    h = TrailingPercentile(500, 3)
    for x in (1.0, 2.0, 3.0):
        h.push(x)
    r_before = h.rank(2.5)
    h.push(1000.0)
    assert h.rank(2.5) != r_before                # only NEW pushes change it
    assert r_before == pytest.approx(2 / 3)


def test_no_signal_before_history_minimum():
    h = TrailingPercentile(CFG["absorption"]["history_len"],
                           CFG["absorption"]["history_min_obs"])
    for _ in range(CFG["absorption"]["history_min_obs"] - 1):
        h.push(1.0)
    assert not h.ready()
    h.push(1.0)
    assert h.ready()


def test_absorption_history_is_not_a_full_day_or_global_statistic():
    """The window is bounded, so it can never become a whole-sample percentile."""
    h = TrailingPercentile(CFG["absorption"]["history_len"], 1)
    for i in range(5000):
        h.push(float(i))
    assert len(h) == CFG["absorption"]["history_len"]


# ------------------------------------------------------ 3. no future bars ----
def test_atr_of_completed_minutes_only():
    n = 40
    m = pl.DataFrame({"minute": np.arange(n, dtype=np.int64),
                      "open": np.full(n, 100.0), "high": np.full(n, 101.0),
                      "low": np.full(n, 99.0), "close": np.full(n, 100.0),
                      "volume": np.full(n, 1, dtype=np.int64)})
    a = FT.causal_atr_minutes(m, 14)["atr_prev"].to_numpy()
    m2 = m.with_columns(pl.when(pl.col("minute") >= 25).then(pl.lit(1e6))
                        .otherwise(pl.col("high")).alias("high"))
    a2 = FT.causal_atr_minutes(m2, 14)["atr_prev"].to_numpy()
    assert np.allclose(a[:26], a2[:26], equal_nan=True)


def test_densify_never_backfills_from_the_future():
    t0 = 1_700_000_000
    b = FT.second_bars(pl.DataFrame({
        "trading_date": [dt.date(2023, 5, 10)], "symbol": ["NQM3"],
        "ts_ns": [(t0 + 5) * NS], "px_ticks": [400], "size": [1],
        "side_raw": [1], "row_seq": [0]},
        schema_overrides={"px_ticks": pl.Int32, "size": pl.Int32, "side_raw": pl.Int32}))
    g = FT.densify_seconds(b, t0, t0 + 8)
    c = g["close"].to_numpy()
    assert np.isnan(c[:5]).all()                  # nothing is known before the print
    assert (c[5:] == 100.0).all()


# ------------------------------------------- 4. confirmed-extreme delay ----
def test_dc_extremes_are_never_published_at_their_own_index():
    rng = np.random.default_rng(0)
    px = 100 + np.cumsum(rng.normal(0, 0.5, 4000))
    out = FT.directional_changes(px + 0.25, px - 0.25, px,
                                 np.full(len(px), 2.0), np.ones(len(px), bool))
    assert out
    assert all(d["conf_idx"] > d["ext_idx"] for d in out)


def test_legs_only_use_data_up_to_their_own_extreme():
    hist = TrailingPercentile(100, 1)
    hist.push(1.0)
    dcs = [dict(kind="PEAK", ext_idx=2, ext_price=10.0, conf_idx=3,
                start_idx=0, start_price=0.0)]
    buy = np.array([0.0, 10.0, 20.0, 30.0, 999999.0])
    ask = np.array([1.0, 2.0, 3.0, 4.0, 1e6])
    a = build_legs(dcs, +1, buy, np.zeros(5), ask, ask, ask - 0.25, ask - 0.25,
                   np.ones(5, bool), TrailingPercentile(100, 1))
    buy2 = buy.copy(); buy2[3:] = -1e9
    ask2 = ask.copy(); ask2[3:] = -1e9
    b = build_legs(dcs, +1, buy2, np.zeros(5), ask2, ask2, ask2 - 0.25, ask2 - 0.25,
                   np.ones(5, bool), TrailingPercentile(100, 1))
    assert a[0].agg_vol == b[0].agg_vol
    assert a[0].bbo_advance_ticks == b[0].bbo_advance_ticks


# ----------------------------------------------------- 5. holdout sealed ----
def test_sql_guard_still_active_and_on_trading_date():
    g = sql_date_guard("ts_event")
    assert "2025-01-01" in g and "America/New_York" in g and "INTERVAL 6 HOUR" in g


def test_p2_caches_contain_no_holdout_month():
    for d in (cache2.P2_TICKS, cache2.P2_BBO1S):
        ms = cache2.months_available(d)
        if ms:
            assert max(ms) < "2025-01", f"{d} reaches {max(ms)}"


def test_p2_cache_band_excludes_nothing_needed_and_no_2025():
    ms = cache2.months_available(cache2.P2_TICKS)
    if not ms:
        pytest.skip("cache not built")
    tk = cache2.load_month_ticks(ms[-1])
    assert tk["trading_date"].max() < HOLDOUT_START


# ------------------------------------------------- 6. contract causality ----
def test_front_contract_choice_is_causal():
    from nqr.data.contracts import build_front_map
    d = [dt.date(2021, 3, 12), dt.date(2021, 3, 15), dt.date(2021, 3, 16)]
    dv = pl.DataFrame({"trading_date": d * 2,
                       "symbol": ["NQH1"] * 3 + ["NQM1"] * 3,
                       "volume": [900.0, 100.0, 50.0, 100.0, 900.0, 950.0],
                       "n_trades": [9, 1, 1, 1, 9, 9]})
    f = build_front_map(dv).sort("trading_date")
    got = dict(zip(f["trading_date"].to_list(), f["front_symbol"].to_list()))
    assert got[d[1]] == "NQH1"        # decided by d0 volume, not d1's own


# ------------------------------------------- 7. metric correctness regression ----
def test_breakeven_win_rate_matches_the_target_multiple():
    """REGRESSION (impl1 bug): Phase-2 target tags are 'r1p0'/'r1p25'/'r1p5'/'r2p0'.
    The old code only recognised 'r1'/'r2' and silently tested every Phase-2 win
    rate against a 1/3 null instead of 1/2."""
    from nqr.metrics.stats import breakeven_win_rate, rr_of_tag
    assert rr_of_tag("r1") == 1.0 and rr_of_tag("r2") == 2.0
    assert rr_of_tag("r1p0") == 1.0
    assert rr_of_tag("r1p25") == 1.25
    assert rr_of_tag("r1p5") == 1.5
    assert rr_of_tag("r2p0") == 2.0
    assert breakeven_win_rate("r1p0") == pytest.approx(0.5)
    assert breakeven_win_rate("r1") == pytest.approx(0.5)
    assert breakeven_win_rate("r1p25") == pytest.approx(1 / 2.25)
    assert breakeven_win_rate("r1p5") == pytest.approx(0.4)
    assert breakeven_win_rate("r2p0") == pytest.approx(1 / 3)
    assert breakeven_win_rate("r2") == pytest.approx(1 / 3)


def test_one_sided_p_value_direction_is_sane():
    """A win rate BELOW break-even must never produce a small one-sided p-value."""
    from nqr.metrics.stats import binom_p_value
    assert binom_p_value(4, 15, 0.5) > 0.9
    assert binom_p_value(13, 15, 0.5) < 0.01
