"""Performance statistics.  Every number is computed, never asserted."""
from __future__ import annotations

import math

import numpy as np
import polars as pl
from scipy import stats as sps

NS = 1_000_000_000


def wilson_ci(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Wilson score interval - the standard 95% CI for a binomial proportion."""
    if n == 0:
        return (float("nan"), float("nan"))
    z = sps.norm.ppf(1 - alpha / 2)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def binom_p_value(k: int, n: int, p0: float) -> float:
    """One-sided test: P(X >= k | Binom(n, p0))."""
    if n == 0:
        return float("nan")
    return float(sps.binomtest(k, n, p0, alternative="greater").pvalue)


def max_drawdown(series: np.ndarray) -> float:
    if series.size == 0:
        return 0.0
    eq = np.cumsum(series)
    peak = np.maximum.accumulate(np.concatenate(([0.0], eq)))[1:]
    return float(np.max(peak - eq))


def streaks(wins: np.ndarray) -> tuple[int, int]:
    """(longest winning streak, longest losing streak)."""
    best_w = best_l = cur_w = cur_l = 0
    for w in wins:
        if w:
            cur_w += 1; cur_l = 0
        else:
            cur_l += 1; cur_w = 0
        best_w = max(best_w, cur_w)
        best_l = max(best_l, cur_l)
    return best_w, best_l


_TAG_RR = {"r1": 1.0, "r2": 2.0}


def rr_of_tag(tag: str) -> float:
    """Reward:risk multiple encoded in a target tag.

    Phase 1 used 'r1'/'r2'.  Phase 2 encodes fractional multiples as 'r1p25',
    'r1p5', 'r2p0'.  Getting this wrong silently tests the win rate against the
    wrong null, so it is parsed explicitly rather than guessed.
    """
    if tag in _TAG_RR:
        return _TAG_RR[tag]
    body = tag[1:] if tag.startswith("r") else tag
    return float(body.replace("p", "."))


def breakeven_win_rate(tag: str) -> float:
    """p such that p*RR = (1-p)*1, i.e. the win rate at which the book is flat."""
    return 1.0 / (1.0 + rr_of_tag(tag))


def compute(trades: pl.DataFrame, tag: str, friction: float = 0.0,
            n_days: int | None = None, n_days_rth: int | None = None,
            breakeven_p0: float | None = None) -> dict:
    """``tag`` is 'r1' or 'r2'.  ``friction`` is round-trip cost in NQ points."""
    t = trades.filter(pl.col("status") == "ACCEPTED")
    n = t.height
    out = {"n_trades": n, "friction_points": friction}
    if n == 0:
        return out
    pts = t[f"{tag}_points"].to_numpy().astype(float) - friction
    r = t["r_points"].to_numpy().astype(float)
    R = pts / r
    outcome = t[f"{tag}_outcome"].to_numpy()
    d = t["direction"].to_numpy()
    hold = t[f"{tag}_hold_s"].to_numpy().astype(float)
    mfe = t[f"{tag}_mfe"].to_numpy().astype(float)
    mae = t[f"{tag}_mae"].to_numpy().astype(float)

    wins = pts > 0
    losses = pts < 0
    bes = pts == 0
    k = int(wins.sum())
    lo, hi = wilson_ci(k, n)
    gp = float(pts[wins].sum())
    gl = float(-pts[losses].sum())

    p0 = breakeven_p0 if breakeven_p0 is not None else breakeven_win_rate(tag)
    out.update({
        "wins": k, "losses": int(losses.sum()), "breakevens": int(bes.sum()),
        "win_rate": k / n, "win_rate_ci95_lo": lo, "win_rate_ci95_hi": hi,
        "breakeven_win_rate": p0,
        "p_value_gt_breakeven": binom_p_value(k, n, p0),
        "tp_hits": int((outcome == "TP").sum()), "sl_hits": int((outcome == "SL").sum()),
        "timeouts": int((outcome == "TIMEOUT").sum()),
        "longs": int((d > 0).sum()), "shorts": int((d < 0).sum()),
        "avg_R": float(R.mean()), "expectancy_R": float(R.mean()),
        "expectancy_points": float(pts.mean()),
        "total_points": float(pts.sum()), "total_R": float(R.sum()),
        "profit_factor": (gp / gl) if gl > 0 else float("inf"),
        "avg_winner_points": float(pts[wins].mean()) if k else 0.0,
        "avg_loser_points": float(pts[losses].mean()) if losses.any() else 0.0,
        "median_winner_points": float(np.median(pts[wins])) if k else 0.0,
        "median_loser_points": float(np.median(pts[losses])) if losses.any() else 0.0,
        "avg_winner_R": float(R[wins].mean()) if k else 0.0,
        "avg_loser_R": float(R[losses].mean()) if losses.any() else 0.0,
        "max_drawdown_R": max_drawdown(R),
        "max_drawdown_points": max_drawdown(pts),
        "avg_MAE_points": float(mae.mean()), "median_MAE_points": float(np.median(mae)),
        "avg_MFE_points": float(mfe.mean()), "median_MFE_points": float(np.median(mfe)),
        "avg_hold_min": float(hold.mean()) / 60.0,
        "median_hold_min": float(np.median(hold)) / 60.0,
        "avg_R_distance_points": float(r.mean()),
        "median_R_distance_points": float(np.median(r)),
        "t_stat_R": float(R.mean() / (R.std(ddof=1) / math.sqrt(n))) if n > 1 and R.std(ddof=1) > 0 else float("nan"),
    })
    lw, ll = streaks(wins)
    out["longest_win_streak"], out["longest_loss_streak"] = lw, ll
    if n_days:
        out["trades_per_day"] = n / n_days
        out["n_trading_days"] = n_days
    if n_days_rth:
        out["n_days_rth_window"] = n_days_rth
    return out


def by_group(trades: pl.DataFrame, tag: str, col: str, friction: float = 0.0) -> pl.DataFrame:
    rows = []
    acc = trades.filter(pl.col("status") == "ACCEPTED")
    for key in acc[col].unique().sort().to_list():
        sub = acc.filter(pl.col(col) == key)
        m = compute(sub, tag, friction)
        m[col] = key
        rows.append(m)
    if not rows:
        return pl.DataFrame()
    cols = [col, "n_trades", "wins", "losses", "win_rate", "win_rate_ci95_lo",
            "win_rate_ci95_hi", "expectancy_R", "expectancy_points", "total_points",
            "profit_factor", "avg_MAE_points", "avg_MFE_points", "median_hold_min"]
    df = pl.DataFrame(rows)
    return df.select([c for c in cols if c in df.columns]).sort(col)
