# IMPULSE_EXHAUSTION_SPEC.md

**Candidate #2 — Širc-style E-mini Nasdaq-100 impulse exhaustion / absorption reversal**

**Spec version `impexh-1.0.0`**
**Written and frozen BEFORE any strategy P&L was computed.**

---

## 0. Hypothesis under test

> A strong directional NQ impulse becomes vulnerable to reversal when price
> continues making new extremes while aggressive order flow becomes
> progressively less effective, aggressive activity is absorbed without
> proportional price progress, and continuation subsequently fails.

SHORT: bullish impulse → higher highs → buying aggression deteriorates →
buying is absorbed → upside continuation fails → short. LONG is the exact
mirror and shares the same code path, signed by the impulse direction.

**What is NOT claimed.** Nothing here observes intent. There is no assertion
about market makers, traps, or hidden orders. MBP-1 exposes only the top of
book, so individual-order queue position and hidden liquidity are *not
observable*; the corresponding quantity is therefore named `absorption_proxy`
throughout and is defined purely from observable volume and quote movement.

---

## 1. Data, clocks and contracts

Reused from Phase 1 without modification (`DATA_AUDIT.md`):

| item | value |
|---|---|
| instrument | CME **NQ**, outright contracts only (spreads excluded) |
| tick | 0.25 pt ($5/tick, $20/pt) |
| sources | Databento GLBX.MDP3 `trades` **and** `mbp1`, T9, read-only |
| clock | `ts_event` (exchange matching engine), tz-aware UTC |
| session tz | `America/New_York` via `zoneinfo` (DST from the tz database) |
| trading day | Globex day D = 18:00 ET (D−1) → 17:00 ET (D) |
| front contract | highest volume on the **previous** trading day; roll days excluded |
| back-adjustment | none |

**Event ordering.** The source files are sorted by `ts_recv`; roughly 1 row in
3 million has a different `ts_event` order. Phase 2 sorts every cache by
`(ts_event, source row number)`, so all causality is expressed in **event
time**, and `open`/`close` of any derived bar resolve deterministically even
when a sweep produces several fills sharing one `ts_event`.

**Cached band.** Only 08:00–16:15 ET is cached and processed. The state machine
starts at **09:00 ET** (warm-up only, no signals) and entries are permitted only
between **09:30:00 and 16:00:00 ET**.

---

## 2. Trade signing (STEP 1)

Databento's `trades` schema carries a native `side` field. Phase 2 does **not**
assume its meaning. It is verified against a causal quote rule reconstructed
from MBP-1 on a stratified random sample of development days (2021–2023 only):

* for a trade at `ts_event = t`, the BBO used is the last MBP-1 top-of-book
  state with **`ts_event < t` — strictly before**. A book update stamped at the
  same nanosecond as the trade is the book *after* that trade, or is
  order-ambiguous with it, so it is excluded. This can only make the quote
  staler, never fresher, and makes quote lookahead structurally impossible;
* a trade at or above the prevailing ask ⇒ buyer-initiated;
* a trade at or below the prevailing bid ⇒ seller-initiated;
* strictly inside the spread ⇒ **UNKNOWN**. There is deliberately **no
  tick-rule fallback**: guessing would manufacture signed volume that the data
  does not support. Unknown volume is tracked separately and contributes to
  neither buy nor sell aggression.

The measured agreement rate is recorded in `results/p2_signing_verification.json`
and in `PHASE2_LEAKAGE_AUDIT.md`. **Decision rule, fixed in advance:** if the
native field agrees with the causal quote rule on ≥ 99 % of unambiguous trades,
the native field is used (it is available on every trade, including inside-spread
ones, and needs no quote join at runtime); otherwise the quote rule is used and
inside-spread trades are UNKNOWN.

Tracked per second: `buy_vol`, `sell_vol`, `unk_vol`, `delta = buy − sell`,
cumulative delta, trade count, max trade size.

---

## 3. Derived resolutions

All bars are half-open `[t, t+Δ)` on the UTC epoch grid and are knowable only at
their end. No centred windows, no interpolation, no backward fill from the
future anywhere.

* **1-second trade bars** — OHLC, volume, trade count, signed volumes. Untraded
  seconds produce no bar; when the grid is densified, prices are **forward**
  filled from the last *past* close and volumes are zero. A `traded` flag marks
  real seconds, and the state machine only ever acts on `traded` seconds.
