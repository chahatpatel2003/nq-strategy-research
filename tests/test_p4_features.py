"""Phase-4 causal feature tests.

The master test is `test_features_are_invariant_to_truncating_the_future`:
rebuild the whole state vector from a tape that has been cut off immediately
after the decision timestamp and require every one of the 55 features to be
bit-identical.  A feature that peeked at even one future print cannot survive it.
"""
import datetime as dt

import numpy as np
import polars as pl
import pytest

from nqr.p2 import features as FT
from nqr.p4 import cache4
from nqr.p4 import features4 as F4

TICK = F4.TICK
NS = F4.NS
DAY = dt.date(2021, 3, 10)
PDH, PDL = 12867.5, 12326.0


@pytest.fixture(scope="module")
def day_ticks():
    m = cache4.load_month("2021-03")
    if m.height == 0:
        pytest.skip("phase-4 tick cache not built")
    return m.filter(pl.col("trading_date") == DAY)


@pytest.fixture(scope="module")
def grid(day_ticks):
    return F4.build_grid(day_ticks, F4.et_sec(DAY, F4.BAND_START_ET),
                         F4.et_sec(DAY, F4.BAND_END_ET))


@pytest.fixture(scope="module")
def state(grid):
    return F4.build_state_matrix(grid, DAY, PDH, PDL)


# ---------------------------------------------------------- registry ----
def test_registry_conformance():
    assert len(F4.FEATURE_NAMES) == 55
    assert len(set(F4.FEATURE_NAMES)) == 55
    assert len(F4.FEATURE_NAMES) <= 60                     # SEARCH_BUDGET cap
    sizes = {}
    for n in F4.FEATURE_NAMES:
        sizes[F4.FAMILY_OF[n]] = sizes.get(F4.FAMILY_OF[n], 0) + 1
    assert sizes == {1: 8, 2: 5, 3: 7, 4: 9, 5: 6, 6: 6, 7: 3, 8: 6, 9: 5}


def test_return_horizons_are_the_registered_six():
    assert F4.RET_HORIZONS == (5, 15, 30, 60, 120, 300)


# ------------------------------------------------- the master causality ----
@pytest.mark.parametrize("hhmm", ["10:15", "11:00", "11:29:55"])
def test_features_are_invariant_to_truncating_the_future(day_ticks, state, grid, hhmm):
    parts = hhmm.split(":")
    t_dec = F4.et_sec(DAY, ":".join(parts[:2])) + (int(parts[2]) if len(parts) > 2 else 0)
    gi = t_dec - grid["sec0"] - 1

    cut = day_ticks.filter(pl.col("ts_ns") < t_dec * NS)
    g2 = F4.build_grid(cut, F4.et_sec(DAY, F4.BAND_START_ET), t_dec)
    s2 = F4.build_state_matrix(g2, DAY, PDH, PDL)
    assert s2 is not None
    gi2 = t_dec - g2["sec0"] - 1
    assert gi2 == g2["n"] - 1

    full = state["X"][gi]
    trunc = s2["X"][gi2]
    bad = [F4.FEATURE_NAMES[j] for j in range(55)
           if not (np.isclose(full[j], trunc[j], rtol=1e-9, atol=1e-9)
                   or (np.isnan(full[j]) and np.isnan(trunc[j])))]
    assert not bad, f"features changed when the future was removed: {bad}"
    assert np.isclose(state["r_points"][gi], s2["r_points"][gi2])


# --------------------------------------------------------- ATR / vol ----
def test_atr_uses_only_completed_minutes(grid):
    """Rewriting the CURRENT minute must not move the ATR published inside it."""
    g = dict(grid)
    atr_a, _ = F4.causal_atr(g)
    k = 8000                                    # some second well inside the day
    m0 = (g["sec0"] + k) // 60
    lo = int(m0 * 60 - g["sec0"]); hi = lo + 60
    g2 = {kk: (v.copy() if isinstance(v, np.ndarray) else v) for kk, v in g.items()}
    g2["high"][lo:hi] += 500.0                  # violent range in the live minute
    g2["low"][lo:hi] -= 500.0
    atr_b, _ = F4.causal_atr(g2)
    assert np.allclose(atr_a[lo:hi], atr_b[lo:hi], equal_nan=True)


def test_causal_atr_matches_frozen_phase2_implementation(grid):
    _, m = F4._minute_bars(grid)
    ref = FT.causal_atr_minutes(m, F4.ATR_LOOKBACK)
    atr, mine = F4.causal_atr(grid)
    assert np.allclose(ref["atr_prev"].to_numpy(), mine["atr_prev"].to_numpy(),
                       equal_nan=True)


def test_atr_floor_and_r_rule():
    assert F4.ATR_FLOOR == 2.0
    a = np.array([0.5, 2.0, 10.0, 100.0])
    assert np.allclose(F4.r_from_atr(np.maximum(a, F4.ATR_FLOOR)), [1.0, 1.0, 5.0, 25.0])


