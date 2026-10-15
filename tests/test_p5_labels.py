"""Phase-5 larger-R labelling, timeout, clock, portfolio and budget tests."""
import datetime as dt

import numpy as np
import polars as pl
import pytest

from nqr.backtest.engine import TICK
from nqr.p3.fastpass import resolve_fast
from nqr.p4 import features4 as F4
from nqr.p5 import backtest5 as BT
from nqr.p5 import dataset5, model5
from nqr.p5.labels5 import excursions_p5, resolve_p5

NS = 1_000_000_000


def _tape(prices, step_s=1, t0=1_600_000_000):
    ts = np.array([(t0 + i * step_s) * NS for i in range(len(prices))], dtype=np.int64)
    return ts, np.array(prices, dtype=np.int64)


# ------------------------------------------------------------ R scaling ----
def test_r_scales_are_the_three_preregistered_multiples():
    assert dataset5.R_MULTS == {"r2p0": 2.0, "r3p0": 3.0, "r4p0": 4.0}
    assert dataset5.R_FLOOR == 5.0 and dataset5.R_CAP == 200.0


def test_r_is_volatility_normalised_and_railed():
    atr = np.array([1.0, 10.0, 15.0, 100.0])
    assert np.allclose(dataset5.r_points(atr, 2.0), [5.0, 20.0, 30.0, 200.0])
    assert np.allclose(dataset5.r_points(atr, 4.0), [5.0, 40.0, 60.0, 200.0])


def test_phase5_r_is_materially_larger_than_phase4():
    """The whole hypothesis: R must be several times the Phase-4 scale."""
    atr = 15.0
    p4 = np.clip(0.5 * atr, 1.0, 25.0)
    for tag, mult in dataset5.R_MULTS.items():
        p5 = dataset5.r_points(np.array([atr]), mult)[0]
        assert p5 >= 4 * p4, tag


def test_friction_over_r_is_small_at_every_scale():
    """The central economic claim, checked at a typical development ATR."""
    atr = np.array([15.0])
    for tag, mult in dataset5.R_MULTS.items():
        r = float(dataset5.r_points(atr, mult)[0])
        assert 1.0 / r < 0.05, f"{tag}: friction/R = {1.0/r:.1%}"
    p4_ratio = 1.0 / np.clip(0.5 * 15.0, 1.0, 25.0)
    assert p4_ratio > 0.13                      # Phase 4 was ~14%


# ------------------------------------------------- first passage / timeout ----
def test_target_needs_a_trade_through_and_stop_fills_on_touch():
    ts, px = _tape([400, 441, 400])             # entry 100.0, R 10 -> tp 110, sl 90
    f = resolve_p5(ts, px, 0, ts[-1] + NS, 1, 110.0, 90.0)
    assert f.kind == "TP" and f.price == 110.0  # 441 ticks = 110.25, THROUGH by a tick
    ts2, px2 = _tape([400, 440, 400])           # 440 ticks = 110.00 exactly: a touch
    f2 = resolve_p5(ts2, px2, 0, ts2[-1] + NS, 1, 110.0, 90.0)
    assert f2.kind != "TP", "a touch of the limit must not fill"
    ts3, px3 = _tape([400, 355])                # 88.75, beyond the 90 stop
    f3 = resolve_p5(ts3, px3, 0, ts3[-1] + NS, 1, 110.0, 90.0)
    assert f3.kind == "SL" and f3.price == 355 * TICK   # fills at the print, not at 90


def test_first_of_tp_and_sl_wins_by_tape_order():
    ts, px = _tape([400, 355, 460])
    assert resolve_p5(ts, px, 0, ts[-1] + NS, 1, 110.0, 90.0).kind == "SL"
    ts2, px2 = _tape([400, 460, 355])
    assert resolve_p5(ts2, px2, 0, ts2[-1] + NS, 1, 110.0, 90.0).kind == "TP"


def test_timeout_exits_at_the_first_print_AT_OR_AFTER_the_cutoff():
    """Phase 4 took the last print BEFORE the cutoff, which is not executable."""
    ts, px = _tape([400, 401, 402, 403, 404], step_s=1)
    cutoff = int(ts[2])                         # exactly on a print
    f = resolve_p5(ts, px, 0, cutoff, 1, 200.0, 0.0)
    old = resolve_fast(ts, px, 0, cutoff, 1, 200.0, 0.0)
    assert f.kind == "TIMEOUT" and old.kind == "TIMEOUT"
    assert f.ts_ns >= cutoff
    assert f.ts_ns > old.ts_ns                  # strictly later, i.e. executable


