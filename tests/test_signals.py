import numpy as np
import pytest
from nqr.signals.fast_slow import detect_abc, time_ratio_bucket
from nqr.signals import triggers as TG

STEP = 120_000_000_000


def series(pairs):
    """pairs = [(high, low), ...] -> arrays with contiguous 2-minute bar ends."""
    h = np.array([p[0] for p in pairs], float)
    l = np.array([p[1] for p in pairs], float)
    be = np.arange(1, len(pairs) + 1, dtype=np.int64) * STEP
    return h, l, be


BASE = dict(min_ab_dist=10.0, min_ab_bars=2, max_ab_bars=60, max_bc_bars=240,
            time_ratio_min=2.0, dist_ratio_min=0.90, dist_ratio_max=1.25,
            step_ns=STEP)


def test_basic_up_excursion_gives_long():
    # level 100, tol 1.  touch, fast up to 130 in 3 bars, slow return in 9 bars
    pairs = [(101, 99)]                                     # A (touch)
    pairs += [(112, 105), (124, 115), (131, 126)]           # up leg, B at bar 3
    pairs += [(130, 124), (127, 121), (124, 118), (121, 115), (118, 112),
              (115, 109), (112, 106), (109, 104), (106, 102)]   # slow return
    pairs += [(104, 99.5)]                                  # C touches
    h, l, be = series(pairs)
    got = detect_abc(h, l, be, 100.0, 1.0, **BASE)
    assert len(got) == 1
    a = got[0]
    assert a.reject is None
    assert a.direction == 1
    assert a.a_idx == 0 and a.b_idx == 3 and a.c_idx == 13
    assert a.b_price == 131.0
    assert a.ab_dist == 31.0
    assert a.ab_ns == 3 * STEP and a.bc_ns == 10 * STEP
    assert a.time_ratio == pytest.approx(10 / 3)


def test_down_excursion_c_price_is_return_direction_extreme():
    pairs = [(101, 99)] + [(95, 88), (85, 76), (74, 69)]
    pairs += [(80, 74), (84, 78), (88, 82), (90, 85), (92, 87), (94, 89),
              (95, 91), (96, 92), (97, 93)] + [(101, 99.5)]
    h, l, be = series(pairs)
    g = [x for x in detect_abc(h, l, be, 100.0, 1.0, **BASE) if x.reject is None][0]
    assert g.c_price == 101.0            # the C bar's HIGH, because the return was upward
    assert g.bc_dist == pytest.approx(32.0)


def test_down_excursion_gives_short():
    pairs = [(101, 99)]
    pairs += [(95, 88), (85, 76), (74, 69)]
    pairs += [(80, 74), (84, 78), (88, 82), (90, 85), (92, 87), (94, 89),
              (95, 91), (96, 92), (97, 93)]
    pairs += [(101, 99.5)]
    h, l, be = series(pairs)
    got = [g for g in detect_abc(h, l, be, 100.0, 1.0, **BASE) if g.reject is None]
    assert got and got[0].direction == -1 and got[0].b_price == 69.0


def test_time_ratio_below_2_is_rejected():
    pairs = [(101, 99)] + [(112, 105), (124, 115), (131, 126)] + \
            [(120, 110), (110, 101)] + [(104, 99.5)]
    h, l, be = series(pairs)
    got = detect_abc(h, l, be, 100.0, 1.0, keep_rejects=True, **BASE)
    assert len(got) == 1 and got[0].reject == "TIME_RATIO_TOO_LOW"


def test_small_ab_move_rejected():
    pairs = [(101, 99)] + [(103, 101.5), (104, 102), (105, 103)] + \
            [(104.5, 102)] * 8 + [(101, 99.5)]
    h, l, be = series(pairs)
    got = detect_abc(h, l, be, 100.0, 1.0, keep_rejects=True, **BASE)
    assert got and got[0].reject == "AB_MOVE_TOO_SMALL"


def test_blow_through_rejected_by_distance_ratio():
    # C bar smashes far below the level -> BC/AB > 1.25
    pairs = [(101, 99)] + [(112, 105), (124, 115), (131, 126)] + \
            [(128, 122)] * 9 + [(120, 80)]
    h, l, be = series(pairs)
    got = detect_abc(h, l, be, 100.0, 1.0, keep_rejects=True, **BASE)
    assert got and got[0].reject == "DIST_RATIO_OUT_OF_RANGE"


def test_a_is_last_touching_bar_of_a_cluster():
    pairs = [(101, 99), (100.8, 99.2), (101, 98.9)]         # 3-bar touch cluster
    pairs += [(112, 105), (124, 115), (131, 126)]
    pairs += [(128, 122)] * 9 + [(104, 99.5)]
    h, l, be = series(pairs)
    got = [g for g in detect_abc(h, l, be, 100.0, 1.0, **BASE) if g.reject is None]
    assert got and got[0].a_idx == 2


def test_one_candidate_per_departure_no_duplicates():
    """Two separate departure/return cycles must give exactly two candidates."""
    cyc = [(112, 105), (124, 115), (131, 126)] + [(128, 122)] * 9 + [(104, 99.5)]
    pairs = [(101, 99)] + cyc + cyc
    h, l, be = series(pairs)
    got = [g for g in detect_abc(h, l, be, 100.0, 1.0, **BASE) if g.reject is None]
    assert len(got) == 2


def test_excursion_straddling_the_level_is_discarded():
    pairs = [(101, 99)] + [(130, 120), (80, 70), (130, 120)] + [(128, 122)] * 9 + [(104, 99.5)]
    h, l, be = series(pairs)
    got = detect_abc(h, l, be, 100.0, 1.0, keep_rejects=True, **BASE)
    assert got == []


def test_untraded_gap_cannot_fake_a_fast_leg():
    """Same bar indices, but a 1-hour hole inside A->B makes the leg slow."""
    pairs = [(101, 99)] + [(112, 105), (124, 115), (131, 126)] + \
            [(128, 122)] * 9 + [(104, 99.5)]
    h, l, be = series(pairs)
    be2 = be.copy()
    be2[2:] += 30 * STEP                      # one hour missing between bar1 and bar2
    ok = [g for g in detect_abc(h, l, be, 100.0, 1.0, **BASE) if g.reject is None]
    slow = detect_abc(h, l, be2, 100.0, 1.0, keep_rejects=True, **BASE)
    assert ok and slow[0].reject == "TIME_RATIO_TOO_LOW"


def test_time_ratio_buckets():
    assert time_ratio_bucket(1.9) == "<2.0"
    assert time_ratio_bucket(2.0) == "2.0-2.5"
    assert time_ratio_bucket(2.7) == "2.5-3.0"
    assert time_ratio_bucket(9.0) == ">=3.0"
