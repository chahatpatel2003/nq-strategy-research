"""Prior-session levels, strictly causal.

For Globex trading day D we build *level segments*: (family, price, valid_from,
valid_to).  A level's price is the high/low of the MOST RECENTLY COMPLETED
session of that type, so it steps forward during the day:

  epoch 1  18:00 ET (D-1) -> 03:00 ET (D)   ASIA(D-1) EU(D-1) US(D-1) PD(D-1)
  epoch 2  03:00 ET (D)   -> 09:30 ET (D)   ASIA(D)   EU(D-1) US(D-1) PD(D-1)
  epoch 3  09:30 ET (D)   -> 16:00 ET (D)   ASIA(D)   EU(D)   US(D-1) PD(D-1)
  epoch 4  16:00 ET (D)   -> 17:00 ET (D)   ASIA(D)   EU(D)   US(D)   PD(D-1)

Nothing in this file ever looks at a bar that closes at or after the boundary
at which the level becomes usable.

ATR20 (daily) is the 20-day mean of (session high - session low) over the 20
most recent COMPLETED trading days.  Using the day range rather than the
classic true range makes it immune to the price jump at a contract roll.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import numpy as np
import polars as pl

from nqr.sessions.calendar import (SESSION_DEFS, day_bounds_utc, sessions_for_day,
                                   to_utc, DAY_END_ET)

FAMILIES = ("PDH", "PDL", "US_H", "US_L", "EU_H", "EU_L", "ASIA_H", "ASIA_L")
PRIORITY = {f: i for i, f in enumerate(FAMILIES)}
NS = 1_000_000_000


def _ns(ts: dt.datetime) -> int:
    return int(ts.timestamp() * NS)


def session_extremes(bars: pl.DataFrame) -> pl.DataFrame:
    """Per (trading_date, session) high/low/bar-count from 2-minute bars."""
    return (
        bars.group_by(["trading_date", "session"])
            .agg(pl.col("high").max().alias("hi"),
                 pl.col("low").min().alias("lo"),
                 pl.len().alias("n_bars"))
            .sort(["trading_date", "session"])
    )


def day_extremes(bars: pl.DataFrame) -> pl.DataFrame:
    return (
        bars.group_by("trading_date")
            .agg(pl.col("high").max().alias("hi"),
                 pl.col("low").min().alias("lo"),
                 pl.len().alias("n_bars"))
            .sort("trading_date")
    )


def daily_atr(day_ext: pl.DataFrame, lookback: int = 20) -> pl.DataFrame:
    """ATR20 usable ON day D = mean day-range of the 20 days strictly before D."""
    d = day_ext.with_columns((pl.col("hi") - pl.col("lo")).alias("day_range"))
    d = d.with_columns(
        pl.col("day_range").shift(1).rolling_mean(window_size=lookback, min_samples=lookback)
        .alias("atr20_prev")
    )
    return d.select(["trading_date", "day_range", "atr20_prev"])


@dataclass(frozen=True)
class LevelSegment:
    trading_date: dt.date
    family: str
    price: float
    valid_from_ns: int
    valid_to_ns: int
    source_date: dt.date
    tolerance: float


def _epochs(d: dt.date) -> list[tuple[int, int, str]]:
    """(start_ns, end_ns, epoch_tag) for the four intra-day level epochs."""
    ws = {w.name: w for w in sessions_for_day(d)}
    day_s, day_e = day_bounds_utc(d)
    b = [_ns(day_s), _ns(ws["ASIA"].end_utc), _ns(ws["EU"].end_utc),
         _ns(ws["US"].end_utc), _ns(day_e)]
    return [(b[0], b[1], "E1"), (b[1], b[2], "E2"), (b[2], b[3], "E3"), (b[3], b[4], "E4")]


# which source session-date each family reads from, per epoch index
_EPOCH_SOURCE = {
    0: {"ASIA": -1, "EU": -1, "US": -1},
    1: {"ASIA": 0, "EU": -1, "US": -1},
    2: {"ASIA": 0, "EU": 0, "US": -1},
    3: {"ASIA": 0, "EU": 0, "US": 0},
}
_SESSION_FAMILIES = {"ASIA": ("ASIA_H", "ASIA_L"), "EU": ("EU_H", "EU_L"), "US": ("US_H", "US_L")}


def build_level_segments(trading_dates: list[dt.date], sess_ext: pl.DataFrame,
                         day_ext: pl.DataFrame, atr: pl.DataFrame,
                         *, min_session_bars: int, tol_atr_frac: float,
                         tol_min: float, tol_max: float,
                         dedup_mult: float) -> list[LevelSegment]:
    se = {(r["trading_date"], r["session"]): (r["hi"], r["lo"], r["n_bars"])
          for r in sess_ext.iter_rows(named=True)}
    de = {r["trading_date"]: (r["hi"], r["lo"], r["n_bars"]) for r in day_ext.iter_rows(named=True)}
    at = {r["trading_date"]: r["atr20_prev"] for r in atr.iter_rows(named=True)}
    dates = sorted(trading_dates)
    prev_of = {d: dates[i - 1] for i, d in enumerate(dates) if i > 0}

    out: list[LevelSegment] = []
    for d in dates:
        a = at.get(d)
        if a is None or not np.isfinite(a):
            continue                                   # ATR warm-up: no levels, no signals
        tol = float(min(max(tol_atr_frac * a, tol_min), tol_max))
        pd_ = prev_of.get(d)
        if pd_ is None:
            continue
        raw: list[tuple[str, float, int, int, dt.date]] = []
        for ei, (s_ns, e_ns, _tag) in enumerate(_epochs(d)):
            cand: list[tuple[str, float, dt.date]] = []
            # previous day high/low (always from the previous completed day)
            if pd_ in de and de[pd_][2] >= min_session_bars:
                cand.append(("PDH", de[pd_][0], pd_))
                cand.append(("PDL", de[pd_][1], pd_))
            for sname, off in _EPOCH_SOURCE[ei].items():
                sd = d if off == 0 else pd_
                v = se.get((sd, sname))
                if v is None or v[2] < min_session_bars:
                    continue
                fh, fl = _SESSION_FAMILIES[sname]
                cand.append((fh, v[0], sd))
                cand.append((fl, v[1], sd))
            # dedup by priority: drop a level sitting within dedup_mult*tol of a
            # already-kept higher-priority level
            cand.sort(key=lambda c: PRIORITY[c[0]])
            kept: list[tuple[str, float, dt.date]] = []
            for fam, px, sd in cand:
                if any(abs(px - k[1]) <= dedup_mult * tol for k in kept):
                    continue
                kept.append((fam, px, sd))
            for fam, px, sd in kept:
                raw.append((fam, px, s_ns, e_ns, sd))
        # merge adjacent epochs carrying an identical (family, price, source)
        raw.sort(key=lambda r: (r[0], r[1], r[2]))
        merged: list[tuple[str, float, int, int, dt.date]] = []
        for r in raw:
            if merged and merged[-1][0] == r[0] and merged[-1][1] == r[1] \
               and merged[-1][4] == r[4] and merged[-1][3] == r[2]:
                p = merged[-1]
                merged[-1] = (p[0], p[1], p[2], r[3], p[4])
            else:
                merged.append(r)
        for fam, px, s_ns, e_ns, sd in merged:
            out.append(LevelSegment(d, fam, float(px), s_ns, e_ns, sd, tol))
    return out


def segments_to_frame(segs: list[LevelSegment]) -> pl.DataFrame:
    if not segs:
        return pl.DataFrame(schema={"trading_date": pl.Date, "family": pl.String,
                                    "price": pl.Float64, "valid_from_ns": pl.Int64,
                                    "valid_to_ns": pl.Int64, "source_date": pl.Date,
                                    "tolerance": pl.Float64})
    return pl.DataFrame({
        "trading_date": [s.trading_date for s in segs],
        "family": [s.family for s in segs],
        "price": [s.price for s in segs],
        "valid_from_ns": [s.valid_from_ns for s in segs],
        "valid_to_ns": [s.valid_to_ns for s in segs],
        "source_date": [s.source_date for s in segs],
        "tolerance": [s.tolerance for s in segs],
    })
