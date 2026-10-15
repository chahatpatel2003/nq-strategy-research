"""Phase-6: causal context activation, the six entry mechanics, controls, budget."""
import datetime as dt
import hashlib
import json
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from nqr.p4 import features4 as F4
from nqr.p5 import dataset5
from nqr.p6 import backtest6 as BT
from nqr.p6 import context6 as C6
from nqr.p6 import holdout6 as H6

ROOT = Path(__file__).resolve().parents[1]
NS = C6.NS
DAY = dt.date(2021, 6, 1)
OPEN_S = F4.et_sec(DAY, "09:30")

FROZEN_IDS = {
    "results/frozen_manifest.json": "fastslow-1.0.0+5980044a44eebf7b",
    "results/p2_frozen_manifest.json": "impexh-1.0.0.impl2+48c76a0e68b88947",
    "results/p3_frozen_manifest.json": "dcevent-1.0.0.impl3+d33e5d5d116f1adb",
    "results/p4_frozen_manifest.json": "statedisc-1.0.0+c147134184dfb32d",
}


def tape(prices, t_start_s, step_ms=500):
    """Tick tape starting at an absolute epoch second."""
    ts = np.array([t_start_s * NS + i * step_ms * 1_000_000 for i in range(len(prices))],
                  dtype=np.int64)
    return ts, np.asarray(prices, dtype=np.int64)


def grid(n_min=120):
    """Decision grid arrays for one session: 120 one-minute decisions."""
    sec = np.arange(0, n_min * 60, 60, dtype=np.int64)
    return (OPEN_S + sec) * NS, sec


# ------------------------------------------------- previous phases frozen ----
@pytest.mark.parametrize("rel,fid", sorted(FROZEN_IDS.items()))
def test_previous_phase_manifests_match_disk(rel, fid):
    man = json.loads((ROOT / rel).read_text())
    assert man["frozen_id"] == fid
    assert not [f for f, d in man["files"].items()
                if hashlib.sha256((ROOT / f).read_bytes()).hexdigest() != d]


def test_phase6_defines_no_features_and_no_new_R():
    src = "".join(f.read_text() for f in (ROOT / "src" / "nqr" / "p6").glob("*.py"))
    assert "FEATURE_NAMES = " not in src
    assert "R_MULTS = " not in src, "Phase 6 must not redefine R"
    assert dataset5.R_MULTS["r4p0"] == 4.0


# ---------------------------------------------------- context activation ----
def _ctx_args(score, direction, ok=None, r=40.0):
    dec, sec = grid()
    n = len(sec)
    ok = np.ones(n, bool) if ok is None else ok
    return dec, sec, np.asarray(score, float), np.asarray(direction), np.full(n, r), ok


def test_context_activates_on_the_FIRST_qualifying_signal_in_a_bucket():
    dec, sec, sc, dr, r, ok = _ctx_args(np.zeros(120), np.ones(120, int))
    sc[3] = 0.5      # 09:33  -> should activate bucket 0
    sc[9] = 0.9      # 09:39  -> higher score, but LATER: must NOT be used
    ts, px = tape([40000] * 40000, OPEN_S - 60, step_ms=250)
    cs = C6.build_contexts(DAY, "NQM1", dec, sec, sc, dr, r, ok, 0.2, ts, px)
    assert len(cs) == 1
    assert cs[0].bucket == 0
    assert cs[0].activation_ts == int(dec[3])
    assert cs[0].score == 0.5, "a later, higher score must not define the context"
    assert cs[0].n_qualifying == 2


def test_direction_is_locked_for_the_rest_of_the_bucket():
    dec, sec, sc, dr, r, ok = _ctx_args(np.zeros(120), np.ones(120, int))
    sc[2] = 0.5; dr[2] = 1
    sc[8] = 0.9; dr[8] = -1          # later flip must be ignored
    ts, px = tape([40000] * 40000, OPEN_S - 60, step_ms=250)
    cs = C6.build_contexts(DAY, "NQM1", dec, sec, sc, dr, r, ok, 0.2, ts, px)
    assert len(cs) == 1 and cs[0].direction == 1


def test_at_most_one_context_per_bucket_and_four_buckets():
    dec, sec, sc, dr, r, ok = _ctx_args(np.zeros(120), np.ones(120, int))
    for i in (1, 5, 31, 35, 61, 91):   # two in bucket 0, two in bucket 1, one each in 2,3
        sc[i] = 0.5
    ts, px = tape([40000] * 40000, OPEN_S - 60, step_ms=250)
    cs = C6.build_contexts(DAY, "NQM1", dec, sec, sc, dr, r, ok, 0.2, ts, px)
    assert [c.bucket for c in cs] == [0, 1, 2, 3]
    assert cs[0].activation_ts == int(dec[1]) and cs[1].activation_ts == int(dec[31])


