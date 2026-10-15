"""Phase-7 causal MBP-1 + trades merger and per-second book-state cache.

WHY A PER-SECOND CACHE
    The raw MBP-1 corpus is 7.89 billion rows / 222 GB.  Re-scanning it for every
    model configuration is impossible, and downsampling the *events* would destroy
    the transition information the phase is about.  So every event-level quantity
    -- OFI, size increases/decreases at an unchanged best price, best-price steps,
    add/cancel counts -- is computed **event by event in the scan**, from the
    ordered stream, and only then aggregated into one row per second.  Nothing is
    approximated from a snapshot.

EVENT ORDERING (audited, see MBP1_SCHEMA_AUDIT.md)
    ORDER BY ts_event, sequence, file_row_number

    `sequence` is monotone in `ts_event` (0 decreases over a sampled RTH day) but
    is NOT unique: multi-message exchange packets share both fields -- e.g. one
    aggressive order sweeping two price levels emits two `T` rows with identical
    ts_event and sequence.  File row order is the exchange's within-packet order
    and is the only defensible final tie-break.  It is deterministic.

BOOK-STATE SEMANTICS
    Each row carries the top of book at that message.  A `T` row still shows the
    resting size being consumed; the removal appears on the `C`/`M` row that
    follows in the same packet.  OFI is therefore computed on book-state
    transitions between consecutive rows and captures trade-driven depletion via
    the following message, without double counting.

CAUSALITY
    Every aggregate in second `s` is derived only from events inside second `s`,
    plus the immediately preceding event for the lag.  No forward fill from a
    later second, no centred window, no nearest-neighbour join.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import polars as pl

from nqr import paths
from nqr.p7 import holdout7 as H7

P7_BOOK = paths.CACHE_DIR / "p7_book1s"
TICK = 0.25
NS = 1_000_000_000

BAND_START_ET = "09:00"          # 30 min of warm-up before the 09:30 session
BAND_END_ET = "12:00"            # 11:30 last signal + 15 min hold + head room

_ET_MIN = ("(EXTRACT(hour FROM ({ts} AT TIME ZONE 'America/New_York')) * 60 "
           "+ EXTRACT(minute FROM ({ts} AT TIME ZONE 'America/New_York')))")


def band_predicate(ts: str = "ts_event") -> str:
    h0, m0 = (int(x) for x in BAND_START_ET.split(":"))
    h1, m1 = (int(x) for x in BAND_END_ET.split(":"))
    e = _ET_MIN.format(ts=ts)
    return f"{e} >= {h0*60+m0} AND {e} < {h1*60+m1}"


# One row per (trading_date, symbol, second).  Every column is derived from the
# ordered event stream inside that second.
BOOK_SQL = """
COPY (
  WITH src AS (
    SELECT
      {td}                                        AS trading_date,
      symbol,
      CAST(epoch_ns(ts_event) / 1000000000 AS BIGINT) AS sec,
      sequence,
      file_row_number                             AS frn,
      action, side, price, size,
      bid_px_00 AS pb, ask_px_00 AS pa,
      CAST(bid_sz_00 AS BIGINT) AS qb, CAST(ask_sz_00 AS BIGINT) AS qa,
      CAST(bid_ct_00 AS BIGINT) AS cb, CAST(ask_ct_00 AS BIGINT) AS ca
    FROM read_parquet('{path}', file_row_number=true)
    WHERE ts_event >= TIMESTAMPTZ '{t0}' AND ts_event < TIMESTAMPTZ '{t1}'
      AND {guard} AND {band}
      AND symbol NOT LIKE '%-%'
      AND regexp_matches(symbol, '{outright}')
      AND bid_px_00 IS NOT NULL AND ask_px_00 IS NOT NULL
      AND bid_sz_00 > 0 AND ask_sz_00 > 0
      AND ask_px_00 > bid_px_00
  ),
  f AS (
    SELECT s.* FROM src s
    JOIN front_map_p7 m ON s.trading_date = m.trading_date AND s.symbol = m.front_symbol
  ),
  lagged AS (
    SELECT *,
      lag(pb) OVER w AS lpb, lag(qb) OVER w AS lqb,
      lag(pa) OVER w AS lpa, lag(qa) OVER w AS lqa
    FROM f
    WINDOW w AS (PARTITION BY trading_date, symbol ORDER BY sec, sequence, frn)
  ),
  ev AS (
    SELECT *,
      -- Cont-Kukanov-Stoikov top-of-book order-flow imbalance, per event.
      -- bid side:  price up -> +qb ; unchanged -> qb-lqb ; price down -> -lqb
      -- ask side:  price down -> -qa ; unchanged -> -(qa-lqa) ; price up -> +lqa
      (CASE WHEN lpb IS NULL THEN 0
            WHEN pb > lpb THEN qb WHEN pb = lpb THEN qb - lqb ELSE -lqb END)
      + (CASE WHEN lpa IS NULL THEN 0
              WHEN pa < lpa THEN -qa WHEN pa = lpa THEN -(qa - lqa) ELSE lqa END) AS ofi,
      CASE WHEN lpb IS NOT NULL AND pb = lpb AND qb > lqb THEN qb - lqb ELSE 0 END AS b_inc,
      CASE WHEN lpb IS NOT NULL AND pb = lpb AND qb < lqb THEN lqb - qb ELSE 0 END AS b_dec,
      CASE WHEN lpa IS NOT NULL AND pa = lpa AND qa > lqa THEN qa - lqa ELSE 0 END AS a_inc,
      CASE WHEN lpa IS NOT NULL AND pa = lpa AND qa < lqa THEN lqa - qa ELSE 0 END AS a_dec,
      CASE WHEN lpb IS NOT NULL AND pb > lpb THEN 1 ELSE 0 END AS b_up,
      CASE WHEN lpb IS NOT NULL AND pb < lpb THEN 1 ELSE 0 END AS b_dn,
      CASE WHEN lpa IS NOT NULL AND pa > lpa THEN 1 ELSE 0 END AS a_up,
      CASE WHEN lpa IS NOT NULL AND pa < lpa THEN 1 ELSE 0 END AS a_dn,
      CASE WHEN lpb IS NOT NULL AND (pb <> lpb OR qb <> lqb) THEN 1 ELSE 0 END AS b_upd,
      CASE WHEN lpa IS NOT NULL AND (pa <> lpa OR qa <> lqa) THEN 1 ELSE 0 END AS a_upd,
      (qb - qa) / CAST(qb + qa AS DOUBLE) AS imb,
      (pa * qb + pb * qa) / CAST(qb + qa AS DOUBLE) AS micro,
      (pa + pb) / 2.0 AS mid,
      pa - pb AS spread
    FROM lagged
  )
  SELECT
    trading_date, symbol, sec,
    count(*)                                             AS n_events,
    arg_max(pb, sec * 1000000000 + sequence)             AS bid_px,
    arg_max(pa, sec * 1000000000 + sequence)             AS ask_px,
    arg_max(qb, sec * 1000000000 + sequence)             AS bid_sz,
    arg_max(qa, sec * 1000000000 + sequence)             AS ask_sz,
    arg_max(cb, sec * 1000000000 + sequence)             AS bid_ct,
    arg_max(ca, sec * 1000000000 + sequence)             AS ask_ct,
    arg_max(imb, sec * 1000000000 + sequence)            AS imb_last,
    avg(imb)                                             AS imb_mean,
    sum(CASE WHEN imb > 0 THEN 1 ELSE 0 END)             AS n_imb_pos,
    sum(CASE WHEN imb < 0 THEN 1 ELSE 0 END)             AS n_imb_neg,
    arg_max(micro, sec * 1000000000 + sequence)          AS micro_last,
    avg(micro - mid)                                     AS micro_off_mean,
    arg_max(mid, sec * 1000000000 + sequence)            AS mid_last,
    avg(spread)                                          AS spread_mean,
    arg_max(spread, sec * 1000000000 + sequence)         AS spread_last,
    sum(ofi)                                             AS ofi,
    sum(b_inc) AS b_inc, sum(b_dec) AS b_dec,
    sum(a_inc) AS a_inc, sum(a_dec) AS a_dec,
    sum(CASE WHEN b_inc > 0 THEN 1 ELSE 0 END)           AS n_b_inc,
    sum(CASE WHEN b_dec > 0 THEN 1 ELSE 0 END)           AS n_b_dec,
    sum(CASE WHEN a_inc > 0 THEN 1 ELSE 0 END)           AS n_a_inc,
    sum(CASE WHEN a_dec > 0 THEN 1 ELSE 0 END)           AS n_a_dec,
    sum(b_up) AS n_b_up, sum(b_dn) AS n_b_dn,
    sum(a_up) AS n_a_up, sum(a_dn) AS n_a_dn,
    sum(b_upd) AS n_b_upd, sum(a_upd) AS n_a_upd,
    sum(CASE WHEN action='A' AND side='B' THEN 1 ELSE 0 END) AS n_add_b,
    sum(CASE WHEN action='A' AND side='A' THEN 1 ELSE 0 END) AS n_add_a,
    sum(CASE WHEN action='C' AND side='B' THEN 1 ELSE 0 END) AS n_can_b,
    sum(CASE WHEN action='C' AND side='A' THEN 1 ELSE 0 END) AS n_can_a,
    sum(CASE WHEN action='T' AND side='B' THEN size ELSE 0 END) AS trd_buy_vol,
    sum(CASE WHEN action='T' AND side='A' THEN size ELSE 0 END) AS trd_sell_vol,
    sum(CASE WHEN action='T' THEN 1 ELSE 0 END)          AS trd_n,
    arg_max(CASE WHEN action='T' THEN price END, CASE WHEN action='T'
            THEN sec * 1000000000 + sequence END)        AS trd_px_last,
    strftime(trading_date, '%Y-%m')                      AS ym
  FROM ev
  GROUP BY trading_date, symbol, sec
) TO '{outdir}' (FORMAT PARQUET, PARTITION_BY (ym), COMPRESSION ZSTD,
                 APPEND, FILENAME_PATTERN '{{uuid}}')
