"""Phase-4 performance statistics and DAY-BLOCK inference.

Adjacent 5-second observations overlap by up to 30 minutes, so no interval here
is ever computed as if trades were independent.  Every uncertainty statement is
a bootstrap over whole TRADING DAYS, which keeps a day's internal dependence
intact by construction.
"""
from __future__ import annotations

import numpy as np
import polars as pl

from nqr.metrics.stats import max_drawdown, streaks, wilson_ci
from nqr.p4.dataset4 import PRIMARY_FRICTION

N_BOOT = 10_000
BOOT_SEED = 20260819


def _net(t: pl.DataFrame, friction: float) -> np.ndarray:
    return t["points"].to_numpy().astype(float) - friction


def summarize(t: pl.DataFrame, friction: float = PRIMARY_FRICTION,
              n_days_available: int | None = None) -> dict:
    """Full prop-firm metric block for one accepted-trade book."""
    n = t.height
    out = {"n_trades": n, "friction_points": friction}
    if n == 0:
        return out
    pts = _net(t, friction)
    r = t["r_points"].to_numpy().astype(float)
    R = pts / r
    d = t["direction"].to_numpy()
    outc = t["outcome"].to_numpy()
    hold = t["hold_s"].to_numpy().astype(float)
    mfe = t["mfe"].to_numpy().astype(float)
    mae = t["mae"].to_numpy().astype(float)
    sec = t["sec_since_open"].to_numpy()
    wins = pts > 0
    k = int(wins.sum())
    gp = float(pts[wins].sum()); gl = float(-pts[~wins & (pts < 0)].sum())
    lo, hi = wilson_ci(k, n)

    days = t["trading_date"].to_numpy()
    uniq, inv = np.unique(days, return_inverse=True)
    dayR = np.bincount(inv, weights=R, minlength=len(uniq))
    dayN = np.bincount(inv, minlength=len(uniq))
    n_active = len(uniq)
    n_avail = n_days_available or n_active
    zero_days = max(0, n_avail - n_active)
    counts = np.concatenate([dayN, np.zeros(zero_days, dtype=int)])
    lw, ll = streaks(wins)

    out.update({
        "wins": k, "losses": int((pts < 0).sum()), "breakevens": int((pts == 0).sum()),
        "win_rate": k / n, "win_rate_ci95_lo": lo, "win_rate_ci95_hi": hi,
        "expectancy_R": float(R.mean()), "expectancy_points": float(pts.mean()),
        "total_R": float(R.sum()), "total_points": float(pts.sum()),
        "profit_factor": (gp / gl) if gl > 0 else float("inf"),
        "tp_hits": int((outc == "TP").sum()), "sl_hits": int((outc == "SL").sum()),
        "timeouts": int((outc == "TIMEOUT").sum()),
        "longs": int((d > 0).sum()), "shorts": int((d < 0).sum()),
        "long_win_rate": float((pts[d > 0] > 0).mean()) if (d > 0).any() else float("nan"),
        "short_win_rate": float((pts[d < 0] > 0).mean()) if (d < 0).any() else float("nan"),
        "avg_winner_R": float(R[wins].mean()) if k else 0.0,
        "avg_loser_R": float(R[~wins].mean()) if (~wins).any() else 0.0,
        "avg_MFE_points": float(mfe.mean()), "median_MFE_points": float(np.median(mfe)),
        "avg_MAE_points": float(mae.mean()), "median_MAE_points": float(np.median(mae)),
        "avg_hold_min": float(hold.mean()) / 60.0,
        "median_hold_min": float(np.median(hold)) / 60.0,
        "avg_R_distance_points": float(r.mean()),
        "max_drawdown_R": max_drawdown(R), "max_drawdown_points": max_drawdown(pts),
        "longest_win_streak": lw, "longest_loss_streak": ll,
        "n_trading_days_active": n_active, "n_trading_days_available": n_avail,
        "trades_per_day": n / n_avail,
        "median_trades_per_day": float(np.median(counts)),
        "pct_zero_trade_days": zero_days / n_avail,
        "pct_1_trade_days": float((counts == 1).mean()),
        "pct_2_trade_days": float((counts == 2).mean()),
        "pct_3plus_trade_days": float((counts >= 3).mean()),
        "trades_0930_1030": int((sec < 3600).sum()),
        "trades_1030_1130": int(((sec >= 3600) & (sec < 7200)).sum()),
        "R_per_day": float(R.sum() / n_avail),
        "median_R_per_day": float(np.median(np.concatenate([dayR, np.zeros(zero_days)]))),
        "pct_profitable_days": float((dayR > 0).mean()),
        "max_daily_loss_R": float(dayR.min()),
        "p95_daily_loss_R": float(np.quantile(dayR, 0.05)),
        "max_daily_gain_R": float(dayR.max()),
        "drawdown_recovery_days": _recovery_days(uniq, dayR),
    })
    return out


def _recovery_days(days: np.ndarray, dayR: np.ndarray) -> float:
    """Trading days from the deepest equity peak to the first full recovery."""
    eq = np.cumsum(dayR)
    peak = np.maximum.accumulate(eq)
    dd = peak - eq
    if dd.size == 0 or dd.max() <= 0:
        return 0.0
    i = int(np.argmax(dd))
    lvl = peak[i]
    after = np.flatnonzero(eq[i:] >= lvl)
    return float(after[0]) if after.size else float("inf")


