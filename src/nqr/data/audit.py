"""Phase-0 data audit: schema, quality, contract inventory.

Only reads half-year files that pass the holdout guard.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

import duckdb
import numpy as np
import pyarrow.parquet as pq

from nqr import paths
from nqr.holdout import sql_date_guard, sql_trading_date, assert_paths_allowed

OUTRIGHT_RE = re.compile(r"^NQ[FGHJKMNQUVXZ]\d{1,2}$")
MONTH_CODE = {"F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6,
              "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12}


def connect(memory_limit: str = "6GB", threads: int = 8) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(f"SET memory_limit='{memory_limit}'; SET threads={threads};")
    con.execute("SET preserve_insertion_order=false;")
    return con


def schema_report(path: Path) -> dict:
    pf = pq.ParquetFile(path)
    md = pf.metadata
    return {
        "file": path.name,
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "num_rows": md.num_rows,
        "num_row_groups": md.num_row_groups,
        "created_by": md.created_by,
        "columns": [{"name": f.name, "type": str(f.type)} for f in pf.schema_arrow],
    }


def order_and_dup_report(path: Path, batch_size: int = 4_000_000) -> dict:
    """Streamed check of timestamp ordering + duplicate-key behaviour."""
    pf = pq.ParquetFile(path)
    cols = ["ts_recv", "ts_event", "sequence", "instrument_id"]
    prev_recv = prev_evt = None
    n = 0
    recv_desc = evt_desc = 0
    evt_gt_recv = 0
    dup_seq = 0
    prev_seq = prev_iid = None
    for b in pf.iter_batches(batch_size=batch_size, columns=cols):
        recv = b.column("ts_recv").to_numpy().astype("datetime64[ns]").view("int64")
        evt = b.column("ts_event").to_numpy().astype("datetime64[ns]").view("int64")
        seq = b.column("sequence").to_numpy()
        iid = b.column("instrument_id").to_numpy()
        n += len(recv)
        if prev_recv is not None:
            recv = np.concatenate(([prev_recv], recv))
            evt = np.concatenate(([prev_evt], evt))
            seq = np.concatenate(([prev_seq], seq))
            iid = np.concatenate(([prev_iid], iid))
        recv_desc += int((np.diff(recv) < 0).sum())
        evt_desc += int((np.diff(evt) < 0).sum())
        evt_gt_recv += int((evt > recv).sum())
        dup_seq += int(((np.diff(seq) == 0) & (np.diff(iid) == 0) & (np.diff(evt) == 0)).sum())
        prev_recv, prev_evt, prev_seq, prev_iid = recv[-1], evt[-1], seq[-1], iid[-1]
    return {
        "file": path.name,
        "rows": n,
        "ts_recv_out_of_order": recv_desc,
        "ts_event_out_of_order": evt_desc,
        "ts_event_after_ts_recv": evt_gt_recv,
        "same_evt_seq_instrument_adjacent": dup_seq,
    }


def quality_report(con, path: Path) -> dict:
    guard = sql_date_guard("ts_event")
    q = f"""
    SELECT
      count(*)                                                        AS rows_scanned,
      sum(CASE WHEN symbol LIKE '%-%' THEN 1 ELSE 0 END)              AS spread_rows,
      sum(CASE WHEN symbol NOT LIKE '%-%' THEN size ELSE 0 END)       AS outright_volume,
      sum(CASE WHEN (price*4) != round(price*4) THEN 1 ELSE 0 END)    AS off_tick_rows,
      sum(CASE WHEN price IS NULL OR size IS NULL THEN 1 ELSE 0 END)  AS null_rows,
      sum(CASE WHEN size <= 0 THEN 1 ELSE 0 END)                      AS nonpositive_size,
      count(DISTINCT action)                                          AS n_actions,
      count(DISTINCT rtype)                                           AS n_rtypes,
      count(DISTINCT publisher_id)                                    AS n_publishers,
      count(DISTINCT flags)                                           AS n_flag_values,
      min(flags) AS flag_min, max(flags) AS flag_max,
      min(ts_event) AS ts_min, max(ts_event) AS ts_max,
      avg(epoch_ns(ts_recv - ts_event))/1e6                           AS mean_latency_ms,
      quantile_cont(epoch_ns(ts_recv - ts_event)/1e6, 0.5)            AS p50_latency_ms,
      quantile_cont(epoch_ns(ts_recv - ts_event)/1e6, 0.99)           AS p99_latency_ms,
      max(epoch_ns(ts_recv - ts_event))/1e6                           AS max_latency_ms
    FROM read_parquet('{path}')
    WHERE {guard}
    """
    d = con.execute(q).df().to_dict("records")[0]
    d["file"] = path.name
    sides = con.execute(
        f"SELECT side, count(*) n FROM read_parquet('{path}') WHERE {guard} GROUP BY 1 ORDER BY n DESC"
    ).df()
    d["side_counts"] = {r.side: int(r.n) for r in sides.itertuples()}
    return d


def daily_symbol_volume(con, paths_: list[Path]):
    guard = sql_date_guard("ts_event")
    td = sql_trading_date("ts_event")
    files = "[" + ",".join(f"'{p}'" for p in paths_) + "]"
    q = f"""
    SELECT {td} AS trading_date,
           symbol,
           instrument_id,
           count(*)   AS n_trades,
           sum(size)  AS volume,
           min(price) AS px_min,
           max(price) AS px_max,
           min(ts_event) AS first_ts,
           max(ts_event) AS last_ts
    FROM read_parquet({files})
    WHERE {guard} AND symbol NOT LIKE '%-%'
    GROUP BY 1,2,3
    ORDER BY 1,2
    """
    return con.execute(q).df()


def run_audit(out_dir: Path | None = None) -> dict:
    out_dir = out_dir or paths.RESULTS_DIR
    files = paths.allowed_half_files("trades")
    assert_paths_allowed(files.values())
    con = connect()
    rep = {"trades_dir": str(paths.find_dataset_dir("trades")),
           "mbp1_dir": str(paths.find_dataset_dir("mbp1")),
           "all_trade_halves": {k: str(v) for k, v in paths.half_files("trades").items()},
           "all_mbp1_halves": {k: str(v) for k, v in paths.half_files("mbp1").items()},
           "audited_halves": list(files),
           "schemas": [], "quality": [], "ordering": []}
    for k, p in files.items():
        rep["schemas"].append(schema_report(p))
        rep["quality"].append(quality_report(con, p))
        rep["ordering"].append(order_and_dup_report(p))
        print(f"  audited {k}", flush=True)
    dsv = daily_symbol_volume(con, list(files.values()))
    dsv.to_parquet(out_dir / "contract_daily_volume.parquet", index=False)
    rep["daily_symbol_volume_rows"] = len(dsv)
    (out_dir / "data_audit.json").write_text(json.dumps(rep, indent=2, default=str))
    return rep


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    run_audit()
