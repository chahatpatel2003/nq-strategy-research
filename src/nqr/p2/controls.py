"""Pre-registered control and null tests.

Both procedures were defined in IMPULSE_EXHAUSTION_SPEC.md before being run,
and neither may touch holdout data.
"""
from __future__ import annotations

import numpy as np

from nqr.backtest.engine import TICK, find_entry, resolve

NS = 1_000_000_000


def control_entries(rng: np.random.Generator, day_sec: np.ndarray, traded: np.ndarray,
                    vu: np.ndarray, bucket_lo: int, bucket_hi: int, k: int) -> list[int]:
    """Uniform draws from traded seconds in the matched 30-minute bucket."""
    m = traded & np.isfinite(vu) & (day_sec >= bucket_lo) & (day_sec < bucket_hi)
    idx = np.flatnonzero(m)
    if idx.size == 0:
        return []
    return [int(idx[i]) for i in rng.choice(idx.size, size=min(k, idx.size), replace=False)]


def resolve_control(ts: np.ndarray, px: np.ndarray, sig_ns: int, direction: int,
                    r_points: float, end_ns: int, latency_ns: int,
                    max_wait_ns: int) -> dict | None:
    """Same entry model, same first-passage engine, same R as the matched signal."""
    ent = find_entry(ts, px, sig_ns + latency_ns, max_wait_ns)
    if ent is None:
        return None
    eidx, ets, epx = ent
    stop = epx - direction * r_points
    tp = epx + direction * r_points
    f = resolve(ts, px, eidx, end_ns, direction, tp, stop)
    pts = (f.price - epx) * direction
    return {"entry_ns": ets, "entry_price": epx, "stop": stop, "target": tp,
            "outcome": f.kind, "exit_ns": f.ts_ns, "exit_price": f.price,
            "points": pts, "R": pts / r_points if r_points > 0 else 0.0,
            "direction": direction, "r_points": r_points}


def bootstrap_diff_ci(a: np.ndarray, b: np.ndarray, n_boot: int, rng: np.random.Generator,
                      alpha: float = 0.05) -> tuple[float, float, float]:
    """Percentile bootstrap CI for mean(a) - mean(b) (independent resampling)."""
    d = np.empty(n_boot)
    na, nb = len(a), len(b)
    for i in range(n_boot):
        d[i] = a[rng.integers(0, na, na)].mean() - b[rng.integers(0, nb, nb)].mean()
    return (float(a.mean() - b.mean()),
            float(np.quantile(d, alpha / 2)), float(np.quantile(d, 1 - alpha / 2)))


def permutation_p(a: np.ndarray, b: np.ndarray, n_perm: int,
                  rng: np.random.Generator) -> float:
    """One-sided: P(pooled relabelling gives a difference >= the observed one)."""
    obs = a.mean() - b.mean()
    pool = np.concatenate([a, b])
    na = len(a)
    cnt = 0
    for _ in range(n_perm):
        rng.shuffle(pool)
        if pool[:na].mean() - pool[na:].mean() >= obs:
            cnt += 1
    return (cnt + 1) / (n_perm + 1)


def label_shuffle_null(ts_by_day: dict, trades: list[dict], n_rep: int,
                       rng: np.random.Generator, long_frac: float) -> dict:
    """Re-resolve every signal with randomly reassigned DIRECTION labels.

    Entry timestamp, entry price and R are held fixed; only the sign of the
    trade changes, which destroys any link between the exhaustion features and
    subsequent direction while preserving the exact set of market moments, the
    time-of-day distribution and the risk geometry.
    """
    wr = np.empty(n_rep)
    ex = np.empty(n_rep)
    for r in range(n_rep):
        pts = []
        for t in trades:
            d = 1 if rng.random() < long_frac else -1
            ts, px, end_ns = ts_by_day[t["trading_date"]]
            eidx = int(np.searchsorted(ts, t["entry_ns"], side="left"))
            if eidx >= len(ts):
                continue
            epx = t["entry_price"]
            f = resolve(ts, px, eidx, end_ns, d, epx + d * t["r_points"],
                        epx - d * t["r_points"])
            pts.append((f.price - epx) * d / t["r_points"])
        p = np.asarray(pts)
        wr[r] = float((p > 0).mean()) if p.size else np.nan
        ex[r] = float(p.mean()) if p.size else np.nan
    return {"null_win_rate": wr, "null_expectancy_R": ex}