* **1-minute bars** — aggregated from traded seconds, used only for volatility.
* **1-second BBO summary** — from MBP-1: first/last/min/max best bid and ask,
  last and mean sizes, event count, mean spread. Joined to the second grid and
  forward filled from the past only.

---

## 4. Volatility unit (VU)

```
VU(t) = max( ATR14 of COMPLETED 1-minute bars strictly before t's minute ,  2.0 pt )
```

True range uses the previous completed minute's close. The minute containing `t`
contributes nothing, so an in-progress minute can never leak its eventual high or
low into the threshold that detects an event inside it. During the ATR warm-up VU
is `NaN` and **the state machine refuses to act on a non-finite VU**.

*Why ATR14 of 1-minute bars:* the strategy's whole timescale is tens of seconds
to a few minutes, so the natural yardstick is what one recent minute of NQ
typically covers. Fourteen periods is the conventional ATR length and was not
varied. The 2.0-point (8-tick) floor is a safety rail against a degenerate dead
tape; NQ RTH 1-minute ATR is an order of magnitude above it, so it should never
bind during RTH.

---

## 5. State machine

```
IDLE → IMPULSE → EXHAUSTION_WATCH → ARMED → (SIGNAL | ABANDON) → COOLDOWN
```

One instance per direction, one live candidate per direction, symmetric code
signed by `s = −direction` (`s = +1` for a bullish impulse / short candidate).

### Stage A — IMPULSE

At each traded second `i`, over the trailing `W = 90 s` window (inclusive):

```
displacement = high(i) − min(low over [i−89, i])          (bullish)
IMPULSE if displacement ≥ max( 1.00 × VU(i) , 5.0 pt )
```

The impulse start is the argmin inside that window; the impulse end is `i`.

*Why 1.00 × VU:* one whole minute's worth of typical range, achieved
*directionally*, is the smallest move that is unambiguously an impulse rather
than ordinary two-sided noise. *Why 90 s:* 1.5× the ATR measurement period — a
move needing longer than that to cover one minute's range is a drift, not an
impulse. Both sit inside the brief's suggested regions (0.75–1.25 VU, 30–120 s)
and were chosen as the single canonical value; **the region was not swept**.
The 5.0-point absolute floor prevents a low-volatility stretch from
manufacturing micro-signals.

### Stage B — CONTINUED EXTENSION

Successive extremes are identified by a **directional-change (DC) tracker**, not
by pivots that peek forward:

* threshold `θ(t) = max(0.25 × VU(t), 1.0 pt)`;
* while tracking a peak the running maximum extends; once price retraces `θ`
  from it the peak is **CONFIRMED**;
* a confirmed extreme is published at the second the retracement completed —
  never at the second the extreme printed;
* **confirmation requires `conf_idx > ext_idx`.** Within one second we cannot
  know whether the high or the low printed first, so a second that both sets a
  new extreme and appears to retrace from it does not confirm; confirmation
  waits for a strictly later second. This can only delay information;
* the tracker starts undecided and adopts a direction only when the first `θ`
  move resolves it — no direction is assumed at the open.

Requirement: **three** confirmed peaks after the impulse start, strictly
increasing (`High1 < High2 < High3`; mirrored for longs). A confirmed extreme
that is *not* a new extreme terminates the sequence (`NOT_A_NEW_EXTREME`). All
three must occur within **600 s** of the impulse start (`EXTENSION_TOO_SLOW`).

*Why θ = 0.25 × VU:* a quarter of a typical minute's range is a real micro-pullback
yet small enough that a 1.0-VU impulse contains several of them, so three
attempts are attainable within the 600-second budget.

### Stage C — AGGRESSION DETERIORATION

Each confirmed peak `k` defines a **leg** running from the previous confirmed
opposite extreme to that peak. For each leg:

```
AggVol_k     = aggressive volume in the impulse direction over the leg
Progress_k   = |peak_k − trough_k|                      (points)
Efficiency_k = Progress_k / max(AggVol_k, 1)            (points per aggressive contract)
```

Both of the following must hold over legs 1→3, using one frozen test:

```
nonincreasing(x, tol = 0.10, drop = 0.20)  ⇔
      x[k+1] ≤ x[k] × 1.10   for every step        (noise tolerance)
  AND x[3]   ≤ x[1] × 0.80                          (economic significance)
```

