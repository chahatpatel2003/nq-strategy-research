# FAST_SLOW_SPEC.md — Fast-Slow Nasdaq-100, mechanical specification

**Spec version `fastslow-1.0.0`**
**Status: written and frozen BEFORE any strategy profitability was computed.**

This document turns the published Fast-Slow concept

> important pre-existing level → fast movement away → slower return →
> return reaches the original level → 2-minute reversal trigger → trade the reversal

into an algorithm with no discretionary component. Every threshold below was
chosen from *a priori* reasoning about NQ's structure and tick size, not from
looking at P&L. Where the paper is silent, the choice made here is stated
together with why it was made.

The original research reports ≈541 observations, 71.72 % success at 1:1 and
52.68 % at 1:2. **Those numbers are treated as a hypothesis to be tested, not
as an assumption.**

---

## 0. Universe, time and price

| Item | Value |
|---|---|
| Instrument | CME **NQ** (E-mini Nasdaq-100), outright contracts only |
| Tick size | 0.25 index points ($5.00 per tick, $20.00 per point) |
| Source | Databento GLBX.MDP3 `trades` schema, half-year parquet, read-only |
| Canonical timestamp | `ts_event` (exchange matching-engine time), tz-aware UTC |
| Session logic timezone | `America/New_York` (DST handled by `zoneinfo`, never by fixed offsets) |
| Price representation | `double`, verified 100 % tick-aligned for outrights; stored internally as **integer ticks** (`price / 0.25`) so all comparisons are exact |

`ts_recv` (capture time) is used only for the data audit. Median
`ts_recv − ts_event` is 0.24–0.27 ms and p99 < 6 ms, so the choice of clock is
immaterial at a 2-minute horizon; `ts_event` is preferred because it is the
exchange's own ordering.

### Globex trading day

    trading day D  =  18:00 ET (D−1)  →  17:00 ET (D)

Implemented as `trading_date = date(ts_ET + 6h)`, which maps 18:00 ET to
00:00 of the next calendar day. 17:00–18:00 ET is the CME maintenance halt and
contains no bars.

### Sessions (the ONE frozen mapping)

| Session | ET window | Notes |
|---|---|---|
| `ASIA` | 18:00 → 03:00 | spans midnight; belongs to the *following* trading date |
| `EU` | 03:00 → 09:30 | |
| `US` | 09:30 → 16:00 | RTH |
| `POST` | 16:00 → 17:00 | not one of the four published sessions; labelled for completeness |

These are the boundaries named in the project brief. They were **not** varied
and no alternative was tested. The 16:00–17:00 ET hour is not covered by the
brief's mapping; it is retained in the *day* high/low but defines no session
level of its own.

---

## 1. Contract handling

The parquet files contain several NQ expiries simultaneously **and** calendar
spreads (`NQH1-NQM1`, …). Spreads have non-tick-aligned and sometimes negative
prices — 100 % of all off-tick prints in the dataset are spreads. They are
excluded by `symbol NOT LIKE '%-%'` plus `^NQ[FGHJKMNQUVXZ][0-9]{1,2}$`.

**Front-contract rule (frozen):** for trading day D, the front contract is the
outright symbol with the highest traded volume on the **previous** trading day
D−1. This is strictly causal — nothing about day D is used to choose day D's
contract. Ties break on symbol name.

**Consequences, all deliberate:**

* One and only one contract is used for the whole of day D, *including* that
  day's Asia session which begins at 18:00 ET on calendar day D−1.
* **Every level for day D is computed from the same contract's own bars.** A
  previous-day high is therefore always a price that actually traded in the
  instrument being traded. There is no synthetic splicing of two expiries into
  one series, and **no back-adjustment** — the strategy trades real levels, so
  the levels must be real prices.
* **Roll days are excluded from signal generation** (`exclude_roll_day: true`).
  On a roll day the newly-front contract's preceding sessions were thin; from
  D+1 onward the previous day was already fully liquid in the new contract, so
  only the roll day itself needs excluding. Cost: 16 days per 4 years.

Detected rolls (2021–2024) are the standard quarterly cycle, ~8 calendar days
before the third-Friday expiry — see `results/roll_dates.parquet`.

---

## 2. Two-minute bars

Half-open intervals `[t, t+2min)` aligned to multiples of 2 minutes **from the
UTC epoch**. Every US/Eastern UTC offset is a whole number of hours, so these
boundaries coincide exactly with even-minute ET boundaries in both EST and EDT.

* `open` = first print in the interval, `close` = last print, in exact source
  order (`file_row_number`), so multi-fill sweeps sharing one `ts_event`
  resolve deterministically.
