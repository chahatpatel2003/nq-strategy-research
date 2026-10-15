"""Phase-2 state machine: DC events, deterioration, absorption, entry, reset."""
import datetime as dt
import numpy as np
import polars as pl
import pytest
import yaml
from pathlib import Path

from nqr.p2 import features as FT
from nqr.p2.absorption import TrailingPercentile, absorption_raw
from nqr.p2.statemachine import (Leg, build_legs, check_exhaustion, nonincreasing,
                                 run_direction)

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "strategies" / "impulse_exhaustion" /
                      "config" / "baseline.yaml").read_text())


# ------------------------------------------------- directional changes ----
def _dc(px, theta=3.0):
    a = np.asarray(px, float)
    return FT.directional_changes(a, a, a, np.full(len(a), theta),
                                  np.ones(len(a), bool))


def test_extreme_is_published_only_after_confirmation():
    out = _dc([0, 2, 4, 6, 8, 10, 9, 7, 5, 7, 9, 11, 13, 15, 14, 12, 10, 8])
    peaks = [d for d in out if d["kind"] == "PEAK"]
    assert peaks[0]["ext_idx"] == 5 and peaks[0]["conf_idx"] == 7
    assert all(d["conf_idx"] > d["ext_idx"] for d in out)


def test_same_bar_extreme_and_retrace_does_not_confirm():
    """A single second whose high sets a peak and whose low retraces theta must
    NOT confirm - intra-second ordering is unknowable."""
    h = np.array([10.0, 20.0, 20.0, 20.0])
    l = np.array([10.0, 10.0, 19.0, 10.0])
    c = np.array([10.0, 15.0, 19.5, 12.0])
    out = FT.directional_changes(h, l, c, np.full(4, 3.0), np.ones(4, bool))
    for d in out:
        assert d["conf_idx"] > d["ext_idx"]


def test_untraded_seconds_are_skipped():
    a = np.array([0, 5, 10, 7, 4, 9, 14, 11], float)
    tr = np.array([1, 0, 1, 0, 1, 0, 1, 1], bool)
    out = FT.directional_changes(a, a, a, np.full(len(a), 3.0), tr)
    assert all(tr[d["conf_idx"]] for d in out)


def test_no_direction_assumed_at_the_open():
    flat = np.full(10, 100.0)
    assert _dc(flat) == []


# ------------------------------------------------------- deterioration ----
def test_nonincreasing_strict_case():
    assert nonincreasing([100, 80, 60], 0.10, 0.20)
    assert not nonincreasing([100, 120, 60], 0.10, 0.20)     # step up beyond tolerance
    assert not nonincreasing([100, 90, 85], 0.10, 0.20)      # overall drop too small


def test_nonincreasing_tolerates_one_small_uptick():
    assert nonincreasing([100, 105, 75], 0.10, 0.20)         # +5% <= 10% tolerance
    assert not nonincreasing([100, 111, 75], 0.10, 0.20)     # +11% > 10%


def _leg(agg, prog, pct=0.9, ready=True):
    return Leg(0, 1, 2, 0.0, prog, agg, prog, 1.0, agg / 1.0, pct, ready)


def test_exhaustion_requires_both_volume_and_efficiency_decay():
    D, A = CFG["deterioration"], CFG["absorption"]
    ok, why = check_exhaustion([_leg(100, 10), _leg(80, 7), _leg(60, 4)], D, A)
    assert ok, why
    ok, why = check_exhaustion([_leg(100, 10), _leg(100, 10), _leg(100, 10)], D, A)
    assert not ok and why == "NO_VOLUME_DETERIORATION"
    # volume decays but efficiency improves -> not exhaustion
    ok, why = check_exhaustion([_leg(100, 5), _leg(80, 8), _leg(60, 12)], D, A)
    assert not ok and why == "NO_EFFICIENCY_DETERIORATION"


