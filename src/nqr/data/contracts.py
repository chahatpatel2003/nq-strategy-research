"""Front-contract selection and roll calendar.

Rule (frozen): for Globex trading day D the front contract is the outright NQ
symbol with the highest traded volume on the *previous* trading day D-1.
This is strictly causal - the choice for day D uses only data that finished
before day D began.

Spread symbols (containing '-') are never eligible: they are calendar spreads,
not outright prices.

No back-adjustment is applied.  Each trading day uses one and only one
contract, and every level for that day is computed from that same contract's
own price history, so no cross-contract price jump can enter a comparison.

A trading day where F(D) != F(D-1) (the roll day) is flagged ``is_roll_day``
and excluded from signal generation, because the newly-front contract's
immediately preceding sessions were thin.
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import polars as pl

from nqr import paths

OUTRIGHT_RE = re.compile(r"^NQ[FGHJKMNQUVXZ]\d{1,2}$")
MONTH_CODE = {"F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6,
              "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12}


def is_outright(sym: str) -> bool:
    return bool(OUTRIGHT_RE.match(sym))


def expiry_key(sym: str, ref_year: int) -> tuple[int, int]:
    """(year, month) of a CME symbol like 'NQH1' / 'NQH21' given a reference year."""
    body = sym[2:]
    mon = MONTH_CODE[body[0]]
    ydig = body[1:]
    if len(ydig) == 1:
        decade = (ref_year // 10) * 10
        yr = decade + int(ydig)
        if yr < ref_year - 1:
            yr += 10
    else:
        yr = 2000 + int(ydig)
    return yr, mon


def build_front_map(daily_volume: pl.DataFrame) -> pl.DataFrame:
    """daily_volume: trading_date, symbol, volume, n_trades -> front-contract table."""
    df = daily_volume.with_columns(pl.col("trading_date").cast(pl.Date)).filter(
        pl.col("symbol").map_elements(is_outright, return_dtype=pl.Boolean)
    )
    # winner of each trading day by volume; deterministic tie-break on symbol
    winners = (
        df.sort(["trading_date", "volume", "symbol"], descending=[False, True, False])
          .group_by("trading_date", maintain_order=True)
          .first()
          .select(["trading_date", "symbol", "volume", "n_trades"])
          .rename({"symbol": "vol_leader", "volume": "leader_volume",
                   "n_trades": "leader_trades"})
          .sort("trading_date")
    )
    # front contract for day D = volume leader of day D-1 (previous *trading* day)
    winners = winners.with_columns(
        pl.col("vol_leader").shift(1).alias("front_symbol"),
        pl.col("trading_date").shift(1).alias("basis_date"),
    )
    # first day has no basis -> fall back to its own leader
    winners = winners.with_columns(
        pl.when(pl.col("front_symbol").is_null()).then(pl.col("vol_leader"))
          .otherwise(pl.col("front_symbol")).alias("front_symbol")
    )
    winners = winners.with_columns(
        (pl.col("front_symbol") != pl.col("front_symbol").shift(1)).fill_null(True).alias("is_roll_day")
    )
    return winners


def roll_dates(front_map: pl.DataFrame) -> pl.DataFrame:
    return front_map.filter(pl.col("is_roll_day")).select(
        ["trading_date", "front_symbol", "vol_leader", "basis_date"]
    )


def load_front_map(results_dir: Path | None = None) -> pl.DataFrame:
    results_dir = results_dir or paths.RESULTS_DIR
    return pl.read_parquet(results_dir / "front_map.parquet")
