"""Phase-7: schema assumptions, causal alignment, feature formulas, controls, seals."""
import datetime as dt
import hashlib
import json
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from nqr.p4 import features4 as F4
from nqr.p7 import backtest7 as BT
from nqr.p7 import cache7, dataset7, model7
from nqr.p7 import features7 as F7
from nqr.p7 import holdout7 as H7

ROOT = Path(__file__).resolve().parents[1]
NS = F7.NS

FROZEN_IDS = {
    "results/frozen_manifest.json": "fastslow-1.0.0+5980044a44eebf7b",
    "results/p2_frozen_manifest.json": "impexh-1.0.0.impl2+48c76a0e68b88947",
    "results/p3_frozen_manifest.json": "dcevent-1.0.0.impl3+d33e5d5d116f1adb",
    "results/p4_frozen_manifest.json": "statedisc-1.0.0+c147134184dfb32d",
}


# ------------------------------------------------- phases 1-6 immutable ----
@pytest.mark.parametrize("rel,fid", sorted(FROZEN_IDS.items()))
def test_previous_phase_manifests_match_disk(rel, fid):
    man = json.loads((ROOT / rel).read_text())
    assert man["frozen_id"] == fid
    assert not [f for f, d in man["files"].items()
                if hashlib.sha256((ROOT / f).read_bytes()).hexdigest() != d]


def test_phase5_and_phase6_artifacts_unchanged():
    man = json.loads((ROOT / "results" / "p5_artifact_manifest.json").read_text())
    assert not [f for f, d in man["files"].items()
                if hashlib.sha256((ROOT / f).read_bytes()).hexdigest() != d]
    assert (ROOT / "strategies/context_entry/PHASE6_VERDICT.md").exists()


# ------------------------------------------------------ schema assumptions ----
def test_phase7_assumes_only_one_book_level():
    """No feature or SQL may reference a level beyond _00."""
    src = "".join((ROOT / "src" / "nqr" / "p7" / f).read_text()
                  for f in ("cache7.py", "features7.py", "dataset7.py"))
    for lvl in ("_01", "_02", "_03", "_04", "_05", "_06", "_07", "_08", "_09"):
        assert f"bid_px{lvl}" not in src and f"ask_px{lvl}" not in src
        assert f"bid_sz{lvl}" not in src and f"ask_sz{lvl}" not in src
    for banned in ("queue_position", "order_id", "hidden", "iceberg"):
        assert banned not in src.lower()


def test_feature_registry_is_within_the_hard_cap():
    assert len(F7.FEATURE_NAMES) == 40
    assert len(set(F7.FEATURE_NAMES)) == 40
    sizes = {}
    for n in F7.FEATURE_NAMES:
        sizes[F7.FAMILY_OF[n]] = sizes.get(F7.FAMILY_OF[n], 0) + 1
    assert sizes == {1: 7, 2: 4, 3: 4, 4: 4, 5: 3, 6: 4, 7: 2, 8: 4, 9: 2, 10: 2, 11: 4}


def test_ablation_groups_partition_the_registry():
    assert len(F7.ABLATIONS["A0_full"]) == 40
    assert len(F7.ABLATIONS["A1_quote_only"]) == 32
    assert len(F7.ABLATIONS["A2_trades_context"]) == 8
    assert set(F7.ABLATIONS["A1_quote_only"]) <= set(F7.FEATURE_NAMES)
    assert set(F7.ABLATIONS["A2_trades_context"]) <= set(F7.FEATURE_NAMES)
    assert not (set(F7.TRADE_DEPENDENT) & set(F7.ABLATIONS["A1_quote_only"]))


# ---------------------------------------------------------- microprice ----
def test_microprice_weights_each_price_by_the_OPPOSITE_size():
    # heavy bid must pull the microprice UP toward the ask
    m = F7.microprice(100.0, 101.0, bid_sz=9, ask_sz=1)
    assert m > 100.5 and m < 101.0
    # heavy ask must pull it DOWN toward the bid
    m2 = F7.microprice(100.0, 101.0, bid_sz=1, ask_sz=9)
    assert m2 < 100.5 and m2 > 100.0
    # balanced book -> exactly the midpoint
    assert F7.microprice(100.0, 101.0, 5, 5) == pytest.approx(100.5)
    # always inside the spread
    for b, a in [(1, 1), (1, 50), (50, 1), (7, 3)]:
        assert 100.0 <= F7.microprice(100.0, 101.0, b, a) <= 101.0