def test_no_qualifying_signal_means_no_context():
    dec, sec, sc, dr, r, ok = _ctx_args(np.zeros(120), np.ones(120, int))
    ts, px = tape([40000] * 40000, OPEN_S - 60, step_ms=250)
    assert C6.build_contexts(DAY, "NQM1", dec, sec, sc, dr, r, ok, 0.2, ts, px) == []


def test_bucket_bounds_are_the_four_half_hours_and_dst_correct():
    for d in (dt.date(2021, 1, 20), dt.date(2021, 7, 20)):
        o = F4.et_sec(d, "09:30")
        for b in range(4):
            b0, b1 = C6.bucket_bounds(d, b)
            assert b0 == o + b * 1800 and b1 == o + (b + 1) * 1800
        assert C6.bucket_bounds(d, 3)[1] == F4.et_sec(d, "11:30")


def test_context_uses_no_information_after_its_activation_timestamp():
    """Truncate the whole future and the context must be identical."""
    dec, sec, sc, dr, r, ok = _ctx_args(np.zeros(120), np.ones(120, int))
    sc[4] = 0.5
    ts, px = tape(list(40000 + np.arange(40000) % 17), OPEN_S - 60, step_ms=250)
    full = C6.build_contexts(DAY, "NQM1", dec, sec, sc, dr, r, ok, 0.2, ts, px)[0]
    cut = int(dec[4]) + 5 * NS
    keep = ts < cut
    sc2 = sc.copy(); sc2[5:] = 0.0            # delete every later signal
    trunc = C6.build_contexts(DAY, "NQM1", dec, sec, sc2, dr, r, ok, 0.2,
                              ts[keep], px[keep])[0]
    assert (full.activation_ts, full.direction, full.r_points, full.act_price) == \
           (trunc.activation_ts, trunc.direction, trunc.r_points, trunc.act_price)


# -------------------------------------------------------- entry mechanics ----
def _ctx(direction=1, r=40.0, act_price=10000.0, act_sec=OPEN_S, act_idx=0):
    b0, b1 = C6.bucket_bounds(DAY, 0)
    return C6.Context(DAY, "NQM1", 0, act_sec * NS, direction, 0.5, r, b1 * NS,
                      act_idx, act_sec * NS, act_price, 1, 0)


def test_E1_and_E2_are_exactly_5_and_10_minutes():
    assert C6.E1_DELAY_S == 300 and C6.E2_DELAY_S == 600
    ts, px = tape([40000] * 8000, OPEN_S, step_ms=500)
    c = _ctx()
    for meth, delay in (("E1", 300), ("E2", 600)):
        trig, i, ets, epx = C6.entry_of(meth, ts, px, c)
        assert trig == c.activation_ts + delay * NS
        assert ets >= trig + C6.LATENCY_NS


def test_delay_entry_is_refused_if_it_would_fall_outside_the_bucket():
    b0, b1 = C6.bucket_bounds(DAY, 0)
    c = _ctx(act_sec=b1 - 120)                     # only 2 minutes of bucket left
    ts, px = tape([40000] * 4000, b1 - 130, step_ms=500)
    assert C6.entry_of("E1", ts, px, c) is None
    assert C6.entry_of("E2", ts, px, c) is None


def test_E3_and_E4_trigger_on_the_adverse_threshold_only():
    assert C6.E3_PULLBACK_R == 0.25 and C6.E4_PULLBACK_R == 0.50
    # LONG, act 10000.0, R 40 -> E3 level 9990.0 (39960 t), E4 level 9980.0 (39920 t)
    prices = [40000] * 10 + [39955] * 10 + [39915] * 10 + [40100] * 100
    ts, px = tape(prices, OPEN_S, step_ms=500)
    c = _ctx(act_price=10000.0)
    e3 = C6.entry_of("E3", ts, px, c)
    e4 = C6.entry_of("E4", ts, px, c)
    assert e3 is not None and e4 is not None
    assert e3[0] == int(ts[10])                   # 9988.75, first print at/below 9990.0
    assert e4[0] == int(ts[20])                   # 9978.75, first print at/below 9980.0
    assert e3[0] < e4[0]
    # and a tape that only reaches 9991.25 must trigger neither
    ts2, px2 = tape([40000] * 10 + [39965] * 200, OPEN_S, step_ms=500)
    assert C6.entry_of("E3", ts2, px2, c) is None


