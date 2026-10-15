"""Phase-4 strategy backtest and the four controls.

Every trade, every control and every null uses the SAME realised entry, the
same 1R/1R bracket, the same 30-minute horizon and the same friction, because
all of them read the labels already resolved tick-by-tick in the state dataset.
There is no second execution model anywhere in Phase 4.
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from nqr.p4.dataset4 import FRICTIONS, PRIMARY_FRICTION

NS = 1_000_000_000
CONTROL_SEED = 20260819          # PREREG A11
CONTROLS_PER_TRADE = 10
BUCKET_S = 1800                  # 30-minute time-of-day bucket
R_MATCH_LO, R_MATCH_HI = 0.80, 1.25
OUTCOME_NAME = {1: "TP", -1: "SL", 0: "TIMEOUT", -9: "NO_DATA"}


def _cols(df: pl.DataFrame) -> dict:
    # NOTE: .to_numpy() on a Date column yields np.datetime64, which does NOT
    # compare equal to the datetime.date keys used elsewhere -- that silently
    # emptied the matched-control pool.  Python dates throughout.
    return {
        "date": np.array(df["trading_date"].to_list(), dtype=object),
        "sym": np.array(df["symbol"].to_list(), dtype=object),
        "ts": df["decision_ts_ns"].to_numpy(),
        "sec": df["sec_since_open"].to_numpy(),
        "r": df["r_points"].to_numpy().astype(float),
        "ent": df["entry_ns"].to_numpy(),
        "epx": df["entry_price"].to_numpy().astype(float),
        "lo": df["long_outcome"].to_numpy(), "lp": df["long_points"].to_numpy().astype(float),
        "lf": df["long_mfe"].to_numpy().astype(float), "la": df["long_mae"].to_numpy().astype(float),
        "lh": df["long_hold_s"].to_numpy().astype(float), "lx": df["long_exit_ns"].to_numpy(),
        "so": df["short_outcome"].to_numpy(), "sp": df["short_points"].to_numpy().astype(float),
        "sf": df["short_mfe"].to_numpy().astype(float), "sa": df["short_mae"].to_numpy().astype(float),
        "sh": df["short_hold_s"].to_numpy().astype(float), "sx": df["short_exit_ns"].to_numpy(),
    }


def _pick(C: dict, i: int, direction: int) -> dict:
    if direction > 0:
        o, p, f, a, h, x = C["lo"][i], C["lp"][i], C["lf"][i], C["la"][i], C["lh"][i], C["lx"][i]
    else:
        o, p, f, a, h, x = C["so"][i], C["sp"][i], C["sf"][i], C["sa"][i], C["sh"][i], C["sx"][i]
    r = C["r"][i]
    return {"outcome": OUTCOME_NAME[int(o)], "points": float(p), "R": float(p / r),
            "mfe": float(f), "mae": float(a), "hold_s": float(h), "exit_ns": int(x),
            "exit_price": float(C["epx"][i] + direction * p)}


def _base(C: dict, i: int, direction: int, score: float) -> dict:
    r = C["r"][i]
    return {"trading_date": C["date"][i], "symbol": C["sym"][i],
            "decision_ts_ns": int(C["ts"][i]), "sec_since_open": int(C["sec"][i]),
            "direction": direction, "side": "LONG" if direction > 0 else "SHORT",
            "score": float(score), "edge": float(abs(score)),
            "entry_ns": int(C["ent"][i]), "entry_price": float(C["epx"][i]),
            "r_points": float(r),
            "stop": float(C["epx"][i] - direction * r),
            "target": float(C["epx"][i] + direction * r)}


def _with_frictions(rec: dict) -> dict:
    for fr in FRICTIONS:
        rec[f"net_{str(fr).replace('.', 'p')}"] = rec["points"] - fr
        rec[f"netR_{str(fr).replace('.', 'p')}"] = (rec["points"] - fr) / rec["r_points"]
    return rec


# ------------------------------------------------------------ strategy ----
def run_strategy(df: pl.DataFrame, score: np.ndarray, tau: float,
                 usable: np.ndarray) -> pl.DataFrame:
    """One position at a time.  Candidates during an open position are logged
    SKIPPED_OVERLAP and never become a second position."""
    C = _cols(df)
    n = df.height
    dates = C["date"]
    rows: list[dict] = []
    busy_until = -1
    cur_day = None
    for i in range(n):
        if dates[i] != cur_day:
            cur_day, busy_until = dates[i], -1
        if not usable[i]:
            continue
        s = score[i]
        if abs(s) < tau:
            continue
        direction = 1 if s > 0 else -1
        rec = _base(C, i, direction, s)
        if C["ent"][i] <= 0:
            rec.update(status="SKIPPED", skip_reason="NO_ENTRY_PRINT")
            rows.append(rec); continue
        if C["ts"][i] < busy_until:
            rec.update(status="SKIPPED", skip_reason="SKIPPED_OVERLAP")
            rows.append(rec); continue
        rec.update(_pick(C, i, direction))
        _with_frictions(rec)
        rec.update(status="ACCEPTED", skip_reason=None)
        busy_until = rec["exit_ns"]
        rows.append(rec)
    return _frame(rows)


def _frame(rows: list[dict]) -> pl.DataFrame:
    if not rows:
        return pl.DataFrame()
    keys: list[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    full = [{k: r.get(k) for k in keys} for r in rows]
    ov = {"trading_date": pl.Date, "symbol": pl.String,
          "exit_ns": pl.Int64, "outcome": pl.String, "skip_reason": pl.String,
          "points": pl.Float64, "R": pl.Float64, "mfe": pl.Float64, "mae": pl.Float64,
          "hold_s": pl.Float64, "exit_price": pl.Float64}
    for fr in FRICTIONS:
        ov[f"net_{str(fr).replace('.', 'p')}"] = pl.Float64
        ov[f"netR_{str(fr).replace('.', 'p')}"] = pl.Float64
    return pl.DataFrame(full, strict=False,
                        schema_overrides={k: v for k, v in ov.items() if k in keys})


def accepted(trades: pl.DataFrame) -> pl.DataFrame:
    if trades.height == 0:
        return trades
    return trades.filter(pl.col("status") == "ACCEPTED")


# ------------------------------------------- C1: matched-random control ----
def matched_controls(trades: pl.DataFrame, df: pl.DataFrame, usable: np.ndarray,
                     k: int = CONTROLS_PER_TRADE, seed: int = CONTROL_SEED) -> pl.DataFrame:
    """PREREG A11.  Same day, same 30-min bucket, same direction, matched R,
    identical execution.  Controls are independent entries: the one-position
    rule deliberately does not apply to them."""
    acc = accepted(trades)
    if acc.height == 0:
        return pl.DataFrame()
    C = _cols(df)
    rng = np.random.default_rng(seed)
    dates = C["date"]
    bucket = (C["sec"] // BUCKET_S).astype(np.int64)
    pool: dict[tuple, np.ndarray] = {}
    ok = usable & (C["ent"] > 0)
    for i in range(len(dates)):
        if ok[i]:
            pool.setdefault((dates[i], int(bucket[i])), []).append(i)
    pool = {kk: np.asarray(v) for kk, v in pool.items()}

    rows: list[dict] = []
    for t in acc.iter_rows(named=True):
        cand = pool.get((t["trading_date"], t["sec_since_open"] // BUCKET_S))
        if cand is None or cand.size == 0:
            continue
        rr = C["r"][cand] / t["r_points"]
        elig = cand[(rr >= R_MATCH_LO) & (rr <= R_MATCH_HI)]
        if elig.size == 0:
            continue
        take = rng.choice(elig.size, size=min(k, elig.size), replace=False)
        for j in elig[take]:
            rec = _base(C, int(j), t["direction"], 0.0)
            rec.update(_pick(C, int(j), t["direction"]))
            _with_frictions(rec)
            rec.update(status="ACCEPTED", skip_reason=None,
                       matched_to_ts=t["decision_ts_ns"])
            rows.append(rec)
    return _frame(rows)


# --------------------------------------------- C2: opposite direction ----
def opposite_direction(trades: pl.DataFrame, df: pl.DataFrame,
                       usable: np.ndarray) -> pl.DataFrame:
    """Same signal timestamps, direction flipped, everything else identical."""
    acc = accepted(trades)
    if acc.height == 0:
        return pl.DataFrame()
    C = _cols(df)
    pos = {int(ts): i for i, ts in enumerate(C["ts"])}
    rows = []
    for t in acc.iter_rows(named=True):
        i = pos.get(t["decision_ts_ns"])
        if i is None:
            continue
        d = -t["direction"]
        rec = _base(C, i, d, -t["score"])
        rec.update(_pick(C, i, d))
        _with_frictions(rec)
        rec.update(status="ACCEPTED", skip_reason=None)
        rows.append(rec)
    return _frame(rows)


# ------------------------------------------------ C3: shuffled labels ----
def shuffled_direction_null(trades: pl.DataFrame, df: pl.DataFrame, usable: np.ndarray,
                            n_rep: int = 1000, seed: int = CONTROL_SEED + 1,
                            friction: float = PRIMARY_FRICTION) -> dict:
    """Re-resolve every executed trade with a randomly reassigned direction,
    preserving the realised long fraction.  Entry, R and horizon are unchanged,
    so only the feature->direction link is destroyed."""
    acc = accepted(trades)
    if acc.height == 0:
        return {}
    C = _cols(df)
    pos = {int(ts): i for i, ts in enumerate(C["ts"])}
    idx = np.array([pos[t] for t in acc["decision_ts_ns"].to_list() if t in pos])
    long_frac = float((acc["direction"] > 0).mean())
    r = C["r"][idx]
    lp, sp = C["lp"][idx], C["sp"][idx]
    rng = np.random.default_rng(seed)
    wr = np.empty(n_rep); ex = np.empty(n_rep)
    for j in range(n_rep):
        pick_long = rng.random(idx.size) < long_frac
        pts = np.where(pick_long, lp, sp) - friction
        wr[j] = float((pts > 0).mean())
        ex[j] = float((pts / r).mean())
    return {"n_rep": n_rep, "long_frac": long_frac,
            "null_win_rate": wr, "null_expectancy_R": ex}
