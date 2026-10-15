"""DC-A / DC-B / DC-C signal construction, causality and deduplication."""
import numpy as np
import pytest
import yaml
from pathlib import Path

from nqr.p3.dc_engine import detect_events
from nqr.p3.strategies import build_signals, signals_dc_a, signals_dc_b, signals_dc_c

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "strategies" / "directional_change" /
                      "config" / "baseline.yaml").read_text())
NS = 1_000_000_000
PATH = [10, 12, 14, 16, 18, 20, 19, 17, 15, 12, 10, 8, 10, 13, 16, 19, 22, 25, 24, 22, 19, 16, 13, 12, 14]


def _events(px, theta=3.0):
    px = np.asarray(px, float)
    n = len(px)
    ts = np.arange(n, dtype=np.int64) * NS
    return px, ts, detect_events(px, ts, np.full(n, theta), np.full(n, theta * 2),
                                 np.arange(1, n + 1, dtype=np.int64),
                                 np.arange(1, n + 1, dtype=float))


# ------------------------------------------------------------------ DC-A ----
def test_dc_a_one_signal_per_event_in_the_dc_direction():
    px, ts, evs = _events(PATH)
    sigs = signals_dc_a(evs)
    assert len(sigs) == len(evs)
    assert len({s.event_seq for s in sigs}) == len(sigs)      # no duplicates
    for s, e in zip(sigs, evs):
        assert s.direction == e.direction
        assert s.signal_ts == e.conf_ts                        # never ext_ts
        assert s.signal_ts > e.ext_ts


def test_dc_a_never_signals_at_the_extreme():
    px, ts, evs = _events(PATH)
    for s in signals_dc_a(evs):
        assert s.signal_price != s.ext_price or s.signal_ts != s.ext_ts


# ------------------------------------------------------------------ DC-B ----
def test_dc_b_requires_the_move_to_extend_beta_theta():
    px, ts, evs = _events(PATH)
    beta = 0.5
    sigs = signals_dc_b(evs, px, ts, beta)
    for s in sigs:
        ev = [e for e in evs if e.seq == s.event_seq][0]
        level = ev.conf_price + ev.direction * beta * ev.theta
        assert s.ref_price == pytest.approx(level)
        if ev.direction > 0:
            assert s.signal_price >= level
        else:
            assert s.signal_price <= level
        assert s.signal_ts > ev.conf_ts                        # strictly after


def test_dc_b_at_most_one_signal_per_event():
    px, ts, evs = _events(PATH)
    sigs = signals_dc_b(evs, px, ts, 0.5)
    assert len({s.event_seq for s in sigs}) == len(sigs)


def test_dc_b_trigger_cannot_come_from_a_later_event():
    px, ts, evs = _events(PATH)
    sigs = signals_dc_b(evs, px, ts, 0.5)
    by_seq = {e.seq: e for e in evs}
    for s in sigs:
        nxt = by_seq.get(s.event_seq + 1)
        if nxt is not None:
            assert s.signal_ts < nxt.conf_ts


def test_dc_b_emits_nothing_when_the_move_never_extends():
    # confirm a DC then immediately reverse: no beta*theta extension exists
    px, ts, evs = _events([10, 13, 20, 17, 20, 23, 26])
    sigs = signals_dc_b(evs, px, ts, 0.5)
    down = [e for e in evs if e.direction == -1]
    assert down
    assert all(s.event_seq != down[0].seq for s in sigs)


# ------------------------------------------------------------------ DC-C ----
def test_dc_c_is_a_subset_of_dc_a_filtered_on_prior_overshoot():
    px, ts, evs = _events(PATH)
    a = {s.event_seq for s in signals_dc_a(evs)}
    c = signals_dc_c(evs, gamma=2.0)
    assert {s.event_seq for s in c} <= a
    for s in c:
        assert s.prev_overshoot >= 2.0 * s.theta


