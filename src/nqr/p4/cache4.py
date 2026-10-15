"""Phase-4 tick access and previous-day levels.

2021-2024 reuses the Phase-2 signed tick cache verbatim (read-only).  It is
already exactly what Phase 4 needs: front-contract outright trade prints,
08:00-16:15 ET, sorted by (ts_event, source row), **with the native Databento
aggressor side**.  Phase 4 reads that side field directly; MBP-1 is never
opened (see FEATURE_REGISTRY.md, family 6).

2025-H2 and 2026-Q1 are built fresh into ``data_cache/p4_ticks`` because the
Phase-3 cache dropped the side column.  2025-H1 and 2026-04-01+ have no code
path at all: ``holdout4`` refuses both with no unlock.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import polars as pl

from nqr import paths
from nqr.p2.cache2 import P2_TICKS, band_predicate
from nqr.p4 import holdout4 as H4

P4_TICKS = paths.CACHE_DIR / "p4_ticks"
P4_LEVELS = paths.CACHE_DIR / "p4_levels"
TICK = 0.25

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
    WHERE ts_event >= TIMESTAMPTZ '{t0}' AND ts_event < TIMESTAMPTZ '{t1}'
      AND {guard} AND {band}
      AND symbol NOT LIKE '%-%'
      AND regexp_matches(symbol, '{outright}')
  )
  SELECT s.trading_date, s.symbol, s.ts_ns, s.px_ticks, s.size, s.side_raw, s.row_seq,
         strftime(s.trading_date, '%Y-%m') AS ym
  FROM src s
  JOIN front_map_p4 f
    ON s.trading_date = f.trading_date AND s.symbol = f.front_symbol
  ORDER BY s.ts_ns, s.row_seq
) TO '{outdir}' (FORMAT PARQUET, PARTITION_BY (ym), COMPRESSION ZSTD,
                 APPEND, FILENAME_PATTERN '{{uuid}}')
"""

VOLUME_SQL = """
SELECT {td} AS trading_date, symbol,
       count(*) AS n_trades, sum(size) AS volume
FROM read_parquet('{path}')
WHERE ts_event >= TIMESTAMPTZ '{t0}' AND ts_event < TIMESTAMPTZ '{t1}'
  AND {guard}
  AND symbol NOT LIKE '%-%'
  AND regexp_matches(symbol, '{outright}')
GROUP BY 1, 2
"""

# Full Globex-day extremes of the front contract -> PDH / PDL.  No band filter:
# the previous day's high/low is a whole-day level, matching the frozen Phase-1
# definition (max of 2-minute bar highs over the trading day).
EXTREMES_SQL = """
WITH src AS (
  SELECT {td} AS trading_date, symbol, price
  FROM read_parquet('{path}')
  WHERE ts_event >= TIMESTAMPTZ '{t0}' AND ts_event < TIMESTAMPTZ '{t1}'
    AND {guard}
    AND symbol NOT LIKE '%-%'
    AND regexp_matches(symbol, '{outright}')
)
SELECT s.trading_date, s.symbol, max(s.price) AS hi, min(s.price) AS lo, count(*) AS n
FROM src s
JOIN front_map_p4 f
  ON s.trading_date = f.trading_date AND s.symbol = f.front_symbol
GROUP BY 1, 2
"""


def _month_bounds(y: int, m: int) -> tuple[str, str]:
    y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
    return f"{y:04d}-{m:02d}-01 00:00:00+0000", f"{y2:04d}-{m2:02d}-01 00:00:00+0000"


