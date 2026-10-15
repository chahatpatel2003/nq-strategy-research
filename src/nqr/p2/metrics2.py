"""Phase-2 metrics: reuses Phase-1 statistics and adds prop-firm daily measures."""
from __future__ import annotations

import numpy as np
import polars as pl

from nqr.metrics.stats import compute, wilson_ci, binom_p_value, max_drawdown, streaks

NS = 1_000_000_000
ET = "America/New_York"


def enrich(df: pl.DataFrame) -> pl.DataFrame:
    """Attach ET clock columns and the diagnostic buckets."""
    if df.height == 0:
        return df
    out = df.with_columns(
        pl.from_epoch(pl.col("signal_ns"), time_unit="ns").dt.replace_time_zone("UTC")
          .alias("signal_ts"))
    for c in ("entry_ns", "imp_start_ns", "imp_end_ns", "ext_ns", "arm_ns"):
        if c in df.columns:
            out = out.with_columns(
                pl.when(pl.col(c).is_not_null())
                  .then(pl.from_epoch(pl.col(c).fill_null(0), time_unit="ns")
                        .dt.replace_time_zone("UTC")).alias(c.replace("_ns", "_ts")))
    # The spec defines the reporting windows on the moment the ENTRY becomes
    # executable, so use entry_ts where it exists and fall back to signal_ts
    # for rows that never reached an entry.
    clock = (pl.coalesce([pl.col("entry_ts"), pl.col("signal_ts")])
             if "entry_ts" in out.columns else pl.col("signal_ts"))
    et = clock.dt.convert_time_zone(ET)
    mod = et.dt.hour().cast(pl.Int32) * 60 + et.dt.minute().cast(pl.Int32)
    out = out.with_columns(
        et.dt.strftime("%Y-%m-%d %H:%M:%S").alias("window_clock_et"),
        pl.col("signal_ts").dt.convert_time_zone(ET).dt.strftime("%Y-%m-%d %H:%M:%S").alias("signal_et"),
        mod.alias("et_minute"),
        et.dt.hour().cast(pl.Int32).alias("et_hour"),
        pl.col("trading_date").dt.year().alias("year"),
        pl.col("trading_date").dt.strftime("%Y-%m").alias("month"),
        ((mod >= 570) & (mod < 690)).alias("w_0930_1130"),
        ((mod >= 570) & (mod < 720)).alias("w_0930_1200"),
        ((mod >= 570) & (mod < 960)).alias("w_0930_1600"),
        ((mod >= 570) & (mod < 630)).alias("w_0930_1030"),
        ((mod >= 630) & (mod < 690)).alias("w_1030_1130"),
    )
    if "imp_disp_vu" in out.columns:
        out = out.with_columns(_bucket("imp_disp_vu", [1.25, 1.75, 2.5]).alias("imp_size_bucket"))
    if "imp_seconds" in out.columns:
        out = out.with_columns(_bucket("imp_seconds", [20, 45, 70]).alias("imp_dur_bucket"))
    if "agg_drop_ratio" in out.columns:
        out = out.with_columns(_bucket("agg_drop_ratio", [0.4, 0.6, 0.7]).alias("agg_drop_bucket"))
    if "absorption_pct" in out.columns:
        out = out.with_columns(_bucket("absorption_pct", [0.8, 0.9, 0.96]).alias("absorption_bucket"))
    if "r_points" in out.columns and "vu" in out.columns:
        out = out.with_columns((pl.col("r_points") / pl.col("vu")).alias("r_over_vu"))
        out = out.with_columns(_bucket("r_over_vu", [0.3, 0.5, 0.75]).alias("stop_bucket"))
    return out


def _bucket(col: str, edges: list[float]) -> pl.Expr:
    e = pl.col(col)
    expr = pl.when(e < edges[0]).then(pl.lit(f"<{edges[0]}"))
    for a, b in zip(edges, edges[1:]):
        expr = expr.when(e < b).then(pl.lit(f"{a}-{b}"))
    return expr.when(e >= edges[-1]).then(pl.lit(f">={edges[-1]}")).otherwise(pl.lit("na"))


def daily_stats(acc: pl.DataFrame, tag: str, friction: float,
                all_days: int) -> dict:
    """Prop-firm relevant daily distribution measures."""
    if acc.height == 0:
        return {}
    d = (acc.with_columns((pl.col(f"{tag}_points") - friction).alias("net_pts"),
                          ((pl.col(f"{tag}_points") - friction) / pl.col("r_points")).alias("net_R"))
           .group_by("trading_date")
           .agg(pl.col("net_R").sum().alias("day_R"), pl.len().alias("n"))
           .sort("trading_date"))
    n_active = d.height
    counts = d["n"].to_numpy()
    dr = d["day_R"].to_numpy()
    zero_days = all_days - n_active
    eq = np.cumsum(dr)
    peak = np.maximum.accumulate(np.concatenate(([0.0], eq)))[1:]
    dd = peak - eq
    rec = _recovery_times(dd)
    return {
        "trading_days_in_window": all_days,
        "days_with_trades": n_active,
        "pct_days_zero_trades": zero_days / max(all_days, 1),
        "pct_days_1_trade": float((counts == 1).sum()) / max(all_days, 1),
        "pct_days_2_trades": float((counts == 2).sum()) / max(all_days, 1),
        "pct_days_3plus_trades": float((counts >= 3).sum()) / max(all_days, 1),
        "trades_per_day_mean": float(acc.height / max(all_days, 1)),
        "trades_per_active_day_median": float(np.median(counts)),
        "pct_profitable_days": float((dr > 0).sum()) / max(n_active, 1),
        "daily_R_mean": float(dr.mean()), "daily_R_median": float(np.median(dr)),
        "daily_R_std": float(dr.std(ddof=1)) if n_active > 1 else float("nan"),
        "daily_R_p05": float(np.quantile(dr, 0.05)),
        "daily_R_p95": float(np.quantile(dr, 0.95)),
        "worst_day_R": float(dr.min()), "best_day_R": float(dr.max()),
        "max_drawdown_R_daily": float(dd.max()) if dd.size else 0.0,
        "max_recovery_days": rec,
    }


def _recovery_times(dd: np.ndarray) -> int:
    """Longest run of consecutive days spent below a previous equity peak."""
    best = cur = 0
    for x in dd:
        cur = cur + 1 if x > 1e-12 else 0
        best = max(best, cur)
    return int(best)


def window_report(acc: pl.DataFrame, tag: str, friction: float, all_days: int) -> dict:
    m = compute(acc, tag, friction=friction, n_days=all_days)
    m.update(daily_stats(acc, tag, friction, all_days))
    if acc.height:
        pts = acc[f"{tag}_points"].to_numpy() - friction
        r = acc["r_points"].to_numpy()
        R = pts / r
        w = pts > 0
        m["adverse_excursion_before_winner"] = float(acc[f"{tag}_mae"].to_numpy()[w].mean()) if w.any() else 0.0
        m["favorable_excursion_before_loser"] = float(acc[f"{tag}_mfe"].to_numpy()[~w].mean()) if (~w).any() else 0.0
        m["median_R"] = float(np.median(R))
    return m
