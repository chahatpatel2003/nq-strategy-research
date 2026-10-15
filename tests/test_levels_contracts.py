import datetime as dt
import numpy as np
import polars as pl
import pytest

from nqr.data.contracts import build_front_map, is_outright, expiry_key
from nqr.levels.build import build_level_segments, daily_atr, FAMILIES, PRIORITY
from nqr.sessions.calendar import to_utc, day_bounds_utc

NS = 1_000_000_000


def test_outright_vs_spread_symbols():
    for s in ["NQH1", "NQZ4", "NQM24"]:
        assert is_outright(s)
    for s in ["NQH1-NQM1", "NQM1-NQU1", "ESH1", "MNQH1"]:
        assert not is_outright(s)


def test_expiry_key():
    assert expiry_key("NQH1", 2021) == (2021, 3)
    assert expiry_key("NQH2", 2021) == (2022, 3)


def _dv(rows):
    return pl.DataFrame({"trading_date": [r[0] for r in rows],
                         "symbol": [r[1] for r in rows],
                         "volume": [float(r[2]) for r in rows],
                         "n_trades": [int(r[2]) for r in rows]})


def test_front_contract_uses_previous_day_volume_only():
    d = [dt.date(2021, 3, 12), dt.date(2021, 3, 15), dt.date(2021, 3, 16)]
    dv = _dv([(d[0], "NQH1", 900), (d[0], "NQM1", 100),
              (d[1], "NQH1", 100), (d[1], "NQM1", 900),   # volume flips on d1
              (d[2], "NQH1", 50),  (d[2], "NQM1", 950)])
    f = build_front_map(dv).sort("trading_date")
    got = dict(zip(f["trading_date"].to_list(), f["front_symbol"].to_list()))
    # d1 still trades H1 because the decision used d0's volume
    assert got[d[1]] == "NQH1"
    assert got[d[2]] == "NQM1"


def test_roll_day_flag():
    d = [dt.date(2021, 3, 12), dt.date(2021, 3, 15), dt.date(2021, 3, 16), dt.date(2021, 3, 17)]
    dv = _dv([(d[0], "NQH1", 900), (d[1], "NQH1", 100), (d[1], "NQM1", 900),
              (d[2], "NQM1", 950), (d[3], "NQM1", 960)])
    f = build_front_map(dv).sort("trading_date")
    got = dict(zip(f["trading_date"].to_list(), f["is_roll_day"].to_list()))
    assert got[d[2]] is True and got[d[3]] is False


def test_spreads_never_become_the_front_contract():
    d = dt.date(2021, 3, 12)
    dv = _dv([(d, "NQH1-NQM1", 10_000_000), (d, "NQH1", 5)])
    f = build_front_map(dv)
    assert f["front_symbol"].to_list() == ["NQH1"]


# --------------------------------------------------------------- levels ----
def _synthetic(days):
    """Build (sess_ext, day_ext, atr) where day k has an easily predicted range."""
    se, de = [], []
    for k, d in enumerate(days):
        for s, hi, lo in (("ASIA", 100 + k, 90 + k), ("EU", 105 + k, 95 + k),
                          ("US", 110 + k, 85 + k), ("POST", 101 + k, 99 + k)):
            se.append({"trading_date": d, "session": s, "hi": float(hi),
                       "lo": float(lo), "n_bars": 200})
        de.append({"trading_date": d, "hi": float(110 + k), "lo": float(85 + k),
                   "n_bars": 690})
    return pl.DataFrame(se), pl.DataFrame(de)


def test_levels_are_strictly_previous_and_step_at_session_ends():
    days = [dt.date(2023, 5, d) for d in range(1, 30)]
    se, de = _synthetic(days)
    atr = daily_atr(de, lookback=20)
    segs = build_level_segments(days, se, de, atr, min_session_bars=30,
                                tol_atr_frac=0.02, tol_min=1.0, tol_max=20.0,
                                dedup_mult=1.0)
    D = days[25]
    k = days.index(D)
    mine = [s for s in segs if s.trading_date == D]
    assert mine, "day should have levels"
    day_s, day_e = day_bounds_utc(D)
    asia_end = int(to_utc(D, dt.time(3, 0)).timestamp() * NS)
    eu_end = int(to_utc(D, dt.time(9, 30)).timestamp() * NS)

    def at(fam, t):
        v = [s.price for s in mine if s.family == fam and s.valid_from_ns <= t < s.valid_to_ns]
        return v[0] if v else None

    # PDH/PDL always come from the previous day
    assert at("PDH", asia_end + 1) == 110 + (k - 1)
    assert at("PDL", asia_end + 1) == 85 + (k - 1)
    # Asia is yesterday's before 03:00 ET and today's after
    assert at("ASIA_H", asia_end - 1) == 100 + (k - 1)
    assert at("ASIA_H", asia_end + 1) == 100 + k
    # EU steps at 09:30 ET
    assert at("EU_H", eu_end - 1) == 105 + (k - 1)
    assert at("EU_H", eu_end + 1) == 105 + k