* `high`/`low`/`volume`/`trades` are the obvious aggregates.
* A bar is knowable only at `bar_end`. **No print with `ts_event >= bar_end`
  can influence it.**
* Intervals with no prints produce **no bar**. All durations are therefore
  measured in *wall-clock nanoseconds*, never in bar counts, so an untraded
  gap can never make a slow leg look fast.

---

## 3. Levels

Eight families: `PDH PDL US_H US_L EU_H EU_L ASIA_H ASIA_L`.

**Availability rule (frozen):** at time *t*, the level of type *S* is the
high/low of the **most recently COMPLETED** session of type *S* strictly before
*t*. This is what a trader actually reads off a chart, and it makes the
no-lookahead requirement explicit. It produces four intra-day epochs:

| epoch | ET window | ASIA from | EU from | US from | PD from |
|---|---|---|---|---|---|
| E1 | 18:00 (D−1) → 03:00 (D) | D−1 | D−1 | D−1 | D−1 |
| E2 | 03:00 → 09:30 | **D** | D−1 | D−1 | D−1 |
| E3 | 09:30 → 16:00 | D | **D** | D−1 | D−1 |
| E4 | 16:00 → 17:00 | D | D | **D** | D−1 |

`PDH`/`PDL` are the high/low of the entire previous Globex trading day and are
valid for all of day D.

A level is only published if its source session contains **≥ 30 two-minute
bars** (≥ 1 hour of traded time). This suppresses levels from holiday stubs.

### Level touch tolerance

```
tol(D) = clamp(0.02 × ATR20_daily_prev(D),  1.0 pt,  20.0 pt)
```

`ATR20_daily_prev(D)` = mean of `(day high − day low)` over the **20 most recent
completed trading days** before D. The plain day range is used instead of the
classic true range specifically because true range would absorb the price gap
at a contract roll; the day range cannot.

*Why 2 % of daily ATR:* NQ's daily range over 2021–2024 runs roughly 200–350
points, giving a 4–7 point band. A fixed 4-tick (1 pt) band is far tighter than
NQ's own bid/ask noise and would make "touching a level" essentially random; a
band proportional to daily volatility keeps the notion of "at the level"
comparable between the 13 000-index regime of 2021 and the 21 000-index regime
of 2024. The floor and cap are pure sanity rails.

### Level deduplication

PDH and the previous US session high are frequently the *same price*. Within
each epoch, levels are visited in the fixed priority order

    PDH > PDL > US_H > US_L > EU_H > EU_L > ASIA_H > ASIA_L

and any level within `1.0 × tol` of an already-kept level is dropped. Without
this, one price would generate up to four identical trades.

---

## 4. A–B–C detection

Runs independently inside each *level segment* — one constant level price over
one validity window.

```
touch(i)  ⇔  low_i − tol ≤ L ≤ high_i + tol
```

* **A** = the **last** bar of a contiguous run of touching bars, i.e. the final
  bar in contact with the level before price leaves it.
* The excursion is the run of non-touching bars after A.
  It must lie **entirely on one side** of the level; an excursion that jumps
  across the level without touching is discarded.
* **B** = the excursion's extreme (`max high` above, `min low` below).
* **C** = the **first** bar after B that touches the level again.

**Deduplication is structural, not a filter.** Because C is defined as the
*first* return, each departure/return cycle produces at most one (A,B,C)
candidate, and the scan resumes from C. One price movement can therefore never
produce ten overlapping trades.

Reference prices:

| symbol | price used |
|---|---|
| A | the level `L` itself |
| B | the excursion extreme |
| C | the C bar's extreme **in the direction of the return** (its low when returning downward, its high when returning upward) |

### Direction

An excursion **above** the level returns down onto it → the level is support →
**LONG**. An excursion **below** returns up into it → resistance → **SHORT**.
Trade direction therefore equals the sign of the A→B leg — the trade resumes
the fast move and reverses the slow return, exactly as the published pattern
describes.

### Gates (all frozen)

| Gate | Value | Why |
|---|---|---|
| minimum A→B move | `max(0.10 × ATR20_daily_prev, 10.0 pt)` | An excursion must be a real intraday swing, not noise. 10 % of the daily range (≈ 25 pt in 2021, ≈ 35 pt in 2024) is well above the ≈5 pt tolerance band, so A and B are unambiguously distinct. The 10-point floor stops the rule collapsing in a dead-volatility regime. |
| minimum A→B duration | 2 bars (4 min) | With 2-minute granularity a 1-bar leg would quantise the time ratio by 100 %. Two bars keeps the ratio measurable. |
| maximum A→B duration | 60 bars (2 h) | "Fast" cannot mean half a session. |
| maximum B→C duration | 240 bars (8 h) | Keeps the pattern inside one trading day. |
| **time ratio** | `duration(B→C) ≥ 2.0 × duration(A→B)` | **This is the paper's primary condition and the canonical baseline.** 2.5× and 3.0× are *recorded and reported* but the strategy is defined at 2.0×. |
| distance ratio | `0.90 ≤ |C−B| / |B−A| ≤ 1.25` | Since A and C both sit on the level this is ≈1 by construction; its real job is the **upper** bound, which rejects a C bar that blows *through* the level by more than 25 % of the excursion. That is a breakout, not a rejection. |
| containment | A, B, C all inside one level segment and one trading day | A level that has been superseded is no longer that level. |

