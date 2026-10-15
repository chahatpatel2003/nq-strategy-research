"""Markdown report generation for a Fast-Slow run."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np
import polars as pl

from nqr.metrics.stats import compute, by_group
from nqr.signals.fast_slow import time_ratio_bucket

NS = 1_000_000_000
ET = "America/New_York"


def enrich(df: pl.DataFrame) -> pl.DataFrame:
    """Add ET timestamps, session labels and reporting buckets."""
    def ts(col):
        return pl.from_epoch(pl.col(col), time_unit="ns").dt.replace_time_zone("UTC")
    out = df.with_columns(
        ts("signal_ns").alias("signal_ts"),
        ts("a_ns").alias("a_ts"), ts("b_ns").alias("b_ts"), ts("c_ns").alias("c_ts"),
    )
    if "entry_ns" in df.columns:
        out = out.with_columns(
            pl.when(pl.col("entry_ns").is_not_null())
              .then(pl.from_epoch(pl.col("entry_ns").fill_null(0), time_unit="ns")
                    .dt.replace_time_zone("UTC")).alias("entry_ts"))
    for tag in ("r1", "r2"):
        if f"{tag}_exit_ns" in df.columns:
            out = out.with_columns(
                pl.when(pl.col(f"{tag}_exit_ns").is_not_null())
                  .then(pl.from_epoch(pl.col(f"{tag}_exit_ns").fill_null(0), time_unit="ns")
                        .dt.replace_time_zone("UTC")).alias(f"{tag}_exit_ts"))
    et = pl.col("signal_ts").dt.convert_time_zone(ET)
    mod = et.dt.hour().cast(pl.Int32) * 60 + et.dt.minute().cast(pl.Int32)
    out = out.with_columns(
        et.dt.strftime("%Y-%m-%d %H:%M:%S").alias("signal_et"),
        mod.alias("et_minute"),
        pl.when((mod >= 18 * 60) | (mod < 3 * 60)).then(pl.lit("ASIA"))
          .when(mod < 9 * 60 + 30).then(pl.lit("EU"))
          .when(mod < 16 * 60).then(pl.lit("US"))
          .otherwise(pl.lit("POST")).alias("session"),
        ((mod >= 9 * 60 + 30) & (mod < 11 * 60 + 30)).alias("is_0930_1130"),
        pl.col("trading_date").dt.year().alias("year"),
        pl.col("trading_date").dt.strftime("%Y-%m").alias("month"),
        pl.when(pl.col("direction") > 0).then(pl.lit("LONG")).otherwise(pl.lit("SHORT")).alias("side"),
        pl.col("time_ratio").map_elements(time_ratio_bucket, return_dtype=pl.String).alias("tr_bucket"),
        (pl.col("ab_ns") / 6e10).alias("ab_minutes"),
        (pl.col("bc_ns") / 6e10).alias("bc_minutes"),
    )
    return out


def _fmt(v):
    if v is None:
        return "-"
    if isinstance(v, float):
        if np.isnan(v):
            return "nan"
        if abs(v) >= 1000:
            return f"{v:,.0f}"
        return f"{v:.3f}"
    return str(v)


def kv_table(m: dict, keys: list[tuple[str, str]]) -> str:
    lines = ["| metric | value |", "|---|---|"]
    for k, label in keys:
        if k in m:
            lines.append(f"| {label} | {_fmt(m[k])} |")
    return "\n".join(lines)


HEADLINE = [
    ("n_trades", "executed trades"), ("trades_per_day", "trades / trading day"),
    ("longs", "long"), ("shorts", "short"),
    ("wins", "wins"), ("losses", "losses"), ("breakevens", "breakevens"),
    ("win_rate", "win rate"), ("win_rate_ci95_lo", "win rate 95% CI low"),
    ("win_rate_ci95_hi", "win rate 95% CI high"),
    ("breakeven_win_rate", "break-even win rate"),
    ("p_value_gt_breakeven", "p(win rate > break-even), one-sided"),
    ("expectancy_R", "expectancy (R)"), ("expectancy_points", "expectancy (NQ points)"),
    ("avg_R", "average R"), ("total_points", "total points"), ("total_R", "total R"),
    ("profit_factor", "profit factor"),
    ("avg_winner_points", "average winner (pts)"), ("avg_loser_points", "average loser (pts)"),
    ("median_winner_points", "median winner (pts)"), ("median_loser_points", "median loser (pts)"),
    ("max_drawdown_R", "max drawdown (R)"), ("max_drawdown_points", "max drawdown (pts)"),
    ("longest_win_streak", "longest winning streak"),
    ("longest_loss_streak", "longest losing streak"),
    ("avg_MAE_points", "average MAE (pts)"), ("median_MAE_points", "median MAE (pts)"),
    ("avg_MFE_points", "average MFE (pts)"), ("median_MFE_points", "median MFE (pts)"),
    ("avg_hold_min", "average hold (min)"), ("median_hold_min", "median hold (min)"),
    ("avg_R_distance_points", "average R distance (pts)"),
    ("tp_hits", "TP exits"), ("sl_hits", "SL exits"), ("timeouts", "timeout exits"),
    ("t_stat_R", "t-stat of mean R"),
]


def df_to_md(df: pl.DataFrame, max_rows: int = 200) -> str:
    if df is None or df.height == 0:
        return "_(no rows)_"
    df = df.head(max_rows)
    cols = df.columns
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for row in df.iter_rows():
        lines.append("| " + " | ".join(_fmt(v) for v in row) + " |")
    return "\n".join(lines)
