"""Phase-4 period guard + previous-phase immutability."""
import datetime as dt
import hashlib
import json
from pathlib import Path

import pytest

from nqr.p4 import holdout4 as H4

ROOT = Path(__file__).resolve().parents[1]
D = dt.date

FROZEN_IDS = {
    "results/frozen_manifest.json": "fastslow-1.0.0+5980044a44eebf7b",
    "results/p2_frozen_manifest.json": "impexh-1.0.0.impl2+48c76a0e68b88947",
    "results/p3_frozen_manifest.json": "dcevent-1.0.0.impl3+d33e5d5d116f1adb",
}


# ------------------------------------------------------ sealed windows ----
@pytest.mark.parametrize("d", [D(2025, 1, 1), D(2025, 3, 15), D(2025, 6, 30)])
def test_2025_h1_is_hard_blocked(d):
    with pytest.raises(H4.Phase4Violation):
        H4.assert_date_allowed(d)


def test_2025_h1_stays_blocked_even_with_the_validation_unlock():
    """The unlock opens 2026-Q1 and NOTHING else."""
    H4._VAL_UNLOCKED = True
    try:
        for d in (D(2025, 1, 2), D(2025, 5, 5), D(2025, 6, 30)):
            with pytest.raises(H4.Phase4Violation):
                H4.assert_date_allowed(d)
        with pytest.raises(H4.Phase4Violation):
            H4.assert_path_allowed("/x/2025_H1.parquet")
    finally:
        H4._VAL_UNLOCKED = False


def test_no_unlock_function_can_open_2025_h1_or_the_final_holdout():
    """There is exactly one unlock and it is named for 2026-Q1."""
    unlocks = [n for n in dir(H4) if n.startswith("unlock")]
    assert unlocks == ["unlock_phase4_validation"]


@pytest.mark.parametrize("d", [D(2026, 4, 1), D(2026, 6, 17), D(2027, 1, 1)])
def test_april_2026_onward_is_hard_blocked(d):
    with pytest.raises(H4.Phase4Violation):
        H4.assert_date_allowed(d)
    H4._VAL_UNLOCKED = True
    try:
        with pytest.raises(H4.Phase4Violation):
            H4.assert_date_allowed(d)
    finally:
        H4._VAL_UNLOCKED = False


def test_range_spanning_a_sealed_window_is_refused():
    for lo, hi in [(D(2024, 12, 1), D(2025, 8, 1)),      # spans 2025-H1
                   (D(2025, 7, 1), D(2026, 2, 1)),        # end needs the unlock
                   (D(2026, 1, 1), D(2026, 5, 1))]:       # reaches the final holdout
        with pytest.raises(H4.Phase4Violation):
            H4.assert_range_allowed(lo, hi)


def test_sql_window_guard_refuses_forbidden_ranges_and_bounds_allowed_ones():
    with pytest.raises(H4.Phase4Violation):
        H4.sql_window_guard(D(2025, 1, 1), D(2025, 6, 30))
    with pytest.raises(H4.Phase4Violation):
        H4.sql_window_guard(D(2026, 1, 1), D(2026, 12, 31))
    H4._VAL_UNLOCKED = True
    try:
        sql = H4.sql_window_guard(D(2026, 1, 1), D(2026, 3, 31))
    finally:
        H4._VAL_UNLOCKED = False
    assert "DATE '2026-03-31'" in sql and "DATE '2026-01-01'" in sql


# --------------------------------------------- controlled 2026-Q1 unlock ----
def test_fresh_validation_requires_the_exact_phrase():
    with pytest.raises(H4.Phase4Violation):
        H4.unlock_phase4_validation("please")
    assert not H4.validation_unlocked()


def test_2026_q1_blocked_by_default_and_open_only_after_the_unlock():
    d = D(2026, 2, 10)
    with pytest.raises(H4.Phase4Violation):
        H4.assert_date_allowed(d)
    with pytest.raises(H4.Phase4Violation):
        H4.assert_path_allowed("/x/2026_H1.parquet")
    H4._VAL_UNLOCKED = True
    try:
        H4.assert_date_allowed(d)
        H4.assert_path_allowed("/x/2026_H1.parquet")
    finally:
        H4._VAL_UNLOCKED = False
    with pytest.raises(H4.Phase4Violation):
        H4.assert_date_allowed(d)


def test_period_map_is_exhaustive_and_ordered():
    assert H4.period_of(D(2021, 1, 1)) == "DISCOVERY_TRAIN"
    assert H4.period_of(D(2021, 12, 31)) == "DISCOVERY_TRAIN"
    assert H4.period_of(D(2022, 1, 1)) == "SELECTION"
    assert H4.period_of(D(2023, 12, 31)) == "INTERNAL_TEST"
    assert H4.period_of(D(2024, 7, 1)) == "CONTAM_2024"
    assert H4.period_of(D(2025, 6, 30)) == "SEALED_2025H1"
    assert H4.period_of(D(2025, 7, 1)) == "CONTAM_2025H2"
    assert H4.period_of(D(2026, 3, 31)) == "FRESH_VAL"
    assert H4.period_of(D(2026, 4, 1)) == "SEALED_FINAL"


def test_contaminated_splits_are_labelled_as_such():
    assert H4.CONTAMINATED == {"CONTAM_2024", "CONTAM_2025H2"}
    for s in ("contam2024", "contam2025h2"):
        lo, hi = H4.SPLITS[s]
        assert H4.period_of(lo) in H4.CONTAMINATED
        assert H4.period_of(hi) in H4.CONTAMINATED


# ------------------------------------------- previous-phase immutability ----
@pytest.mark.parametrize("rel,frozen_id", sorted(FROZEN_IDS.items()))
def test_previous_phase_frozen_manifest_still_matches_disk(rel, frozen_id):
    man = json.loads((ROOT / rel).read_text())
    assert man["frozen_id"] == frozen_id
    drifted = [f for f, dg in man["files"].items()
               if hashlib.sha256((ROOT / f).read_bytes()).hexdigest() != dg]
    assert not drifted, f"{rel}: {drifted}"


def test_phase4_does_not_import_or_shadow_earlier_holdout_modules():
    """holdout4 sits ALONGSIDE the frozen guards; it never relaxes them."""
    src = (ROOT / "src" / "nqr" / "p4" / "holdout4.py").read_text()
    assert "unlock_phase3" not in src and "unlock_holdout" not in src
    for tag in ("2025_H1", "2026_H2"):
        assert tag in H4.FORBIDDEN_FILE_TAGS