---

## 5. Reversal triggers

All three families are evaluated on every bar; a *variant* selects which are
eligible. `ATR2M` is the **causal** 20-bar ATR of the 2-minute series
(bar *i* uses true ranges of bars *i−20 … i−1* only — the bar being classified
never contributes to its own threshold).

Notation: `rng = h−l`, `body = |c−o|`, `up = h−max(o,c)`, `dn = min(o,c)−l`,
`clo = (c−l)/rng`.

### ENGULFING (2 bars)

Bullish:
```
prev bearish            c₁ < o₁
current bullish         c₂ > o₂
body engulfs body       o₂ ≤ c₁   and   c₂ ≥ o₁
current body larger     |c₂−o₂| > |c₁−o₁|
both bodies material    |c₁−o₁| ≥ 0.10 × ATR2M   and   |c₂−o₂| ≥ 0.30 × ATR2M
```
Bearish is the exact mirror. The two size gates exist so that "engulfing a
doji" — trivially satisfied and meaningless — does not count.

### PIN (1 bar)

Bullish (hammer):
```
rng ≥ 0.50 × ATR2M
body ≤ 0.35 × rng
dn   ≥ 0.55 × rng      and   dn ≥ 2.0 × body
up   ≤ 0.20 × rng
clo  ≥ 0.60
```
Bearish (shooting star) mirrors with `up`, `dn` and `1−clo` swapped. These are
the conventional textbook proportions written as inequalities; nothing is
tuned.

### STAR (3 bars)

Bullish morning star:
```
bar1  bearish, rng₁ ≥ 0.50 × ATR2M, body₁ ≥ 0.35 × rng₁
bar2  body₂ ≤ 0.40 × body₁,  low₂ ≤ low₁,  max(o₂,c₂) < c₁
bar3  bullish, body₃ ≥ 0.35 × rng₃,  c₃ > midpoint of bar1's real body
```
Bearish evening star mirrors. This is the classical definition made arithmetic;
"looks like a star" plays no part.

### Where the trigger may occur

* The trigger pattern's **last** bar must fall in `[C, C+2]` (`window_bars: 3`).
* All pattern bars must be **strictly after B** and **contiguous in time**
  (consecutive 2-minute boundaries, same trading day) — a "2-bar engulfing"
  spanning a 40-minute untraded gap is not an engulfing.
* The pattern must itself reach the level zone: for a long, its low must be
  ≤ `L + tol`; for a short, its high ≥ `L − tol`.
* At each bar of the window the level must still be holding: the running
  penetration since B, `|running extreme − B| / |B − L|`, must stay ≤ 1.25. The
  first bar that breaks this kills the candidate (`skip_reason = LEVEL_BROKEN`).
* Direction must match: bullish trigger for a long, bearish for a short.
* At most **one** signal per A-B-C pattern: earliest trigger bar wins, ties
  broken by the fixed precedence `ENGULFING > PIN > STAR`.

### Variants reported

`ENGULFING` · `PIN` · `STAR` · `ANY`. **`ANY` at the 1R target is the single
pre-registered primary hypothesis.** The other three are diagnostics. Choosing
whichever variant happens to win would be selection on the test set and is
explicitly not done.

---

## 6. Entry

1. The trigger bar must **close**. The signal timestamp is the bar's end
   boundary, not any earlier moment.
2. A market order is assumed sent at that instant and to reach the exchange
   after `latency_ms = 250`.
3. **Entry price = the price of the first real trade print with
   `ts_event ≥ bar_end + 250 ms`.** No fill at the trigger close, ever.
4. If no print appears within 60 s the signal is abandoned
   (`skip_reason = NO_ENTRY_PRINT`). Never observed on front-month NQ.

Recorded per trade: trigger close, modelled entry, and
`entry_slippage = (entry − trigger close) × direction` in points.

250 ms is a deliberately unflattering round-trip allowance for a retail
co-location-free setup; it is longer than the p99 feed latency of 6 ms by more
than an order of magnitude.

---

## 7. Stop

```
LONG   SL = (lowest low  of the complete trigger pattern) − 1.00 pt
SHORT  SL = (highest high of the complete trigger pattern) + 1.00 pt
```