def test_microprice_is_not_reversed():
    """The classic sign bug: weighting each price by its OWN size."""
    reversed_ = (100.0 * 9 + 101.0 * 1) / 10          # what the bug would give
    assert F7.microprice(100.0, 101.0, 9, 1) != pytest.approx(reversed_)


# ------------------------------------------------------------------- OFI ----
@pytest.mark.parametrize("case,args,want", [
    # (pb, qb, pa, qa, lpb, lqb, lpa, lqa)
    ("bid price rises",      (101, 5, 103, 7, 100, 4, 103, 7), +5),
    ("bid price falls",      (99, 5, 103, 7, 100, 4, 103, 7), -4),
    ("bid size increases",   (100, 9, 103, 7, 100, 4, 103, 7), +5),
    ("bid size decreases",   (100, 2, 103, 7, 100, 4, 103, 7), -2),
    ("ask price falls",      (100, 4, 102, 6, 100, 4, 103, 7), -6),
    ("ask price rises",      (100, 4, 104, 6, 100, 4, 103, 7), +7),
    ("ask size increases",   (100, 4, 103, 9, 100, 4, 103, 7), -2),
    ("ask size decreases",   (100, 4, 103, 3, 100, 4, 103, 7), +4),
    ("nothing changes",      (100, 4, 103, 7, 100, 4, 103, 7), 0),
])
def test_ofi_transition_cases(case, args, want):
    assert F7.ofi_event(*args) == want, case


def test_ofi_sign_convention_is_buying_pressure_positive():
    # bid lifts and ask lifts -> buyers pushing the book up -> positive
    assert F7.ofi_event(101, 5, 104, 6, 100, 4, 103, 7) > 0
    # bid drops and ask drops -> sellers pushing the book down -> negative
    assert F7.ofi_event(99, 5, 102, 6, 100, 4, 103, 7) < 0


def test_ofi_reference_matches_the_sql_case_ladder():
    """features7.ofi_event must mirror cache7.BOOK_SQL exactly."""
    sql = (ROOT / "src" / "nqr" / "p7" / "cache7.py").read_text()
    assert "WHEN pb > lpb THEN qb WHEN pb = lpb THEN qb - lqb ELSE -lqb END" in sql
    assert "WHEN pa < lpa THEN -qa WHEN pa = lpa THEN -(qa - lqa) ELSE lqa END" in sql


# --------------------------------------------------------- causal windows ----
def test_rolling_windows_are_trailing_and_closed():
    a = np.arange(10.0)
    assert F7._roll_sum(a, 3)[5] == a[3] + a[4] + a[5]
    assert F7._roll_mean(a, 3)[5] == pytest.approx((3 + 4 + 5) / 3)
    assert np.isnan(F7._shift(a, 3)[2]) and F7._shift(a, 3)[5] == 2.0


def _grid(n=200, sec0=1_600_000_000):
    """Synthetic per-second book frame."""
    rng = np.random.default_rng(0)
    return pl.DataFrame({
        "trading_date": [dt.date(2021, 6, 1)] * n, "symbol": ["NQM1"] * n,
        "sec": np.arange(sec0, sec0 + n, dtype=np.int64),
        "n_events": np.full(n, 10.0),
        "bid_px": 14000.0 + np.zeros(n), "ask_px": 14000.5 + np.zeros(n),
        "bid_sz": np.full(n, 4.0), "ask_sz": np.full(n, 2.0),
        "bid_ct": np.full(n, 2.0), "ask_ct": np.full(n, 1.0),
        "imb_last": np.full(n, 1 / 3), "imb_mean": np.full(n, 1 / 3),
        "n_imb_pos": np.full(n, 10.0), "n_imb_neg": np.zeros(n),
        "micro_last": np.full(n, 14000.0 + 0.5 * 4 / 6), "micro_off_mean": np.full(n, 0.0833),
        "mid_last": np.full(n, 14000.25), "spread_mean": np.full(n, 0.5),
        "spread_last": np.full(n, 0.5), "ofi": np.full(n, 3.0),
        "b_inc": np.full(n, 5.0), "b_dec": np.full(n, 2.0),
        "a_inc": np.full(n, 1.0), "a_dec": np.full(n, 4.0),
        "n_b_up": np.full(n, 2.0), "n_b_dn": np.full(n, 1.0),
        "n_a_up": np.full(n, 3.0), "n_a_dn": np.full(n, 1.0),
        "n_b_upd": np.full(n, 6.0), "n_a_upd": np.full(n, 4.0),
        "n_add_b": np.full(n, 3.0), "n_add_a": np.full(n, 2.0),
        "n_can_b": np.full(n, 2.0), "n_can_a": np.full(n, 3.0),
        "trd_buy_vol": np.full(n, 8.0), "trd_sell_vol": np.full(n, 4.0),
        "trd_n": np.full(n, 3.0), "trd_px_last": np.full(n, 14000.25),
    })