"""

BOOK_COLS = ["trading_date", "symbol", "sec", "n_events", "bid_px", "ask_px", "bid_sz",
             "ask_sz", "bid_ct", "ask_ct", "imb_last", "imb_mean", "n_imb_pos",
             "n_imb_neg", "micro_last", "micro_off_mean", "mid_last", "spread_mean",
             "spread_last", "ofi", "b_inc", "b_dec", "a_inc", "a_dec", "n_b_inc",
             "n_b_dec", "n_a_inc", "n_a_dec", "n_b_up", "n_b_dn", "n_a_up", "n_a_dn",
             "n_b_upd", "n_a_upd", "n_add_b", "n_add_a", "n_can_b", "n_can_a",
             "trd_buy_vol", "trd_sell_vol", "trd_n", "trd_px_last"]


def _month_bounds(y: int, m: int) -> tuple[str, str]:
    y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
    return f"{y:04d}-{m:02d}-01 00:00:00+0000", f"{y2:04d}-{m2:02d}-01 00:00:00+0000"


def months_of(split: str) -> list[tuple[int, int]]:
    s, e = H7.SPLITS[split]
    out, y, m = [], s.year, s.month
    while (y, m) <= (e.year, e.month):
        out.append((y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def months_for(split: str) -> list[str]:
    return [f"{y:04d}-{m:02d}" for y, m in months_of(split)]


def mbp1_file_for(year: int, half: int) -> Path:
    """The MBP-1 half-year file, guard-checked."""
    p = paths.find_dataset_dir("mbp1") / f"{year}_H{half}.parquet"
    H7.assert_path_allowed(p)
    return p


def build_book_cache(con, front: pl.DataFrame, split: str,
                     outdir: Path = P7_BOOK, outright: str = r"^NQ[FGHJKMNQUVXZ]\d{1,2}$",
                     verbose: bool = True) -> list[dict]:
    """Build the per-second book cache for one split.  Guard-checked per month."""
    s, e = H7.SPLITS[split]
    H7.assert_range_allowed(s, e, f"book cache {split}")
    guard = H7.sql_window_guard(s, e, "ts_event")
    outdir.mkdir(parents=True, exist_ok=True)
    con.register("fm_p7_pl", front.select(["trading_date", "front_symbol"]).to_pandas())
    con.execute("CREATE OR REPLACE TABLE front_map_p7 AS SELECT * FROM fm_p7_pl")
    recs = []
    import time
    for y, m in months_of(split):
        half = 1 if m <= 6 else 2
        src = mbp1_file_for(y, half)
        t0, t1 = _month_bounds(y, m)
        t = time.time()
        con.execute(BOOK_SQL.format(path=src, guard=guard, td=H7.sql_trading_date("ts_event"),
                                    band=band_predicate("ts_event"), outright=outright,
                                    outdir=outdir, t0=t0, t1=t1))
        recs.append({"ym": f"{y:04d}-{m:02d}", "src": src.name,
                     "seconds": round(time.time() - t, 1)})
        if verbose:
            print(f"  p7 book {y:04d}-{m:02d}  [{time.time()-t:.0f}s]", flush=True)
    return recs


def load_month(ym: str) -> pl.DataFrame:
    y, m = int(ym[:4]), int(ym[5:])
    H7.assert_date_allowed(dt.date(y, m, 1), f"book cache {ym}")
    d = P7_BOOK / f"ym={ym}"
    if not d.exists():
        return pl.DataFrame()
    return pl.read_parquet(list(d.glob("*.parquet")), columns=BOOK_COLS).sort(["sec"])


def months_available() -> list[str]:
    return sorted(p.name.split("=")[1] for p in P7_BOOK.glob("ym=*")) if P7_BOOK.exists() else []
