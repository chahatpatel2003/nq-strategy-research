"""Phase-7 backtest, matched-random controls and the causality assertions.

Phase 6 closed on a control-causality defect: 44.1 % of the Phase-5 controls
entered BEFORE the signal that gave them their direction.  Phase 7 therefore
asserts control causality as a hard runtime check and FAILS THE RUN on any
violation, rather than reporting a number that a later phase has to retract.
"""
from __future__ import annotations

import numpy as np
import polars as pl

from nqr.p7.dataset7 import FRICTIONS, PRIMARY_FRICTION, R_POINTS

NS = 1_000_000_000
CONTROL_SEED = 20260822
CONTROLS_PER_TRADE = 10
BUCKET_S = 300                       # 5-minute time-of-day bucket
COOLDOWN_S = 5                       # one full decision interval
OUTCOME_NAME = {1: "TP", -1: "SL", 0: "TIMEOUT", -9: "NO_DATA"}


class ControlCausalityViolation(RuntimeError):
    """A control used information that did not exist at its own decision time."""


def _cols(df: pl.DataFrame, tag: str) -> dict:
    g = {
        # .to_numpy() on a Date column yields np.datetime64, which does not compare
        # equal to the datetime.date keys used for matching (Phase-5 bug).
        "date": np.array(df["trading_date"].to_list(), dtype=object),
        "sym": np.array(df["symbol"].to_list(), dtype=object),
        "ts": df["decision_ts_ns"].to_numpy(),
        "sec": df["sec_since_open"].to_numpy(),
        "ent": df["entry_ns"].to_numpy(),
        "epx": df["entry_price"].to_numpy().astype(float),
        "atr": df["atr1m_ticks"].to_numpy().astype(float),
        "spr": df["spread_ticks"].to_numpy().astype(float),
    }
    for side, pre in (("long", "l"), ("short", "s")):
        for k, short in (("outcome", "o"), ("points", "p"), ("mfe", "f"),
                         ("mae", "a"), ("hold_s", "h"), ("exit_ns", "x")):
            v = df[f"{tag}_{side}_{k}"].to_numpy()
            g[pre + short] = v if k in ("outcome", "exit_ns") else v.astype(float)
    return g


