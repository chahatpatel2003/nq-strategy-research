"""Phase-4 causal state dataset: one row per decision timestamp.

Each row carries the 55 registered causal features observed at the decision
timestamp, plus the realistically-executed LONG and SHORT 1R/1R first-passage
outcomes of a hypothetical trade opened at that timestamp.  Features are
strictly trailing; outcomes are strictly forward.  Nothing crosses.

The label engine is the frozen Phase-1/3 machinery (`find_entry`,
`resolve_fast`, `excursions_fast`) used with the Phase-3 entry convention, so a
Phase-4 trade and a Phase-3 trade opened at the same instant would fill
identically.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import polars as pl

from nqr import paths
from nqr.backtest.engine import find_entry
from nqr.p3.fastpass import excursions_fast, resolve_fast
from nqr.p4 import features4 as F4
from nqr.p4 import holdout4 as H4

NS = F4.NS
LATENCY_NS = 250 * 1_000_000        # identical to Phases 1, 2 and 3
MAX_WAIT_NS = 60_000 * 1_000_000
MAX_HOLD_S = 1800                   # 30 minutes
HARD_EXIT_ET = "16:00"
FRICTIONS = (0.0, 0.5, 1.0, 2.0)
PRIMARY_FRICTION = 1.0

OUT_DIR = paths.PROJECT_ROOT / "strategies" / "state_discovery" / "features"
_KIND = {"TP": 1, "SL": -1, "TIMEOUT": 0, "NO_DATA": -9}

META_COLS = ["trading_date", "symbol", "decision_ts_ns", "sec_since_open",
             "et_minute", "in_primary", "r_points", "entry_ns", "entry_price"]
LABEL_COLS = ([f"long_{c}" for c in ("outcome", "points", "mfe", "mae", "hold_s", "exit_ns")]
              + [f"short_{c}" for c in ("outcome", "points", "mfe", "mae", "hold_s", "exit_ns")]
              + ["y"])


def build_day(day: pl.DataFrame, d: dt.date, pdh: float, pdl: float,
              end_et: str = F4.DIAG_END_ET) -> pl.DataFrame | None:
    """One trading day -> decision rows with features and both-direction labels."""
    b0, b1 = F4.et_sec(d, F4.BAND_START_ET), F4.et_sec(d, F4.BAND_END_ET)
    g = F4.build_grid(day, b0, b1)
    if g is None:
        return None
    S = F4.build_state_matrix(g, d, pdh, pdl)
    if S is None:
        return None
    idx = F4.decision_indices(g, d, F4.SESSION_START_ET, end_et)
    if idx.size == 0:
        return None
    # every decision must sit far enough past the first print that no window
    # reaches into the constant-filled head of the grid
    if int(idx[0]) < g["first_traded"] + F4.MAX_LOOKBACK_S:
        return None

    ts, px = g["ts"], g["px_t"]
    dec_ns = F4.decision_ts_ns(g, idx)
    r_all = S["r_points"]
    hard_ns = F4.et_sec(d, HARD_EXIT_ET) * NS
    sess0 = F4.et_sec(d, F4.SESSION_START_ET)
    sess1 = F4.et_sec(d, F4.SESSION_END_ET)

    n = idx.size
    entry_ns = np.zeros(n, dtype=np.int64)
    entry_px = np.full(n, np.nan)
    lab = {k: np.full(n, np.nan) for k in
           ("l_pts", "l_mfe", "l_mae", "l_hold", "s_pts", "s_mfe", "s_mae", "s_hold")}
    l_out = np.full(n, -9, dtype=np.int8); s_out = np.full(n, -9, dtype=np.int8)
    l_exit = np.zeros(n, dtype=np.int64); s_exit = np.zeros(n, dtype=np.int64)

    for i in range(n):
        gi = int(idx[i])
        r = float(r_all[gi])
        if not np.isfinite(r):
            continue
        ent = find_entry(ts, px, int(dec_ns[i]) + LATENCY_NS, MAX_WAIT_NS)
        if ent is None:
            continue
        eidx, ets, epx = ent
        entry_ns[i] = ets
        entry_px[i] = epx
        end_ns = min(hard_ns, ets + MAX_HOLD_S * NS)
        for sign, pre, oarr, earr in ((1, "l_", l_out, l_exit), (-1, "s_", s_out, s_exit)):
            f = resolve_fast(ts, px, eidx, end_ns, sign, epx + sign * r, epx - sign * r)
            mfe, mae = excursions_fast(ts, px, eidx, f.ts_ns, sign, epx)
            lab[pre + "pts"][i] = (f.price - epx) * sign
            lab[pre + "mfe"][i] = mfe
            lab[pre + "mae"][i] = mae
            lab[pre + "hold"][i] = (f.ts_ns - ets) / NS
            oarr[i] = _KIND[f.kind]
            earr[i] = f.ts_ns

    dec_sec = (dec_ns // NS).astype(np.int64)
    out = {
        "trading_date": pl.Series("trading_date", [d] * n, dtype=pl.Date),
        "symbol": pl.Series("symbol", [day["symbol"][0]] * n, dtype=pl.String),
        "decision_ts_ns": dec_ns,
        "sec_since_open": (dec_sec - sess0).astype(np.int32),
        "et_minute": ((dec_sec - sess0) // 60 + 570).astype(np.int32),   # 09:30 == 570
        "in_primary": (dec_sec < sess1),
        "r_points": r_all[idx].astype(np.float32),
        "entry_ns": entry_ns,
        "entry_price": entry_px.astype(np.float32),
        "long_outcome": l_out, "long_points": lab["l_pts"].astype(np.float32),
        "long_mfe": lab["l_mfe"].astype(np.float32), "long_mae": lab["l_mae"].astype(np.float32),
        "long_hold_s": lab["l_hold"].astype(np.float32), "long_exit_ns": l_exit,
        "short_outcome": s_out, "short_points": lab["s_pts"].astype(np.float32),
        "short_mfe": lab["s_mfe"].astype(np.float32), "short_mae": lab["s_mae"].astype(np.float32),
        "short_hold_s": lab["s_hold"].astype(np.float32), "short_exit_ns": s_exit,
        # PREREG_ADDENDUM A6: y = 1 iff the LONG bracket ends gross-positive
        "y": (lab["l_pts"] > 0).astype(np.int8),
    }
    X = S["X"][idx]
    for j, nm in enumerate(F4.FEATURE_NAMES):
        out[nm] = X[:, j].astype(np.float32)
    return pl.DataFrame(out)


def out_dir(split: str) -> Path:
    return OUT_DIR / f"split={split}"


def build_month(ym: str, split: str, levels: dict, roll: set, ticks_loader) -> dict:
    """Build and write one month.  Returns a small provenance record."""
    s, e = H4.SPLITS[split]
    m = ticks_loader(ym)
    if m.height == 0:
        return {"ym": ym, "days": 0, "rows": 0}
    frames = []
    for d in m["trading_date"].unique().sort().to_list():
        if not (s <= d <= e) or d in roll or d not in levels:
            continue
        H4.assert_date_allowed(d, "decision date")
        pdh, pdl = levels[d]
        df = build_day(m.filter(pl.col("trading_date") == d), d, pdh, pdl)
        if df is not None:
            frames.append(df)
    if not frames:
        return {"ym": ym, "days": 0, "rows": 0}
    all_df = pl.concat(frames)
    dd = out_dir(split) / f"ym={ym}"
    dd.mkdir(parents=True, exist_ok=True)
    all_df.write_parquet(dd / "part.parquet", compression="zstd")
    return {"ym": ym, "days": len(frames), "rows": all_df.height}


def load_split(split: str, primary_only: bool = True,
               columns: list[str] | None = None) -> pl.DataFrame:
    d = out_dir(split)
    files = sorted(d.glob("ym=*/part.parquet"))
    if not files:
        return pl.DataFrame()
    df = pl.read_parquet(files, columns=columns)
    if primary_only:
        df = df.filter(pl.col("in_primary"))
    return df.sort(["trading_date", "decision_ts_ns"])


def feature_matrix(df: pl.DataFrame) -> np.ndarray:
    return df.select(F4.FEATURE_NAMES).to_numpy().astype(np.float64)


def finite_mask(df: pl.DataFrame) -> np.ndarray:
    X = feature_matrix(df)
    ok = np.isfinite(X).all(axis=1)
    ok &= df["entry_ns"].to_numpy() > 0
    ok &= np.isfinite(df["r_points"].to_numpy())
    ok &= df["long_outcome"].to_numpy() != -9
    ok &= df["short_outcome"].to_numpy() != -9
    return ok