def test_trailing_percentile_is_strictly_prior(state, grid):
    """atr_pct_rank at a second may not know its own minute's rank neighbours."""
    j = F4.FEATURE_NAMES.index("atr_pct_rank")
    v = state["X"][:, j]
    fin = v[np.isfinite(v)]
    assert fin.min() >= 0.0 and fin.max() <= 1.0
    # a strictly-prior rank over <=120 values can never be an exact 1/N of a
    # window that includes itself: verify against a direct recomputation
    minute, m = F4._minute_bars(grid)
    atr_m = FT.causal_atr_minutes(m, F4.ATR_LOOKBACK)
    mins = atr_m["minute"].to_numpy(); vals = atr_m["atr_prev"].to_numpy()
    k = 200
    prior = vals[max(0, k - F4.PCT_RANK_MINUTES):k]
    prior = prior[np.isfinite(prior)]
    want = float((prior <= vals[k]).mean())
    sec = int(mins[k] * 60 - grid["sec0"])
    assert np.isclose(state["X"][sec, j], want)


# ------------------------------------------------------- fixed horizons ----
def test_fixed_horizon_returns_match_a_direct_computation(state, grid):
    c = grid["close"]; atr = state["atr"]
    i = 12000
    for h in F4.RET_HORIZONS:
        j = F4.FEATURE_NAMES.index(f"ret_norm_{h}")
        want = (c[i] - c[i - h]) / (atr[i] * np.sqrt(h / 60.0))
        assert np.isclose(state["X"][i, j], want)


def test_rolling_windows_are_trailing_and_closed():
    a = np.arange(10.0)
    assert np.allclose(F4._roll_sum(a, 3)[5], a[3] + a[4] + a[5])
    assert F4._roll_max(a, 3)[5] == 5.0
    assert F4._roll_min(a, 3)[5] == 3.0
    assert np.isnan(F4._shift(a, 3)[2]) and F4._shift(a, 3)[5] == 2.0


def test_trailing_extremes_never_see_the_future():
    a = np.array([1.0, 5.0, 2.0, 9.0, 3.0])
    assert list(F4._roll_max(a, 3)) == [1.0, 5.0, 5.0, 9.0, 9.0]
    assert list(F4._secs_since_extreme(a, 3, True)) == [0, 0, 1, 0, 1]


# ------------------------------------------------------ trade side / delta ----
def test_grid_splits_volume_by_the_native_side_field():
    ts0 = 1_600_000_000
    df = pl.DataFrame({
        "ts_ns": [ts0 * NS + i for i in range(4)] + [(ts0 + 1) * NS],
        "px_ticks": [100, 101, 100, 102, 103],
        "size": [1, 2, 3, 4, 5],
        "side_raw": [1, -1, 1, 0, -1],
        "symbol": ["NQZ0"] * 5, "row_seq": list(range(5)),
    })
    df = pl.concat([df, df.with_columns(pl.col("ts_ns") + 2 * NS)] * 200).sort("ts_ns")
    g = F4.build_grid(df, ts0, ts0 + 10)
    assert g["buy"][0] == 4 * 200 and g["sell"][0] == 2 * 200
    assert g["vol"][0] == 10 * 200                      # side 0 counts in volume
    assert g["cnt"][0] == 4 * 200
    assert g["maxsz"][0] == 4


def test_cumulative_delta_starts_at_the_open_and_is_bounded(state, grid):
    j = F4.FEATURE_NAMES.index("cum_delta_norm")
    v = state["X"][:, j]
    i_open = state["i_open"]
    assert np.all(v[:i_open + 1] == 0.0)                 # nothing before 09:30
    fin = v[np.isfinite(v)]
    assert fin.min() >= -1.0 and fin.max() <= 1.0


def test_delta_per_vol_is_a_signed_share(state):
    for nm in ("delta_per_vol_60", "delta_per_vol_300"):
        v = state["X"][:, F4.FEATURE_NAMES.index(nm)]
        fin = v[np.isfinite(v)]
        assert fin.min() >= -1.0 - 1e-9 and fin.max() <= 1.0 + 1e-9


# ------------------------------------------------------ event causality ----
def test_dc_context_matches_the_frozen_phase3_runner(day_ticks, grid):
    """Family 9 must reproduce the frozen Phase-3 engine exactly."""
    import yaml
    from strategies.directional_change.runner import build_day_path, run_day
    cfg = yaml.safe_load(open("strategies/directional_change/config/baseline.yaml"))
    p = build_day_path(day_ticks, cfg, DAY)
    evs, _ = run_day(p, cfg)
    ref = [(e.conf_ts, e.direction, round(e.dc_magnitude, 6)) for e in evs
           if e.conf_ts >= grid["ts"][0]]

    atr, _ = F4.causal_atr(grid)
    mine_all = F4._dc_events_for_test(grid, atr)
    mine = [(e.conf_ts, e.direction, round(e.dc_magnitude, 6)) for e in mine_all]
    assert mine == ref


