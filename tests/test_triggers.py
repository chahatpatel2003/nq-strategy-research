import numpy as np
import pytest
from nqr.signals import triggers as TG

CFG = {
    "engulfing": dict(min_prev_body_atr_frac=0.10, min_cur_body_atr_frac=0.30),
    "pin": dict(min_range_atr_frac=0.50, max_body_frac_of_range=0.35,
                min_dom_wick_frac_of_range=0.55, min_dom_wick_over_body=2.0,
                max_opp_wick_frac_of_range=0.20, min_close_location=0.60),
    "star": dict(min_range1_atr_frac=0.50, min_body1_frac_of_range1=0.35,
                 max_body2_over_body1=0.40, min_body3_frac_of_range3=0.35),
}


def arr(*rows):
    a = np.array(rows, float)
    return a[:, 0], a[:, 1], a[:, 2], a[:, 3]


def test_atr2m_is_causal():
    n = 40
    h = np.arange(n, dtype=float) + 10
    l = np.arange(n, dtype=float)
    c = (h + l) / 2
    a = TG.atr2m(h, l, c, 20)
    assert np.isnan(a[:20]).all()
    # value at i must not change if bars from i onward are altered
    h2, l2, c2 = h.copy(), l.copy(), c.copy()
    h2[25:] += 1000
    a2 = TG.atr2m(h2, l2, c2, 20)
    assert a[25] == pytest.approx(a2[25])


def test_bullish_engulfing():
    o, h, l, c = arr((100, 100.5, 97.5, 98), (98, 101.2, 97.8, 101))
    a = np.array([np.nan, 4.0])
    assert TG.engulfing(o, h, l, c, a, **CFG["engulfing"]).tolist() == [0, 1]


def test_bearish_engulfing():
    o, h, l, c = arr((98, 100.5, 97.5, 100), (100, 100.8, 97.2, 97.5))
    a = np.array([np.nan, 4.0])
    assert TG.engulfing(o, h, l, c, a, **CFG["engulfing"]).tolist() == [0, -1]


def test_engulfing_of_a_doji_is_rejected():
    o, h, l, c = arr((100, 100.2, 99.8, 99.99), (99.9, 103, 99.5, 102))
    a = np.array([np.nan, 4.0])
    assert TG.engulfing(o, h, l, c, a, **CFG["engulfing"]).tolist() == [0, 0]


def test_engulfing_requires_full_body_cover():
    # current body misses the previous open by a hair
    o, h, l, c = arr((100, 100.5, 97.5, 98), (98.1, 101, 97.9, 99.9))
    a = np.array([np.nan, 4.0])
    assert TG.engulfing(o, h, l, c, a, **CFG["engulfing"]).tolist() == [0, 0]


def test_hammer_and_shooting_star():
    o, h, l, c = arr((100.0, 100.5, 97.5, 100.4))
    assert TG.pin(o, h, l, c, np.array([4.0]), **CFG["pin"]).tolist() == [1]
    o, h, l, c = arr((100.0, 103.0, 99.9, 100.1))
    assert TG.pin(o, h, l, c, np.array([4.0]), **CFG["pin"]).tolist() == [-1]


def test_pin_rejects_big_body_and_two_sided_wicks():
    o, h, l, c = arr((98.0, 103.0, 97.5, 102.5))          # big body
    assert TG.pin(o, h, l, c, np.array([4.0]), **CFG["pin"]).tolist() == [0]
    o, h, l, c = arr((100.0, 103.0, 97.0, 100.2))         # doji, both wicks long
    assert TG.pin(o, h, l, c, np.array([4.0]), **CFG["pin"]).tolist() == [0]


def test_pin_rejects_tiny_range():
    o, h, l, c = arr((100.0, 100.1, 99.4, 100.05))
    assert TG.pin(o, h, l, c, np.array([4.0]), **CFG["pin"]).tolist() == [0]


def test_morning_star():
    o, h, l, c = arr((104, 104.5, 99.5, 100),     # decisive bearish
                     (99.8, 100.2, 98.5, 99.6),   # small body, extends the low
                     (99.9, 103.5, 99.7, 103.0))  # decisive bullish back over midpoint
    a = np.array([np.nan, np.nan, 4.0])
    assert TG.star(o, h, l, c, a, **CFG["star"]).tolist() == [0, 0, 1]


def test_evening_star():
    o, h, l, c = arr((100, 104.5, 99.5, 104),
                     (104.2, 105.5, 104.1, 104.4),
                     (104.1, 104.3, 100.5, 101.0))
    a = np.array([np.nan, np.nan, 4.0])
    assert TG.star(o, h, l, c, a, **CFG["star"]).tolist() == [0, 0, -1]


def test_star_rejects_when_bar3_fails_midpoint():
    o, h, l, c = arr((104, 104.5, 99.5, 100),
                     (99.8, 100.2, 98.5, 99.6),
                     (99.9, 101.5, 99.7, 101.2))    # closes below midpoint 102
    a = np.array([np.nan, np.nan, 4.0])
    assert TG.star(o, h, l, c, a, **CFG["star"]).tolist() == [0, 0, 0]


def test_no_trigger_while_atr_is_undefined():
    o, h, l, c = arr((100, 100.5, 97.5, 98), (98, 101.2, 97.8, 101))
    a = np.array([np.nan, np.nan])
    assert TG.engulfing(o, h, l, c, a, **CFG["engulfing"]).tolist() == [0, 0]


def test_pattern_bar_counts():
    assert TG.PATTERN_BARS == {"ENGULFING": 2, "PIN": 1, "STAR": 3}
