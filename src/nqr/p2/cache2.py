"""Phase-2 caches.  Nothing here touches any Phase-1 file or output.

Two caches are built, both restricted to the extended RTH band 08:00-16:15 ET
(the strategy only ever operates 09:30-16:00; the extra head room warms the
volatility and directional-change state causally, and the tail covers exits):

  data_cache/p2_ticks/      front-contract trade prints WITH the aggressor side
                            ts_ns, px_ticks, size, side_code, row_seq
  data_cache/p2_bbo1s/      one row per (trading_date, second) summarising the
                            MBP-1 top of book

`side_code`:  +1 buyer-initiated, -1 seller-initiated, 0 unknown/none.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import duckdb
import polars as pl

from nqr import paths
from nqr.holdout import sql_date_guard, sql_trading_date

P2_TICKS = paths.CACHE_DIR / "p2_ticks"
P2_BBO1S = paths.CACHE_DIR / "p2_bbo1s"
TICK = 0.25
NS = 1_000_000_000

# extended RTH band, in ET minutes-of-day
BAND_START_ET = "08:00"
BAND_END_ET = "16:15"

_ET_MIN = ("(EXTRACT(hour FROM ({ts} AT TIME ZONE 'America/New_York')) * 60 "
           "+ EXTRACT(minute FROM ({ts} AT TIME ZONE 'America/New_York')))")


def et_minute_sql(ts: str = "ts_event") -> str:
    return _ET_MIN.format(ts=ts)


def band_predicate(ts: str = "ts_event") -> str:
    h0, m0 = (int(x) for x in BAND_START_ET.split(":"))
    h1, m1 = (int(x) for x in BAND_END_ET.split(":"))
    return f"{et_minute_sql(ts)} >= {h0*60+m0} AND {et_minute_sql(ts)} < {h1*60+m1}"


TICKS_SQL = """
COPY (
  WITH src AS (
    SELECT
      {td}                                       AS trading_date,
      symbol,
      CAST(epoch_ns(ts_event) AS BIGINT)         AS ts_ns,
      CAST(round(price / {tick}) AS INTEGER)     AS px_ticks,
      CAST(size AS INTEGER)                      AS size,
      CASE side WHEN 'B' THEN 1 WHEN 'A' THEN -1 ELSE 0 END AS side_raw,
      CAST({fidx} AS BIGINT) * 1099511627776 + file_row_number AS row_seq
    FROM read_parquet('{path}', file_row_number=true)
    WHERE {guard} AND {band}
      AND symbol NOT LIKE '%-%'
      AND regexp_matches(symbol, '{outright}')
  )
  SELECT s.trading_date, s.symbol, s.ts_ns, s.px_ticks, s.size, s.side_raw, s.row_seq,
         strftime(s.trading_date, '%Y-%m') AS ym
  FROM src s
  JOIN front_map f ON s.trading_date = f.trading_date AND s.symbol = f.front_symbol
  ORDER BY s.ts_ns, s.row_seq
) TO '{outdir}' (FORMAT PARQUET, PARTITION_BY (ym), COMPRESSION ZSTD,
                 APPEND, FILENAME_PATTERN '{{uuid}}')