def test_dc_features_only_use_confirmed_events(grid, state):
    """secs_since_last_dc is never negative: an event is unknown before conf."""
    j = F4.FEATURE_NAMES.index("secs_since_last_dc")
    v = state["X"][:, j]
    assert np.nanmin(v) >= 0.0
    assert np.nanmax(v) <= 3600.0


# --------------------------------------------------- clock and sessions ----
@pytest.mark.parametrize("d", [dt.date(2021, 3, 10),    # EDT (after the switch)
                               dt.date(2021, 1, 20),    # EST
                               dt.date(2021, 3, 15),    # first EDT Monday
                               dt.date(2021, 11, 8)])   # first EST Monday
def test_decision_clock_is_5s_and_dst_correct(d):
    g = {"sec0": F4.et_sec(d, F4.BAND_START_ET),
         "n": F4.et_sec(d, F4.BAND_END_ET) - F4.et_sec(d, F4.BAND_START_ET)}
    prim = F4.decision_indices(g, d, F4.SESSION_START_ET, F4.SESSION_END_ET)
    assert len(prim) == 1440                                   # 2 h / 5 s
    assert np.all(np.diff(prim) == F4.DECISION_STEP_S)
    first_ts = g["sec0"] + prim[0] + 1
    assert first_ts == F4.et_sec(d, "09:30")                   # exactly the open
    last_ts = g["sec0"] + prim[-1] + 1
    assert last_ts == F4.et_sec(d, "11:30") - 5
    full = F4.decision_indices(g, d, F4.SESSION_START_ET, F4.DIAG_END_ET)
    assert len(full) == 4680                                   # 6.5 h / 5 s


def test_et_sec_tracks_dst_offsets():
    assert F4.et_sec(dt.date(2021, 1, 20), "09:30") % 86400 == (14 * 3600 + 30 * 60)
    assert F4.et_sec(dt.date(2021, 7, 20), "09:30") % 86400 == (13 * 3600 + 30 * 60)


def test_session_features_are_anchored_on_the_open(state):
    i_open = state["i_open"]
    j = F4.FEATURE_NAMES.index("secs_since_open")
    assert state["X"][i_open, j] == 0.0
    k = F4.FEATURE_NAMES.index("is_second_hour")
    assert state["X"][i_open, k] == 0.0
    assert state["X"][i_open + 3600, k] == 1.0


def test_opening_range_is_zero_until_it_completes(state):
    for nm in ("dist_or30_hi_norm", "dist_or30_lo_norm"):
        v = state["X"][:, F4.FEATURE_NAMES.index(nm)]
        assert np.all(v[:state["i_or_end"]] == 0.0)
    assert state["or_hi"] >= state["or_lo"]


# ----------------------------------- regressions for the recovered defects ----
def test_grid_high_low_are_not_nan_poisoned():
    """Regression: NaN-seeded maximum.at wiped out every high and low."""
    ts0 = 1_600_000_000
    df = pl.DataFrame({"ts_ns": [ts0 * NS + i * 1000 for i in range(600)],
                       "px_ticks": (100 + np.arange(600) % 7).tolist(),
                       "size": [1] * 600, "side_raw": [1] * 600,
                       "symbol": ["NQZ0"] * 600, "row_seq": list(range(600))})
    g = F4.build_grid(df, ts0, ts0 + 5)
    assert np.isfinite(g["high"]).all() and np.isfinite(g["low"]).all()
    assert g["high"][0] == 106 * TICK and g["low"][0] == 100 * TICK


def test_grid_open_and_close_are_first_and_last_print():
    """Regression: duplicate fancy-index assignment relied on 'last write wins'."""
    ts0 = 1_600_000_000
    px = [100, 140, 90, 120]
    df = pl.DataFrame({"ts_ns": [ts0 * NS + i for i in range(4)] * 150,
                       "px_ticks": px * 150, "size": [1] * 600, "side_raw": [1] * 600,
                       "symbol": ["NQZ0"] * 600, "row_seq": list(range(600))}).sort("ts_ns")
    g = F4.build_grid(df, ts0, ts0 + 3)
    assert g["open"][0] == 100 * TICK and g["close"][0] == 120 * TICK
    assert g["high"][0] == 140 * TICK and g["low"][0] == 90 * TICK


def test_untraded_seconds_carry_the_last_past_price(grid):
    """Regression: polars treats np.nan as a value, so forward_fill was a no-op."""
    assert np.isfinite(grid["close"]).all()
    untraded = np.flatnonzero(~grid["traded"])
    assert untraded.size > 0                              # the day really has gaps
    k = int(untraded[untraded > 100][0])
    assert grid["close"][k] == grid["close"][k - 1]
    assert grid["high"][k] == grid["close"][k] == grid["low"][k]


def test_no_feature_is_nan_on_a_real_session(state, grid):
    idx = F4.decision_indices(grid, DAY, F4.SESSION_START_ET, F4.DIAG_END_ET)
    X = state["X"][idx]
    assert np.isfinite(X).all(), "non-finite features on a normal trading day"
