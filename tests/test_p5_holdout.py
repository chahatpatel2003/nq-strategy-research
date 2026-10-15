"""Phase-5 period guard + Phase 1-4 immutability."""
import datetime as dt
import hashlib
import json
from pathlib import Path

import pytest

from nqr.p5 import holdout5 as H5

ROOT = Path(__file__).resolve().parents[1]
D = dt.date

FROZEN_IDS = {
    "results/frozen_manifest.json": "fastslow-1.0.0+5980044a44eebf7b",
    "results/p2_frozen_manifest.json": "impexh-1.0.0.impl2+48c76a0e68b88947",
    "results/p3_frozen_manifest.json": "dcevent-1.0.0.impl3+d33e5d5d116f1adb",
    "results/p4_frozen_manifest.json": "statedisc-1.0.0+c147134184dfb32d",
}


# ------------------------------------------------- Phase 1-4 immutability ----
@pytest.mark.parametrize("rel,frozen_id", sorted(FROZEN_IDS.items()))
def test_previous_phase_frozen_manifest_still_matches_disk(rel, frozen_id):
    man = json.loads((ROOT / rel).read_text())
    assert man["frozen_id"] == frozen_id
    drifted = [f for f, dg in man["files"].items()
               if hashlib.sha256((ROOT / f).read_bytes()).hexdigest() != dg]
    assert not drifted, f"{rel}: {drifted}"


def test_phase5_adds_no_feature_code():
    """The 55-feature state must be imported, never re-implemented."""
    p5 = ROOT / "src" / "nqr" / "p5"
    src = "".join(f.read_text() for f in p5.glob("*.py"))
    assert "FEATURE_NAMES = " not in src, "Phase 5 must not define its own feature list"
    from nqr.p4.features4 import FEATURE_NAMES
    assert len(FEATURE_NAMES) == 55


# ------------------------------------------------------ sealed 2025-H1 ----
@pytest.mark.parametrize("d", [D(2025, 1, 1), D(2025, 3, 15), D(2025, 6, 30)])
def test_2025_h1_is_hard_blocked(d):
    with pytest.raises(H5.Phase5Violation):
        H5.assert_date_allowed(d)


def test_2025_h1_stays_blocked_even_with_the_validation_unlock():
    H5._VAL_UNLOCKED = True
    try:
        for d in (D(2025, 1, 2), D(2025, 5, 5), D(2025, 6, 30)):
            with pytest.raises(H5.Phase5Violation):
                H5.assert_date_allowed(d)
        with pytest.raises(H5.Phase5Violation):
            H5.assert_path_allowed("/x/2025_H1.parquet")
    finally:
        H5._VAL_UNLOCKED = False


def test_exactly_one_unlock_function_exists_and_it_is_named_for_q1():
    assert [n for n in dir(H5) if n.startswith("unlock")] == ["unlock_phase5_validation"]


def test_range_spanning_a_sealed_window_is_refused():
    for lo, hi in [(D(2024, 12, 1), D(2025, 8, 1)),
                   (D(2025, 7, 1), D(2026, 2, 1)),
                   (D(2026, 1, 1), D(2026, 5, 1))]:
        with pytest.raises(H5.Phase5Violation):
            H5.assert_range_allowed(lo, hi)


# ------------------------------------------------------ sealed April 2026+ ----
@pytest.mark.parametrize("d", [D(2026, 4, 1), D(2026, 6, 17), D(2027, 1, 1)])
def test_april_2026_onward_is_hard_blocked(d):
    with pytest.raises(H5.Phase5Violation):
        H5.assert_date_allowed(d)
    H5._VAL_UNLOCKED = True
    try:
        with pytest.raises(H5.Phase5Violation):
            H5.assert_date_allowed(d)
    finally:
        H5._VAL_UNLOCKED = False


def test_sql_guard_on_2026_fires_before_emitting_any_predicate():
    """2026_H1.parquet contains April+; the guard must refuse at construction."""
    with pytest.raises(H5.Phase5Violation):
        H5.sql_window_guard(D(2026, 1, 1), D(2026, 12, 31))
    with pytest.raises(H5.Phase5Violation):
        H5.sql_window_guard(D(2026, 1, 1), D(2026, 4, 1))
    with pytest.raises(H5.Phase5Violation):
        H5.sql_window_guard(D(2025, 1, 1), D(2025, 6, 30))


def test_sql_guard_bounds_an_allowed_q1_window_on_the_trading_date():
    H5._VAL_UNLOCKED = True
    try:
        sql = H5.sql_window_guard(D(2026, 1, 1), D(2026, 3, 31))
    finally:
        H5._VAL_UNLOCKED = False
    assert "DATE '2026-01-01'" in sql and "DATE '2026-03-31'" in sql
    assert "America/New_York" in sql and "INTERVAL 6 HOUR" in sql


# ------------------------------------------- controlled 2026-Q1 unlock ----
def test_fresh_validation_requires_the_exact_phrase():
    with pytest.raises(H5.Phase5Violation):
        H5.unlock_phase5_validation("please")
    with pytest.raises(H5.Phase5Violation):
        H5.unlock_phase5_validation("I_AM_UNLOCKING_ONLY_2026_Q1_FOR_PHASE4_VALIDATION")
    assert not H5.validation_unlocked()


def test_2026_q1_blocked_by_default_and_open_only_after_the_unlock():
    d = D(2026, 2, 10)
    with pytest.raises(H5.Phase5Violation):
        H5.assert_date_allowed(d)
    with pytest.raises(H5.Phase5Violation):
        H5.assert_path_allowed("/x/2026_H1.parquet")
    H5._VAL_UNLOCKED = True
    try:
        H5.assert_date_allowed(d)
        H5.assert_path_allowed("/x/2026_H1.parquet")
    finally:
        H5._VAL_UNLOCKED = False
    with pytest.raises(H5.Phase5Violation):
        H5.assert_date_allowed(d)


# ------------------------------------------------------- trades only ----
@pytest.mark.parametrize("p", ["/Volumes/T9/nq data/raw/mbp1/2021_H1.parquet",
                               "/x/MBP1/2023_H2.parquet",
                               "/x/glbx-mdp3-20260617.trades.dbn.zst",
                               "/x/a.dbn"])
def test_phase5_refuses_mbp1_and_raw_dbn(p):
    with pytest.raises(H5.Phase5Violation):
        H5.assert_path_allowed(p)


def test_trades_files_in_allowed_periods_are_permitted():
    for k in ("2021_H1", "2022_H2", "2023_H1", "2024_H2", "2025_H2"):
        H5.assert_path_allowed(f"/x/{k}.parquet")


def test_period_map_and_contamination_labels():
    assert H5.period_of(D(2021, 1, 1)) == "DISCOVERY_TRAIN"
    assert H5.period_of(D(2022, 6, 1)) == "SELECTION"
    assert H5.period_of(D(2023, 12, 31)) == "INTERNAL_TEST"
    assert H5.period_of(D(2024, 7, 1)) == "CONTAM_2024"
    assert H5.period_of(D(2025, 6, 30)) == "SEALED_2025H1"
    assert H5.period_of(D(2025, 7, 1)) == "CONTAM_2025H2"
    assert H5.period_of(D(2026, 3, 31)) == "FRESH_VAL"
    assert H5.period_of(D(2026, 4, 1)) == "SEALED_FINAL"
    assert H5.CONTAMINATED == {"CONTAM_2024", "CONTAM_2025H2"}
