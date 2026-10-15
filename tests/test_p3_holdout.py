"""Phase-3 period policy: 2025-H1 and 2026 have NO unlock path; 2025-H2 has one."""
import datetime as dt
import pytest

from nqr.p3 import holdout3 as H
from nqr.p3 import cache3

D = dt.date


def test_period_classification():
    assert H.period_of(D(2021, 1, 4)) == "DEV"
    assert H.period_of(D(2023, 12, 31)) == "DEV"
    assert H.period_of(D(2024, 6, 1)) == "DIAG_2024"
    assert H.period_of(D(2025, 1, 1)) == "SEALED_H1"
    assert H.period_of(D(2025, 6, 30)) == "SEALED_H1"
    assert H.period_of(D(2025, 7, 1)) == "VAL_2025H2"
    assert H.period_of(D(2025, 12, 31)) == "VAL_2025H2"
    assert H.period_of(D(2026, 1, 1)) == "SEALED_2026"


@pytest.mark.parametrize("d", [D(2025, 1, 1), D(2025, 3, 15), D(2025, 6, 30)])
def test_2025_h1_is_blocked_even_when_validation_is_unlocked(d, monkeypatch):
    monkeypatch.setattr(H, "_VAL_UNLOCKED", True)
    with pytest.raises(H.Phase3Violation, match="SEALED 2025-H1"):
        H.assert_date_allowed(d)


@pytest.mark.parametrize("d", [D(2026, 1, 1), D(2026, 7, 1), D(2027, 1, 1)])
def test_2026_is_blocked_even_when_validation_is_unlocked(d, monkeypatch):
    monkeypatch.setattr(H, "_VAL_UNLOCKED", True)
    with pytest.raises(H.Phase3Violation, match="final holdout"):
        H.assert_date_allowed(d)


def test_2025_h2_blocked_until_unlocked(monkeypatch):
    monkeypatch.setattr(H, "_VAL_UNLOCKED", False)
    monkeypatch.delenv("NQR_P3_UNLOCK_VAL", raising=False)
    with pytest.raises(H.Phase3Violation, match="validation unlock"):
        H.assert_date_allowed(D(2025, 9, 1))
    monkeypatch.setattr(H, "_VAL_UNLOCKED", True)
    H.assert_date_allowed(D(2025, 9, 1))


def test_dev_and_2024_always_allowed(monkeypatch):
    monkeypatch.setattr(H, "_VAL_UNLOCKED", False)
    monkeypatch.delenv("NQR_P3_UNLOCK_VAL", raising=False)
    H.assert_range_allowed(*H.SPLITS["dev"])
    H.assert_range_allowed(*H.SPLITS["diag2024"])


def test_unlock_requires_the_exact_phrase():
    with pytest.raises(H.Phase3Violation):
        H.unlock_phase3_validation("please")
    with pytest.raises(H.Phase3Violation):
        H.unlock_phase3_validation("I_AM_DELIBERATELY_UNSEALING_THE_HOLDOUT")


def test_range_cannot_straddle_the_sealed_window(monkeypatch):
    monkeypatch.setattr(H, "_VAL_UNLOCKED", True)
    with pytest.raises(H.Phase3Violation, match="spans the sealed"):
        H.assert_range_allowed(D(2024, 1, 1), D(2025, 12, 31))


@pytest.mark.parametrize("f", ["2025_H1.parquet", "2026_H1.parquet"])
def test_forbidden_files_blocked_even_when_unlocked(f, monkeypatch):
    monkeypatch.setattr(H, "_VAL_UNLOCKED", True)
    with pytest.raises(H.Phase3Violation):
        H.assert_path_allowed("/Volumes/T9/nq data/raw/trades/" + f)


def test_2025_h2_file_requires_unlock(monkeypatch):
    monkeypatch.setattr(H, "_VAL_UNLOCKED", False)
    monkeypatch.delenv("NQR_P3_UNLOCK_VAL", raising=False)
    with pytest.raises(H.Phase3Violation):
        H.assert_path_allowed("/x/2025_H2.parquet")
    monkeypatch.setattr(H, "_VAL_UNLOCKED", True)
    H.assert_path_allowed("/x/2025_H2.parquet")


def test_sql_guard_is_on_the_globex_trading_date():
    g = H.sql_window_guard(D(2021, 1, 1), D(2023, 12, 31))
    assert "America/New_York" in g and "INTERVAL 6 HOUR" in g
    assert "2021-01-01" in g and "2023-12-31" in g


def test_month_loader_refuses_sealed_months(monkeypatch):
    monkeypatch.setattr(H, "_VAL_UNLOCKED", True)
    for ym in ("2025-01", "2025-04", "2025-06"):
        with pytest.raises(H.Phase3Violation):
            cache3.load_month(ym)
    for ym in ("2026-01", "2026-08"):
        with pytest.raises(H.Phase3Violation):
            cache3.load_month(ym)


def test_split_month_lists_never_include_sealed_months():
    assert cache3.months_for("dev")[-1] == "2023-12"
    assert cache3.months_for("diag2024") == [f"2024-{m:02d}" for m in range(1, 13)]
    assert cache3.months_for("val2025h2") == [f"2025-{m:02d}" for m in range(7, 13)]
    for split in ("dev", "diag2024", "val2025h2"):
        for ym in cache3.months_for(split):
            assert not ("2025-01" <= ym <= "2025-06")
            assert not ym.startswith("2026")