1. **volume deterioration** on `AggVol`;
2. **efficiency deterioration** on `Efficiency` — more aggression for less
   movement.

*Why a tolerance rather than strict monotonicity:* requiring exact
`x1 > x2 > x3` on a noisy volume series is pathological — a single contract
would void an otherwise clear decay. 10 % per step admits that noise; the 20 %
overall drop forces the decay to be economically meaningful rather than a
rounding difference. Both numbers were fixed here, before any outcome was seen.

### Stage D — ABSORPTION PROXY

Window: the **final extension leg** (trough₃ → peak₃) — the aggression that
produced the last, weakest push.

```
absorption_raw = AggVol₃ / max( best-price advance over the leg, in ticks , 1 )
```

For a bullish leg the denominator is the advance of the **best ASK**; for a
bearish leg, the decline of the best **BID**. Using the *quote* rather than the
traded price is deliberate: the hypothesis is about aggression failing to move
the offer.

`absorption_raw` scales with the volume regime, so it is compared against a
**strictly trailing** empirical distribution:

* a rolling deque of the last **2 000** `absorption_raw` values from
  same-direction DC legs **confirmed strictly earlier**; it carries across days
  and is never reset intraday;
* **session-matched**: only legs whose extreme printed inside RTH
  (09:30–16:00 ET) enter the reference distribution, and only such legs can be
  ranked against it. A leg outside RTH is still measured and logged but can
  never qualify;
* the current leg's rank is taken **before** the leg is pushed, so a leg never
  contributes to its own reference distribution;
* no signal at all until **500** observations exist (`ABSORPTION_HISTORY_WARMUP`);
* required: `percentile rank ≥ 0.70`.

**No global, full-sample or full-day percentile is used anywhere.**

*Why the 70th percentile:* the gate must select the more-absorbed cases while
leaving a viable sample after four other gates. Requiring, say, the 90th would
push trade count toward zero.

*Why 2 000 / 500, and why session-matched.* Confirmed same-direction DC legs
occur at roughly 900–1 300 per day at this θ, so 2 000 legs ≈ **two RTH days** —
long enough to be statistically stable, short enough to track the current volume
and volatility regime. The session match is essential rather than cosmetic:
pre-open legs carry far less volume per tick than RTH legs, so an unmatched
reference distribution is dominated by them, almost every RTH leg ranks near the
top, and the gate stops discriminating. That defect was found from a pure
**count** diagnostic before the freeze — the gate was rejecting only 20 of 61 320
candidates — and corrected here, with no P&L computed. It is recorded in
`results/p2_count_calibration.json`.

**Exactly one absorption formula was written. No alternatives were coded, run,
or compared.**

### Stage E — FAILED CONTINUATION (the entry confirmation)

Once Stages A–D hold, the candidate is **ARMED** at that second, recording the
exhaustion extreme (peak₃). Then:

* **SIGNAL** at the first traded second where
  `(peak₃ − low(i)) ≥ 0.35 × VU` (mirrored for longs);
* if price makes a **new extreme beyond peak₃** while armed, the arm is
  cancelled and evaluation re-opens at the next confirmed DC extreme, so a
  stale extreme is never traded (`NEW_EXTREME_WHILE_ARMED`);
* if nothing happens within **300 s**, abandon (`ARM_TIMEOUT`);
* anything still armed at the end of the grid expires (`END_OF_SESSION`).

*Why 0.35 × VU:* strictly larger than the 0.25-VU threshold that confirmed
peak₃, so "continuation failed" is a stronger statement than "a normal
micro-pullback happened", yet small enough that entry is still near the extreme
and the stop stays tight. *Why 300 s:* ~3× the impulse window; beyond that the
setup is stale.

No candlestick pattern is used. No FVG, BOS, MSS or CHOCH. The trigger is a
volatility-normalised displacement, nothing else.

---

## 6. Entry

1. The signalling 1-second bar must **close**; the signal timestamp is that
   bar's end boundary.
2. A market order is assumed to reach the exchange after **250 ms**.
3. **Entry = the price of the first real trade print with
   `ts_event ≥ signal_ns + 250 ms`.** Never the signal bar's close, never the
   extreme that printed before confirmation, never an assumed limit fill.
