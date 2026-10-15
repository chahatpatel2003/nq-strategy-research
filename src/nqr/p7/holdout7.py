"""Phase-7 period guard.

Stricter than every previous phase, because Phase 7 spends the last untouched
MBP-1 window and must not be able to reach anything else.

    2021-01-01 .. 2021-12-31   TRAIN        fit model, scaler, selectivity quantiles
    2022-01-01 .. 2022-12-31   SELECT       the 12 configurations, once
    2023-01-01 .. 2023-12-31   ITEST        internal development OOS
    2024-01-01 .. 2024-12-31   CONTAM_2024  CONTAMINATED diagnostic, post-freeze only
    2025-01-01 .. 2025-06-30   FRESH_VAL    the ONLY fresh validation.  Narrow unlock.
    2025-07-01 .. 2025-12-31   NOT_PHASE7   FORBIDDEN.  Not a Phase-7 period at all.
    2026-01-01 ..              FORBIDDEN.   NO UNLOCK PATH EXISTS, ever.

Phase 7 has no reason to touch 2026 and deliberately has no code path to it:
2026-Q1 remains an independent untouched Trades-only reserve for a later phase,
and 2026-04-01+ is the project's final holdout.
"""
from __future__ import annotations

import datetime as _dt
import os
from typing import Iterable

D = _dt.date

TRAIN_START, TRAIN_END = D(2021, 1, 1), D(2021, 12, 31)
SELECT_START, SELECT_END = D(2022, 1, 1), D(2022, 12, 31)
ITEST_START, ITEST_END = D(2023, 1, 1), D(2023, 12, 31)
DEV_START, DEV_END = TRAIN_START, ITEST_END
CONTAM24_START, CONTAM24_END = D(2024, 1, 1), D(2024, 12, 31)
VAL_START, VAL_END = D(2025, 1, 1), D(2025, 6, 30)      # 2025-H1: the MBP holdout
NOT_P7_START, NOT_P7_END = D(2025, 7, 1), D(2025, 12, 31)
FORBIDDEN_2026_START = D(2026, 1, 1)

_VAL_UNLOCKED = False
_UNLOCK_PHRASE = "I_AM_UNLOCKING_ONLY_2025_H1_FOR_PHASE7_FRESH_VALIDATION"


class Phase7Violation(RuntimeError):
    """Raised when Phase-7 code tries to touch a period it must not."""


def unlock_phase7_validation(confirm: str = "") -> None:
    """Open 2025-01-01..2025-06-30 and nothing else."""
    global _VAL_UNLOCKED
    if confirm != _UNLOCK_PHRASE:
        raise Phase7Violation("unlock_phase7_validation() requires the explicit phrase")
    _VAL_UNLOCKED = True


def validation_unlocked() -> bool:
    return _VAL_UNLOCKED or os.environ.get("NQR_P7_UNLOCK_VAL") == "1"


def period_of(d: D) -> str:
    if d < TRAIN_START:
        return "PRE"
    if d <= TRAIN_END:
        return "TRAIN"
    if d <= SELECT_END:
        return "SELECT"
    if d <= ITEST_END:
        return "ITEST"
    if d <= CONTAM24_END:
        return "CONTAM_2024"
    if d <= VAL_END:
        return "FRESH_VAL"
    if d <= NOT_P7_END:
        return "NOT_PHASE7"
    return "FORBIDDEN_2026"


CONTAMINATED = {"CONTAM_2024"}
DEV_PERIODS = ("train2021", "select2022", "itest2023")


def assert_date_allowed(d: D, what: str = "date") -> None:
    p = period_of(d)
    if p == "FORBIDDEN_2026":
        raise Phase7Violation(
            f"{what} {d} is 2026 or later. Phase 7 has NO unlock path for it: 2026-Q1 is "
            "an independent untouched Trades-only reserve and 2026-04-01+ is the final "
            "holdout.")
    if p == "NOT_PHASE7":
        raise Phase7Violation(
            f"{what} {d} is 2025-H2, which is not a Phase-7 period (it was spent as "
            "Phase-3 validation). Phase 7 has no unlock path for it.")
    if p == "FRESH_VAL" and not validation_unlocked():
        raise Phase7Violation(
            f"{what} {d} is inside the Phase-7 FRESH MBP-1 holdout "
            f"({VAL_START}..{VAL_END}) and the explicit unlock has not been given. "
            "This is the last untouched Trades+MBP-1 window in the project.")
    if p == "PRE":
        raise Phase7Violation(f"{what} {d} is before the project's data start")


def assert_range_allowed(start: D, end: D, what: str = "range") -> None:
    assert_date_allowed(start, f"{what} start")
    assert_date_allowed(end, f"{what} end")
    if end >= FORBIDDEN_2026_START:
        raise Phase7Violation(f"{what} {start}..{end} reaches 2026")
    if start <= NOT_P7_END and end >= NOT_P7_START:
        raise Phase7Violation(f"{what} {start}..{end} spans 2025-H2")
    if not validation_unlocked() and start <= VAL_END and end >= VAL_START:
        raise Phase7Violation(f"{what} {start}..{end} spans the sealed 2025-H1 MBP holdout")


FORBIDDEN_FILE_TAGS = ("2025_H2", "2026_H1", "2026_H2")
VAL_FILE_TAGS = ("2025_H1",)


def assert_path_allowed(path: str | os.PathLike) -> None:
    name = os.path.basename(str(path))
    for tag in FORBIDDEN_FILE_TAGS:
        if tag in name:
            raise Phase7Violation(f"Refusing to open {name}: Phase 7 must never read {tag}.")
    if str(path).lower().endswith((".dbn", ".dbn.zst")):
        raise Phase7Violation(f"Refusing to open {name}: raw DBN archives are never a "
                              "Phase-7 input.")
    for tag in VAL_FILE_TAGS:
        if tag in name and not validation_unlocked():
            raise Phase7Violation(
                f"Refusing to open {name}: it holds the sealed 2025-H1 MBP-1 holdout and "
                "the Phase-7 fresh-validation unlock has not been given.")


def assert_paths_allowed(paths: Iterable[str | os.PathLike]) -> None:
    for p in paths:
        assert_path_allowed(p)


TRADING_DATE_SQL = "CAST(({ts} AT TIME ZONE 'America/New_York') + INTERVAL 6 HOUR AS DATE)"


def sql_trading_date(ts_col: str = "ts_event") -> str:
    return TRADING_DATE_SQL.format(ts=ts_col)


def sql_window_guard(start: D, end: D, ts_col: str = "ts_event") -> str:
    """The ONLY sanctioned way for Phase 7 to bound a raw scan.

    Refuses the whole window before emitting a predicate, so a forbidden row can
    never be produced even transiently by a file that also contains allowed rows.
    """
    assert_range_allowed(start, end, "sql window")
    td = sql_trading_date(ts_col)
    return f"{td} >= DATE '{start.isoformat()}' AND {td} <= DATE '{end.isoformat()}'"


SPLITS = {
    "train2021": (TRAIN_START, TRAIN_END),
    "select2022": (SELECT_START, SELECT_END),
    "itest2023": (ITEST_START, ITEST_END),
    "dev": (DEV_START, DEV_END),
    "contam2024": (CONTAM24_START, CONTAM24_END),
    "val2025h1": (VAL_START, VAL_END),
}
