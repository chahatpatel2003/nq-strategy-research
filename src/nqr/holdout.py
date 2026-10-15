"""Holdout protection.

Phase 1 policy (frozen):
  DEVELOPMENT      2021-01-01 .. 2023-12-31
  VALIDATION       2024-01-01 .. 2024-12-31
  SEALED HOLDOUT   2025-01-01 .. 2025-06-30   (trades + mbp1)
  EXTRA HOLDOUT    2025-07-01 ..              (trades only)

Any attempt to read market *content* dated >= HOLDOUT_START raises
HoldoutViolation unless the process was explicitly unlocked via
``unlock_holdout()`` (wired to a ``--unlock-holdout`` CLI flag that is
NOT to be used in Phase 1).

Knowing that a file *exists* is allowed; reading rows from it is not.
"""
from __future__ import annotations

import datetime as _dt
import os
from typing import Iterable

HOLDOUT_START = _dt.date(2025, 1, 1)

DEV_START = _dt.date(2021, 1, 1)
DEV_END = _dt.date(2023, 12, 31)
VAL_START = _dt.date(2024, 1, 1)
VAL_END = _dt.date(2024, 12, 31)

_UNLOCKED = False


class HoldoutViolation(RuntimeError):
    """Raised when Phase-1 code tries to touch sealed data."""


def unlock_holdout(confirm: str = "") -> None:
    """Deliberate, explicit unlock. Not used in Phase 1."""
    global _UNLOCKED
    if confirm != "I_AM_DELIBERATELY_UNSEALING_THE_HOLDOUT":
        raise HoldoutViolation("unlock_holdout() requires the explicit confirmation string")
    _UNLOCKED = True


def is_unlocked() -> bool:
    return _UNLOCKED or os.environ.get("NQR_UNLOCK_HOLDOUT") == "1"


def assert_date_allowed(d: _dt.date, what: str = "date") -> None:
    if d >= HOLDOUT_START and not is_unlocked():
        raise HoldoutViolation(
            f"{what} {d} is on/after the sealed holdout start {HOLDOUT_START}. "
            "Phase 1 must not read this data."
        )


def assert_range_allowed(start: _dt.date, end: _dt.date, what: str = "range") -> None:
    assert_date_allowed(end, f"{what} end")
    assert_date_allowed(start, f"{what} start")


def assert_path_allowed(path: str | os.PathLike) -> None:
    """Refuse source files whose name indicates holdout content."""
    name = os.path.basename(str(path))
    for tag in ("2025_H1", "2025_H2", "2026_H1", "2026_H2", "2025-", "2026-"):
        if tag in name and not is_unlocked():
            raise HoldoutViolation(
                f"Refusing to read {name}: it contains data on/after {HOLDOUT_START}."
            )


def assert_paths_allowed(paths: Iterable[str | os.PathLike]) -> None:
    for p in paths:
        assert_path_allowed(p)


# Globex trading day starts 18:00 ET.  Shifting ET time by +6h maps
# 18:00 ET -> 00:00 of the next calendar day, so the calendar date of the
# shifted timestamp IS the Globex trading date.
TRADING_DATE_SQL = (
    "CAST(({ts} AT TIME ZONE 'America/New_York') + INTERVAL 6 HOUR AS DATE)"
)


def sql_trading_date(ts_col: str = "ts_event") -> str:
    return TRADING_DATE_SQL.format(ts=ts_col)


def sql_date_guard(ts_col: str = "ts_event") -> str:
    """SQL predicate that hard-caps any query at the holdout boundary.

    Guards on the *Globex trading date*, not the UTC calendar date, so the
    23:00-24:00 UTC tail of 2024-12-31 (which belongs to Globex trading day
    2025-01-02) is excluded too.
    """
    if is_unlocked():
        return "TRUE"
    return f"{sql_trading_date(ts_col)} < DATE '{HOLDOUT_START.isoformat()}'"


def split_of(d: _dt.date) -> str:
    if d < DEV_START:
        return "PRE"
    if d <= DEV_END:
        return "DEV"
    if d <= VAL_END:
        return "VAL"
    return "HOLDOUT"