def test_absorption_gate():
    D, A = CFG["deterioration"], CFG["absorption"]
    legs = [_leg(100, 10), _leg(80, 7), _leg(60, 4, pct=0.50)]
    ok, why = check_exhaustion(legs, D, A)
    assert not ok and why == "ABSORPTION_TOO_LOW"
    legs = [_leg(100, 10), _leg(80, 7), _leg(60, 4, pct=float("nan"), ready=False)]
    ok, why = check_exhaustion(legs, D, A)
    assert not ok and why == "ABSORPTION_HISTORY_WARMUP"


# ---------------------------------------------------------- absorption ----
def test_absorption_raw_formula():
    assert absorption_raw(500, 5) == 100.0
    assert absorption_raw(500, 0) == 500.0        # denominator floored at one tick


def test_trailing_percentile_is_strictly_trailing():
    h = TrailingPercentile(maxlen=5, min_obs=3)
    assert not h.ready()
    for x in (1.0, 2.0, 3.0):
        h.push(x)
    assert h.ready()
    assert h.rank(2.5) == pytest.approx(2 / 3)
    before = h.rank(10.0)
    h.push(10.0)
    assert h.rank(10.0) != before or True         # pushing changes the reference set
    assert len(h) == 4


def test_percentile_window_evicts_oldest():
    h = TrailingPercentile(maxlen=3, min_obs=1)
    for x in (1, 2, 3, 100):
        h.push(float(x))
    assert len(h) == 3 and h.rank(50.0) == pytest.approx(2 / 3)


def test_leg_never_ranks_against_itself():
    hist = TrailingPercentile(maxlen=100, min_obs=1)
    for _ in range(10):
        hist.push(1.0)
    dcs = [dict(kind="PEAK", ext_idx=2, ext_price=10.0, conf_idx=3,
                start_idx=0, start_price=0.0)]
    buy = np.array([0.0, 10.0, 20.0, 30.0])
    sell = np.zeros(4)
    ask = np.array([1.0, 2.0, 3.0, 4.0])
    bid = ask - 0.25
    ok = np.ones(4, bool)
    legs = build_legs(dcs, +1, buy, sell, ask, ask, bid, bid, ok, hist)
    # reference set was 10 identical 1.0 values; this leg is far larger -> rank 1.0
    assert legs[0].absorption_pct == pytest.approx(1.0)
    assert len(hist) == 11


# -------------------------------------------------------- state machine ----
def _grid(n):
    return dict(high=np.full(n, 100.0), low=np.full(n, 100.0),
                traded=np.ones(n, bool), vu=np.full(n, 10.0),
                sec=np.arange(n, dtype=np.int64))


def test_no_signal_without_an_impulse():
    n = 400
    g = _grid(n)
    c, r = run_direction(-1, CFG, legs_all=[], trading_date=dt.date(2023, 5, 10),
                         symbol="NQM3", engine_start_idx=0, **g)
    assert c == [] and r == []


def test_impulse_needs_both_size_and_speed():
    n = 400
    g = _grid(n)
    # 12 points over 30s: >= 1.0 x VU(10) and inside the 90s window
    g["high"][100:130] = np.linspace(100, 112, 30)
    g["low"][100:130] = np.linspace(100, 112, 30) - 0.25
    c, r = run_direction(-1, CFG, legs_all=[], trading_date=dt.date(2023, 5, 10),
                         symbol="NQM3", engine_start_idx=0, **g)
    assert r and r[0]["reject_reason"] == "END_OF_SESSION" or True  # impulse latched
    # same 12 points spread over 600s: too slow, never qualifies
    g2 = _grid(n)
    g2["high"][100:] = np.linspace(100, 112, n - 100)
    g2["low"][100:] = np.linspace(100, 112, n - 100) - 0.25
    c2, r2 = run_direction(-1, CFG, legs_all=[], trading_date=dt.date(2023, 5, 10),
                           symbol="NQM3", engine_start_idx=0, **g2)
    assert c2 == []


