# EVENT_ENGINE.md — the Phase-3 directional-change engine

Reference documentation for `src/nqr/p3/dc_engine.py`, validated in Phase 3A
**before** any strategy existed.

---

## 1. What it does

Reconstructs, tick by tick from NQ trade prints, the sequence of confirmed
directional-change (DC) events and the overshoots between them.

```
UP run   : high = max(high, price)
           price <= high - θ   ->   DOWNWARD DC confirmed on `high`
DOWN run : low  = min(low,  price)
           price >= low  + θ   ->   UPWARD  DC confirmed on `low`
```

An UP run is the market making higher prices; it ends when price retraces θ from
the running high, and that retracement **confirms** the high as an extreme.

## 2. The causality rule

The extreme printed at `ext_ts` is not known to be an extreme until the
threshold is crossed at `conf_ts`. The engine therefore stores **both** and
guarantees `conf_idx > ext_idx` strictly. Nothing downstream may treat `ext_ts`
as a tradeable moment.

Three independent tests enforce this:

| test | what it proves |
|---|---|
| `test_truncating_the_path_at_confirmation_reproduces_the_event` | cutting the price path at each confirmation reproduces the identical event — no future price was needed |
| `test_future_prices_cannot_alter_a_confirmed_event` | overwriting all later prices with junk leaves earlier events unchanged |
| `test_confirmation_is_always_strictly_after_the_extreme` | `conf_idx > ext_idx` on randomised walks |

**Measured on 643,758 development events:** `conf_idx > ext_idx` holds for
100 % of events. `conf_ts > ext_ts` holds for 99.98 %; the remaining 134 events
(0.02 %) confirm inside the **same nanosecond** as their extreme, because one
aggressive sweep produced several prints sharing a `ts_event` and crossed θ
within it. Ordering is by `(ts_event, source row number)`, so the confirming
print still follows the extreme in exchange sequence order — this is not
lookahead, and the 250 ms entry latency is applied from the confirmation
timestamp regardless.

## 3. θ

```
θ = max( 0.50 × VU , 1.00 pt )
VU = max( ATR14 of COMPLETED 1-minute bars strictly before t's minute , 2.0 pt )
```

θ is **sampled once at the start of each run** — that is, at the previous
event's confirmation — and held constant for that whole run. A drifting
threshold would make "has price moved θ from the extreme?" ambiguous.

## 4. Price-path compression

The engine runs on the sequence of **distinct consecutive prices**, keeping the
first print at each new price. This is exact: running extremes and threshold
crossings depend only on the sequence of prices, and keeping the first
occurrence preserves the earliest time each price was reached, so a confirmation
can never be late. Entries and first-passage resolution always use the full,
uncompressed tick stream.

Compression ratio on NQ: roughly 200 k prints/day → 55 k distinct-price points.

## 5. The overshoot identity

After a downward DC confirms at `conf_price(k)`, price may keep falling; the low
it reaches is the extreme that the *next* upward DC will confirm. Therefore

```
overshoot(k) = |ext_price(k+1) − conf_price(k)| = total_move(k+1)
```

Two consequences, both tested:

* the overshoot of event *k* is **complete and known** the instant event *k+1*
  confirms — which is exactly when DC-C consults it, so DC-C is fully causal;
* the **last event of each day has an unfinished overshoot**, which is left
  `NaN` so no strategy can consume an incomplete measurement.

## 6. Recorded fields

| field | meaning |
|---|---|
| `seq`, `direction` | index within the day; +1 upward DC, −1 downward DC |
| `theta`, `vu` | threshold and volatility unit governing the run that just ended |
| `ext_idx/ts/price` | the confirmed extreme — **not a tradeable moment** |
| `conf_idx/ts/price` | where the threshold was crossed — **the signal moment** |
| `trigger_price` | the theoretical level `ext_price ∓ θ` |
| `dc_magnitude` | `|conf_price − ext_price|`, always ≥ θ |
| `run_start_idx/ts/price` | the previous confirmation |
| `total_move`, `total_move_ns` | the run just ended, and its duration |
| `event_ns` | confirmation-to-confirmation duration |
| `n_trades`, `volume` | aggregates over the run |
| `velocity` | points per second over the run |
| `prev_direction`, `prev_dc_magnitude` | previous event context |
| `prev_overshoot`, `prev_overshoot_ratio` | the completed overshoot DC-C keys off |
| `overshoot`, `overshoot_ns`, `overshoot_ratio`, `overshoot_ext_*` | filled in when the next event confirms |

## 7. Measured behaviour (development 2021–2023, 762 days)

| quantity | value |
|---|---|
| events | 643,758 |
| events / day (08:00–16:15 ET) | 844.8 |
| events / day (RTH 09:30–16:00) | 670.7 |
| events / day (primary 09:30–11:30) | 234.5 |
| θ, points (p25 / median / p75) | 2.83 / 4.06 / 5.88 |
| θ in the primary window | 3.94 / 5.60 / 7.71 |
| direction balance | 321,863 up / 321,895 down (0.005 % apart) |
| `dc_magnitude / θ`, median | 1.032 |
| event duration, median / p90 | 22.8 s / 76.5 s |
| extreme→confirmation, median | 9.3 s |
| prior overshoot / θ, median / p90 | 0.68 / 2.36 |

Threshold monotonicity is verified: raising θ strictly reduces the event count
(427.8 → 120.4 → 55.6 → 32.2 events/day for θ = 0.25 / 0.50 / 0.75 / 1.00 × VU).

## 8. Visual validation

`diagnostics/events_*/dcseq_*.png` plot randomly chosen 12-minute windows. Each
extreme appears as a **hollow** marker at the time it printed, each confirmation
as a **solid** marker, and the interval between them is shaded — so an entry
drawn inside the shaded band would be an immediately visible lookahead error.
The θ trigger level is drawn as a dotted line across that interval.
