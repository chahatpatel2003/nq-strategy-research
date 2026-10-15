"""Phase-5 period guard.

Structurally identical to the Phase-4 guard and equally strict.  It sits
alongside `holdout.py`, `p3/holdout3.py` and `p4/holdout4.py`, all of which are
inside earlier frozen manifests and are never modified.

    2021-01-01 .. 2021-12-31   DISCOVERY_TRAIN   fit models, scalers, baselines
    2022-01-01 .. 2022-12-31   SELECTION         choose among <=18 configurations
    2023-01-01 .. 2023-12-31   INTERNAL_TEST     internal out-of-sample test
    2024-01-01 .. 2024-12-31   CONTAM_2024       CONTAMINATED - diagnostic only
    2025-01-01 .. 2025-06-30   SEALED_2025H1     FORBIDDEN.  No unlock path exists.
                                                 Last untouched Trades+MBP-1 window.
    2025-07-01 .. 2025-12-31   CONTAM_2025H2     CONTAMINATED - diagnostic only
    2026-01-01 .. 2026-03-31   FRESH_VAL         Phase-5 fresh validation.  Narrow unlock.
    2026-04-01 ..              SEALED_FINAL      FORBIDDEN.  No unlock path exists.

The unlock opens 2026-Q1 and NOTHING else: 2025-H1 and 2026-04-01 onward stay
blocked while it is active.

`2026_H1.parquet` physically extends to 2026-06-17, so every read of it must
carry `sql_window_guard`, which refuses outright any range reaching 2026-04-01.
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
SEALED_H1_START, SEALED_H1_END = D(2025, 1, 1), D(2025, 6, 30)
CONTAM25H2_START, CONTAM25H2_END = D(2025, 7, 1), D(2025, 12, 31)
VAL_START, VAL_END = D(2026, 1, 1), D(2026, 3, 31)
SEALED_FINAL_START = D(2026, 4, 1)

_VAL_UNLOCKED = False
_UNLOCK_PHRASE = "I_AM_UNLOCKING_ONLY_2026_Q1_FOR_PHASE5_VALIDATION"


class Phase5Violation(RuntimeError):
    """Raised when Phase-5 code tries to touch a period it must not."""


def unlock_phase5_validation(confirm: str = "") -> None:
    """Open 2026-01-01..2026-03-31 and nothing else."""
    global _VAL_UNLOCKED
    if confirm != _UNLOCK_PHRASE:
        raise Phase5Violation("unlock_phase5_validation() requires the explicit phrase")
    _VAL_UNLOCKED = True


def validation_unlocked() -> bool:
    return _VAL_UNLOCKED or os.environ.get("NQR_P5_UNLOCK_VAL") == "1"


def period_of(d: D) -> str:
    if d < TRAIN_START:
        return "PRE"
    if d <= TRAIN_END:
        return "DISCOVERY_TRAIN"
    if d <= SELECT_END:
        return "SELECTION"
    if d <= ITEST_END:
        return "INTERNAL_TEST"
    if d <= CONTAM24_END:
        return "CONTAM_2024"
    if d <= SEALED_H1_END:
        return "SEALED_2025H1"
    if d <= CONTAM25H2_END:
        return "CONTAM_2025H2"
    if d <= VAL_END:
        return "FRESH_VAL"
    return "SEALED_FINAL"


CONTAMINATED = {"CONTAM_2024", "CONTAM_2025H2"}


def assert_date_allowed(d: D, what: str = "date") -> None:
    p = period_of(d)
    if p == "SEALED_2025H1":
        raise Phase5Violation(
            f"{what} {d} is inside the SEALED 2025-H1 window "
            f"({SEALED_H1_START}..{SEALED_H1_END}). Phase 5 has NO unlock path for it: "
            "it is the last untouched period holding both Trades and MBP-1, and "
            "Phase 5 is trades-only so it has no reason to spend it.")
    if p == "SEALED_FINAL":
        raise Phase5Violation(
            f"{what} {d} is on/after {SEALED_FINAL_START} (final holdout). "
            "Phase 5 has NO unlock path for it.")
    if p == "FRESH_VAL" and not validation_unlocked():
        raise Phase5Violation(
            f"{what} {d} is Phase-5 fresh validation ({VAL_START}..{VAL_END}) and the "
            "explicit validation unlock has not been given.")
    if p == "PRE":
        raise Phase5Violation(f"{what} {d} is before the project's data start")


def assert_range_allowed(start: D, end: D, what: str = "range") -> None:
    assert_date_allowed(start, f"{what} start")
    assert_date_allowed(end, f"{what} end")
    if start <= SEALED_H1_END and end >= SEALED_H1_START:
        raise Phase5Violation(f"{what} {start}..{end} spans the sealed 2025-H1 window")
    if end >= SEALED_FINAL_START:
        raise Phase5Violation(f"{what} {start}..{end} reaches the 2026 final holdout")


FORBIDDEN_FILE_TAGS = ("2025_H1", "2026_H2")
VAL_FILE_TAGS = ("2026_H1",)


def assert_path_allowed(path: str | os.PathLike) -> None:
    name = os.path.basename(str(path))
    for tag in FORBIDDEN_FILE_TAGS:
        if tag in name:
            raise Phase5Violation(f"Refusing to open {name}: Phase 5 must never read {tag}.")
    if str(path).lower().endswith((".dbn", ".dbn.zst")):
        raise Phase5Violation(
            f"Refusing to open {name}: raw DBN archives on the drive cover the sealed "
            "2026 final holdout and are never a Phase-5 input.")
    if "mbp1" in str(path).lower() or "mbp-1" in str(path).lower():
        raise Phase5Violation(
            f"Refusing to open {name}: Phase 5 is TRADES ONLY and never opens MBP-1.")
    for tag in VAL_FILE_TAGS:
        if tag in name and not validation_unlocked():
            raise Phase5Violation(
                f"Refusing to open {name}: Phase-5 validation is not unlocked.")


def assert_paths_allowed(paths: Iterable[str | os.PathLike]) -> None:
    for p in paths:
        assert_path_allowed(p)


TRADING_DATE_SQL = "CAST(({ts} AT TIME ZONE 'America/New_York') + INTERVAL 6 HOUR AS DATE)"


def sql_trading_date(ts_col: str = "ts_event") -> str:
    return TRADING_DATE_SQL.format(ts=ts_col)


def sql_window_guard(start: D, end: D, ts_col: str = "ts_event") -> str:
    """Hard SQL bound on the Globex trading date, checked against the policy.

    This is the ONLY sanctioned way for Phase 5 to read a raw parquet.  It
    refuses any window reaching 2026-04-01 before emitting a predicate, so an
    April+ row can never be produced by a Phase-5 query even though
    `2026_H1.parquet` contains them.
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
    "contam2025h2": (CONTAM25H2_START, CONTAM25H2_END),
    "val2026q1": (VAL_START, VAL_END),
}