def test_dc_c_skips_the_first_event_whose_prior_overshoot_is_undefined():
    px, ts, evs = _events(PATH)
    assert all(s.event_seq != 0 for s in signals_dc_c(evs, gamma=0.0))


def test_dc_c_gamma_is_monotone():
    rng = np.random.default_rng(11)
    px = 15000 + np.cumsum(rng.normal(0, 0.5, 20000))
    _, ts, evs = _events(px, theta=4.0)
    counts = [len(signals_dc_c(evs, g)) for g in (0.5, 1.0, 2.0, 4.0)]
    assert counts == sorted(counts, reverse=True)


# -------------------------------------------------------------- combined ----
def test_build_signals_uses_the_frozen_config_values():
    px, ts, evs = _events(PATH)
    got = build_signals(evs, px, ts, CFG)
    assert set(got) == {"DC_A", "DC_B", "DC_C"}
    assert CFG["strategies"]["dc_b"]["beta_extension"] == 0.5
    assert CFG["strategies"]["dc_c"]["gamma_overshoot"] == 2.0
    assert len(got["DC_A"]) == len(evs)


def test_every_signal_is_knowable_at_its_timestamp():
    """Truncating the price path at a signal's timestamp must still produce it."""
    px, ts, evs = _events(PATH)
    for fam, sigs in build_signals(evs, px, ts, CFG).items():
        for s in sigs:
            cut = PATH[:s.signal_idx + 1]
            px2, ts2, evs2 = _events(cut)
            got = build_signals(evs2, px2, ts2, CFG)[fam]
            assert any(g.signal_idx == s.signal_idx and g.direction == s.direction
                       for g in got), f"{fam} signal at {s.signal_idx} needed the future"


# ------------------------------------------------- serialization regression ----
def test_row_schema_is_stable_across_skipped_and_accepted(tmp_path):
    """REGRESSION (impl1): skipped rows left the target columns absent, so polars
    inferred a Null dtype from an all-skipped prefix and then failed to append a
    real int64 timestamp.  Every row must now carry an identical key set."""
    import polars as pl
    from strategies.directional_change.runner import P3_SCHEMA_OVERRIDES, target_tags, _row

    class _P:
        trading_date = __import__("datetime").date(2023, 5, 10)
        symbol = "NQM3"
    px, ts, evs = _events(PATH)
    sigs = signals_dc_a(evs)
    tags = target_tags(CFG)
    fr = CFG["costs"]["round_trip_points_grid"]
    rows = [_row(s, _P(), tags, fr) for s in sigs]
    assert len({tuple(sorted(r)) for r in rows}) == 1, "key sets differ between rows"
    for t in tags:
        assert f"{t}_points" in rows[0] and f"{t}_net_1p0" in rows[0]
    # a real int64 must append cleanly even though the first rows are all null
    rows[-1]["entry_ns"] = 1609857001656178000
    ov = {k: getattr(pl, v) for k, v in P3_SCHEMA_OVERRIDES.items()}
    df = pl.DataFrame(rows, strict=False, schema_overrides=ov)
    assert df.height == len(rows)
    assert df["entry_ns"].dtype == pl.Int64


def test_entry_slippage_sign_matches_phases_1_and_2():
    """REGRESSION (impl2): the sign was inverted, reporting FAVOURABLE slippage as
    positive.  The project-wide convention is ADVERSE-positive:
        slippage = (entry - reference) * direction
    so a long that pays more, and a short that sells lower, both score positive."""
    import inspect
    from strategies.directional_change import runner
    src = inspect.getsource(runner.simulate)
    assert "entry_slippage=(epx - s.ref_price) * d" in src
    assert "signal_to_entry_pts=(epx - s.signal_price) * d" in src
    # long paying 2 pts more than the reference -> +2 adverse
    assert (102.0 - 100.0) * 1 == pytest.approx(2.0)
    # short selling 2 pts below the reference -> +2 adverse
    assert (98.0 - 100.0) * -1 == pytest.approx(2.0)