def test_pullback_that_never_happens_gives_no_trade():
    ts, px = tape([40000] * 200 + [40500] * 200, OPEN_S, step_ms=500)
    c = _ctx(act_price=10000.0)
    assert C6.entry_of("E3", ts, px, c) is None
    assert C6.entry_of("E5", ts, px, c) is None


def test_short_mirrors_long_exactly():
    up = [40000] * 10 + [40045] * 200
    ts, px = tape(up, OPEN_S, step_ms=500)
    c = _ctx(direction=-1, act_price=10000.0)     # SHORT: adverse is UP
    e = C6.entry_of("E3", ts, px, c)
    assert e is not None and e[0] == int(ts[10])


def test_E5_E6_require_a_resumption_off_the_CAUSAL_running_extreme():
    assert C6.RESUME_R == 0.125
    # LONG R=40: pullback level 9990; resume needs +5.0 pt off the running low.
    prices = ([40000] * 5 + [39960] * 5 + [39900] * 5 + [39910] * 5 + [39940] * 200)
    ts, px = tape(prices, OPEN_S, step_ms=500)
    c = _ctx(act_price=10000.0)
    e5 = C6.entry_of("E5", ts, px, c)
    assert e5 is not None
    # running low at index 10..14 is 9975.0; +5 pt -> 9980.0 first reached at index 20
    assert e5[0] == int(ts[20])


def test_E5_never_uses_the_eventual_low_only_the_low_so_far():
    """A deeper low AFTER the entry must not move the entry earlier."""
    base = [40000] * 5 + [39960] * 5 + [39985] * 5
    late = [39800] * 50 + [40000] * 50            # much deeper, but later
    ts, px = tape(base + late, OPEN_S, step_ms=500)
    c = _ctx(act_price=10000.0)
    e = C6.entry_of("E5", ts, px, c)
    assert e is not None and e[0] == int(ts[10])
    ts2, px2 = tape(base + [39990] * 100, OPEN_S, step_ms=500)
    e2 = C6.entry_of("E5", ts2, px2, c)
    assert e2 is not None and e2[0] == e[0], "future prices changed a past decision"


def test_resumption_that_never_completes_gives_no_trade():
    prices = [40000] * 5 + list(39960 - np.arange(300))   # falls forever
    ts, px = tape(prices, OPEN_S, step_ms=500)
    assert C6.entry_of("E5", ts, px, _ctx(act_price=10000.0)) is None


def test_every_entry_is_the_first_print_AFTER_the_trigger_plus_latency():
    ts, px = tape(list(40000 + np.arange(4000) % 23), OPEN_S, step_ms=500)
    c = _ctx(act_price=10000.0)
    for meth in C6.ENTRY_METHODS:
        e = C6.entry_of(meth, ts, px, c)
        if e is None:
            continue
        trig, i, ets, epx = e
        assert ets >= trig + C6.LATENCY_NS
        assert ts[i] == ets
        assert i == 0 or ts[i - 1] < trig + C6.LATENCY_NS, "not the FIRST eligible print"
        assert ets < c.bucket_end_ts


def test_fill_after_bucket_end_is_refused():
    b0, b1 = C6.bucket_bounds(DAY, 0)
    c = _ctx(act_sec=b1 - 400)
    ts, px = tape([40000] * 4, b1 - 410, step_ms=1000)      # tape dies before the trigger
    assert C6.entry_of("E1", ts, px, c) is None


def test_only_six_entry_methods_exist():
    assert C6.ENTRY_METHODS == ("E1", "E2", "E3", "E4", "E5", "E6")
    with pytest.raises(ValueError):
        C6.entry_of("E7", np.array([0]), np.array([0]), _ctx())


# ---------------------------------------------------------------- controls ----
def test_random_control_entries_are_never_before_activation():
    c = _ctx(act_sec=OPEN_S + 600)
    rng = np.random.default_rng(0)
    for _ in range(50):
        for t in C6.random_minutes(c, rng, 10):
            assert t >= c.activation_ts
            assert t < c.bucket_end_ts


def test_random_control_count_shrinks_as_the_bucket_runs_out():
    rng = np.random.default_rng(0)
    early = C6.random_minutes(_ctx(act_sec=OPEN_S), rng, 10)
    late = C6.random_minutes(_ctx(act_sec=OPEN_S + 1740), rng, 10)
    assert len(early) == 10 and len(late) == 1


def test_immediate_control_is_the_activation_fill():
    ts, px = tape([40000] * 100, OPEN_S, step_ms=500)
    c = _ctx(act_idx=7, act_price=10001.25)
    trig, i, ets, epx = C6.entry_immediate(ts, px, c)
    assert i == c.act_idx and epx == c.act_price and trig == c.activation_ts