def test_no_level_segment_starts_before_its_source_session_ended():
    days = [dt.date(2023, 5, d) for d in range(1, 30)]
    se, de = _synthetic(days)
    atr = daily_atr(de, lookback=20)
    segs = build_level_segments(days, se, de, atr, min_session_bars=30,
                                tol_atr_frac=0.02, tol_min=1.0, tol_max=20.0,
                                dedup_mult=1.0)
    ends = {"ASIA": dt.time(3, 0), "EU": dt.time(9, 30), "US": dt.time(16, 0)}
    for s in segs:
        if s.family in ("PDH", "PDL"):
            assert s.source_date < s.trading_date
            continue
        sess = s.family.rsplit("_", 1)[0]
        src_end = int(to_utc(s.source_date, ends[sess]).timestamp() * NS)
        assert s.valid_from_ns >= src_end, (s.family, s.trading_date)


def test_atr_warmup_produces_no_levels():
    days = [dt.date(2023, 5, d) for d in range(1, 30)]
    se, de = _synthetic(days)
    atr = daily_atr(de, lookback=20)
    segs = build_level_segments(days, se, de, atr, min_session_bars=30,
                                tol_atr_frac=0.02, tol_min=1.0, tol_max=20.0,
                                dedup_mult=1.0)
    covered = {s.trading_date for s in segs}
    assert all(d not in covered for d in days[:20])


def test_short_sessions_do_not_publish_levels():
    days = [dt.date(2023, 5, d) for d in range(1, 30)]
    se, de = _synthetic(days)
    se = se.with_columns(pl.when((pl.col("session") == "EU"))
                         .then(pl.lit(5)).otherwise(pl.col("n_bars")).alias("n_bars"))
    atr = daily_atr(de, lookback=20)
    segs = build_level_segments(days, se, de, atr, min_session_bars=30,
                                tol_atr_frac=0.02, tol_min=1.0, tol_max=20.0,
                                dedup_mult=1.0)
    assert not any(s.family.startswith("EU_") for s in segs)


def test_duplicate_prices_are_deduped_by_priority():
    days = [dt.date(2023, 5, d) for d in range(1, 30)]
    se, de = _synthetic(days)
    # make the previous US high identical to the previous day high
    se = se.with_columns(pl.when(pl.col("session") == "US")
                         .then(pl.col("hi")).otherwise(pl.col("hi")).alias("hi"))
    atr = daily_atr(de, lookback=20)
    segs = build_level_segments(days, se, de, atr, min_session_bars=30,
                                tol_atr_frac=0.02, tol_min=1.0, tol_max=20.0,
                                dedup_mult=1.0)
    D = days[25]
    e1 = [s for s in segs if s.trading_date == D
          and s.valid_from_ns <= int(to_utc(D, dt.time(1, 0)).timestamp() * NS) < s.valid_to_ns]
    prices = [s.price for s in e1]
    assert len(prices) == len(set(prices)), "two families must not share one price"
    fams = {s.family for s in e1}
    # US_H == PDH == 110+k-1 in the fixture -> PDH wins on priority
    assert "PDH" in fams and "US_H" not in fams


def test_daily_atr_is_causal():
    days = [dt.date(2023, 5, d) for d in range(1, 30)]
    _, de = _synthetic(days)
    atr = daily_atr(de, lookback=20).sort("trading_date")
    v = atr["atr20_prev"].to_list()
    assert all(x is None or np.isnan(x) for x in v[:20])
    # ATR on day 20 must equal the mean range of days 0..19 (all 25.0 by construction)
    assert v[20] == pytest.approx(25.0)