def by_group(t: pl.DataFrame, col: str, friction: float = PRIMARY_FRICTION,
             keys=None) -> pl.DataFrame:
    if t.height == 0:
        return pl.DataFrame()
    rows = []
    for key in (keys if keys is not None else t[col].unique().sort().to_list()):
        sub = t.filter(pl.col(col) == key)
        if sub.height == 0:
            continue
        m = summarize(sub, friction)
        rows.append({col: key, **{k: m[k] for k in
                                  ("n_trades", "win_rate", "expectancy_R", "total_R",
                                   "profit_factor", "avg_MFE_points", "avg_MAE_points",
                                   "median_hold_min")}})
    return pl.DataFrame(rows) if rows else pl.DataFrame()


# ------------------------------------------------- day-block bootstrap ----
def _by_day(t: pl.DataFrame, vals: np.ndarray, all_days: np.ndarray):
    d = t["trading_date"].to_numpy()
    pos = {day: i for i, day in enumerate(all_days)}
    s = np.zeros(len(all_days)); c = np.zeros(len(all_days))
    for day, v in zip(d, vals):
        j = pos[day]
        s[j] += v; c[j] += 1
    return s, c


def block_bootstrap_diff(a: pl.DataFrame, b: pl.DataFrame, friction: float,
                         stat: str = "expectancy_R", n_boot: int = N_BOOT,
                         seed: int = BOOT_SEED, alpha: float = 0.05) -> dict:
    """95% CI for mean(a) - mean(b), resampling whole TRADING DAYS.

    A bootstrap draw takes a day's strategy trades and that same day's control
    trades together, so the two books stay paired and within-day dependence is
    preserved on both sides.
    """
    if a.height == 0 or b.height == 0:
        return {"n_a": a.height, "n_b": b.height, "diff": float("nan"),
                "ci95_lo": float("nan"), "ci95_hi": float("nan"), "stat": stat}
    days = np.unique(np.concatenate([a["trading_date"].to_numpy(),
                                     b["trading_date"].to_numpy()]))
    va = _stat_vals(a, friction, stat)
    vb = _stat_vals(b, friction, stat)
    sa, ca = _by_day(a, va, days)
    sb, cb = _by_day(b, vb, days)
    rng = np.random.default_rng(seed)
    nd = len(days)
    obs = va.mean() - vb.mean()
    out = np.empty(n_boot)
    for i in range(n_boot):
        p = rng.integers(0, nd, nd)
        na, nb = ca[p].sum(), cb[p].sum()
        out[i] = (sa[p].sum() / na if na else np.nan) - (sb[p].sum() / nb if nb else np.nan)
    out = out[np.isfinite(out)]
    return {"stat": stat, "n_a": a.height, "n_b": b.height, "n_days": int(nd),
            "mean_a": float(va.mean()), "mean_b": float(vb.mean()), "diff": float(obs),
            "ci95_lo": float(np.quantile(out, alpha / 2)),
            "ci95_hi": float(np.quantile(out, 1 - alpha / 2)),
            "p_diff_le_0": float((out <= 0).mean()), "n_boot": int(out.size)}


def _stat_vals(t: pl.DataFrame, friction: float, stat: str) -> np.ndarray:
    pts = _net(t, friction)
    if stat == "expectancy_R":
        return pts / t["r_points"].to_numpy().astype(float)
    if stat == "win_rate":
        return (pts > 0).astype(float)
    if stat == "expectancy_points":
        return pts
    raise ValueError(stat)


def block_bootstrap_ci(t: pl.DataFrame, friction: float, stat: str = "expectancy_R",
                       n_boot: int = N_BOOT, seed: int = BOOT_SEED,
                       alpha: float = 0.05) -> dict:
    if t.height == 0:
        return {"stat": stat, "mean": float("nan"), "ci95_lo": float("nan"),
                "ci95_hi": float("nan")}
    days = np.unique(t["trading_date"].to_numpy())
    v = _stat_vals(t, friction, stat)
    s, c = _by_day(t, v, days)
    rng = np.random.default_rng(seed)
    nd = len(days)
    out = np.empty(n_boot)
    for i in range(n_boot):
        p = rng.integers(0, nd, nd)
        n = c[p].sum()
        out[i] = s[p].sum() / n if n else np.nan
    out = out[np.isfinite(out)]
    return {"stat": stat, "mean": float(v.mean()), "n_days": int(nd),
            "ci95_lo": float(np.quantile(out, alpha / 2)),
            "ci95_hi": float(np.quantile(out, 1 - alpha / 2))}


def weekly_concentration(t: pl.DataFrame, friction: float = PRIMARY_FRICTION) -> dict:
    """PREREG A14 / Gate 7: deleting the single best ISO week must leave the
    period still profitable."""
    if t.height == 0:
        return {}
    R = _net(t, friction) / t["r_points"].to_numpy().astype(float)
    wk = np.array([f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}"
                   for d in t["trading_date"].to_list()])
    uw, inv = np.unique(wk, return_inverse=True)
    wR = np.bincount(inv, weights=R, minlength=len(uw))
    total = float(R.sum())
    best = int(np.argmax(wR))
    return {"n_weeks": len(uw), "total_net_R": total,
            "best_week": str(uw[best]), "best_week_net_R": float(wR[best]),
            "best_week_share": float(wR[best] / total) if total != 0 else float("nan"),
            "total_ex_best_week_R": float(total - wR[best]),
            "gate7_pass": bool(total - wR[best] > 0),
            "weekly_R": {str(u): float(v) for u, v in zip(uw, wR)}}