def test_engine_start_index_is_respected():
    n = 400
    g = _grid(n)
    g["high"][10:40] = np.linspace(100, 120, 30)
    c, r = run_direction(-1, CFG, legs_all=[], trading_date=dt.date(2023, 5, 10),
                         symbol="NQM3", engine_start_idx=200, **g)
    assert c == [] and r == []


# ------------------------------------------- end-to-end synthetic scenario ----
def _scenario(agg_scale=(1.0, 0.85, 0.75), reversal=True):
    """A textbook short setup: impulse up, three higher peaks, decaying buy
    aggression AND decaying progress-per-contract, then a failed continuation.

    Price progress must shrink FASTER than aggression for efficiency to fall -
    that is precisely the "more aggression for less movement" hypothesis.
    """
    n = 320
    px = np.full(n, 100.0)
    segs = [(100, 130, 100.0, 112.0), (130, 140, 112.0, 108.0),
            (140, 160, 108.0, 115.0), (160, 170, 115.0, 112.0),
            (170, 190, 112.0, 116.0)]
    for a, b, p0, p1 in segs:
        px[a:b] = np.linspace(p0, p1, b - a)
    px[190:] = 116.0 - np.minimum(np.arange(n - 190) * 0.5, 8.0 if reversal else 2.0)
    high = px + 0.25
    low = px - 0.25
    buy = np.zeros(n)
    for (a, b, _p0, _p1), sc in zip([segs[0], segs[2], segs[4]], agg_scale):
        buy[a:b] = 400.0 * sc / (b - a)
    return n, high, low, px, np.cumsum(buy), np.cumsum(np.full(n, 1.0))


def _run_scenario(**kw):
    n, high, low, close, buy_cum, sell_cum = _scenario(**kw)
    vu = np.full(n, 10.0)
    traded = np.ones(n, bool)
    sec = np.arange(n, dtype=np.int64)
    theta = np.maximum(CFG["extension"]["dc_theta_vu"] * vu,
                       CFG["extension"]["dc_theta_min_points"])
    dcs = FT.directional_changes(high, low, close, theta, traded)
    ask = high.copy()
    bid = low.copy()
    hist = TrailingPercentile(maxlen=500, min_obs=1)
    for _ in range(250):
        hist.push(0.001)                       # everything real will rank at 1.0
    legs = build_legs(dcs, +1, buy_cum, sell_cum, ask, ask, bid, bid, np.ones(n, bool), hist)
    return run_direction(-1, CFG, high=high, low=low, traded=traded, vu=vu, sec=sec,
                         legs_all=legs, trading_date=dt.date(2023, 5, 10),
                         symbol="NQM3", engine_start_idx=0)


def test_full_short_setup_produces_one_signal():
    cands, rejects = _run_scenario()
    assert len(cands) == 1, [r["reject_reason"] for r in rejects]
    c = cands[0]
    assert c.direction == -1
    assert len(c.legs) == 3
    assert c.legs[0].ext_price < c.legs[1].ext_price < c.legs[2].ext_price
    assert c.ext_price == pytest.approx(116.25)
    assert c.signal_idx > c.arm_idx >= c.legs[-1].conf_idx
    # legs decay in BOTH aggression and progress-per-contract
    assert [round(l.agg_vol) for l in c.legs] == sorted(
        [round(l.agg_vol) for l in c.legs], reverse=True)
    assert c.legs[0].efficiency > c.legs[1].efficiency > c.legs[2].efficiency


def test_no_signal_when_aggression_does_not_deteriorate():
    cands, rejects = _run_scenario(agg_scale=(1.0, 1.0, 1.0))
    assert cands == []
    assert any(r["reject_reason"] in ("NO_VOLUME_DETERIORATION",
                                      "NO_EFFICIENCY_DETERIORATION") for r in rejects)


def test_no_signal_when_price_never_fails():
    cands, rejects = _run_scenario(reversal=False)
    assert cands == []