# -------------------------------------------------- geometry and portfolio ----
def _fake_ctx_list(n, direction=1, r=40.0, gap_s=900):
    out = []
    for k in range(n):
        b = min(3, (k * gap_s) // 1800)
        b0, b1 = C6.bucket_bounds(DAY, b)
        a = OPEN_S + k * gap_s
        out.append(C6.Context(DAY, "NQM1", b, a * NS, direction, 0.5, r, b1 * NS,
                              0, a * NS, 10000.0, 1, k * gap_s))
    return out


def test_one_position_at_a_time_per_method():
    ts, px = tape([40000] * 60000, OPEN_S - 60, step_ms=250)
    cs = _fake_ctx_list(4, gap_s=600)
    rng = np.random.default_rng(0)
    r = BT.run_day(DAY, cs, ts, px, rng, [], np.array([1, -1]))
    for meth in C6.ENTRY_METHODS:
        acc = BT.accepted(BT.frame(r["books"][meth]))
        if acc.height < 2:
            continue
        e = acc["entry_ns"].to_numpy(); x = acc["exit_ns"].to_numpy()
        assert (e[1:] >= x[:-1]).all()


def test_trade_geometry_is_the_frozen_phase5_r4p0():
    ts, px = tape([40000] * 60000, OPEN_S - 60, step_ms=250)
    cs = _fake_ctx_list(1, r=40.0)
    r = BT.run_day(DAY, cs, ts, px, np.random.default_rng(0), [], np.array([1]))
    acc = BT.accepted(BT.frame(r["books"]["E1"]))
    assert acc.height == 1
    t = acc.row(0, named=True)
    assert t["r_points"] == 40.0
    assert np.isclose(t["target"] - t["entry_price"], 40.0)
    assert np.isclose(t["entry_price"] - t["stop"], 40.0)
    assert t["hold_s"] <= dataset5.MAX_HOLD_S + 60      # 60 min + the timeout wait rail
    assert np.isclose(t["friction_over_r"], 1.0 / 40.0)
    for fr in dataset5.FRICTIONS:
        k = str(fr).replace(".", "p")
        assert np.isclose(t[f"net_{k}"], t["points"] - fr)


def test_pf_r_is_computed_in_R_units():
    t = pl.DataFrame({"points": [40.0, -20.0], "r_points": [40.0, 20.0]})
    assert np.isclose(BT.pf_r(t, 0.0), 1.0)            # +1R vs -1R
    t2 = pl.DataFrame({"points": [40.0, -20.0], "r_points": [40.0, 10.0]})
    assert np.isclose(BT.pf_r(t2, 0.0), 0.5)           # +1R vs -2R


# -------------------------------------------------------------- seals ----
@pytest.mark.parametrize("d", [dt.date(2025, 1, 1), dt.date(2025, 6, 30)])
def test_2025_h1_blocked_even_with_the_unlock(d):
    with pytest.raises(H6.Phase6Violation):
        H6.assert_date_allowed(d)
    H6._VAL_UNLOCKED = True
    try:
        with pytest.raises(H6.Phase6Violation):
            H6.assert_date_allowed(d)
    finally:
        H6._VAL_UNLOCKED = False


@pytest.mark.parametrize("d", [dt.date(2026, 4, 1), dt.date(2026, 6, 17)])
def test_april_2026_blocked_even_with_the_unlock(d):
    H6._VAL_UNLOCKED = True
    try:
        with pytest.raises(H6.Phase6Violation):
            H6.assert_date_allowed(d)
    finally:
        H6._VAL_UNLOCKED = False


def test_mbp1_and_raw_dbn_are_refused():
    for p in ("/x/mbp1/2021_H1.parquet", "/x/MBP-1/a.parquet", "/x/a.dbn.zst", "/x/a.dbn"):
        with pytest.raises(H6.Phase6Violation):
            H6.assert_path_allowed(p)


def test_2026_q1_needs_the_phase6_phrase_and_pushes_the_date_predicate():
    with pytest.raises(H6.Phase6Violation):
        H6.unlock_phase6_validation("I_AM_UNLOCKING_ONLY_2026_Q1_FOR_PHASE5_VALIDATION")
    with pytest.raises(H6.Phase6Violation):
        H6.assert_date_allowed(dt.date(2026, 2, 1))
    with pytest.raises(H6.Phase6Violation):
        H6.sql_window_guard(dt.date(2026, 1, 1), dt.date(2026, 12, 31))
    H6._VAL_UNLOCKED = True
    try:
        sql = H6.sql_window_guard(dt.date(2026, 1, 1), dt.date(2026, 3, 31))
    finally:
        H6._VAL_UNLOCKED = False
    assert "DATE '2026-03-31'" in sql and "America/New_York" in sql