1.00 point = **4 ticks**, the paper's rule. "Complete trigger pattern" means all
bars of the pattern: 1 bar for PIN, 2 for ENGULFING, 3 for STAR.

`R = |entry − SL|`, measured from the *modelled* entry, not the trigger close.

Two sanity rails, frozen in advance, neither of which is a performance filter:

* `R < 2.0 pt` → rejected (`R_TOO_SMALL`): a sub-8-tick stop is not survivable
  on NQ.
* `R > 0.25 × ATR20_daily_prev` → rejected (`R_TOO_LARGE`): a stop wider than a
  quarter of the daily range is a different trade.

---

## 8. Targets

* **Primary `1R`** — `TP = entry + direction × R`
* **Secondary `2R`** — `TP = entry + direction × 2R`

Both are evaluated on the **same** accepted entries, so the two books differ
only in exit. (Consequence, stated openly: the 2R book's occupancy is governed
by the 1R book's exits, so in live trading a 2R-only version would take
somewhat fewer trades.)

No other target is evaluated. Targets are not optimised.

`MFE`/`MAE` are computed from raw prints over each book's realised holding
period.

---

## 9. Exact TP-before-SL resolution

**Outcomes are never inferred from 2-minute OHLC.** Once filled, the raw
chronological trade stream is walked from the entry print forward, and whichever
of the two conditions occurs first in tape order decides the trade. When both
prices occur inside the same 2-minute candle, event sequencing — not a guess —
resolves it.

Comparisons happen on the integer tick grid, so "touched" is exact.

| Order | Fill condition | Fill price |
|---|---|---|
| **Stop** (stop-market) | first print at or beyond `SL` | that print's price |
| **Target** (resting limit) | first print that trades **through** the limit by ≥ 1 tick | the limit price |

Requiring the tape to trade *through* a resting limit is the conservative
treatment of queue position: **a touch is not a fill.** Using touch-equals-fill
would inflate the win rate.

A single print cannot be on both sides of the entry, so TP/SL ties are
impossible.

**Timeout:** if neither is reached, the position is closed at the last print
before **16:59 ET** (`outcome = TIMEOUT`), flat before the 17:00 halt.

---

## 10. Portfolio and costs

* **One open Fast-Slow position at a time.** A signal arriving while a position
  is open is logged with `status = SKIPPED`, `skip_reason = CONCURRENT_POSITION`
  and never stacked. Occupancy is governed by the primary (1R) book.
* Costs are **not** assumed. Results are reported gross **and** at round-trip
  friction of **0.0 / 0.5 / 1.0 / 2.0 NQ points**, all four always shown. The
  modelled entry slippage (first print after confirmation) is *on top of* this.
  1.0 point ≈ $20/contract round trip, which comfortably brackets a typical
  prop-account commission plus one tick of stop slippage.

---

## 11. Reporting (diagnostic only)

Results are broken down by year, month, level family, trigger type, direction,
session, the 09:30–11:30 ET window, and time-ratio bucket (`<2.0`, `2.0–2.5`,
`2.5–3.0`, `≥3.0`). **These are diagnostics.** The strategy is the whole
pre-registered rule set; no subgroup is promoted to "the strategy".

---

## 12. Pre-registered verdict rule

Declared before any result was seen. Applied to the **primary hypothesis**
(`ANY`, 1R target) on **2024 validation**, at **1.0 point** round-trip friction:

* **PASS** — win rate 95 % CI lower bound > 0.50 **and** expectancy > 0
  **and** profit factor > 1.10 **and** the one-sided binomial p-value against
  a 50 % break-even is < 0.05 **and** ≥ 100 trades.
* **PROMISING BUT INCONCLUSIVE** — point-estimate expectancy > 0 but the
  evidence fails any of the significance/size gates above.
* **FAIL** — expectancy ≤ 0 at 1.0 point friction, or the 95 % CI upper bound
  is below the break-even win rate.

Break-even win rate is 50 % at 1R and 33.3 % at 2R (before friction).

---

## 13. Holdout

`2025-01-01` onward is sealed. `src/nqr/holdout.py` raises `HoldoutViolation`
on any attempt to read a date, a date range or a filename in that region, and
every SQL query carries a `trading_date < 2025-01-01` predicate. The guard is
enforced on the **Globex trading date**, not the UTC calendar date, so the
23:00–24:00 UTC tail of 2024-12-31 — which belongs to Globex day 2025-01-02 —
is excluded as well. Unlocking requires an explicit confirmation string that
Phase 1 never supplies.

No scaler, ATR, tolerance, session statistic, contract choice or threshold in
this document is derived from data on or after 2025-01-01.
