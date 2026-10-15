"""Phase-5 backtest: one position, cooldown, and the two controls.

Strategy trades and every control read the SAME tick-resolved labels from the
same dataset rows, so execution is identical by construction.
"""
from __future__ import annotations

import numpy as np
import polars as pl

from nqr.p5.dataset5 import FRICTIONS, PRIMARY_FRICTION

NS = 1_000_000_000
CONTROL_SEED = 20260820                  # PHASE5_SPEC S15
CONTROLS_PER_TRADE = 10
BUCKET_S = 1800
R_MATCH_LO, R_MATCH_HI = 0.80, 1.25
COOLDOWN_NS = 60 * NS                    # PHASE5_SPEC S13: one decision interval
OUTCOME_NAME = {1: "TP", -1: "SL", 0: "TIMEOUT", -9: "NO_DATA"}


def _cols(df: pl.DataFrame, tag: str) -> dict:
    g = {
        # .to_numpy() on a Date column yields np.datetime64, which does NOT
        # compare equal to the datetime.date keys used for control matching.
        "date": np.array(df["trading_date"].to_list(), dtype=object),
        "sym": np.array(df["symbol"].to_list(), dtype=object),
        "ts": df["decision_ts_ns"].to_numpy(),
        "sec": df["sec_since_open"].to_numpy(),
        "atr": df["atr1m"].to_numpy().astype(float),
        "r": df[f"{tag}_R"].to_numpy().astype(float),
        "ent": df["entry_ns"].to_numpy(),
        "epx": df["entry_price"].to_numpy().astype(float),
    }
    for side, pre in (("long", "l"), ("short", "s")):
        for s, k in (("outcome", "o"), ("points", "p"), ("mfe", "f"),
                     ("mae", "a"), ("hold_s", "h"), ("exit_ns", "x")):
            v = df[f"{tag}_{side}_{s}"].to_numpy()
            g[pre + k] = v if s in ("outcome", "exit_ns") else v.astype(float)
    return g


def _pick(C: dict, i: int, direction: int) -> dict:
    p = "l" if direction > 0 else "s"
    r = C["r"][i]
    return {"outcome": OUTCOME_NAME[int(C[p + "o"][i])], "points": float(C[p + "p"][i]),
            "R": float(C[p + "p"][i] / r), "mfe": float(C[p + "f"][i]),
            "mae": float(C[p + "a"][i]), "hold_s": float(C[p + "h"][i]),
            "exit_ns": int(C[p + "x"][i]),
            "exit_price": float(C["epx"][i] + direction * C[p + "p"][i])}


def _base(C: dict, i: int, direction: int, score: float) -> dict:
    r = C["r"][i]
    return {"trading_date": C["date"][i], "symbol": C["sym"][i],
            "decision_ts_ns": int(C["ts"][i]), "sec_since_open": int(C["sec"][i]),
            "bucket15": int(C["sec"][i] // 900),
            "direction": direction, "side": "LONG" if direction > 0 else "SHORT",
            "score": float(score), "edge": float(score),
            "atr1m": float(C["atr"][i]),
            "entry_ns": int(C["ent"][i]), "entry_price": float(C["epx"][i]),
            "r_points": float(r),
            "stop": float(C["epx"][i] - direction * r),
            "target": float(C["epx"][i] + direction * r),
            "friction_over_r": float(PRIMARY_FRICTION / r)}


def _with_frictions(rec: dict) -> dict:
    for fr in FRICTIONS:
        k = str(fr).replace(".", "p")
        rec[f"net_{k}"] = rec["points"] - fr
        rec[f"netR_{k}"] = (rec["points"] - fr) / rec["r_points"]
    return rec


def _frame(rows: list[dict]) -> pl.DataFrame:
    if not rows:
        return pl.DataFrame()
    keys: list[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    full = [{k: r.get(k) for k in keys} for r in rows]
    ov = {"trading_date": pl.Date, "symbol": pl.String, "exit_ns": pl.Int64,
          "outcome": pl.String, "skip_reason": pl.String, "points": pl.Float64,
          "R": pl.Float64, "mfe": pl.Float64, "mae": pl.Float64,
          "hold_s": pl.Float64, "exit_price": pl.Float64}
    for fr in FRICTIONS:
        k = str(fr).replace(".", "p")
        ov[f"net_{k}"] = pl.Float64
        ov[f"netR_{k}"] = pl.Float64
    return pl.DataFrame(full, strict=False,
                        schema_overrides={k: v for k, v in ov.items() if k in keys})


def accepted(trades: pl.DataFrame) -> pl.DataFrame:
    return trades if trades.height == 0 else trades.filter(pl.col("status") == "ACCEPTED")


# ------------------------------------------------------------- strategy ----
def run_strategy(df: pl.DataFrame, tag: str, score: np.ndarray, direction: np.ndarray,
                 tau: float, usable: np.ndarray) -> pl.DataFrame:
    """One position at a time, plus a one-interval cooldown after each exit."""
    C = _cols(df, tag)
    dates = C["date"]
    rows: list[dict] = []
    busy_until = -1          # exit of the open position
    ready_at = -1            # cooldown barrier
    cur_day = None
    for i in range(df.height):
        if dates[i] != cur_day:
            cur_day, busy_until, ready_at = dates[i], -1, -1
        if not usable[i] or score[i] < tau:
            continue
        d = int(direction[i])
        rec = _base(C, i, d, score[i])
        if C["ent"][i] <= 0:
            rec.update(status="SKIPPED", skip_reason="NO_ENTRY_PRINT")
            rows.append(rec); continue
        if C["ts"][i] < busy_until:
            rec.update(status="SKIPPED", skip_reason="SKIPPED_OVERLAP")
            rows.append(rec); continue
        if C["ts"][i] < ready_at:
            rec.update(status="SKIPPED", skip_reason="COOLDOWN")
            rows.append(rec); continue
        rec.update(_pick(C, i, d))
        _with_frictions(rec)
        rec.update(status="ACCEPTED", skip_reason=None)
        busy_until = rec["exit_ns"]
        ready_at = rec["exit_ns"] + COOLDOWN_NS
        rows.append(rec)
    return _frame(rows)


# --------------------------------------------- C1: matched-random control ----
def matched_controls(trades: pl.DataFrame, df: pl.DataFrame, tag: str,
                     usable: np.ndarray, k: int = CONTROLS_PER_TRADE,
                     seed: int = CONTROL_SEED) -> pl.DataFrame:
    """Same day, same 30-min bucket, same direction, matched R, same execution.
    Controls are independent entries: the one-position and cooldown rules
    deliberately do not apply to them."""
    acc = accepted(trades)
    if acc.height == 0:
        return pl.DataFrame()
    C = _cols(df, tag)
    rng = np.random.default_rng(seed)
    dates, bucket = C["date"], (C["sec"] // BUCKET_S).astype(np.int64)
    ok = usable & (C["ent"] > 0)
    pool: dict[tuple, list] = {}
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


# ----------------------------------------------- C2: opposite direction ----
def opposite_direction(trades: pl.DataFrame, df: pl.DataFrame, tag: str) -> pl.DataFrame:
    """Same signal timestamps, direction flipped, everything else identical."""
    acc = accepted(trades)
    if acc.height == 0:
        return pl.DataFrame()
    C = _cols(df, tag)
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
