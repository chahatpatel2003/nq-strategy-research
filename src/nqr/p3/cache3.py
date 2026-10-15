"""Phase-3 tick access.

2021-2024 reuses the Phase-2 signed tick cache verbatim (read-only) - it is
already exactly what Phase 3 needs: front-contract outright trade prints,
08:00-16:15 ET, sorted by (ts_event, source row).  Phase 3 reads only
ts/price/size from it and never touches the aggressor column: this phase is
deliberately TRADES-ONLY.

2025-H2 is built fresh into ``data_cache/p3_ticks`` and only when the Phase-3
validation unlock is active.  2025-H1 and 2026 have no code path at all.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import polars as pl

from nqr import paths
from nqr.p2.cache2 import P2_TICKS, band_predicate, et_minute_sql
from nqr.p3 import holdout3 as H3

P3_TICKS = paths.CACHE_DIR / "p3_ticks"
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
      CAST({fidx} AS BIGINT) * 1099511627776 + file_row_number AS row_seq
    FROM read_parquet('{path}', file_row_number=true)
    WHERE ts_event >= TIMESTAMPTZ '{t0}' AND ts_event < TIMESTAMPTZ '{t1}'
      AND {guard} AND {band}
      AND symbol NOT LIKE '%-%'
      AND regexp_matches(symbol, '{outright}')
  )
  SELECT s.trading_date, s.symbol, s.ts_ns, s.px_ticks, s.size, s.row_seq,
         strftime(s.trading_date, '%Y-%m') AS ym
  FROM src s
  JOIN front_map_p3 f
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


def _month_bounds(y: int, m: int) -> tuple[str, str]:
    y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
    return f"{y:04d}-{m:02d}-01 00:00:00+0000", f"{y2:04d}-{m2:02d}-01 00:00:00+0000"


def build_validation_cache(con, trades_path: Path, outright_regex: str,
                           front_map: pl.DataFrame, outdir: Path = P3_TICKS) -> None:
    """2025-H2 only.  Refuses to run unless the validation unlock is active."""
    if not H3.validation_unlocked():
        raise H3.Phase3Violation("Phase-3 validation cache requires the explicit unlock")
    H3.assert_path_allowed(trades_path)
    outdir.mkdir(parents=True, exist_ok=True)
    con.register("front_map_p3_pl", front_map.select(["trading_date", "front_symbol"]).to_pandas())
    con.execute("CREATE OR REPLACE TABLE front_map_p3 AS SELECT * FROM front_map_p3_pl")
    guard = H3.sql_window_guard(H3.VAL_START, H3.VAL_END, "ts_event")
    for m in range(7, 13):
        t0, t1 = _month_bounds(2025, m)
        con.execute(TICKS_SQL.format(
            path=trades_path, guard=guard, td=H3.sql_trading_date("ts_event"),
            band=band_predicate("ts_event"), tick=TICK, outright=outright_regex,
            outdir=outdir, fidx=99, t0=t0, t1=t1))
        print(f"  p3 ticks 2025-{m:02d}", flush=True)


def validation_daily_volume(con, trades_path: Path, outright_regex: str) -> pl.DataFrame:
    """Per (trading_date, symbol) volume for 2025-H2, for the front-contract rule."""
    if not H3.validation_unlocked():
        raise H3.Phase3Violation("requires the Phase-3 validation unlock")
    H3.assert_path_allowed(trades_path)
    guard = H3.sql_window_guard(H3.VAL_START, H3.VAL_END, "ts_event")
    frames = []
    for m in range(7, 13):
        t0, t1 = _month_bounds(2025, m)
        frames.append(con.execute(VOLUME_SQL.format(
            path=trades_path, guard=guard, td=H3.sql_trading_date("ts_event"),
            outright=outright_regex, t0=t0, t1=t1)).pl())
    return pl.concat(frames).with_columns(pl.col("trading_date").cast(pl.Date))


# ------------------------------------------------------------- loading ----
def months_for(split: str) -> list[str]:
    s, e = H3.SPLITS[split]
    out, y, m = [], s.year, s.month
    while (y, m) <= (e.year, e.month):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def load_month(ym: str) -> pl.DataFrame:
    """Read a month from whichever cache holds it.  Never reads 2025-01..06."""
    y, m = int(ym[:4]), int(ym[5:])
    d = dt.date(y, m, 1)
    if H3.period_of(d) == "SEALED_H1":
        raise H3.Phase3Violation(f"{ym} is inside the sealed 2025-H1 window")
    if H3.period_of(d) == "SEALED_2026":
        raise H3.Phase3Violation(f"{ym} is inside the 2026 final holdout")
    src = P3_TICKS if d >= H3.VAL_START else P2_TICKS
    p = src / f"ym={ym}"
    if not p.exists():
        return pl.DataFrame()
    cols = ["trading_date", "symbol", "ts_ns", "px_ticks", "size", "row_seq"]
    return pl.read_parquet(list(p.glob("*.parquet")), columns=cols).sort(["ts_ns", "row_seq"])
