import datetime as dt
from zoneinfo import ZoneInfo
import pytest
from nqr.sessions.calendar import (ET, day_bounds_utc, sessions_for_day,
                                   session_of, trading_date_of, to_utc)

UTC = dt.timezone.utc


def test_globex_day_is_23_hours_year_round():
    for d in (dt.date(2021, 1, 15), dt.date(2021, 7, 15), dt.date(2024, 3, 11),
              dt.date(2024, 11, 4), dt.date(2024, 12, 31)):
        s, e = day_bounds_utc(d)
        assert e - s == dt.timedelta(hours=23), d


def test_dst_offsets_are_not_hardcoded():
    # winter: ET = UTC-5 ; summer: ET = UTC-4
    assert to_utc(dt.date(2024, 1, 15), dt.time(9, 30)).hour == 14
    assert to_utc(dt.date(2024, 7, 15), dt.time(9, 30)).hour == 13


def test_spring_forward_day():
    # 2024-03-10 02:00 EST -> 03:00 EDT.  Globex day 2024-03-11 opens 18:00 EDT.
    s, e = day_bounds_utc(dt.date(2024, 3, 11))
    assert s == dt.datetime(2024, 3, 10, 22, 0, tzinfo=UTC)
    assert e == dt.datetime(2024, 3, 11, 21, 0, tzinfo=UTC)


def test_fall_back_day():
    s, e = day_bounds_utc(dt.date(2024, 11, 4))
    assert s == dt.datetime(2024, 11, 3, 23, 0, tzinfo=UTC)
    assert e == dt.datetime(2024, 11, 4, 22, 0, tzinfo=UTC)


def test_sessions_tile_the_day_without_overlap():
    for d in (dt.date(2022, 6, 1), dt.date(2024, 3, 11), dt.date(2024, 11, 4)):
        ws = sessions_for_day(d)
        s, e = day_bounds_utc(d)
        assert ws[0].start_utc == s
        assert ws[-1].end_utc == e
        for a, b in zip(ws, ws[1:]):
            assert a.end_utc == b.start_utc, (d, a.name, b.name)


def test_trading_date_boundaries():
    # 17:59:59 ET belongs to day D ; 18:00:00 ET belongs to day D+1
    a = dt.datetime.combine(dt.date(2023, 5, 10), dt.time(17, 59, 59), tzinfo=ET)
    b = dt.datetime.combine(dt.date(2023, 5, 10), dt.time(18, 0, 0), tzinfo=ET)
    assert trading_date_of(a.astimezone(UTC)) == dt.date(2023, 5, 10)
    assert trading_date_of(b.astimezone(UTC)) == dt.date(2023, 5, 11)


@pytest.mark.parametrize("t,expect", [
    (dt.time(18, 30), "ASIA"), (dt.time(2, 59), "ASIA"), (dt.time(3, 0), "EU"),
    (dt.time(9, 29), "EU"), (dt.time(9, 30), "US"), (dt.time(15, 59), "US"),
    (dt.time(16, 0), "POST"), (dt.time(16, 59), "POST"),
])
def test_session_labels(t, expect):
    d = dt.date(2023, 6, 14)
    day = d - dt.timedelta(days=1) if t >= dt.time(18, 0) else d
    ts = dt.datetime.combine(day, t, tzinfo=ET).astimezone(UTC)
    assert session_of(ts) == expect


def test_polars_session_labels_no_int8_overflow():
    """dt.hour() is Int8; 18*60 must not wrap."""
    import polars as pl
    from nqr.sessions.calendar import add_session
    rows = [("2023-06-14 22:30", "ASIA"), ("2023-06-14 07:30", "EU"),
            ("2023-06-14 14:00", "US"), ("2023-06-14 20:30", "POST"),
            ("2023-06-14 21:30", "HALT")]
    df = pl.DataFrame({"ts": [r[0] for r in rows]}).with_columns(
        pl.col("ts").str.to_datetime("%Y-%m-%d %H:%M").dt.replace_time_zone("UTC"))
    got = add_session(df, "ts")
    assert got["et_minute"].min() >= 0 and got["et_minute"].max() < 1440
    assert got["session"].to_list() == [r[1] for r in rows]
