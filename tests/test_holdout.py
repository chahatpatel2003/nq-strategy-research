import datetime as dt
import pytest
from nqr import holdout


def test_dev_and_val_allowed():
    holdout.assert_range_allowed(dt.date(2021, 1, 1), dt.date(2023, 12, 31))
    holdout.assert_range_allowed(dt.date(2024, 1, 1), dt.date(2024, 12, 31))


@pytest.mark.parametrize("d", [dt.date(2025, 1, 1), dt.date(2025, 6, 30),
                              dt.date(2025, 7, 1), dt.date(2026, 1, 5)])
def test_holdout_dates_blocked(d):
    with pytest.raises(holdout.HoldoutViolation):
        holdout.assert_date_allowed(d)


@pytest.mark.parametrize("f", ["2025_H1.parquet", "2025_H2.parquet", "2026_H1.parquet"])
def test_holdout_files_blocked(f):
    with pytest.raises(holdout.HoldoutViolation):
        holdout.assert_path_allowed("/Volumes/T9/nq data/raw/trades/" + f)


def test_dev_files_allowed():
    for f in ["2021_H1.parquet", "2024_H2.parquet"]:
        holdout.assert_path_allowed("/x/" + f)


def test_sql_guard_uses_trading_date_not_utc_date():
    g = holdout.sql_date_guard("ts_event")
    assert "America/New_York" in g and "INTERVAL 6 HOUR" in g
    assert "2025-01-01" in g


def test_unlock_requires_confirmation():
    with pytest.raises(holdout.HoldoutViolation):
        holdout.unlock_holdout("please")


def test_split_of():
    assert holdout.split_of(dt.date(2022, 5, 1)) == "DEV"
    assert holdout.split_of(dt.date(2024, 5, 1)) == "VAL"
    assert holdout.split_of(dt.date(2025, 5, 1)) == "HOLDOUT"


def test_allowed_half_files_excludes_2025_plus():
    from nqr import paths
    got = set(paths.allowed_half_files("trades"))
    assert got == {"2021_H1", "2021_H2", "2022_H1", "2022_H2",
                   "2023_H1", "2023_H2", "2024_H1", "2024_H2"}