def test_book_grid_forward_fills_state_but_not_flow():
    df = _grid(n=100)
    df = df.filter(pl.col("sec") % 3 != 1)          # punch holes
    g = F7.build_book_grid(df, 1_600_000_000, 1_600_000_100, min_rows=10)
    assert g is not None
    assert np.isfinite(g["bid_px"]).all(), "state must carry forward"
    gaps = ~g["present"]
    assert gaps.sum() > 0
    assert (g["ofi"][gaps] == 0).all(), "flow must be zero in event-less seconds"
    assert (g["n_events"][gaps] == 0).all()


def test_state_matrix_uses_no_future_second():
    """Truncate the grid right after a decision second; features must be identical."""
    df = _grid(n=300)
    d = dt.date(2021, 6, 1)
    sec0 = F4.et_sec(d, F7.BOOK_BAND_START_ET)
    df = df.with_columns(pl.Series("sec", np.arange(sec0, sec0 + 300, dtype=np.int64)))
    atr = np.full(300, 20.0); rank = np.full(300, 0.5)
    g_full = F7.build_book_grid(df, sec0, sec0 + 300, min_rows=10)
    S_full = F7.build_state_matrix(g_full, d, atr, rank)
    cut = 200
    g_cut = F7.build_book_grid(df.filter(pl.col("sec") < sec0 + cut), sec0, sec0 + cut,
                               min_rows=10)
    S_cut = F7.build_state_matrix(g_cut, d, atr[:cut], rank[:cut])
    i = cut - 1
    bad = [F7.FEATURE_NAMES[j] for j in range(40)
           if not np.isclose(S_full["X"][i, j], S_cut["X"][i, j], rtol=1e-9, atol=1e-9)]
    assert not bad, f"features changed when the future was removed: {bad}"


def test_decision_clock_is_5s_and_dst_correct():
    for d in (dt.date(2021, 1, 20), dt.date(2021, 7, 20)):
        g = {"sec0": F4.et_sec(d, F7.BOOK_BAND_START_ET),
             "n": F4.et_sec(d, F7.BOOK_BAND_END_ET) - F4.et_sec(d, F7.BOOK_BAND_START_ET)}
        idx = F7.decision_indices(g, d)
        assert len(idx) == 1440                      # 2 h / 5 s
        assert np.all(np.diff(idx) == 5)
        assert g["sec0"] + idx[0] + 1 == F4.et_sec(d, "09:30")
        assert g["sec0"] + idx[-1] + 1 == F4.et_sec(d, "11:30") - 5


def test_imbalance_and_microprice_features_have_the_right_sign():
    df = _grid(n=100)                                # bid 4, ask 2 -> bid heavy
    d = dt.date(2021, 6, 1)
    sec0 = F4.et_sec(d, F7.BOOK_BAND_START_ET)
    df = df.with_columns(pl.Series("sec", np.arange(sec0, sec0 + 100, dtype=np.int64)))
    g = F7.build_book_grid(df, sec0, sec0 + 100, min_rows=10)
    S = F7.build_state_matrix(g, d, np.full(100, 20.0), np.full(100, 0.5))
    i = 60
    assert S["X"][i, F7.FEATURE_NAMES.index("imb")] == pytest.approx(1 / 3)
    assert S["X"][i, F7.FEATURE_NAMES.index("micro_off_ticks")] > 0
    assert S["X"][i, F7.FEATURE_NAMES.index("spread_ticks")] == pytest.approx(2.0)
    assert S["X"][i, F7.FEATURE_NAMES.index("ofi_5")] > 0


# ----------------------------------------------------- labels and geometry ----
def test_r_scales_and_hold_are_the_preregistered_values():
    assert dataset7.R_POINTS == {"R15": 15.0, "R25": 25.0}
    assert dataset7.MAX_HOLD_S == 900
    assert dataset7.PRIMARY_FRICTION == 1.0
    assert 1.0 / dataset7.R_POINTS["R15"] == pytest.approx(0.0667, abs=1e-4)
    assert 1.0 / dataset7.R_POINTS["R25"] == pytest.approx(0.0400, abs=1e-4)


