"""Phase-3 period guard.

Phase 3 needs a FINER policy than the Phase-1/2 guard, which simply blocks
everything from 2025-01-01 onward.  ``src/nqr/holdout.py`` is inside both the
Phase-1 and the Phase-2 frozen manifests and is therefore never modified; this
module sits alongside it and is strictly more restrictive in the places that
matter.

    2021-01-01 .. 2023-12-31   DEV          development
    2024-01-01 .. 2024-12-31   DIAG_2024    CONTAMINATED - diagnostic only,
                                            already used as validation in
                                            Phases 1 and 2.  Never counts
                                            toward a Phase-3 PASS.
    2025-01-01 .. 2025-06-30   SEALED_H1    FORBIDDEN.  There is deliberately
                                            NO unlock path in Phase 3 - this is
                                            the only untouched period with both
                                            Trades and MBP-1 and it is reserved
                                            for future order-flow research.
    2025-07-01 .. 2025-12-31   VAL_2025H2   Phase-3 fresh validation.  Requires
                                            an explicit unlock.
    2026-01-01 ..              SEALED_2026  FORBIDDEN.  No unlock path in
                                            Phase 3 under any circumstance.

The unlock is deliberately narrow: ``unlock_phase3_validation()`` opens
2025-07-01..2025-12-31 and NOTHING else.  2025-H1 and 2026 stay blocked even
while it is active.
"""
from __future__ import annotations

import datetime as _dt
import os
from typing import Iterable

D = _dt.date

DEV_START, DEV_END = D(2021, 1, 1), D(2023, 12, 31)
DIAG_START, DIAG_END = D(2024, 1, 1), D(2024, 12, 31)
SEALED_H1_START, SEALED_H1_END = D(2025, 1, 1), D(2025, 6, 30)
VAL_START, VAL_END = D(2025, 7, 1), D(2025, 12, 31)
SEALED_2026_START = D(2026, 1, 1)

_VAL_UNLOCKED = False
_UNLOCK_PHRASE = "I_AM_UNLOCKING_ONLY_2025_H2_FOR_PHASE3_VALIDATION"


class Phase3Violation(RuntimeError):
    """Raised when Phase-3 code tries to touch a period it must not."""


def unlock_phase3_validation(confirm: str = "") -> None:
    """Open 2025-07-01..2025-12-31 and nothing else."""
    global _VAL_UNLOCKED
    if confirm != _UNLOCK_PHRASE:
        raise Phase3Violation("unlock_phase3_validation() requires the explicit phrase")
    _VAL_UNLOCKED = True


def validation_unlocked() -> bool:
    return _VAL_UNLOCKED or os.environ.get("NQR_P3_UNLOCK_VAL") == "1"


def period_of(d: D) -> str:
    if d < DEV_START:
        return "PRE"
    if d <= DEV_END:
        return "DEV"
    if d <= DIAG_END:
        return "DIAG_2024"
    if d <= SEALED_H1_END:
        return "SEALED_H1"
    if d <= VAL_END:
        return "VAL_2025H2"
    return "SEALED_2026"


def assert_date_allowed(d: D, what: str = "date") -> None:
    p = period_of(d)
    if p == "SEALED_H1":
        raise Phase3Violation(
            f"{what} {d} is inside the SEALED 2025-H1 window "
            f"({SEALED_H1_START}..{SEALED_H1_END}). Phase 3 has NO unlock path for it: "
            "it is the only untouched period holding both Trades and MBP-1.")
    if p == "SEALED_2026":
        raise Phase3Violation(
            f"{what} {d} is on/after {SEALED_2026_START} (final holdout). "
            "Phase 3 has NO unlock path for it.")
    if p == "VAL_2025H2" and not validation_unlocked():
        raise Phase3Violation(
            f"{what} {d} is Phase-3 fresh validation ({VAL_START}..{VAL_END}) and the "
            "explicit validation unlock has not been given.")
    if p == "PRE":
        raise Phase3Violation(f"{what} {d} is before the project's data start")


def assert_range_allowed(start: D, end: D, what: str = "range") -> None:
    assert_date_allowed(start, f"{what} start")
    assert_date_allowed(end, f"{what} end")
    # a range must not straddle a sealed window even if both endpoints are legal
    if start <= SEALED_H1_END and end >= SEALED_H1_START:
        raise Phase3Violation(
            f"{what} {start}..{end} spans the sealed 2025-H1 window")
    if end >= SEALED_2026_START:
        raise Phase3Violation(f"{what} {start}..{end} reaches the 2026 final holdout")


# ---------------------------------------------------------------- files ----
FORBIDDEN_FILE_TAGS = ("2025_H1", "2026_H1", "2026_H2")
VAL_FILE_TAGS = ("2025_H2",)


def assert_path_allowed(path: str | os.PathLike) -> None:
    name = os.path.basename(str(path))
    for tag in FORBIDDEN_FILE_TAGS:
        if tag in name:
            raise Phase3Violation(
                f"Refusing to open {name}: Phase 3 must never read {tag}.")
    for tag in VAL_FILE_TAGS:
        if tag in name and not validation_unlocked():
            raise Phase3Violation(
                f"Refusing to open {name}: Phase-3 validation is not unlocked.")


def assert_paths_allowed(paths: Iterable[str | os.PathLike]) -> None:
    for p in paths:
        assert_path_allowed(p)


# ------------------------------------------------------------------ SQL ----
TRADING_DATE_SQL = (
    "CAST(({ts} AT TIME ZONE 'America/New_York') + INTERVAL 6 HOUR AS DATE)")


def sql_trading_date(ts_col: str = "ts_event") -> str:
    return TRADING_DATE_SQL.format(ts=ts_col)


def sql_window_guard(start: D, end: D, ts_col: str = "ts_event") -> str:
    """Hard SQL bound on the Globex trading date, checked against the policy.

    Expressed on the Globex trading date rather than the UTC calendar date so
    the evening tail of a calendar day cannot leak into the next trading day.
    """
    assert_range_allowed(start, end, "sql window")
    td = sql_trading_date(ts_col)
    return f"{td} >= DATE '{start.isoformat()}' AND {td} <= DATE '{end.isoformat()}'"


SPLITS = {
    "dev": (DEV_START, DEV_END),
    "diag2024": (DIAG_START, DIAG_END),
    "val2025h2": (VAL_START, VAL_END),
}
