"""Directional-change engine: state machine, causality, overshoot, resets."""
import numpy as np
import pytest

from nqr.p3.dc_engine import DOWN, UP, detect_events

NS = 1_000_000_000


def _run(px, theta=3.0, start=0):
    px = np.asarray(px, float)
    n = len(px)
    ts = np.arange(n, dtype=np.int64) * NS
    return detect_events(px, ts, np.full(n, theta), np.full(n, theta * 2),
                         np.arange(1, n + 1, dtype=np.int64),
                         np.arange(1, n + 1, dtype=float), start_i=start)


PATH = [10, 12, 14, 16, 18, 20, 19, 17, 15, 12, 10, 8, 10, 13, 16, 19, 22, 25, 24, 22, 19, 16, 13, 12, 14]


# ------------------------------------------------------- state machine ----
def test_alternating_directions():
    evs = _run(PATH)
    assert [e.direction for e in evs] == [1, -1, 1, -1]


def test_running_high_is_tracked_until_theta_retrace():
    evs = _run(PATH)
    down = [e for e in evs if e.direction == -1][0]
    assert down.ext_price == 20.0 and down.ext_idx == 5
    assert down.conf_idx == 7 and down.conf_price == 17.0
    assert down.trigger_price == pytest.approx(17.0)


def test_running_low_is_tracked_until_theta_rally():
    evs = _run(PATH)
    up = [e for e in evs if e.direction == 1][1]
    assert up.ext_price == 8.0 and up.ext_idx == 11
    assert up.conf_idx == 13 and up.conf_price == 13.0


def test_exact_threshold_confirms_and_one_tick_short_does_not():
    # [10, 13] already confirms an UPWARD DC off the opening low, so the
    # downward test is the SECOND event.
    exact = _run([10, 13, 20, 17], theta=3.0)             # exactly -3.00 from 20
    assert len(exact) == 2 and exact[1].direction == -1
    assert exact[1].ext_price == 20.0 and exact[1].conf_price == 17.0
    short = _run([10, 13, 20, 17.25], theta=3.0)          # one tick short
    assert len(short) == 1


# ---------------------------------------------------------- CAUSALITY ----
def test_confirmation_is_always_strictly_after_the_extreme():
    rng = np.random.default_rng(7)
    px = 15000 + np.cumsum(rng.normal(0, 0.5, 5000))
    for e in _run(px, theta=4.0):
        assert e.conf_idx > e.ext_idx
        assert e.conf_ts > e.ext_ts


def test_truncating_the_path_at_confirmation_reproduces_the_event():
    """If any event used a future price, cutting the path at its confirmation
    would change or delete it."""
    full = _run(PATH)
    assert full
    for e in full:
        cut = _run(PATH[:e.conf_idx + 1])
        assert cut, f"event {e.seq} vanished when the future was removed"
        last = cut[-1]
        assert (last.direction, last.ext_idx, last.ext_price,
                last.conf_idx, last.conf_price) == \
               (e.direction, e.ext_idx, e.ext_price, e.conf_idx, e.conf_price)


def test_future_prices_cannot_alter_a_confirmed_event():
    base = _run(PATH)
    tampered = list(PATH)
    tampered[20:] = [999.0] * (len(PATH) - 20)
    got = _run(tampered)
    for a, b in zip(base[:3], got[:3]):
        assert (a.direction, a.ext_idx, a.ext_price, a.conf_idx) == \
               (b.direction, b.ext_idx, b.ext_price, b.conf_idx)


def test_extreme_timestamp_is_never_the_signal_timestamp():
    for e in _run(PATH):
        assert e.conf_ts != e.ext_ts


# ----------------------------------------------------------- overshoot ----
def test_overshoot_links_to_the_next_extreme():
    evs = _run(PATH)
    for a, b in zip(evs, evs[1:]):
        assert a.overshoot == pytest.approx(abs(b.ext_price - a.conf_price))
        assert a.overshoot_ext_idx == b.ext_idx
        assert a.overshoot_ns == b.ext_ts - a.conf_ts


def test_last_overshoot_is_left_unfinished():
    evs = _run(PATH)
    assert np.isnan(evs[-1].overshoot)
    assert np.isnan(evs[-1].overshoot_ratio)


def test_prev_overshoot_identity_holds_and_is_known_at_confirmation():
    """overshoot(k) == total_move(k+1): the quantity DC-C keys off is complete."""
    evs = _run(PATH)
    for a, b in zip(evs, evs[1:]):
        assert b.prev_overshoot == pytest.approx(a.overshoot)
        assert b.total_move == pytest.approx(a.overshoot)
    assert np.isnan(evs[0].prev_overshoot)      # no previous event exists


def test_run_start_price_is_the_previous_confirmation():
    evs = _run(PATH)
    for a, b in zip(evs, evs[1:]):
        assert b.run_start_price == pytest.approx(a.conf_price)
        assert b.run_start_ts == a.conf_ts


# -------------------------------------------------------------- misc ----
def test_flat_path_produces_nothing():
    assert _run([100.0] * 50) == []


def test_no_direction_assumed_at_the_open():
    """The first event reflects whichever threshold the path actually crosses."""
    # falls theta from the opening high first -> DOWNWARD DC confirming that high
    falling = _run([100, 99, 98, 97, 96, 95])
    assert falling and falling[0].direction == -1
    assert falling[0].ext_price == 100.0 and falling[0].ext_idx == 0
    # rises theta from the opening low first -> UPWARD DC confirming that low
    rising = _run([100, 101, 102, 103, 104, 105])
    assert rising and rising[0].direction == 1
    assert rising[0].ext_price == 100.0 and rising[0].ext_idx == 0


def test_start_index_is_respected():
    evs = _run(PATH, start=12)
    assert all(e.ext_idx >= 12 and e.conf_idx >= 12 for e in evs)


def test_event_aggregates_are_run_scoped():
    evs = _run(PATH)
    for e in evs:
        assert e.n_trades == e.conf_idx - e.run_start_idx
        assert e.event_ns == e.conf_ts - e.run_start_ts
        assert e.dc_magnitude >= 3.0 - 1e-9


def test_larger_theta_yields_fewer_events():
    rng = np.random.default_rng(3)
    px = 15000 + np.cumsum(rng.normal(0, 0.4, 20000))
    counts = [len(_run(px, theta=t)) for t in (2.0, 4.0, 8.0, 16.0)]
    assert counts == sorted(counts, reverse=True)
    assert counts[0] > counts[-1] * 3
