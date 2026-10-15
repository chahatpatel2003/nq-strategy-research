"""Session / trading-day calendar for CME Globex NQ.

All internal timestamps are tz-aware UTC.  Session logic is expressed in
America/New_York and therefore follows US DST automatically.

Globex trading day D  :  18:00 ET (D-1)  ->  17:00 ET (D)
  ASIA   18:00 -> 03:00 ET   (spans midnight)
  EU     03:00 -> 09:30 ET
  US     09:30 -> 16:00 ET
  POST   16:00 -> 17:00 ET   (not one of the four published sessions)
  (17:00 -> 18:00 ET is the daily CME maintenance halt: no bars)
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from zoneinfo import ZoneInfo

import numpy as np
import polars as pl

ET = ZoneInfo("America/New_York")
UTC = dt.timezone.utc

SESSION_ORDER = ("ASIA", "EU", "US", "POST")

# (name, start_time_ET, end_time_ET, start_day_offset, end_day_offset)
# offsets are relative to the trading date D.
SESSION_DEFS: tuple[tuple[str, dt.time, dt.time, int, int], ...] = (
    ("ASIA", dt.time(18, 0), dt.time(3, 0), -1, 0),
    ("EU", dt.time(3, 0), dt.time(9, 30), 0, 0),
    ("US", dt.time(9, 30), dt.time(16, 0), 0, 0),
    ("POST", dt.time(16, 0), dt.time(17, 0), 0, 0),
)

DAY_START_ET = dt.time(18, 0)   # of D-1
DAY_END_ET = dt.time(17, 0)     # of D
TRADING_DATE_SHIFT_HOURS = 6    # 18:00 ET + 6h -> 00:00 next calendar day


def et_wall(d: dt.date, t: dt.time) -> dt.datetime:
    """Tz-aware ET wall-clock datetime (DST-correct, fold=0 convention)."""
    return dt.datetime.combine(d, t, tzinfo=ET)


def to_utc(d: dt.date, t: dt.time) -> dt.datetime:
    return et_wall(d, t).astimezone(UTC)


def trading_date_of(ts_utc: dt.datetime) -> dt.date:
    """Globex trading date containing ``ts_utc``."""
    et = ts_utc.astimezone(ET)
    return (et + dt.timedelta(hours=TRADING_DATE_SHIFT_HOURS)).date()


def day_bounds_utc(d: dt.date) -> tuple[dt.datetime, dt.datetime]:
    """[start, end) of Globex trading day ``d`` in UTC."""
    return to_utc(d - dt.timedelta(days=1), DAY_START_ET), to_utc(d, DAY_END_ET)


@dataclass(frozen=True)
class SessionWindow:
    trading_date: dt.date
    name: str
    start_utc: dt.datetime
    end_utc: dt.datetime


def sessions_for_day(d: dt.date) -> list[SessionWindow]:
    out = []
    for name, t0, t1, off0, off1 in SESSION_DEFS:
        s = to_utc(d + dt.timedelta(days=off0), t0)
        e = to_utc(d + dt.timedelta(days=off1), t1)
        out.append(SessionWindow(d, name, s, e))
    return out


def session_of(ts_utc: dt.datetime) -> str:
    """Session name for a timestamp (assumes ts is inside a Globex day)."""
    d = trading_date_of(ts_utc)
    for w in sessions_for_day(d):
        if w.start_utc <= ts_utc < w.end_utc:
            return w.name
    return "NONE"


# ---------------------------------------------------------------- polars ----
def add_trading_date(df: pl.DataFrame | pl.LazyFrame, ts_col: str = "ts_event"):
    return df.with_columns(
        (pl.col(ts_col).dt.convert_time_zone("America/New_York") + pl.duration(hours=TRADING_DATE_SHIFT_HOURS))
        .dt.date()
        .alias("trading_date")
    )


def add_session(df: pl.DataFrame | pl.LazyFrame, ts_col: str = "ts_event"):
    """Attach ET minute-of-day and the session label."""
    et = pl.col(ts_col).dt.convert_time_zone("America/New_York")
    # dt.hour()/dt.minute() are Int8 - cast before arithmetic or 18*60 overflows
    mod = et.dt.hour().cast(pl.Int32) * 60 + et.dt.minute().cast(pl.Int32)
    return df.with_columns(
        mod.alias("et_minute"),
        pl.when((mod >= 18 * 60) | (mod < 3 * 60)).then(pl.lit("ASIA"))
        .when(mod < 9 * 60 + 30).then(pl.lit("EU"))
        .when(mod < 16 * 60).then(pl.lit("US"))
        .when(mod < 17 * 60).then(pl.lit("POST"))
        .otherwise(pl.lit("HALT"))
        .alias("session"),
    )


def add_rth_window(df, ts_col: str = "ts_event", start_min: int = 9 * 60 + 30, end_min: int = 11 * 60 + 30):
    et = pl.col(ts_col).dt.convert_time_zone("America/New_York")
    mod = et.dt.hour().cast(pl.Int32) * 60 + et.dt.minute().cast(pl.Int32)
    return df.with_columns(((mod >= start_min) & (mod < end_min)).alias("is_0930_1130"))
