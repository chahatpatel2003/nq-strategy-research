"""STEP 1 — verify the native Databento `side` field against a causal quote rule.

Uses DEVELOPMENT months only (2021-2023).  For each sampled day the BBO is
rebuilt from MBP-1 at full event resolution and, for every trade, the quote
used is the last one STRICTLY BEFORE the trade's ts_event.
"""
import argparse, json, sys, datetime as dt
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import polars as pl
import yaml

from nqr import paths
from nqr.data.audit import connect
from nqr.holdout import sql_date_guard, sql_trading_date, assert_date_allowed
from nqr.sessions.calendar import day_bounds_utc
from nqr.p2 import cache2
from nqr.p2.signing import verify_native_side

ap = argparse.ArgumentParser()
ap.add_argument("--days", type=int, default=12)
ap.add_argument("--seed", type=int, default=20260819)
a = ap.parse_args()

cfg = yaml.safe_load((ROOT / "config" / "fast_slow_baseline.yaml").read_text())
front = pl.read_parquet(paths.RESULTS_DIR / "front_map.parquet")
dev = front.filter((pl.col("trading_date") >= dt.date(2021, 1, 1)) &
                   (pl.col("trading_date") <= dt.date(2023, 12, 31)) &
                   (~pl.col("is_roll_day")))
rng = np.random.default_rng(a.seed)
# stratified: equal numbers from each development year
picks = []
for y in (2021, 2022, 2023):
    sub = dev.filter(pl.col("trading_date").dt.year() == y)["trading_date"].to_list()
    picks += [sub[i] for i in rng.choice(len(sub), size=a.days // 3, replace=False)]
picks = sorted(picks)
for d in picks:
    assert_date_allowed(d, "verification day")

con = connect(memory_limit="5GB", threads=6)
con.execute(f"SET temp_directory='{ROOT/'data_cache'/'duckdb_tmp'}';")
mbp = paths.allowed_half_files("mbp1")
rows = []
for d in picks:
    half = f"{d.year}_H{1 if d.month <= 6 else 2}"
    path = mbp[half]
    sym = front.filter(pl.col("trading_date") == d)["front_symbol"][0]
    # An explicit ts_event RANGE lets parquet row-group statistics prune the file.
    # Filtering only on the computed trading-date expression forces a full scan of
    # a 20 GB file, which is why this predicate is here as well as the guard.
    b0, b1 = day_bounds_utc(d)
    q = con.execute(f"""
        SELECT CAST(epoch_ns(ts_event) AS BIGINT)              AS ts_ns,
               CAST(round(bid_px_00/0.25) AS BIGINT)           AS bid_t,
               CAST(round(ask_px_00/0.25) AS BIGINT)           AS ask_t
        FROM read_parquet('{path}')
        WHERE ts_event >= TIMESTAMPTZ '{b0.strftime('%Y-%m-%d %H:%M:%S%z')}'
          AND ts_event <  TIMESTAMPTZ '{b1.strftime('%Y-%m-%d %H:%M:%S%z')}'
          AND {sql_date_guard('ts_event')}
          AND {sql_trading_date('ts_event')} = DATE '{d}'
          AND symbol = '{sym}'
          AND bid_px_00 IS NOT NULL AND ask_px_00 IS NOT NULL
          AND ask_px_00 > bid_px_00
        ORDER BY ts_event
    """).pl()
    ym = f"{d.year:04d}-{d.month:02d}"
    tk = cache2.load_month_ticks(ym).filter(pl.col("trading_date") == d)
    r = verify_native_side(tk, q)
    r["trading_date"] = str(d)
    r["symbol"] = sym
    rows.append(r)
    print(f"  {d} {sym}: n={r['n']:,} agree={r['agreement_rate']:.6f} "
          f"inside={r['inside_spread_frac']:.4f}", flush=True)

df = pl.DataFrame(rows)
tot_un = int(df["n_unambiguous"].sum()); tot_ag = int(df["n_agree"].sum())
summary = {
    "days_sampled": len(picks), "days": [str(x) for x in picks],
    "total_trades": int(df["n"].sum()),
    "total_unambiguous": tot_un, "total_agree": tot_ag,
    "total_disagree": int(df["n_disagree"].sum()),
    "overall_agreement_rate": tot_ag / max(tot_un, 1),
    "mean_inside_spread_frac": float(df["inside_spread_frac"].mean()),
    "native_unknown_frac": float(df["native_unknown_frac"].mean()),
    "native_buy_frac": float(df["native_buy_frac"].mean()),
    "per_day": rows,
}
out = paths.RESULTS_DIR / "p2_signing_verification.json"
out.write_text(json.dumps(summary, indent=2, default=str))
print(json.dumps({k: v for k, v in summary.items() if k not in ("per_day", "days")}, indent=2))
