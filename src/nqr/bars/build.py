"""Deterministic 2-minute bar construction from raw trade prints.

Bars are half-open [t, t+2min) intervals aligned to multiples of 2 minutes
from the UTC epoch.  Because every US/Eastern UTC offset is a whole number of
hours, epoch-aligned 2-minute boundaries coincide exactly with even-minute ET
boundaries in both EST and EDT.

A bar is CLOSED - and only then knowable - at its end boundary.  No trade with
ts_event >= bar_end can influence the bar.  Empty intervals produce no bar.
"""
from __future__ import annotations

from pathlib import Path

import duckdb

from nqr.holdout import sql_date_guard, sql_trading_date

BAR_SQL = """
WITH src AS (
    SELECT ts_event, price, size, symbol,
           {td} AS trading_date
    FROM read_parquet({files})
    WHERE {guard}
      AND symbol NOT LIKE '%-%'
      AND regexp_matches(symbol, '{outright}')
),
front AS (
    SELECT s.*
    FROM src s
    JOIN front_map f
      ON s.trading_date = f.trading_date AND s.symbol = f.front_symbol
),
bucketed AS (
    SELECT
        trading_date,
        symbol,
        (CAST(epoch_ns(ts_event) AS BIGINT) / {bar_ns}) * {bar_ns} AS bar_ns,
        ts_event, price, size
    FROM front
)
SELECT
    trading_date,
    symbol,
    make_timestamp(bar_ns / 1000)                    AS bar_start,
    make_timestamp((bar_ns + {bar_ns}) / 1000)       AS bar_end,
    arg_min(price, ts_event)                         AS open,
    max(price)                                       AS high,
    min(price)                                       AS low,
    arg_max(price, ts_event)                         AS close,
    sum(size)                                        AS volume,
    count(*)                                         AS trades,
    min(ts_event)                                    AS first_ts,
    max(ts_event)                                    AS last_ts
FROM bucketed
GROUP BY trading_date, symbol, bar_ns
ORDER BY bar_ns
"""


def build_bars(con: duckdb.DuckDBPyConnection, files: list[Path], bar_minutes: int = 2,
               outright_regex: str = r"^NQ[FGHJKMNQUVXZ][0-9]{1,2}$"):
    """front_map must already be registered on ``con`` as a view/table."""
    files_sql = "[" + ",".join(f"'{p}'" for p in files) + "]"
    q = BAR_SQL.format(
        files=files_sql,
        guard=sql_date_guard("ts_event"),
        td=sql_trading_date("ts_event"),
        bar_ns=bar_minutes * 60 * 1_000_000_000,
        outright=outright_regex,
    )
    return con.execute(q).pl()


def arg_min_open_note() -> str:
    """arg_min/arg_max on ts_event resolve open/close deterministically.

    Ties (several prints sharing the identical ts_event, which happens when one
    aggressor sweeps several resting orders) are broken by DuckDB's arg_min /
    arg_max, which return the first/last row encountered.  To make this fully
    deterministic we build bars from the tick cache, which is written in a
    stable (ts_event, sequence, row-order) sort.
    """
    return "see docstring"
