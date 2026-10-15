"""Phase-4 backtest, control and budget tests."""
import datetime as dt

import numpy as np
import polars as pl
import pytest

from nqr.p4 import backtest4 as BT
from nqr.p4 import metrics4, model4
from nqr.p4.features4 import FEATURE_NAMES

NS = 1_000_000_000


def _rows(n=40, day=dt.date(2021, 6, 1), r=5.0, hold_s=60):
    t0 = 1_622_552_000
    d = {
        "trading_date": [day] * n, "symbol": ["NQM1"] * n,
        "decision_ts_ns": [(t0 + 5 * i) * NS for i in range(n)],
        "sec_since_open": [5 * i for i in range(n)],
        "et_minute": [570 + (5 * i) // 60 for i in range(n)],
        "in_primary": [True] * n,
        "r_points": [r] * n,
        "entry_ns": [(t0 + 5 * i) * NS + 250_000_000 for i in range(n)],
        "entry_price": [14000.0] * n,
        "long_outcome": [1 if i % 2 == 0 else -1 for i in range(n)],
        "long_points": [r if i % 2 == 0 else -r for i in range(n)],
        "long_mfe": [r] * n, "long_mae": [0.5] * n, "long_hold_s": [float(hold_s)] * n,
        "long_exit_ns": [(t0 + 5 * i + hold_s) * NS for i in range(n)],
        "short_outcome": [-1 if i % 2 == 0 else 1 for i in range(n)],
        "short_points": [-r if i % 2 == 0 else r for i in range(n)],
        "short_mfe": [r] * n, "short_mae": [0.5] * n, "short_hold_s": [float(hold_s)] * n,
        "short_exit_ns": [(t0 + 5 * i + hold_s) * NS for i in range(n)],
        "y": [1 if i % 2 == 0 else 0 for i in range(n)],
    }
    for f in FEATURE_NAMES:
        d[f] = [0.0] * n
    return pl.DataFrame(d)


# --------------------------------------------------------- search budget ----
def test_budget_is_exactly_18_and_cannot_grow():
    cfgs = model4.enumerate_configs()
    assert len(cfgs) == model4.MAX_CONFIGS == 18
    assert len({c.name for c in cfgs}) == 18
    assert len({c.model_key for c in cfgs}) == 6           # 2 families x 3 hypers
    assert set(model4.THRESHOLD_QUANTILES) == {0.20, 0.10, 0.05}


def test_only_the_two_preregistered_families_exist():
    assert {c.family for c in model4.enumerate_configs()} == {"A_logit", "B_tree"}
    with pytest.raises(model4.BudgetViolation):
        model4.build_estimator("C_forest:n=100", 1000)


def test_tree_is_shallow_and_leaf_constrained():
    est = model4.build_estimator("B_tree:depth=4", 100_000)
    assert est.max_depth <= 4
    assert est.min_samples_leaf == int(0.02 * 100_000)
    assert "Forest" not in type(est).__name__ and "Boost" not in type(est).__name__


# ------------------------------------------------------------- scaling ----
def test_scaler_is_fitted_only_on_training_rows():
    rng = np.random.default_rng(0)
    Xtr = rng.normal(0, 1, (5000, len(FEATURE_NAMES)))
    Xte = rng.normal(50, 9, (5000, len(FEATURE_NAMES)))     # wildly different
    pre = model4.Preprocessor.fit(Xtr, "train2021")
    ref = model4.Preprocessor.fit(Xtr, "train2021")
    pre.transform(Xte)                                       # must not refit
    assert np.allclose(pre.mu, ref.mu) and np.allclose(pre.sd, ref.sd)
    assert np.allclose(pre.transform(Xtr).mean(axis=0), 0, atol=1e-9)
    assert pre.n_fit == 5000 and pre.fit_on == "train2021"


def test_winsorisation_bounds_come_from_training_only():
    Xtr = np.zeros((1000, len(FEATURE_NAMES)))
    Xtr[:, 0] = np.arange(1000)
    pre = model4.Preprocessor.fit(Xtr, "train2021")
    out = pre.transform(np.full((1, len(FEATURE_NAMES)), 1e9))
    assert np.isfinite(out).all()
    assert out[0, 0] <= (pre.hi[0] - pre.mu[0]) / pre.sd[0] + 1e-9


def test_threshold_is_a_training_quantile_and_then_a_fixed_number():
    s = np.linspace(-0.5, 0.5, 10001)
    tau = model4.threshold_from_train(s, 0.10)
    assert 0.44 < tau < 0.46
    assert model4.threshold_from_train(s, 0.05) > tau        # tighter = higher bar


# ------------------------------------------------------ one position rule ----
def test_only_one_position_is_ever_open():
    df = _rows(n=40, hold_s=60)
    score = np.full(40, 0.30)
    book = BT.run_strategy(df, score, 0.1, np.ones(40, bool))
    acc = BT.accepted(book)
    ts = acc["decision_ts_ns"].to_numpy(); ex = acc["exit_ns"].to_numpy()
    assert (ts[1:] >= ex[:-1]).all(), "a second position opened while one was live"
    skipped = book.filter(pl.col("skip_reason") == "SKIPPED_OVERLAP")
    assert skipped.height == 40 - acc.height
    assert acc.height == len(range(0, 40, 12))               # 60s hold / 5s clock


def test_position_state_resets_across_trading_days():
    a = _rows(n=6, day=dt.date(2021, 6, 1))
    b = _rows(n=6, day=dt.date(2021, 6, 2))
    df = pl.concat([a, b])
    book = BT.run_strategy(df, np.full(12, 0.3), 0.1, np.ones(12, bool))
    acc = BT.accepted(book)
    assert acc["trading_date"].n_unique() == 2


def test_threshold_filters_and_sign_sets_direction():
    df = _rows(n=6, hold_s=1)
    score = np.array([0.30, -0.30, 0.01, -0.01, 0.30, -0.30])
    book = BT.run_strategy(df, score, 0.1, np.ones(6, bool))
    acc = BT.accepted(book)
    assert acc.height == 4
    assert list(acc["direction"]) == [1, -1, 1, -1]


def test_nonfinite_rows_never_become_trades():
    df = _rows(n=6, hold_s=1)
    usable = np.array([True, False, True, False, True, False])
    book = BT.run_strategy(df, np.full(6, 0.3), 0.1, usable)
    assert BT.accepted(book).height == 3


def test_missing_entry_print_is_skipped_not_traded():
    df = _rows(n=4, hold_s=1).with_columns(
        pl.Series("entry_ns", [0, 1, 0, 1]).cast(pl.Int64))
    book = BT.run_strategy(df, np.full(4, 0.3), 0.1, np.ones(4, bool))
    assert book.filter(pl.col("skip_reason") == "NO_ENTRY_PRINT").height == 2


# --------------------------------------------------------------- controls ----
def test_matched_controls_are_produced_and_match_day_bucket_direction_and_R():
    """Regression: np.datetime64 keys silently emptied the control pool."""
    df = _rows(n=60, hold_s=1)
    book = BT.run_strategy(df, np.full(60, 0.3), 0.1, np.ones(60, bool))
    acc = BT.accepted(book)
    ctrl = BT.matched_controls(book, df, np.ones(60, bool), k=5)
    assert ctrl.height > 0, "matched control pool came back empty"
    assert ctrl.height <= 5 * acc.height
    assert set(ctrl["trading_date"].unique()) == set(acc["trading_date"].unique())
    assert set(ctrl["direction"].unique()) <= set(acc["direction"].unique())
    rr = ctrl["r_points"].to_numpy() / acc["r_points"][0]
    assert ((rr >= BT.R_MATCH_LO) & (rr <= BT.R_MATCH_HI)).all()


def test_controls_use_the_identical_execution_and_bracket():
    df = _rows(n=60, hold_s=1)
    book = BT.run_strategy(df, np.full(60, 0.3), 0.1, np.ones(60, bool))
    ctrl = BT.matched_controls(book, df, np.ones(60, bool), k=5)
    for t in ctrl.iter_rows(named=True):
        assert np.isclose(abs(t["target"] - t["entry_price"]), t["r_points"])
        assert np.isclose(abs(t["stop"] - t["entry_price"]), t["r_points"])
        assert np.isclose(t["net_1p0"], t["points"] - 1.0)


def test_matched_controls_are_deterministic_under_the_frozen_seed():
    df = _rows(n=60, hold_s=1)
    book = BT.run_strategy(df, np.full(60, 0.3), 0.1, np.ones(60, bool))
    a = BT.matched_controls(book, df, np.ones(60, bool), k=5)
    b = BT.matched_controls(book, df, np.ones(60, bool), k=5)
    assert a.equals(b)


def test_opposite_direction_control_flips_and_nothing_else():
    df = _rows(n=20, hold_s=1)
    book = BT.run_strategy(df, np.full(20, 0.3), 0.1, np.ones(20, bool))
    acc = BT.accepted(book)
    opp = BT.opposite_direction(book, df, np.ones(20, bool))
    assert opp.height == acc.height
    assert (opp["direction"].to_numpy() == -acc["direction"].to_numpy()).all()
    assert np.allclose(opp["entry_price"], acc["entry_price"])
    assert np.allclose(opp["r_points"], acc["r_points"])
    assert np.allclose(opp["points"].to_numpy(), -acc["points"].to_numpy())


def test_shuffled_direction_null_preserves_entries_and_long_fraction():
    df = _rows(n=20, hold_s=1)
    book = BT.run_strategy(df, np.array([0.3, -0.3] * 10), 0.1, np.ones(20, bool))
    out = BT.shuffled_direction_null(book, df, np.ones(20, bool), n_rep=200)
    assert out["n_rep"] == 200
    assert 0.0 <= out["long_frac"] <= 1.0
    assert out["null_win_rate"].shape == (200,)


# ------------------------------------------------------------ inference ----
def test_bootstrap_is_over_trading_days_not_trades():
    days = [dt.date(2021, 6, d) for d in range(1, 21)]
    rng = np.random.default_rng(1)
    frames = []
    for d in days:
        n = 50
        frames.append(pl.DataFrame({
            "trading_date": [d] * n, "r_points": [5.0] * n,
            "points": list(rng.normal(0.0, 0.1, n) + 1.0)}))
    t = pl.concat(frames)
    out = metrics4.block_bootstrap_ci(t, 0.0, "expectancy_R", n_boot=2000)
    assert out["n_days"] == 20
    # a day-block CI on 20 days must be far wider than an iid CI on 1000 trades
    iid = 1.96 * (t["points"].std() / 5.0) / np.sqrt(t.height)
    assert (out["ci95_hi"] - out["ci95_lo"]) / 2 > iid


def test_bootstrap_diff_ci_brackets_a_known_difference():
    days = [dt.date(2021, 6, d) for d in range(1, 31)]
    a = pl.DataFrame({"trading_date": days * 20, "r_points": [1.0] * 600,
                      "points": [1.0] * 600})
    b = pl.DataFrame({"trading_date": days * 20, "r_points": [1.0] * 600,
                      "points": [0.0] * 600})
    out = metrics4.block_bootstrap_diff(a, b, 0.0, "expectancy_R", n_boot=500)
    assert np.isclose(out["diff"], 1.0)
    assert out["ci95_lo"] <= 1.0 <= out["ci95_hi"]


def test_gate7_concentration_rule_is_leave_one_week_out():
    d1 = [dt.date(2026, 1, 5)] * 10          # ISO week 2
    d2 = [dt.date(2026, 1, 12)] * 10         # ISO week 3
    t = pl.DataFrame({"trading_date": d1 + d2, "r_points": [1.0] * 20,
                      "points": [1.0] * 10 + [-0.05] * 10})
    c = metrics4.weekly_concentration(t, friction=0.0)
    assert c["n_weeks"] == 2
    assert c["best_week_net_R"] == 10.0
    assert not c["gate7_pass"]               # removing the best week leaves -0.5
    t2 = t.with_columns(pl.Series("points", [1.0] * 20))
    assert metrics4.weekly_concentration(t2, friction=0.0)["gate7_pass"]


def test_friction_sweep_is_applied_to_pnl_never_to_the_label():
    df = _rows(n=4, hold_s=1)
    book = BT.run_strategy(df, np.full(4, 0.3), 0.1, np.ones(4, bool))
    acc = BT.accepted(book)
    for fr in (0.0, 0.5, 1.0, 2.0):
        col = f"net_{str(fr).replace('.', 'p')}"
        assert np.allclose(acc[col].to_numpy(), acc["points"].to_numpy() - fr)
    assert list(df["y"])[:4] == [1, 0, 1, 0]     # label untouched by friction