# ----------------------------------------------------------------- budget ----
def test_budget_is_exactly_12_and_cannot_grow():
    cfgs = model7.enumerate_configs()
    assert len(cfgs) == model7.MAX_CONFIGS == 12
    assert len({c.name for c in cfgs}) == 12
    assert len({c.r_tag for c in cfgs}) == 2
    assert len({c.family for c in cfgs}) == 2
    assert set(model7.SELECTIVITY) == {0.010, 0.005, 0.002}
    assert len(model7.model_keys()) == 4


def test_only_two_families_and_the_tree_is_depth_3():
    with pytest.raises(model7.BudgetViolation):
        model7.build_estimator("C_forest", 1000)
    t = model7.build_estimator("B_tree", 100_000)
    assert t.max_depth == 3 and t.min_samples_leaf == 2000
    lg = model7.build_estimator("A_logit", 1000)
    assert lg.C == 0.1 and lg.l1_ratio == 0.5


def test_thresholds_come_from_the_training_confidence_distribution():
    p = np.clip(np.random.default_rng(0).normal(0.5, 0.05, 200_000), 0, 1)
    th = model7.thresholds_from_train(p)
    assert set(th) == set(model7.SELECTIVITY)
    assert th[0.002] > th[0.005] > th[0.010]
    c = model7.confidence(p)
    assert (c >= th[0.010]).mean() == pytest.approx(0.010, abs=5e-4)


def test_direction_is_the_sign_of_p_minus_half():
    p = np.array([0.9, 0.51, 0.5, 0.49, 0.1])
    assert list(model7.direction_of(p)) == [1, 1, 1, -1, -1]