4. No print within 60 s ⇒ `NO_ENTRY_PRINT` (not expected on front-month NQ).

Recorded: signal timestamp and price, entry timestamp and price, and
`entry_slippage = (entry − signal price) × direction`.

This is byte-for-byte the Phase-1 entry model (`nqr.backtest.engine.find_entry`).

---

## 7. Stop, sanity rule, targets

```
SHORT  stop = exhaustion extreme + 1.00 pt      (4 ticks)
LONG   stop = exhaustion extreme − 1.00 pt
R = |entry − stop|
```

**Stop-distance sanity range, frozen in advance:**

| rule | value | rejection code |
|---|---|---|
| absolute floor | `R ≥ 2.0 pt` | `R_TOO_SMALL` |
| volatility floor | `R ≥ 0.15 × VU` | `R_TOO_SMALL` |
| volatility cap | `R ≤ 1.20 × VU` | `R_TOO_LARGE` |

*Reasoning:* below 0.15 VU the stop sits inside ordinary one-second noise; above
1.20 VU the reversal has already surrendered more than the entire impulse and is
a different trade. Every rejected signal is logged with its reason.

**Targets.** Primary **1R**. Diagnostics on the *same* entries: 1.25R, 1.5R, 2R,
plus MFE and MAE. Because a high win rate is the explicit objective, the primary
first-passage question is `+1R before −1R`. **The best RR is not selected
afterwards; the primary is 1R, permanently.**

**Exit if neither is reached:** the earlier of entry + 3600 s and 16:00 ET
(`TIMEOUT`).

---

## 8. First-passage execution

Reused verbatim from Phase 1 (`nqr.backtest.engine.resolve`), on the integer
tick grid:

| order | fill condition | fill price |
|---|---|---|
| stop (stop-market) | first print at or beyond the stop | that print's price |
| target (resting limit) | first print trading **through** the limit by ≥ 1 tick | the limit price |

A touch is **not** a limit fill. If TP and SL prices both occur inside the same
derived bar, **raw event sequence decides** — no OHLC inference anywhere.

---

## 9. Portfolio, friction, deduplication

* **One open position at a time.** A signal arriving while a position is open is
  logged `SKIPPED_OVERLAP` and never stacked. Occupancy is governed by the
  primary (1R) book.
* **Friction** reported at **0.0 / 0.5 / 1.0 / 2.0** points round trip, always
  all four. The **primary** hypothesis uses **1.0 point**. Modelled entry
  slippage is on top of this.
* **Cooldown / reset.** After any candidate terminates — entry, invalidation or
  timeout — the direction returns to IDLE and cannot re-arm until **both**:
  (a) 120 s have elapsed, and (b) a **fresh impulse** is detected whose
  displacement leg starts strictly after the previous impulse ended. One
  exhaustion episode therefore cannot emit a cluster of near-identical trades.

---

## 10. Reporting windows

**PRIMARY: entries executable in 09:30:00–11:30:00 ET.** Diagnostics only:
09:30–12:00 and 09:30–16:00. Signals whose entry falls outside 09:30–16:00 are
logged `OUTSIDE_RTH` and never traded. **The best-performing window is not
selected afterwards.**

---

## 11. What the baseline deliberately does NOT use

No PDH/PDL, no Asia or London highs and lows, no prior-US levels, no VWAP, no
opening range, no higher-timeframe points of interest, and no machine learning
of any kind. The question is whether *impulse exhaustion + absorption + failed
continuation* carries information **by itself**. Distances to those references
may be recorded as diagnostic columns; **they never filter a baseline entry.**

---

## 12. Pre-registered component ablation (diagnostic only)

Same data, same execution, differing only in where the entry fires:

| variant | gates required | entry moment |
|---|---|---|
| **A** impulse only | Stage A | impulse confirmation |
| **B** + deterioration | A + B + C | third qualifying peak confirms |
| **C** + absorption | A + B + C + D | ARM moment |
| **D** full baseline | A + B + C + D + E | failed-continuation trigger |

**D is the strategy.** A/B/C exist to show which component carries information
and are never promoted.

---

## 13. Pre-registered control and null tests

