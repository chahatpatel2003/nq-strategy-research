"""Phase-7 decision dataset: one row per 5-second decision.

Each row carries the 40 registered causal book-state features observed at the
decision timestamp, plus the realistically-executed LONG and SHORT 1R/1R
first-passage outcomes at both fixed R scales.

Execution and first passage are the frozen Phase-1/3/5 machinery:
`find_entry` (first print at or after t + 250 ms) and `resolve_p5` (touch-then-
market stop, trade-through-by-a-tick target, executable timeout).  Phase 7
changes the information used to decide, not how a decision is executed.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import polars as pl

from nqr import paths
from nqr.backtest.engine import find_entry
from nqr.p2 import features as FT
from nqr.p2.cache2 import load_month_ticks
from nqr.p4 import features4 as F4
from nqr.p5.labels5 import excursions_p5, resolve_p5
from nqr.p7 import cache7
from nqr.p7 import features7 as F7
from nqr.p7 import holdout7 as H7

NS = F7.NS
TICK = F7.TICK
LATENCY_NS = 250 * 1_000_000        # identical to Phases 1-6
MAX_WAIT_NS = 60_000 * 1_000_000
MAX_HOLD_S = 900                    # 15 minutes  (SEARCH_BUDGET S2)
HARD_EXIT_ET = "16:00"
FRICTIONS = (0.0, 0.5, 1.0, 2.0)
PRIMARY_FRICTION = 1.0
R_POINTS = {"R15": 15.0, "R25": 25.0}

OUT_DIR = paths.PROJECT_ROOT / "strategies" / "orderbook_state" / "features"
_KIND = {"TP": 1, "SL": -1, "TIMEOUT": 0, "NO_DATA": -9}
LABEL_SUFFIX = ("outcome", "points", "mfe", "mae", "hold_s", "exit_ns")


def label_cols() -> list[str]:
    out = []
    for tag in R_POINTS:
        for side in ("long", "short"):
            out += [f"{tag}_{side}_{s}" for s in LABEL_SUFFIX]
        out.append(f"{tag}_y")
    return out


def _atr_for_day(day_ticks: pl.DataFrame, d: dt.date, sec0: int, n: int):
    """ATR14 of completed 1-minute bars and its trailing within-day percentile,
    on the book grid's second axis.  Reuses the frozen Phase-2/4 machinery."""
    tb0, tb1 = F7.et_sec(d, F7.TRADE_BAND_START_ET), F7.et_sec(d, F7.TRADE_BAND_END_ET)
    tg = F4.build_grid(day_ticks, tb0, tb1)
    if tg is None:
        return None, None, None
    atr_t, atr_min = F4.causal_atr(tg, F7.ATR_LOOKBACK, F7.ATR_FLOOR)
    minute = ((np.arange(tg["n"]) + tg["sec0"]) // 60)
    rank_t = F4._atr_pct_rank(minute, atr_min, tg["n"])
    off = sec0 - tg["sec0"]
    if off < 0 or off + n > tg["n"]:
        return None, None, None
    return atr_t[off:off + n], rank_t[off:off + n], tg


def build_day(day_book: pl.DataFrame, day_ticks: pl.DataFrame, d: dt.date,
              symbol: str) -> pl.DataFrame | None:
    """One trading day -> 5-second decision rows with 40 features and both labels."""
    sec0, sec1 = F7.et_sec(d, F7.BOOK_BAND_START_ET), F7.et_sec(d, F7.BOOK_BAND_END_ET)
    g = F7.build_book_grid(day_book, sec0, sec1)
    if g is None:
        return None
    atr, rank, tg = _atr_for_day(day_ticks, d, sec0, g["n"])
    if atr is None or not np.isfinite(atr).any():
        return None
    S = F7.build_state_matrix(g, d, atr, rank)
    if S is None:
        return None
    idx = F7.decision_indices(g, d)
    if idx.size == 0 or int(idx[0]) < g["first_present"] + F7.MAX_LOOKBACK_S:
        return None

    ts, px = tg["ts"], tg["px_t"]
    dec_ns = F7.decision_ts_ns(g, idx)
    hard_ns = F7.et_sec(d, HARD_EXIT_ET) * NS
    sess0 = F7.et_sec(d, F7.SESSION_START_ET)
    n = idx.size

    entry_ns = np.zeros(n, dtype=np.int64)
    entry_px = np.full(n, np.nan)
    eidx = np.full(n, -1, dtype=np.int64)
    for i in range(n):
        ent = find_entry(ts, px, int(dec_ns[i]) + LATENCY_NS, MAX_WAIT_NS)
        if ent is not None:
            eidx[i], entry_ns[i], entry_px[i] = ent

    dec_sec = (dec_ns // NS).astype(np.int64)
    out: dict = {
        "trading_date": pl.Series("trading_date", [d] * n, dtype=pl.Date),
        "symbol": pl.Series("symbol", [symbol] * n, dtype=pl.String),
        "decision_ts_ns": dec_ns,
        "sec_since_open": (dec_sec - sess0).astype(np.int32),
        "bucket15m": ((dec_sec - sess0) // 900).astype(np.int8),
        "entry_ns": entry_ns,
        "entry_price": entry_px.astype(np.float32),
        "book_present": g["present"][idx],
    }
    for tag, R in R_POINTS.items():
        lab = {f"{s}_{k}": np.full(n, np.nan) for s in ("long", "short")
               for k in ("points", "mfe", "mae", "hold_s")}
        o = {s: np.full(n, -9, dtype=np.int8) for s in ("long", "short")}
        x = {s: np.zeros(n, dtype=np.int64) for s in ("long", "short")}
        for i in range(n):
            if eidx[i] < 0:
                continue
            ei, ets, epx = int(eidx[i]), int(entry_ns[i]), float(entry_px[i])
            end_ns = min(hard_ns, ets + MAX_HOLD_S * NS)
            for sign, side in ((1, "long"), (-1, "short")):
                f = resolve_p5(ts, px, ei, end_ns, sign, epx + sign * R, epx - sign * R)
                mfe, mae = excursions_p5(ts, px, ei, f.ts_ns, sign, epx)
                lab[f"{side}_points"][i] = (f.price - epx) * sign
                lab[f"{side}_mfe"][i] = mfe
                lab[f"{side}_mae"][i] = mae
                lab[f"{side}_hold_s"][i] = (f.ts_ns - ets) / NS
                o[side][i] = _KIND[f.kind]
                x[side][i] = f.ts_ns
        for side in ("long", "short"):
            out[f"{tag}_{side}_outcome"] = o[side]
            out[f"{tag}_{side}_exit_ns"] = x[side]
            for k in ("points", "mfe", "mae", "hold_s"):
                out[f"{tag}_{side}_{k}"] = lab[f"{side}_{k}"].astype(np.float32)
        # PHASE7_SPEC S8: UP iff the LONG 1R bracket ends gross-positive.
        # TP -> UP, SL -> DOWN, TIMEOUT -> sign of the realised move.  Nothing dropped.
        out[f"{tag}_y"] = (lab["long_points"] > 0).astype(np.int8)

    X = S["X"][idx]
    for j, nm in enumerate(F7.FEATURE_NAMES):
        out[nm] = X[:, j].astype(np.float32)
    return pl.DataFrame(out)


def out_dir(split: str) -> Path:
    return OUT_DIR / f"split={split}"


def build_month(ym: str, split: str, roll: set) -> dict:
    s, e = H7.SPLITS[split]
    bk = cache7.load_month(ym)
    if bk.height == 0:
        return {"ym": ym, "days": 0, "rows": 0}
    tk = load_month_ticks(ym)
    frames = []
    for d in bk["trading_date"].unique().sort().to_list():
        if not (s <= d <= e) or d in roll:
            continue
        H7.assert_date_allowed(d, "decision date")
        db = bk.filter(pl.col("trading_date") == d)
        dt_ = tk.filter(pl.col("trading_date") == d)
        if db.height < 600 or dt_.height < 500:
            continue
        f = build_day(db, dt_, d, db["symbol"][0])
        if f is not None:
            frames.append(f)
    if not frames:
        return {"ym": ym, "days": 0, "rows": 0}
    all_df = pl.concat(frames)
    dd = out_dir(split) / f"ym={ym}"
    dd.mkdir(parents=True, exist_ok=True)
    all_df.write_parquet(dd / "part.parquet", compression="zstd")
    return {"ym": ym, "days": len(frames), "rows": all_df.height}


def load_split(split: str, columns: list[str] | None = None) -> pl.DataFrame:
    files = sorted(out_dir(split).glob("ym=*/part.parquet"))
    if not files:
        return pl.DataFrame()
    return pl.read_parquet(files, columns=columns).sort(["trading_date", "decision_ts_ns"])


def feature_matrix(df: pl.DataFrame, names: list[str] | None = None) -> np.ndarray:
    return df.select(names or F7.FEATURE_NAMES).to_numpy().astype(np.float64)


def usable_mask(df: pl.DataFrame, tag: str) -> np.ndarray:
    ok = np.isfinite(feature_matrix(df)).all(axis=1)
    ok &= df["entry_ns"].to_numpy() > 0
    ok &= df[f"{tag}_long_outcome"].to_numpy() != -9
    ok &= df[f"{tag}_short_outcome"].to_numpy() != -9
    return ok