def test_timeout_falls_back_to_the_last_print_if_the_tape_goes_quiet():
    ts, px = _tape([400, 401, 402], step_s=1)
    cutoff = int(ts[-1]) + 10 * 60 * NS         # far past the end of the tape
    f = resolve_p5(ts, px, 0, cutoff, 1, 900.0, 0.0)
    assert f.kind == "TIMEOUT" and f.ts_ns == int(ts[-1])


def test_tp_and_sl_branches_match_the_frozen_engine_exactly():
    rng = np.random.default_rng(7)
    checked = 0
    for _ in range(300):
        n = int(rng.integers(200, 2000))
        px = (56000 + np.cumsum(rng.integers(-12, 13, n))).astype(np.int64)
        ts = np.sort(rng.integers(0, 3600, n)).astype(np.int64) * NS + np.arange(n)
        si = int(rng.integers(0, n // 2))
        end = int(ts[si] + rng.integers(60, 3600) * NS)
        d = int(rng.choice([-1, 1])); e = float(px[si]) * TICK; r = float(rng.integers(20, 80))
        a = resolve_fast(ts, px, si, end, d, e + d * r, e - d * r)
        b = resolve_p5(ts, px, si, end, d, e + d * r, e - d * r)
        if a.kind in ("TP", "SL"):
            assert (a.kind, a.ts_ns, a.price) == (b.kind, b.ts_ns, b.price)
            checked += 1
    assert checked > 100, f'only {checked} TP/SL outcomes to compare'


def test_excursions_are_measured_over_the_realised_hold_only():
    ts, px = _tape([400, 420, 380, 400, 999])
    mfe, mae = excursions_p5(ts, px, 0, int(ts[3]), 1, 100.0)
    assert mfe == 5.0 and mae == 5.0            # 420->105, 380->95; 999 is after the exit


# --------------------------------------------------------- horizon & clock ----
def test_max_hold_is_sixty_minutes():
    assert dataset5.MAX_HOLD_S == 3600


def test_decision_clock_is_60s_and_gives_120_decisions_dst_correct():
    for d in (dt.date(2021, 1, 20), dt.date(2021, 7, 20),
              dt.date(2021, 3, 15), dt.date(2021, 11, 8)):
        g = {"sec0": F4.et_sec(d, F4.BAND_START_ET),
             "n": F4.et_sec(d, F4.BAND_END_ET) - F4.et_sec(d, F4.BAND_START_ET)}
        idx = dataset5.decision_indices(g, d)
        assert len(idx) == 120
        assert np.all(np.diff(idx) == 60)
        assert g["sec0"] + idx[0] + 1 == F4.et_sec(d, "09:30")
        assert g["sec0"] + idx[-1] + 1 == F4.et_sec(d, "11:30") - 60


def test_decision_clock_is_much_sparser_than_phase4():
    d = dt.date(2021, 6, 1)
    g = {"sec0": F4.et_sec(d, F4.BAND_START_ET),
         "n": F4.et_sec(d, F4.BAND_END_ET) - F4.et_sec(d, F4.BAND_START_ET)}
    p5 = len(dataset5.decision_indices(g, d))
    p4 = len(F4.decision_indices(g, d, F4.SESSION_START_ET, F4.SESSION_END_ET))
    assert p4 == 1440 and p5 == 120 and p4 // p5 == 12


# ------------------------------------------- portfolio rule and cooldown ----
def _rows(n=30, day=dt.date(2021, 6, 1), r=40.0, hold_s=600, step=60):
    t0 = 1_622_552_000
    d = {"trading_date": [day] * n, "symbol": ["NQM1"] * n,
         "decision_ts_ns": [(t0 + step * i) * NS for i in range(n)],
         "sec_since_open": [step * i for i in range(n)],
         "bucket15": [(step * i) // 900 for i in range(n)],
         "in_primary": [True] * n, "atr1m": [r / 4.0] * n,
         "entry_ns": [(t0 + step * i) * NS + 250_000_000 for i in range(n)],
         "entry_price": [14000.0] * n}
    for tag in dataset5.R_MULTS:
        d[f"{tag}_R"] = [r] * n
        for side, sgn in (("long", 1), ("short", -1)):
            d[f"{tag}_{side}_outcome"] = [1 if (i % 2 == 0) == (sgn > 0) else -1 for i in range(n)]
            d[f"{tag}_{side}_points"] = [r if (i % 2 == 0) == (sgn > 0) else -r for i in range(n)]
            d[f"{tag}_{side}_mfe"] = [r] * n
            d[f"{tag}_{side}_mae"] = [5.0] * n
            d[f"{tag}_{side}_hold_s"] = [float(hold_s)] * n
            d[f"{tag}_{side}_exit_ns"] = [(t0 + step * i + hold_s) * NS for i in range(n)]
        d[f"{tag}_y"] = [1 if i % 2 == 0 else 0 for i in range(n)]
    for f in F4.FEATURE_NAMES:
        d[f] = [0.0] * n
    return pl.DataFrame(d)


def test_only_one_position_is_ever_open():
    df = _rows(n=30, hold_s=600)                 # 10-minute holds on a 60s clock
    book = BT.run_strategy(df, "r4p0", np.full(30, 1.0), np.ones(30, int), 0.5,
                           np.ones(30, bool))
    acc = BT.accepted(book)
    ts = acc["decision_ts_ns"].to_numpy(); ex = acc["exit_ns"].to_numpy()
    assert (ts[1:] >= ex[:-1]).all()
    assert book.filter(pl.col("skip_reason") == "SKIPPED_OVERLAP").height > 0


def test_cooldown_blocks_re_entry_for_one_full_decision_interval():
    df = _rows(n=30, hold_s=60)                  # exit lands exactly on the next decision
    book = BT.run_strategy(df, "r4p0", np.full(30, 1.0), np.ones(30, int), 0.5,
                           np.ones(30, bool))
    acc = BT.accepted(book)
    gaps = np.diff(acc["decision_ts_ns"].to_numpy())
    assert (gaps >= 120 * NS).all(), "re-entered inside the cooldown"
    assert book.filter(pl.col("skip_reason") == "COOLDOWN").height > 0
    assert BT.COOLDOWN_NS == 60 * NS


def test_cooldown_and_position_state_reset_across_days():
    df = pl.concat([_rows(n=5, day=dt.date(2021, 6, 1)),
                    _rows(n=5, day=dt.date(2021, 6, 2))])
    book = BT.run_strategy(df, "r4p0", np.full(10, 1.0), np.ones(10, int), 0.5,
                           np.ones(10, bool))
    assert BT.accepted(book)["trading_date"].n_unique() == 2


def test_threshold_filters_and_direction_is_taken_from_the_signal():
    """Spacing is wide enough here that the cooldown never binds."""
    df = _rows(n=6, hold_s=1, step=600)
    score = np.array([0.9, 0.9, 0.1, 0.1, 0.9, 0.9])
    direction = np.array([1, -1, 1, -1, 1, -1])
    acc = BT.accepted(BT.run_strategy(df, "r4p0", score, direction, 0.5, np.ones(6, bool)))
    assert acc.height == 4
    assert list(acc["direction"]) == [1, -1, 1, -1]


def test_cooldown_costs_exactly_one_decision_after_an_instant_exit():
    """On the 60 s clock an exit 1 s after entry blocks the very next decision."""
    df = _rows(n=6, hold_s=1, step=60)
    score = np.array([0.9, 0.9, 0.9, 0.9, 0.9, 0.9])
    book = BT.run_strategy(df, "r4p0", score, np.ones(6, int), 0.5, np.ones(6, bool))
    assert BT.accepted(book).height == 3
    assert book.filter(pl.col("skip_reason") == "COOLDOWN").height == 3


def test_friction_over_r_is_recorded_per_trade():
    df = _rows(n=4, hold_s=1, r=40.0)
    acc = BT.accepted(BT.run_strategy(df, "r4p0", np.full(4, 1.0), np.ones(4, int), 0.5,
                                      np.ones(4, bool)))
    assert np.allclose(acc["friction_over_r"].to_numpy(), 1.0 / 40.0)
    for fr in dataset5.FRICTIONS:
        col = f"net_{str(fr).replace('.', 'p')}"
        assert np.allclose(acc[col].to_numpy(), acc["points"].to_numpy() - fr)


# ------------------------------------------- training-only baseline / edge ----
def test_baseline_is_estimated_per_bucket_from_training_rows_only():
    sec = np.repeat([0, 1800, 3600, 5400], 100)
    yl = np.concatenate([np.ones(100), np.zeros(100), np.ones(100), np.zeros(100)]).astype(int)
    ys = 1 - yl
    b = model5.fit_baseline(sec, yl, ys)
    assert b["n_fit"] == 400 and len(b["buckets"]) == 4
    assert b["buckets"][0]["b_long"] == 1.0 and b["buckets"][1]["b_long"] == 0.0
    bl, bs = model5.baseline_vectors(b, np.array([0, 1800, 3600, 5400]))
    assert list(bl) == [1.0, 0.0, 1.0, 0.0]
    assert list(bs) == [0.0, 1.0, 0.0, 1.0]


def test_edge_is_measured_against_the_control_not_against_fifty_percent():
    """A model at p=0.50 has NO edge over a 0.50 baseline, and a real edge over
    a baseline below 0.50 -- which is what realistic execution produces."""
    p = np.array([0.50, 0.50])
    even = np.array([0.50, 0.50])
    s_even, _ = model5.edge_and_direction(p, even, even)
    assert np.allclose(s_even, 0.0)
    low = np.array([0.46, 0.46])
    s_low, _ = model5.edge_and_direction(p, low, low)
    assert (s_low > 0).all()


def test_direction_flips_at_the_baseline_adjusted_midpoint_not_at_half():
    b_long = np.array([0.53, 0.53, 0.53])
    b_short = np.array([0.47, 0.47, 0.47])
    # equal-edge point is p = 0.5 + (b_long - b_short)/2 = 0.53
    s, d = model5.edge_and_direction(np.array([0.50, 0.53, 0.56]), b_long, b_short)
    assert list(d) == [-1, 1, 1]
    assert np.isclose(s[1], 0.0)


def test_threshold_is_a_training_quantile_then_a_fixed_number():
    s = np.linspace(-0.2, 0.2, 10001)
    t10 = model5.threshold_from_train(s, 0.10)
    t02 = model5.threshold_from_train(s, 0.02)
    assert t02 > t10
    assert np.isclose(t10, np.quantile(s, 0.90))


# ------------------------------------------------------------- budget ----
def test_budget_is_exactly_18_and_cannot_grow():
    cfgs = model5.enumerate_configs()
    assert len(cfgs) == model5.MAX_CONFIGS == 18
    assert len({c.name for c in cfgs}) == 18
    assert len({c.r_tag for c in cfgs}) == 3
    assert len({c.family for c in cfgs}) == 2
    assert set(model5.SELECTIVITY) == {0.10, 0.05, 0.02}
    assert len(model5.model_keys()) == 6           # 3 R scales x 2 families


def test_only_the_two_preregistered_families_exist():
    with pytest.raises(model5.BudgetViolation):
        model5.build_estimator("C_forest", 1000)
    tree = model5.build_estimator("B_tree", 100_000)
    assert tree.max_depth == 4 and tree.min_samples_leaf == 2000
    assert "Forest" not in type(tree).__name__ and "Boost" not in type(tree).__name__
    logit = model5.build_estimator("A_logit", 1000)
    assert logit.C == 0.1 and logit.l1_ratio == 0.5


def test_matched_controls_share_day_bucket_direction_and_R():
    df = _rows(n=40, hold_s=60)
    book = BT.run_strategy(df, "r4p0", np.full(40, 1.0), np.ones(40, int), 0.5,
                           np.ones(40, bool))
    acc = BT.accepted(book)
    ctrl = BT.matched_controls(book, df, "r4p0", np.ones(40, bool), k=5)
    assert ctrl.height > 0
    assert set(ctrl["trading_date"].unique()) == set(acc["trading_date"].unique())
    assert set(ctrl["direction"].unique()) <= set(acc["direction"].unique())
    rr = ctrl["r_points"].to_numpy() / acc["r_points"][0]
    assert ((rr >= BT.R_MATCH_LO) & (rr <= BT.R_MATCH_HI)).all()
    assert BT.matched_controls(book, df, "r4p0", np.ones(40, bool), k=5).equals(ctrl)


def test_opposite_direction_control_flips_only_the_sign():
    df = _rows(n=20, hold_s=60)
    book = BT.run_strategy(df, "r4p0", np.full(20, 1.0), np.ones(20, int), 0.5,
                           np.ones(20, bool))
    acc = BT.accepted(book)
    opp = BT.opposite_direction(book, df, "r4p0")
    assert opp.height == acc.height
    assert (opp["direction"].to_numpy() == -acc["direction"].to_numpy()).all()
    assert np.allclose(opp["entry_price"], acc["entry_price"])
    assert np.allclose(opp["r_points"], acc["r_points"])