"""

BBO_SQL = """
COPY (
  WITH src AS (
    SELECT
      {td}                                        AS trading_date,
      symbol,
      CAST(epoch_ns(ts_event) / 1000000000 AS BIGINT) AS sec,
      CAST(round(bid_px_00 / {tick}) AS INTEGER)  AS bid_t,
      CAST(round(ask_px_00 / {tick}) AS INTEGER)  AS ask_t,
      CAST(bid_sz_00 AS INTEGER)                  AS bid_sz,
      CAST(ask_sz_00 AS INTEGER)                  AS ask_sz,
      CAST({fidx} AS BIGINT) * 1099511627776 + file_row_number AS row_seq
    FROM read_parquet('{path}', file_row_number=true)
    WHERE ts_event >= TIMESTAMP '{t0}' AND ts_event < TIMESTAMP '{t1}'
      AND {guard} AND {band}
      AND symbol NOT LIKE '%-%'
      AND regexp_matches(symbol, '{outright}')
      AND bid_px_00 IS NOT NULL AND ask_px_00 IS NOT NULL
      AND ask_px_00 > bid_px_00
  ),
  j AS (
    SELECT s.* FROM src s
    JOIN front_map f ON s.trading_date = f.trading_date AND s.symbol = f.front_symbol
  )
  SELECT
    trading_date, any_value(symbol) AS symbol, sec,
    arg_min(bid_t, row_seq)  AS bid_first,  arg_max(bid_t, row_seq)  AS bid_last,
    arg_min(ask_t, row_seq)  AS ask_first,  arg_max(ask_t, row_seq)  AS ask_last,
    min(bid_t) AS bid_min, max(bid_t) AS bid_max,
    min(ask_t) AS ask_min, max(ask_t) AS ask_max,
    arg_max(bid_sz, row_seq) AS bid_sz_last, arg_max(ask_sz, row_seq) AS ask_sz_last,
    CAST(avg(bid_sz) AS INTEGER) AS bid_sz_mean,
    CAST(avg(ask_sz) AS INTEGER) AS ask_sz_mean,
    count(*) AS n_events,
    avg(ask_t - bid_t) AS spread_ticks_mean,
    strftime(trading_date, '%Y-%m') AS ym
  FROM j
  GROUP BY trading_date, sec
) TO '{outdir}' (FORMAT PARQUET, PARTITION_BY (ym), COMPRESSION ZSTD,
                 APPEND, FILENAME_PATTERN '{{uuid}}')
"""


def _month_ranges(year: int, half: int) -> list[tuple[str, str]]:
    """Non-overlapping UTC month windows covering one half-year file.

    Chunking bounds the number of live GROUP BY keys (which is what blew memory
    when the whole half-year was aggregated at once) and lets parquet row-group
    statistics prune most of the file on every chunk.
    """
    months = range(1, 7) if half == 1 else range(7, 13)
    out = []
    for m in months:
        y2, m2 = (year + 1, 1) if m == 12 else (year, m + 1)
        out.append((f"{year:04d}-{m:02d}-01 00:00:00", f"{y2:04d}-{m2:02d}-01 00:00:00"))
    return out


def _build(con, half_files: dict[str, Path], outright_regex: str, outdir: Path,
           sql: str, label: str) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    for fidx, (key, path) in enumerate(sorted(half_files.items())):
        con.execute(sql.format(path=path, guard=sql_date_guard("ts_event"),
                               td=sql_trading_date("ts_event"), band=band_predicate("ts_event"),
                               tick=TICK, outright=outright_regex, outdir=outdir, fidx=fidx))
        print(f"  {label} {key}", flush=True)


def build_tick_cache(con, half_files, outright_regex, outdir: Path = P2_TICKS):
    _build(con, half_files, outright_regex, outdir, TICKS_SQL, "p2 ticks")


def build_bbo_cache(con, half_files, outright_regex, outdir: Path = P2_BBO1S):
    """MBP-1 -> 1-second BBO summary, one calendar month at a time."""
    outdir.mkdir(parents=True, exist_ok=True)
    for fidx, (key, path) in enumerate(sorted(half_files.items())):
        year, half = int(key[:4]), int(key[-1])
        for t0, t1 in _month_ranges(year, half):
            con.execute(BBO_SQL.format(
                path=path, guard=sql_date_guard("ts_event"),
                td=sql_trading_date("ts_event"), band=band_predicate("ts_event"),
                tick=TICK, outright=outright_regex, outdir=outdir, fidx=fidx,
                t0=t0, t1=t1))
            print(f"  p2 bbo1s {key} {t0[:7]}", flush=True)


def load_month(ym: str, outdir: Path, sort_cols: list[str]) -> pl.DataFrame:
    d = outdir / f"ym={ym}"
    if not d.exists():
        return pl.DataFrame()
    return pl.read_parquet(list(d.glob("*.parquet"))).sort(sort_cols)


def load_month_ticks(ym: str) -> pl.DataFrame:
    return load_month(ym, P2_TICKS, ["ts_ns", "row_seq"])


def load_month_bbo(ym: str) -> pl.DataFrame:
    return load_month(ym, P2_BBO1S, ["sec"])


def months_available(outdir: Path) -> list[str]:
    return sorted(p.name.split("=")[1] for p in outdir.glob("ym=*"))
