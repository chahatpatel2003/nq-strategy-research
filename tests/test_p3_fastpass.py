"""The Phase-3 chunked resolver must be byte-equivalent to the frozen engine."""
import numpy as np
import pytest

from nqr.backtest.engine import TICK, resolve, excursions
from nqr.p3.fastpass import resolve_fast, excursions_fast

NS = 1_000_000_000


def _tape(rng, n, start=15000.0):
    steps = rng.integers(-3, 4, size=n)
    px = np.cumsum(steps) + int(start / TICK)
    ts = np.cumsum(rng.integers(1, 500_000, size=n)).astype(np.int64)
    return ts, px.astype(np.int64)


@pytest.mark.parametrize("seed", range(40))
def test_matches_frozen_engine(seed):
    rng = np.random.default_rng(seed)
    ts, px = _tape(rng, 4000)
    for _ in range(6):
        i = int(rng.integers(0, 3000))
        d = int(rng.choice([-1, 1]))
        entry = float(px[i]) * TICK
        r = float(rng.choice([1.0, 2.5, 5.0, 12.0]))
        tp, sl = entry + d * r, entry - d * r
        end = int(ts[min(i + int(rng.integers(50, 900)), len(ts) - 1)])
        a = resolve(ts, px, i, end, d, tp, sl)
        b = resolve_fast(ts, px, i, end, d, tp, sl)
        assert (a.kind, a.ts_ns, a.price) == (b.kind, b.ts_ns, b.price), (seed, i, d, r)
        assert excursions(ts, px, i, a.ts_ns, d, entry) == \
               excursions_fast(ts, px, i, b.ts_ns, d, entry)


def test_no_data_and_timeout_paths_agree():
    ts = np.array([0, NS, 2 * NS], dtype=np.int64)
    px = np.array([60000, 60001, 60002], dtype=np.int64)
    a = resolve(ts, px, 0, 0, 1, 15001.0, 14999.0)
    b = resolve_fast(ts, px, 0, 0, 1, 15001.0, 14999.0)
    assert (a.kind, a.price) == (b.kind, b.price)
    a = resolve(ts, px, 0, 3 * NS, 1, 15100.0, 14900.0)
    b = resolve_fast(ts, px, 0, 3 * NS, 1, 15100.0, 14900.0)
    assert (a.kind, a.ts_ns, a.price) == (b.kind, b.ts_ns, b.price)
