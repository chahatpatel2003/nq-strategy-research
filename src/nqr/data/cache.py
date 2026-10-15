"""Front-contract tick cache.

Writes one compact parquet per calendar month containing ONLY the front
contract's outright trade prints, in exact source order:

    ts_ns        int64   ts_event, nanoseconds since the UTC epoch
    px_ticks     int32   price / 0.25  (exact - all NQ prints are tick aligned)
    size         int32
    row_seq      int64   (file_index * 2^40 + file_row_number) -> global stable order

Original T9 parquet files are never written to.  Everything lands under
``data_cache/`` inside the project.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import duckdb
import numpy as np
import polars as pl

from nqr import paths
from nqr.holdout import sql_date_guard, sql_trading_date

TICKS_DIR = paths.CACHE_DIR / "ticks"
BARS_DIR = paths.CACHE_DIR / "bars"
TICK = 0.25

CACHE_SQL = """
COPY (
  WITH src AS (
    SELECT
      {td}                                            AS trading_date,
      symbol,
      CAST(epoch_ns(ts_event) AS BIGINT)              AS ts_ns,
      CAST(round(price / {tick}) AS INTEGER)          AS px_ticks,
      CAST(size AS INTEGER)                           AS size,
      CAST({fidx} AS BIGINT) * 1099511627776 + file_row_number AS row_seq
    FROM read_parquet('{path}', file_row_number=true)
    WHERE {guard}
      AND symbol NOT LIKE '%-%'
      AND regexp_matches(symbol, '{outright}')
  )
  SELECT s.trading_date, s.symbol, s.ts_ns, s.px_ticks, s.size, s.row_seq,
         strftime(s.trading_date, '%Y-%m') AS ym
  FROM src s
  JOIN front_map f
    ON s.trading_date = f.trading_date AND s.symbol = f.front_symbol
  ORDER BY s.ts_ns, s.row_seq
) TO '{outdir}' (FORMAT PARQUET, PARTITION_BY (ym), COMPRESSION ZSTD,
                 APPEND, FILENAME_PATTERN '{{uuid}}')
"""


def build_tick_cache(con: duckdb.DuckDBPyConnection, half_files: dict[str, Path],
                     outright_regex: str, outdir: Path = TICKS_DIR) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    for fidx, (key, path) in enumerate(sorted(half_files.items())):
        q = CACHE_SQL.format(
            path=path, guard=sql_date_guard("ts_event"), td=sql_trading_date("ts_event"),
            tick=TICK, outright=outright_regex, outdir=outdir, fidx=fidx, stem=key,
        )
        con.execute(q)
        print(f"  cached ticks {key}", flush=True)


def month_keys(start: dt.date, end: dt.date) -> list[str]:
    out, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def load_month_ticks(ym: str, outdir: Path = TICKS_DIR) -> pl.DataFrame:
    d = outdir / f"ym={ym}"
    if not d.exists():
        return pl.DataFrame(schema={"trading_date": pl.Date, "symbol": pl.String,
                                    "ts_ns": pl.Int64, "px_ticks": pl.Int32,
                                    "size": pl.Int32, "row_seq": pl.Int64})
    # ts_event is ~monotonic in the source but has a handful of inversions per
    # half-year, so we sort explicitly: every downstream searchsorted depends on it.
    return pl.read_parquet(list(d.glob("*.parquet"))).sort(["ts_ns", "row_seq"])


def build_bars_from_ticks(ticks: pl.DataFrame, bar_minutes: int = 2) -> pl.DataFrame:
    """Deterministic OHLCV using exact source order for open/close."""
    if ticks.height == 0:
        return pl.DataFrame(schema=BAR_SCHEMA)
    bar_ns = bar_minutes * 60 * 1_000_000_000
    df = ticks.with_columns(((pl.col("ts_ns") // bar_ns) * bar_ns).alias("bar_ns"))
    out = (
        df.group_by(["trading_date", "symbol", "bar_ns"])
          .agg(
              pl.col("px_ticks").first().alias("open_t"),
              pl.col("px_ticks").max().alias("high_t"),
              pl.col("px_ticks").min().alias("low_t"),
              pl.col("px_ticks").last().alias("close_t"),
              pl.col("size").sum().alias("volume"),
              pl.len().alias("trades"),
              pl.col("ts_ns").min().alias("first_ts_ns"),
              pl.col("ts_ns").max().alias("last_ts_ns"),
          )
          .sort("bar_ns")
    )
    return out.with_columns(
        (pl.col("open_t") * TICK).alias("open"),
        (pl.col("high_t") * TICK).alias("high"),
        (pl.col("low_t") * TICK).alias("low"),
        (pl.col("close_t") * TICK).alias("close"),
        (pl.col("bar_ns") + bar_ns).alias("bar_end_ns"),
    ).drop(["open_t", "high_t", "low_t", "close_t"])


BAR_SCHEMA = {
    "trading_date": pl.Date, "symbol": pl.String, "bar_ns": pl.Int64,
    "volume": pl.Int64, "trades": pl.UInt32, "first_ts_ns": pl.Int64,
    "last_ts_ns": pl.Int64, "open": pl.Float64, "high": pl.Float64,
    "low": pl.Float64, "close": pl.Float64, "bar_end_ns": pl.Int64,
}