# ------------------------------------------------------- control causality ----
def _rows(n=40, day=dt.date(2021, 6, 1), t0=1_622_552_000, R="R15"):
    d = {"trading_date": [day] * n, "symbol": ["NQM1"] * n,
         "decision_ts_ns": [(t0 + 5 * i) * NS for i in range(n)],
         "sec_since_open": [5 * i for i in range(n)],
         "bucket15m": [(5 * i) // 900 for i in range(n)],
         "entry_ns": [(t0 + 5 * i) * NS + 250_000_000 for i in range(n)],
         "entry_price": [14000.0] * n, "book_present": [True] * n,
         "atr1m_ticks": [40.0] * n, "spread_ticks": [2.0] * n}
    for tag in dataset7.R_POINTS:
        r = dataset7.R_POINTS[tag]
        for side, sgn in (("long", 1), ("short", -1)):
            d[f"{tag}_{side}_outcome"] = [1 if (i % 2 == 0) == (sgn > 0) else -1 for i in range(n)]
            d[f"{tag}_{side}_points"] = [r if (i % 2 == 0) == (sgn > 0) else -r for i in range(n)]
            d[f"{tag}_{side}_mfe"] = [r] * n
            d[f"{tag}_{side}_mae"] = [2.0] * n
            d[f"{tag}_{side}_hold_s"] = [120.0] * n
            d[f"{tag}_{side}_exit_ns"] = [(t0 + 5 * i + 120) * NS for i in range(n)]
        d[f"{tag}_y"] = [1 if i % 2 == 0 else 0 for i in range(n)]
    for f in F7.FEATURE_NAMES:
        d.setdefault(f, [0.0] * n)
    return pl.DataFrame(d)


def test_cross_day_controls_never_fall_on_the_signals_own_day():
    a = _rows(40, dt.date(2021, 6, 1), 1_622_552_000)
    b = _rows(40, dt.date(2021, 6, 2), 1_622_638_400)
    df = pl.concat([a, b]).sort(["trading_date", "decision_ts_ns"])
    u = np.ones(df.height, bool)
    conf = np.zeros(df.height); conf[:5] = 1.0
    tr = BT.run_strategy(df, "R15", conf, np.ones(df.height, int), 0.5, u)
    ctrl = BT.matched_controls(tr, df, "R15", u, np.array([1., 2., 3.]),
                               np.array([1., 2., 3.]), mode="cross_day")
    assert ctrl.height > 0
    same = np.array(ctrl["trading_date"].to_list(), dtype=object) == \
           np.array(ctrl["matched_to_date"].to_list(), dtype=object)
    assert not same.any()


def test_same_day_controls_are_never_before_their_signal():
    df = _rows(60)
    u = np.ones(df.height, bool)
    conf = np.zeros(df.height); conf[30] = 1.0
    tr = BT.run_strategy(df, "R15", conf, np.ones(df.height, int), 0.5, u)
    ctrl = BT.matched_controls(tr, df, "R15", u, np.array([1., 2., 3.]),
                               np.array([1., 2., 3.]), mode="same_day_forward")
    if ctrl.height:
        assert (ctrl["decision_ts_ns"].to_numpy() >=
                ctrl["matched_to_ts"].to_numpy()).all()


def test_control_causality_assertion_actually_fires():
    bad = BT.frame([{"trading_date": dt.date(2021, 6, 1), "symbol": "NQM1",
                     "decision_ts_ns": 100 * NS, "entry_ns": 90 * NS,
                     "matched_to_ts": 50 * NS, "matched_to_date": dt.date(2021, 6, 2)}])
    with pytest.raises(BT.ControlCausalityViolation):
        BT.assert_control_causality(bad, "cross_day")
    late = BT.frame([{"trading_date": dt.date(2021, 6, 1), "symbol": "NQM1",
                      "decision_ts_ns": 100 * NS, "entry_ns": 101 * NS,
                      "matched_to_ts": 200 * NS, "matched_to_date": dt.date(2021, 6, 1)}])
    with pytest.raises(BT.ControlCausalityViolation):
        BT.assert_control_causality(late, "same_day_forward")


def test_controls_match_direction_R_and_bucket():
    a = _rows(40, dt.date(2021, 6, 1), 1_622_552_000)
    b = _rows(40, dt.date(2021, 6, 2), 1_622_638_400)
    df = pl.concat([a, b]).sort(["trading_date", "decision_ts_ns"])
    u = np.ones(df.height, bool)
    conf = np.zeros(df.height); conf[:3] = 1.0
    tr = BT.run_strategy(df, "R15", conf, -np.ones(df.height, int), 0.5, u)
    acc = BT.accepted(tr)
    ctrl = BT.matched_controls(tr, df, "R15", u, np.array([1., 2., 3.]),
                               np.array([1., 2., 3.]), mode="cross_day")
    assert set(ctrl["direction"].unique()) == set(acc["direction"].unique())
    assert (ctrl["r_points"].to_numpy() == 15.0).all()
    assert set(ctrl["bucket5m"].unique()) <= set(acc["bucket5m"].unique())
    for t in ctrl.iter_rows(named=True):
        assert np.isclose(abs(t["target"] - t["entry_price"]), 15.0)
        assert np.isclose(abs(t["entry_price"] - t["stop"]), 15.0)


def test_one_position_and_cooldown():
    df = _rows(60)
    u = np.ones(df.height, bool)
    tr = BT.run_strategy(df, "R15", np.ones(df.height), np.ones(df.height, int), 0.5, u)
    acc = BT.accepted(tr)
    ts, ex = acc["decision_ts_ns"].to_numpy(), acc["exit_ns"].to_numpy()
    assert (ts[1:] >= ex[:-1] + BT.COOLDOWN_S * NS).all()
    assert tr.filter(pl.col("skip_reason") == "SKIPPED_OVERLAP").height > 0


def test_pf_r_is_in_R_units():
    t = pl.DataFrame({"points": [15.0, -25.0], "r_points": [15.0, 25.0]})
    assert BT.pf_r(t, 0.0) == pytest.approx(1.0)


# -------------------------------------------------------------- holdouts ----
@pytest.mark.parametrize("d", [dt.date(2025, 1, 1), dt.date(2025, 3, 15), dt.date(2025, 6, 30)])
def test_2025h1_blocked_before_the_unlock(d):
    with pytest.raises(H7.Phase7Violation):
        H7.assert_date_allowed(d)
    with pytest.raises(H7.Phase7Violation):
        H7.assert_path_allowed("/x/mbp1/2025_H1.parquet")


def test_2025h1_opens_only_with_the_phase7_phrase():
    with pytest.raises(H7.Phase7Violation):
        H7.unlock_phase7_validation("I_AM_UNLOCKING_ONLY_2026_Q1_FOR_PHASE6_VALIDATION")
    H7._VAL_UNLOCKED = True
    try:
        H7.assert_date_allowed(dt.date(2025, 3, 1))
        H7.assert_path_allowed("/x/mbp1/2025_H1.parquet")
    finally:
        H7._VAL_UNLOCKED = False
    with pytest.raises(H7.Phase7Violation):
        H7.assert_date_allowed(dt.date(2025, 3, 1))


@pytest.mark.parametrize("d", [dt.date(2026, 1, 2), dt.date(2026, 3, 31), dt.date(2026, 6, 1)])
def test_2026_has_no_phase7_unlock_path_at_all(d):
    with pytest.raises(H7.Phase7Violation):
        H7.assert_date_allowed(d)
    H7._VAL_UNLOCKED = True
    try:
        with pytest.raises(H7.Phase7Violation):
            H7.assert_date_allowed(d)
    finally:
        H7._VAL_UNLOCKED = False


def test_2025h2_is_not_a_phase7_period():
    with pytest.raises(H7.Phase7Violation):
        H7.assert_date_allowed(dt.date(2025, 9, 1))
    with pytest.raises(H7.Phase7Violation):
        H7.assert_path_allowed("/x/2025_H2.parquet")


def test_exactly_one_unlock_function_named_for_2025h1():
    assert [n for n in dir(H7) if n.startswith("unlock")] == ["unlock_phase7_validation"]
    assert H7._UNLOCK_PHRASE.endswith("PHASE7_FRESH_VALIDATION")
    assert "2025_H1" in H7._UNLOCK_PHRASE


def test_sql_guard_refuses_forbidden_windows_before_emitting_sql():
    with pytest.raises(H7.Phase7Violation):
        H7.sql_window_guard(dt.date(2024, 1, 1), dt.date(2025, 3, 1))
    with pytest.raises(H7.Phase7Violation):
        H7.sql_window_guard(dt.date(2025, 1, 1), dt.date(2026, 1, 1))
    sql = H7.sql_window_guard(dt.date(2021, 1, 1), dt.date(2023, 12, 31))
    assert "DATE '2023-12-31'" in sql and "America/New_York" in sql


def test_book_cache_loader_refuses_a_sealed_month():
    with pytest.raises(H7.Phase7Violation):
        cache7.load_month("2025-03")
    with pytest.raises(H7.Phase7Violation):
        cache7.load_month("2026-01")


# ------------------------------------------- regression: uint32 underflow ----
def test_cache_sql_casts_sizes_before_subtracting():
    """bid_sz_00/ask_sz_00 are uint32.  Subtracting them without a cast underflows
    (1 - 2 -> 4294967295), which would silently corrupt imbalance and OFI."""
    sql = (ROOT / "src" / "nqr" / "p7" / "cache7.py").read_text()
    assert "CAST(bid_sz_00 AS BIGINT) AS qb" in sql
    assert "CAST(ask_sz_00 AS BIGINT) AS qa" in sql
    assert "CAST(bid_ct_00 AS BIGINT) AS cb" in sql
    assert "CAST(ask_ct_00 AS BIGINT) AS ca" in sql


def test_uint32_underflow_would_have_been_caught():
    """Demonstrates the failure mode the cast prevents."""
    u = np.array([1], dtype=np.uint32) - np.array([2], dtype=np.uint32)
    assert u[0] == 4294967295, "the underflow this test guards against"
    i = np.array([1], dtype=np.int64) - np.array([2], dtype=np.int64)
    assert i[0] == -1


@pytest.mark.parametrize("ym", ["2021-03", "2022-06", "2023-11"])
def test_built_cache_has_valid_imbalance_and_microprice(ym):
    d = cache7.load_month(ym)
    if d.height == 0:
        pytest.skip("cache month not built")
    imb = d["imb_last"].to_numpy()
    assert imb.min() >= -1.0 - 1e-9 and imb.max() <= 1.0 + 1e-9
    mp, bp, ap = (d["micro_last"].to_numpy(), d["bid_px"].to_numpy(), d["ask_px"].to_numpy())
    assert (mp >= bp - 1e-9).all() and (mp <= ap + 1e-9).all()
    assert (ap > bp).all()
    assert (d["bid_sz"].to_numpy() > 0).all() and (d["ask_sz"].to_numpy() > 0).all()


def test_cache_sql_uses_explicit_utc_offsets_in_its_literals():
    """DuckDB parses a naive TIMESTAMPTZ literal in the SESSION timezone.  The
    month bounds must carry an explicit offset or the scan window silently shifts."""
    lo, hi = cache7._month_bounds(2022, 3)
    assert lo.endswith("+0000") and hi.endswith("+0000")
    assert "TIMESTAMPTZ '{t0}'" in cache7.BOOK_SQL and "TIMESTAMPTZ '{t1}'" in cache7.BOOK_SQL
