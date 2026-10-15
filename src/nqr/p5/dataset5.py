"""Phase-5 larger-R state dataset: one row per 60-second decision.

Reuses the FROZEN Phase-4 causal state (`nqr.p4.features4`, 55 features) without
modification.  The only things that change are the decision clock (5 s -> 60 s),
the risk scale (0.5x ATR1m -> 2.0 / 3.0 / 4.0 x ATR1m), the maximum hold
(30 min -> 60 min) and the executable timeout rule.

Every row carries the LONG and SHORT first-passage outcome for all three R
scales, resolved on the raw chronological trade tape.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import polars as pl

from nqr import paths
from nqr.backtest.engine import find_entry
from nqr.p4 import features4 as F4          # frozen upstream, read-only
from nqr.p5 import holdout5 as H5
from nqr.p5.labels5 import excursions_p5, resolve_p5

NS = F4.NS
LATENCY_NS = 250 * 1_000_000                # identical to Phases 1-4
MAX_WAIT_NS = 60_000 * 1_000_000
DECISION_STEP_S = 60                        # PHASE5_SPEC S7
MAX_HOLD_S = 3600                           # PHASE5_SPEC S8
HARD_EXIT_ET = "16:00"
FRICTIONS = (0.0, 0.5, 1.0, 2.0)
PRIMARY_FRICTION = 1.0

# PHASE5_SPEC S6 -- volatility-normalised R on the frozen ATR14(completed 1-min)
# basis, the same unit Phases 2/3/4 used.  Rails are absurdity rails only.
R_MULTS = {"r2p0": 2.0, "r3p0": 3.0, "r4p0": 4.0}
R_FLOOR, R_CAP = 5.0, 200.0

OUT_DIR = paths.PROJECT_ROOT / "strategies" / "larger_r" / "features"
_KIND = {"TP": 1, "SL": -1, "TIMEOUT": 0, "NO_DATA": -9}

LABEL_SUFFIX = ("outcome", "points", "mfe", "mae", "hold_s", "exit_ns")


def r_points(atr1m: np.ndarray, mult: float) -> np.ndarray:
    return np.clip(mult * atr1m, R_FLOOR, R_CAP)


def label_cols() -> list[str]:
    out = []
    for tag in R_MULTS:
        out.append(f"{tag}_R")
        for side in ("long", "short"):
            out += [f"{tag}_{side}_{s}" for s in LABEL_SUFFIX]
        out.append(f"{tag}_y")
    return out


def decision_indices(g: dict, d: dt.date) -> np.ndarray:
    """Grid indices on the fixed 60-second clock inside 09:30-11:30 ET.

    Decision timestamp of grid index i is (sec0 + i + 1), so the clock is
    anchored exactly on the session open and every input second has closed.
    """
    t0 = F4.et_sec(d, F4.SESSION_START_ET)
    t1 = F4.et_sec(d, F4.SESSION_END_ET)
    dec = np.arange(t0, t1, DECISION_STEP_S, dtype=np.int64)
    idx = dec - g["sec0"] - 1
    return idx[(idx >= 0) & (idx < g["n"])]


def build_day(day: pl.DataFrame, d: dt.date, pdh: float, pdl: float) -> pl.DataFrame | None:
    """One trading day -> 60-second decision rows, three R scales, both directions."""
    b0, b1 = F4.et_sec(d, F4.BAND_START_ET), F4.et_sec(d, F4.BAND_END_ET)
    g = F4.build_grid(day, b0, b1)
    if g is None:
        return None
    S = F4.build_state_matrix(g, d, pdh, pdl)
    if S is None:
        return None
    idx = decision_indices(g, d)
    if idx.size == 0 or int(idx[0]) < g["first_traded"] + F4.MAX_LOOKBACK_S:
        return None

    ts, px = g["ts"], g["px_t"]
    dec_ns = (g["sec0"] + idx + 1).astype(np.int64) * NS
    atr = S["atr"][idx]
    hard_ns = F4.et_sec(d, HARD_EXIT_ET) * NS
    sess0 = F4.et_sec(d, F4.SESSION_START_ET)
    n = idx.size

    entry_ns = np.zeros(n, dtype=np.int64)
    entry_px = np.full(n, np.nan)
    eidx_arr = np.full(n, -1, dtype=np.int64)
    for i in range(n):
        ent = find_entry(ts, px, int(dec_ns[i]) + LATENCY_NS, MAX_WAIT_NS)
        if ent is None:
            continue
        eidx_arr[i], entry_ns[i], entry_px[i] = ent[0], ent[1], ent[2]

    dec_sec = (dec_ns // NS).astype(np.int64)
    out: dict = {
        "trading_date": pl.Series("trading_date", [d] * n, dtype=pl.Date),
        "symbol": pl.Series("symbol", [day["symbol"][0]] * n, dtype=pl.String),
        "decision_ts_ns": dec_ns,
        "sec_since_open": (dec_sec - sess0).astype(np.int32),
        "bucket15": ((dec_sec - sess0) // 900).astype(np.int8),
        "in_primary": np.ones(n, dtype=bool),
        "atr1m": atr.astype(np.float32),
        "entry_ns": entry_ns,
        "entry_price": entry_px.astype(np.float32),
    }

    for tag, mult in R_MULTS.items():
        R = r_points(atr, mult)
        lab = {f"{side}_{s}": np.full(n, np.nan) for side in ("long", "short")
               for s in ("points", "mfe", "mae", "hold_s")}
        o = {side: np.full(n, -9, dtype=np.int8) for side in ("long", "short")}
        x = {side: np.zeros(n, dtype=np.int64) for side in ("long", "short")}
        for i in range(n):
            if eidx_arr[i] < 0 or not np.isfinite(R[i]):
                continue
            ei, ets, epx = int(eidx_arr[i]), int(entry_ns[i]), float(entry_px[i])
            end_ns = min(hard_ns, ets + MAX_HOLD_S * NS)
            for sign, side in ((1, "long"), (-1, "short")):
                f = resolve_p5(ts, px, ei, end_ns, sign, epx + sign * R[i], epx - sign * R[i])
                mfe, mae = excursions_p5(ts, px, ei, f.ts_ns, sign, epx)
                lab[f"{side}_points"][i] = (f.price - epx) * sign
                lab[f"{side}_mfe"][i] = mfe
                lab[f"{side}_mae"][i] = mae
                lab[f"{side}_hold_s"][i] = (f.ts_ns - ets) / NS
                o[side][i] = _KIND[f.kind]
                x[side][i] = f.ts_ns
        out[f"{tag}_R"] = R.astype(np.float32)
        for side in ("long", "short"):
            out[f"{tag}_{side}_outcome"] = o[side]
            out[f"{tag}_{side}_exit_ns"] = x[side]
            for s in ("points", "mfe", "mae", "hold_s"):
                out[f"{tag}_{side}_{s}"] = lab[f"{side}_{s}"].astype(np.float32)
        # PHASE5_SPEC S10: y = 1 iff the LONG bracket ends gross-positive
        out[f"{tag}_y"] = (lab["long_points"] > 0).astype(np.int8)

    X = S["X"][idx]
    for j, nm in enumerate(F4.FEATURE_NAMES):
        out[nm] = X[:, j].astype(np.float32)
    return pl.DataFrame(out)


def out_dir(split: str) -> Path:
    return OUT_DIR / f"split={split}"


def build_month(ym: str, split: str, levels: dict, roll: set, ticks_loader) -> dict:
    s, e = H5.SPLITS[split]
    m = ticks_loader(ym)
    if m.height == 0:
        return {"ym": ym, "days": 0, "rows": 0}
    frames = []
    for d in m["trading_date"].unique().sort().to_list():
        if not (s <= d <= e) or d in roll or d not in levels:
            continue
        H5.assert_date_allowed(d, "decision date")
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


def load_split(split: str, columns: list[str] | None = None) -> pl.DataFrame:
    files = sorted(out_dir(split).glob("ym=*/part.parquet"))
    if not files:
        return pl.DataFrame()
    return pl.read_parquet(files, columns=columns).sort(["trading_date", "decision_ts_ns"])


def feature_matrix(df: pl.DataFrame) -> np.ndarray:
    return df.select(F4.FEATURE_NAMES).to_numpy().astype(np.float64)


def usable_mask(df: pl.DataFrame, tag: str) -> np.ndarray:
    ok = np.isfinite(feature_matrix(df)).all(axis=1)
    ok &= df["entry_ns"].to_numpy() > 0
    ok &= np.isfinite(df[f"{tag}_R"].to_numpy())
    ok &= df[f"{tag}_long_outcome"].to_numpy() != -9
    ok &= df[f"{tag}_short_outcome"].to_numpy() != -9
    return ok