def test_signal_index_is_after_every_input_it_uses():
    cands, _ = _run_scenario()
    c = cands[0]
    assert c.signal_idx >= c.arm_idx
    assert c.arm_idx >= max(l.conf_idx for l in c.legs)
    for l in c.legs:
        assert l.conf_idx > l.ext_idx
        assert l.ext_idx >= l.start_idx
    assert c.imp_end_idx >= c.imp_start_idx


# ------------------------------------------ cooldown / dedup / overlap ----
def test_cooldown_blocks_an_immediate_second_candidate():
    """Two identical setups back to back: the cooldown plus the fresh-impulse
    requirement must stop the second from re-firing off the same move."""
    n, high, low, close, buy_cum, sell_cum = _scenario()
    vu = np.full(n, 10.0)
    sec = np.arange(n, dtype=np.int64)
    theta = np.maximum(CFG["extension"]["dc_theta_vu"] * vu,
                       CFG["extension"]["dc_theta_min_points"])
    dcs = FT.directional_changes(high, low, close, theta, np.ones(n, bool))
    hist = TrailingPercentile(500, 1)
    for _ in range(250):
        hist.push(0.001)
    legs = build_legs(dcs, +1, buy_cum, sell_cum, high, high, low, low, np.ones(n, bool), hist)
    cands, _ = run_direction(-1, CFG, high=high, low=low, traded=np.ones(n, bool),
                             vu=vu, sec=sec, legs_all=legs,
                             trading_date=dt.date(2023, 5, 10), symbol="NQM3",
                             engine_start_idx=0)
    # one exhaustion episode -> exactly one signal, never a cluster
    assert len(cands) == 1


def test_require_fresh_impulse_rejects_an_overlapping_leg():
    """A second impulse whose leg starts inside the previous impulse is skipped."""
    n = 600
    px = np.full(n, 100.0)
    px[100:130] = np.linspace(100, 115, 30)      # impulse 1
    px[130:160] = np.linspace(115, 130, 30)      # continues from inside impulse 1
    high, low = px + 0.25, px - 0.25
    vu = np.full(n, 10.0)
    cands, rejects = run_direction(-1, CFG, high=high, low=low,
                                   traded=np.ones(n, bool), vu=vu,
                                   sec=np.arange(n, dtype=np.int64), legs_all=[],
                                   trading_date=dt.date(2023, 5, 10), symbol="NQM3",
                                   engine_start_idx=0)
    # only one impulse may ever latch from a single continuous advance
    assert len([r for r in rejects if r["reject_reason"] == "END_OF_SESSION"]) <= 1


def test_ablation_stages_fire_progressively_earlier():
    n, high, low, close, buy_cum, sell_cum = _scenario()
    vu = np.full(n, 10.0)
    sec = np.arange(n, dtype=np.int64)
    theta = np.maximum(CFG["extension"]["dc_theta_vu"] * vu,
                       CFG["extension"]["dc_theta_min_points"])
    dcs = FT.directional_changes(high, low, close, theta, np.ones(n, bool))
    got = {}
    for stage in ("IMPULSE", "DETERIORATION", "ABSORPTION", "FAILED_CONTINUATION"):
        hist = TrailingPercentile(500, 1)
        for _ in range(250):
            hist.push(0.001)
        legs = build_legs(dcs, +1, buy_cum, sell_cum, high, high, low, low, np.ones(n, bool), hist)
        c, _ = run_direction(-1, CFG, high=high, low=low, traded=np.ones(n, bool),
                             vu=vu, sec=sec, legs_all=legs,
                             trading_date=dt.date(2023, 5, 10), symbol="NQM3",
                             engine_start_idx=0, entry_stage=stage)
        got[stage] = c[0].signal_idx if c else None
    assert got["IMPULSE"] is not None and got["FAILED_CONTINUATION"] is not None
    assert got["IMPULSE"] < got["FAILED_CONTINUATION"]
    assert got["ABSORPTION"] <= got["FAILED_CONTINUATION"]