**Random control.** For each accepted signal, `K = 5` control entries are drawn:
same trading day, same direction, same 30-minute time-of-day bucket, entry
second drawn uniformly from traded seconds in that bucket with finite VU. The
control inherits the matched signal's **R in points**, so risk geometry, time of
day, volatility regime and direction all match. Outcomes are resolved with the
identical first-passage engine. Reported: signal WR, control WR, difference,
bootstrap CI of the difference, and a permutation p-value.

**Label-shuffle null.** Signal timestamps, entry prices and R are held fixed
while the *direction* labels are randomly reassigned (preserving the empirical
long/short proportions) and outcomes are re-resolved. 2 000 replications build a
null distribution of win rate and expectancy; the real statistic's percentile in
that distribution is reported. This destroys the link between the exhaustion
features and subsequent direction while preserving the exact market moments.
**Neither test may use holdout data.**

---

## 14. Pre-registered PASS / FAIL gate

Evaluated on **2024 validation**, **09:30–11:30 ET**, **1R**, **1.0 pt
round-trip friction**.

**PASS** requires all six:

1. executed trades ≥ 100
2. net expectancy > 0 R
3. profit factor > 1.10
4. win rate > 50 %
5. 95 % binomial CI lower bound > 50 %
6. one-sided binomial p-value vs 50 % < 0.05

**PROMISING BUT INCONCLUSIVE** — positive expectancy but the evidence fails a
significance or sample-size gate.

**FAIL** — negative expectancy, PF ≤ 1, or the core directional-edge
requirements are otherwise not met.

Max drawdown and losing streaks are reported but **no drawdown threshold is
created after seeing results**.

### 14.1 Disclosed in advance: the sample-size gate is probably unreachable

The pre-freeze count check (`results/p2_count_calibration.json`, signal counts
only — no outcome of any kind was computed) shows this specification produces
roughly **20 signals per year in the 09:30–11:30 primary window** and ~50 per
year across full RTH. **Gate 1 (≥ 100 executed trades) therefore cannot be met
by a single validation year.**

This is stated *before* validation is run, and **the gate is not changed** — it
is the user's pre-registered standard and moving it after seeing the frequency
would be exactly the error this protocol exists to prevent. The consequence is
recorded honestly instead: unless the primary window unexpectedly yields ≥ 100
trades, the verdict cannot be `PASS`, and the distinction between
`PROMISING BUT INCONCLUSIVE` and `FAIL` will carry the real information.

To give the hypothesis the fairest honest test that the pre-registration allows,
the same frozen strategy is additionally reported on the **09:30–16:00 diagnostic
window** and on the **combined 2021–2023 development sample**, both of which have
materially more statistical power. Those are **diagnostics** and can never
produce a `PASS`; the official verdict follows §14 exactly.

The count check also established that signal frequency is **insensitive to the
impulse threshold** across the brief's entire suggested region (0.75–1.25 VU,
30–120 s all give 60–65 signals in 2021). The binding constraints are Stage B
(three strictly increasing confirmed peaks) and Stage C (double deterioration) —
both mandated by the hypothesis, and therefore **not relaxed**. The originally
reasoned configuration was kept unchanged.

---

## 15. Procedure and integrity commitments

1. This document and `config/baseline.yaml` were completed **before any P&L**.
2. Development (2021–2023) is run per year and combined, for implementation
   verification and diagnostics. **A weak year does not license a rule change.**
3. A genuine implementation **bug** may be fixed; it must be documented, given a
   regression test, bump the frozen implementation version, and force a full
   rerun. **Changing a legitimate rule because results are poor is not a bug fix.**
4. Validation (2024) is run **exactly once** on the frozen configuration.
5. Post-hoc observations go to `reports/FUTURE_HYPOTHESES.md` marked
   `OBSERVED POST-HOC — REQUIRES NEW VALIDATION DATA`, never into this baseline.
6. **2025-01-01 onward stays sealed.** The Phase-1 guard remains active and every
   query carries a `trading_date < 2025-01-01` predicate expressed on the Globex
   trading date.

### One disclosed pre-freeze calibration

Thresholds were chosen from the reasoning above, not from outcomes. Before
freezing, the specification was checked once on development for **signal count
only** — to confirm it is neither degenerate (zero signals) nor absurd (tens of
thousands). Had it been degenerate, the adjustment would have been made on
**count alone, never on any win rate, expectancy or P&L**, and disclosed here.
The outcome of that check is recorded in `IMPULSE_EXHAUSTION_SPEC_FROZEN.md`.