def _months_of(split: str) -> list[tuple[int, int]]:
    s, e = H4.SPLITS[split]
    out, y, m = [], s.year, s.month
    while (y, m) <= (e.year, e.month):
        out.append((y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def months_for(split: str) -> list[str]:
    return [f"{y:04d}-{m:02d}" for y, m in _months_of(split)]


def _register_front(con, front: pl.DataFrame) -> None:
    con.register("front_map_p4_pl", front.select(["trading_date", "front_symbol"]).to_pandas())
    con.execute("CREATE OR REPLACE TABLE front_map_p4 AS SELECT * FROM front_map_p4_pl")


def daily_volume(con, trades_path: Path, outright_regex: str, split: str) -> pl.DataFrame:
    """Per (trading_date, symbol) volume, for the front-contract rule."""
    H4.assert_path_allowed(trades_path)
    s, e = H4.SPLITS[split]
    guard = H4.sql_window_guard(s, e, "ts_event")
    frames = []
    for y, m in _months_of(split):
        t0, t1 = _month_bounds(y, m)
        frames.append(con.execute(VOLUME_SQL.format(
            path=trades_path, guard=guard, td=H4.sql_trading_date("ts_event"),
            outright=outright_regex, t0=t0, t1=t1)).pl())
    return pl.concat(frames).with_columns(pl.col("trading_date").cast(pl.Date))


def build_tick_cache(con, trades_path: Path, outright_regex: str, front: pl.DataFrame,
                     split: str, outdir: Path = P4_TICKS) -> None:
    """Build the signed tick cache for one split.  Guard-checked twice over."""
    H4.assert_path_allowed(trades_path)
    s, e = H4.SPLITS[split]
    H4.assert_range_allowed(s, e, f"tick cache {split}")
    guard = H4.sql_window_guard(s, e, "ts_event")
    outdir.mkdir(parents=True, exist_ok=True)
    _register_front(con, front)
    for y, m in _months_of(split):
        t0, t1 = _month_bounds(y, m)
        con.execute(TICKS_SQL.format(
            path=trades_path, guard=guard, td=H4.sql_trading_date("ts_event"),
            band=band_predicate("ts_event"), tick=TICK, outright=outright_regex,
            outdir=outdir, fidx=97, t0=t0, t1=t1))
        print(f"  p4 ticks {y:04d}-{m:02d}", flush=True)


def build_day_extremes(con, trades_path: Path, outright_regex: str, front: pl.DataFrame,
                       split: str) -> pl.DataFrame:
    """Full-Globex-day high/low of the front contract, for PDH / PDL."""
    H4.assert_path_allowed(trades_path)
    s, e = H4.SPLITS[split]
    guard = H4.sql_window_guard(s, e, "ts_event")
    _register_front(con, front)
    frames = []
    for y, m in _months_of(split):
        t0, t1 = _month_bounds(y, m)
        frames.append(con.execute(EXTREMES_SQL.format(
            path=trades_path, guard=guard, td=H4.sql_trading_date("ts_event"),
            outright=outright_regex, t0=t0, t1=t1)).pl())
        print(f"  p4 extremes {y:04d}-{m:02d}", flush=True)
    return (pl.concat(frames).with_columns(pl.col("trading_date").cast(pl.Date))
            .sort("trading_date"))


# ------------------------------------------------------------- loading ----
def _src_for(ym: str) -> Path:
    y, m = int(ym[:4]), int(ym[5:])
    d = dt.date(y, m, 1)
    p = H4.period_of(d)
    if p in ("SEALED_2025H1", "SEALED_FINAL", "PRE"):
        raise H4.Phase4Violation(f"{ym} is in {p}: Phase 4 must never read it")
    if p == "FRESH_VAL" and not H4.validation_unlocked():
        raise H4.Phase4Violation(f"{ym} is fresh validation and the unlock is not active")
    return P2_TICKS if d < H4.SEALED_H1_START else P4_TICKS


TICK_COLS = ["trading_date", "symbol", "ts_ns", "px_ticks", "size", "side_raw", "row_seq"]


def load_month(ym: str) -> pl.DataFrame:
    """Read one month of signed front-contract ticks from whichever cache holds it."""
    d = _src_for(ym) / f"ym={ym}"
    if not d.exists():
        return pl.DataFrame()
    return (pl.read_parquet(list(d.glob("*.parquet")), columns=TICK_COLS)
            .sort(["ts_ns", "row_seq"]))


# --------------------------------------------------------- PDH / PDL ----
def levels_path(split: str) -> Path:
    return P4_LEVELS / f"day_extremes_{split}.parquet"


def day_extremes_from_phase1_bars() -> pl.DataFrame:
    """2021-2024 PDH/PDL from the frozen Phase-1 2-minute bars (read-only).

    max(bar high) over a trading day == max(trade price) over that day, so this
    is identical to the raw-trade aggregate used for the later splits.
    """
    bars = pl.read_parquet(paths.CACHE_DIR / "bars" / "bars_2m.parquet")
    return (bars.group_by(["trading_date", "symbol"])
                .agg(pl.col("high").max().alias("hi"), pl.col("low").min().alias("lo"),
                     pl.col("trades").sum().alias("n"))
                .sort("trading_date"))


def prev_day_levels(extremes: pl.DataFrame) -> dict[dt.date, tuple[float, float]]:
    """trading_date -> (PDH, PDL) taken from the PREVIOUS trading date present."""
    e = extremes.sort("trading_date")
    dates = e["trading_date"].to_list()
    hi = e["hi"].to_list()
    lo = e["lo"].to_list()
    return {dates[i]: (float(hi[i - 1]), float(lo[i - 1])) for i in range(1, len(dates))}