def _rec(C: dict, i: int, d: int, R: float, score: float, kind: str) -> dict:
    pre = "l" if d > 0 else "s"
    pts = float(C[pre + "p"][i])
    rec = {"trading_date": C["date"][i], "symbol": C["sym"][i],
           "decision_ts_ns": int(C["ts"][i]), "sec_since_open": int(C["sec"][i]),
           "bucket5m": int(C["sec"][i] // BUCKET_S),
           "direction": d, "side": "LONG" if d > 0 else "SHORT",
           "score": float(score), "book": kind,
           "entry_ns": int(C["ent"][i]), "entry_price": float(C["epx"][i]),
           "r_points": R, "stop": float(C["epx"][i] - d * R),
           "target": float(C["epx"][i] + d * R),
           "atr1m_ticks": float(C["atr"][i]), "spread_ticks": float(C["spr"][i]),
           "outcome": OUTCOME_NAME[int(C[pre + "o"][i])], "points": pts,
           "R": pts / R, "mfe": float(C[pre + "f"][i]), "mae": float(C[pre + "a"][i]),
           "hold_s": float(C[pre + "h"][i]), "exit_ns": int(C[pre + "x"][i]),
           "exit_price": float(C["epx"][i] + d * pts)}
    for fr in FRICTIONS:
        k = str(fr).replace(".", "p")
        rec[f"net_{k}"] = pts - fr
        rec[f"netR_{k}"] = (pts - fr) / R
    return rec


def frame(rows: list[dict]) -> pl.DataFrame:
    if not rows:
        return pl.DataFrame()
    keys: list[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    full = [{k: r.get(k) for k in keys} for r in rows]
    ov = {"trading_date": pl.Date, "symbol": pl.String, "outcome": pl.String,
          "skip_reason": pl.String, "status": pl.String, "exit_ns": pl.Int64,
          "entry_ns": pl.Int64, "decision_ts_ns": pl.Int64, "book": pl.String}
    for c in ("points", "R", "mfe", "mae", "hold_s", "exit_price", "entry_price",
              "atr1m_ticks", "spread_ticks", "score", "r_points", "stop", "target"):
        if c in keys:
            ov[c] = pl.Float64
    for fr in FRICTIONS:
        k = str(fr).replace(".", "p")
        for pre in ("net_", "netR_"):
            if pre + k in keys:
                ov[pre + k] = pl.Float64
    return pl.DataFrame(full, strict=False, schema_overrides=ov)


def accepted(t: pl.DataFrame) -> pl.DataFrame:
    return t if t.height == 0 else t.filter(pl.col("status") == "ACCEPTED")


def pf_r(t: pl.DataFrame, friction: float) -> float:
    """Profit factor in R units -- PF(R).  Always labelled; never the points figure."""
    if t.height == 0:
        return float("nan")
    r = (t["points"].to_numpy().astype(float) - friction) / t["r_points"].to_numpy().astype(float)
    gp, gl = float(r[r > 0].sum()), float(-r[r < 0].sum())
    return gp / gl if gl > 0 else float("inf")


# ------------------------------------------------------------- strategy ----
def run_strategy(df: pl.DataFrame, tag: str, conf: np.ndarray, direction: np.ndarray,
                 tau: float, usable: np.ndarray) -> pl.DataFrame:
    """One position at a time plus a one-interval (5 s) cooldown after each exit."""
    C = _cols(df, tag)
    R = R_POINTS[tag]
    dates = C["date"]
    rows: list[dict] = []
    busy = ready = -1
    cur = None
    for i in range(df.height):
        if dates[i] != cur:
            cur, busy, ready = dates[i], -1, -1
        if not usable[i] or conf[i] < tau:
            continue
        d = int(direction[i])
        base = {"trading_date": C["date"][i], "symbol": C["sym"][i],
                "decision_ts_ns": int(C["ts"][i]), "sec_since_open": int(C["sec"][i]),
                "bucket5m": int(C["sec"][i] // BUCKET_S), "direction": d,
                "side": "LONG" if d > 0 else "SHORT", "score": float(conf[i]),
                "r_points": R}
        if C["ent"][i] <= 0:
            rows.append({**base, "status": "SKIPPED", "skip_reason": "NO_ENTRY_PRINT"})
            continue
        if C["ts"][i] < busy:
            rows.append({**base, "status": "SKIPPED", "skip_reason": "SKIPPED_OVERLAP"})
            continue
        if C["ts"][i] < ready:
            rows.append({**base, "status": "SKIPPED", "skip_reason": "COOLDOWN"})
            continue
        rec = _rec(C, i, d, R, conf[i], "STRATEGY")
        rec.update(status="ACCEPTED", skip_reason=None)
        busy = rec["exit_ns"]
        ready = rec["exit_ns"] + COOLDOWN_S * NS
        rows.append(rec)
    return frame(rows)


# ------------------------------------------------ matched-random controls ----
def _quartile_edges(v: np.ndarray) -> np.ndarray:
    return np.quantile(v[np.isfinite(v)], [0.25, 0.50, 0.75])


def _q(v: np.ndarray, edges: np.ndarray) -> np.ndarray:
    return np.digitize(v, edges).astype(np.int64)


def matched_controls(trades: pl.DataFrame, df: pl.DataFrame, tag: str,
                     usable: np.ndarray, atr_edges: np.ndarray, spr_edges: np.ndarray,
                     mode: str = "cross_day", k: int = CONTROLS_PER_TRADE,
                     seed: int = CONTROL_SEED) -> pl.DataFrame:
    """PHASE7_SPEC S11.  Two strictly causal variants, both preregistered.

    `cross_day`  (PRIMARY) -- a DIFFERENT trading day, the SAME 5-minute
        time-of-day bucket, the same direction, the same R, and the same ATR and
        spread quartile measured **at the control's own timestamp**.  Nothing the
        control uses postdates the control.  The direction is a design parameter
        imported from the strategy trade, and because the control sits on a
        different day it carries no information about that day's future.

    `same_day_forward` (SECONDARY) -- the SAME trading day, decision timestamp at
        or after the strategy signal, same direction / R / ATR quartile / spread
        quartile.  Controls for the day's regime; loses exact time-of-day.

    Same-day BACKWARD sampling -- the Phase-5 construction -- is not offered,
    because assigning a later signal's direction to an earlier minute is exactly
    the defect Phase 6 found.
    """
    acc = accepted(trades)
    if acc.height == 0:
        return pl.DataFrame()
    C = _cols(df, tag)
    R = R_POINTS[tag]
    rng = np.random.default_rng(seed)
    ok = usable & (C["ent"] > 0)
    bucket = (C["sec"] // BUCKET_S).astype(np.int64)
    aq, sq = _q(C["atr"], atr_edges), _q(C["spr"], spr_edges)
    pool: dict[tuple, list] = {}
    for i in np.flatnonzero(ok):
        pool.setdefault((int(bucket[i]), int(aq[i]), int(sq[i])), []).append(i)
    pool = {kk: np.asarray(v) for kk, v in pool.items()}

    ts_of = C["ts"]
    rows: list[dict] = []
    for t in acc.iter_rows(named=True):
        j = int(np.searchsorted(ts_of, t["decision_ts_ns"]))
        if j >= len(ts_of) or ts_of[j] != t["decision_ts_ns"]:
            continue
        key = (t["bucket5m"], int(aq[j]), int(sq[j]))
        cand = pool.get(key)
        if cand is None or cand.size == 0:
            continue
        if mode == "cross_day":
            cand = cand[C["date"][cand] != t["trading_date"]]
        elif mode == "same_day_forward":
            cand = cand[(C["date"][cand] == t["trading_date"]) &
                        (ts_of[cand] >= t["decision_ts_ns"])]
        else:
            raise ValueError(mode)
        if cand.size == 0:
            continue
        take = rng.choice(cand.size, size=min(k, cand.size), replace=False)
        for m in cand[take]:
            rec = _rec(C, int(m), t["direction"], R, 0.0, f"CONTROL_{mode}")
            rec.update(status="ACCEPTED", skip_reason=None,
                       matched_to_ts=t["decision_ts_ns"],
                       matched_to_date=t["trading_date"])
            rows.append(rec)
    out = frame(rows)
    assert_control_causality(out, mode)
    return out


def assert_control_causality(ctrl: pl.DataFrame, mode: str) -> None:
    """Hard runtime check.  Any violation FAILS THE RUN."""
    if ctrl.height == 0:
        return
    dec = ctrl["decision_ts_ns"].to_numpy()
    ent = ctrl["entry_ns"].to_numpy()
    bad_entry = int((ent <= dec).sum())
    if bad_entry:
        raise ControlCausalityViolation(
            f"{bad_entry} control entries are not strictly after their own decision")
    if mode == "same_day_forward":
        sig = ctrl["matched_to_ts"].to_numpy()
        bad = int((dec < sig).sum())
        if bad:
            raise ControlCausalityViolation(
                f"{bad} same-day controls decide BEFORE the signal that gave them "
                "their direction -- this is the Phase-5 defect")
    if mode == "cross_day":
        same = np.array(ctrl["trading_date"].to_list(), dtype=object) == \
               np.array(ctrl["matched_to_date"].to_list(), dtype=object)
        if int(same.sum()):
            raise ControlCausalityViolation(
                f"{int(same.sum())} cross-day controls fall on the signal's own day")


def opposite_direction(trades: pl.DataFrame, df: pl.DataFrame, tag: str) -> pl.DataFrame:
    acc = accepted(trades)
    if acc.height == 0:
        return pl.DataFrame()
    C = _cols(df, tag)
    R = R_POINTS[tag]
    pos = {int(t): i for i, t in enumerate(C["ts"])}
    rows = []
    for t in acc.iter_rows(named=True):
        i = pos.get(t["decision_ts_ns"])
        if i is None:
            continue
        rec = _rec(C, i, -t["direction"], R, t["score"], "OPPOSITE")
        rec.update(status="ACCEPTED", skip_reason=None)
        rows.append(rec)
    return frame(rows)
