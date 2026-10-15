"""Phase-3 metrics: reuses the Phase-1 statistics and adds event-time frequency."""
from __future__ import annotations

import numpy as np
import polars as pl

from nqr.metrics.stats import binom_p_value, compute, max_drawdown, streaks, wilson_ci

NS = 1_000_000_000
ET = "America/New_York"
TAGS = ["r0p75", "r1p0", "r1p25", "r1p5", "r2p0"]
TAG_LABEL = {"r0p75": "0.75R", "r1p0": "1R", "r1p25": "1.25R",
             "r1p5": "1.5R", "r2p0": "2R"}


def enrich(df: pl.DataFrame) -> pl.DataFrame:
    if df.height == 0:
        return df
    out = df.with_columns(
        pl.from_epoch(pl.col("signal_ns"), time_unit="ns").dt.replace_time_zone("UTC")
          .alias("signal_ts"),
        pl.when(pl.col("entry_ns").is_not_null())
          .then(pl.from_epoch(pl.col("entry_ns").fill_null(0), time_unit="ns")
                .dt.replace_time_zone("UTC")).alias("entry_ts"))
    clock = pl.coalesce([pl.col("entry_ts"), pl.col("signal_ts")])
    et = clock.dt.convert_time_zone(ET)
    mod = et.dt.hour().cast(pl.Int32) * 60 + et.dt.minute().cast(pl.Int32)
    out = out.with_columns(
        et.dt.strftime("%Y-%m-%d %H:%M:%S").alias("clock_et"),
        mod.alias("et_minute"), et.dt.hour().cast(pl.Int32).alias("et_hour"),
        pl.col("trading_date").dt.year().alias("year"),
        pl.col("trading_date").dt.strftime("%Y-%m").alias("month"),
        ((mod >= 570) & (mod < 690)).alias("w_0930_1130"),
        ((mod >= 570) & (mod < 630)).alias("w_0930_1030"),
        ((mod >= 630) & (mod < 690)).alias("w_1030_1130"),
        ((mod >= 570) & (mod < 720)).alias("w_0930_1200"),
        ((mod >= 570) & (mod < 960)).alias("w_0930_1600"),
        (pl.col("theta") / pl.col("vu")).alias("theta_over_vu"),
        (pl.col("dc_magnitude") / pl.col("theta")).alias("dc_over_theta"),
        (pl.col("event_ns") / 1e9).alias("event_s"),
    )
    out = out.with_columns(
        _bucket("theta", [3.0, 5.0, 8.0]).alias("theta_bucket"),
        _bucket("vu", [6.0, 10.0, 16.0]).alias("vol_bucket"),
        _bucket("dc_over_theta", [1.05, 1.2, 1.5]).alias("event_size_bucket"),
        _bucket("prev_overshoot_ratio", [0.5, 1.0, 2.0]).alias("overshoot_bucket"),
    )
    return out


def _bucket(col: str, edges: list[float]) -> pl.Expr:
    e = pl.col(col)
    expr = pl.when(e < edges[0]).then(pl.lit(f"<{edges[0]}"))
    for a, b in zip(edges, edges[1:]):
        expr = expr.when(e < b).then(pl.lit(f"{a}-{b}"))
    return expr.when(e >= edges[-1]).then(pl.lit(f">={edges[-1]}")).otherwise(pl.lit("na"))


def frequency_stats(acc: pl.DataFrame, all_days: int) -> dict:
    if acc.height == 0 or all_days == 0:
        return {}
    per = (acc.group_by("trading_date").len().rename({"len": "n"}).sort("trading_date"))
    c = per["n"].to_numpy()
    zero = all_days - per.height
    counts = np.concatenate([c, np.zeros(zero, dtype=c.dtype)])
    gaps = []
    for _, g in acc.sort(["trading_date", "entry_ns"]).group_by("trading_date"):
        e = g["entry_ns"].drop_nulls().to_numpy()
        if e.size > 1:
            gaps.append(np.diff(e) / 1e9 / 60.0)
    gaps = np.concatenate(gaps) if gaps else np.array([np.nan])
    h1 = acc.filter(pl.col("w_0930_1030")).height
    h2 = acc.filter(pl.col("w_1030_1130")).height
    return {
        "trading_days_in_window": all_days,
        "trades_per_day_mean": float(acc.height / all_days),
        "trades_per_day_median": float(np.median(counts)),
        "pct_days_0_trades": float((counts == 0).mean()),
        "pct_days_1_trade": float((counts == 1).mean()),
        "pct_days_2_trades": float((counts == 2).mean()),
        "pct_days_3_4_trades": float(((counts >= 3) & (counts <= 4)).mean()),
        "pct_days_5plus_trades": float((counts >= 5).mean()),
        "trades_0930_1030": h1, "trades_1030_1130": h2,
        "trades_per_day_0930_1030": h1 / all_days,
        "trades_per_day_1030_1130": h2 / all_days,
        "median_minutes_between_trades": float(np.nanmedian(gaps)),
        "mean_minutes_between_trades": float(np.nanmean(gaps)),
    }


def daily_stats(acc: pl.DataFrame, tag: str, friction: float, all_days: int) -> dict:
    if acc.height == 0:
        return {}
    d = (acc.with_columns(((pl.col(f"{tag}_points") - friction) / pl.col("r_points")).alias("net_R"))
           .group_by("trading_date").agg(pl.col("net_R").sum().alias("day_R"))
           .sort("trading_date"))
    dr = d["day_R"].to_numpy()
    eq = np.cumsum(dr)
    dd = np.maximum.accumulate(np.concatenate(([0.0], eq)))[1:] - eq
    best = cur = 0
    for x in dd:
        cur = cur + 1 if x > 1e-12 else 0
        best = max(best, cur)
    return {"pct_profitable_days": float((dr > 0).mean()),
            "daily_R_mean": float(dr.mean()), "daily_R_median": float(np.median(dr)),
            "daily_R_p05": float(np.quantile(dr, 0.05)),
            "daily_R_p95": float(np.quantile(dr, 0.95)),
            "worst_day_R": float(dr.min()), "best_day_R": float(dr.max()),
            "max_drawdown_R_daily": float(dd.max()) if dd.size else 0.0,
            "longest_drawdown_days": int(best)}


def window_report(acc: pl.DataFrame, tag: str, friction: float, all_days: int) -> dict:
    m = compute(acc, tag, friction=friction, n_days=all_days)
    m.update(frequency_stats(acc, all_days))
    m.update(daily_stats(acc, tag, friction, all_days))
    if acc.height:
        pts = acc[f"{tag}_points"].to_numpy() - friction
        R = pts / acc["r_points"].to_numpy()
        w = pts > 0
        m["median_R"] = float(np.median(R))
        m["adverse_excursion_before_winner"] = float(acc[f"{tag}_mae"].to_numpy()[w].mean()) if w.any() else 0.0
        m["favorable_excursion_before_loser"] = float(acc[f"{tag}_mfe"].to_numpy()[~w].mean()) if (~w).any() else 0.0
        m["breakeven_wr_at_friction"] = 0.5 + friction / (2.0 * float(acc["r_points"].mean()))
    return m
