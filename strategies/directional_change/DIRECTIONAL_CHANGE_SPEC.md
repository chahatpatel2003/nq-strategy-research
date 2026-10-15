# DIRECTIONAL_CHANGE_SPEC.md

**Candidate #3 — NQ directional-change / event-time strategy**

**Spec version `dcevent-1.0.0`**
**Written and frozen BEFORE any strategy P&L was computed.**

---

## 0. Research question

> Does NQ exhibit a statistically repeatable continuation or reversal edge after
> directional-change events and their subsequent overshoots?

This is **not** assumed to be a reversal strategy. The admissible answers are
*continuation*, *reversal*, and *neither*, and the design is symmetric: a family
that trades in the direction of the confirmed change wins if the change
continues and loses if it reverts, so both outcomes are measured by the same
number.

**Phase 3 uses NQ trade prints only.** MBP-1 is deliberately untouched, which
preserves 2025-H1 — the last period holding both Trades and MBP-1 — for future
order-flow work. No order flow, no candle patterns, no machine learning.

---

## 1. Data, clock, contracts

Reused unchanged from Phases 1–2 (`DATA_AUDIT.md`):

| item | value |
|---|---|
| instrument | CME **NQ**, outright only (spreads excluded) |
| tick | 0.25 pt |
| source | Databento GLBX.MDP3 `trades`, T9, read-only |
| clock | `ts_event`, tz-aware UTC |
| ordering | every cache sorted by `(ts_event, source row number)` — Phase 0 found the source files are sorted by `ts_recv` and that ~1 row in 3 M orders differently; that bug is not reintroduced |
| session tz | `America/New_York` via `zoneinfo` |
| trading day | Globex day D = 18:00 ET (D−1) → 17:00 ET (D) |
| front contract | highest volume on the **previous** trading day; roll days excluded |
| band cached | 08:00–16:15 ET |

2021–2024 reuse the Phase-2 tick cache verbatim (read-only); Phase 3 reads only
timestamp, price and size from it and never the aggressor column.

### Period policy (`src/nqr/p3/holdout3.py`)

| period | status |
|---|---|
| 2021-01-01 … 2023-12-31 | **DEV** — development |
| 2024-01-01 … 2024-12-31 | **CONTAMINATED DIAGNOSTIC** — already used as validation in Phases 1 and 2. **Never counts toward a Phase-3 PASS.** |
| 2025-01-01 … 2025-06-30 | **SEALED.** No unlock path exists in Phase 3 at all. |
| 2025-07-01 … 2025-12-31 | **FRESH VALIDATION.** Requires an explicit unlock phrase. |
| 2026-01-01 … | **SEALED.** No unlock path exists in Phase 3 at all. |

The unlock opens 2025-H2 and nothing else; 2025-H1 and 2026 stay blocked even
while it is active, and the loader refuses those months by name.

---

## 2. Volatility unit

```
VU(t) = max( ATR14 of COMPLETED 1-minute bars strictly before t's minute , 2.0 pt )
```

This is the frozen Phase-2 implementation (`nqr.p2.features.causal_atr_minutes`),
imported read-only. The minute containing *t* contributes nothing, so an
in-progress minute can never leak its own range into a threshold applied inside
it. No centred windows, no full-day statistics, no future normalisation. During
the ATR warm-up VU is undefined and the engine does not run.

---

## 3. The directional-change event engine

Reconstructed **tick by tick** from trade prints.

An UP run tracks the running high. When a print occurs at or below
`high − θ`, a **DOWNWARD directional-change event is CONFIRMED**, and the
extreme it confirms is the prior high. A DOWN run mirrors this exactly.

```
UP run   : high = max(high, price)
           if price <= high - θ  ->  DOWNWARD DC confirmed on `high`
DOWN run : low  = min(low,  price)
           if price >= low  + θ  ->  UPWARD  DC confirmed on `low`
```

### The causality rule — the heart of Phase 3

The extreme printed at `ext_ts` is **not known to be an extreme** until the
threshold is crossed at `conf_ts`. Therefore:

* **the signal does not exist until `conf_ts`**;
* no trade is ever stamped at `ext_ts`;
* confirmation requires `conf_idx > ext_idx` strictly;
* every strategy keys exclusively off `conf_ts`.

This is enforced structurally (the engine cannot emit a confirmation at the
extreme's own index) and tested three ways: truncating the price path at each
confirmation reproduces the identical event; overwriting all later prices leaves
earlier events unchanged; and `conf_ts > ext_ts` is asserted on randomised paths.

### θ — the threshold

```
θ = max( 0.50 × VU , 1.00 pt )
```

`0.50 × VU` is the brief's named research baseline and is adopted unchanged.
**θ is sampled once, at the instant the current run begins** (the previous
event's confirmation) and held constant for that whole run — a threshold that
drifted mid-run would make "has price moved θ from the extreme?" ambiguous. The
1.00-point (4-tick) floor is a safety rail: below one point a "directional
change" is inside the bid-ask bounce. NQ RTH values put θ far above it, so the
floor never binds in the trading window.

The engine resets **per trading day** and starts undecided — no direction is
assumed at the open; the first event is whichever threshold the path actually
crosses first.

### Price-path compression

The engine runs on the sequence of **distinct consecutive prices**, keeping the
first print at each new price. This is exact: running extremes and threshold
crossings depend only on the sequence of prices, and keeping the first
occurrence preserves the **earliest** time each price was reached, so a
confirmation is never late. Entries and first-passage resolution always use the
full, uncompressed tick stream.

### Recorded per event

`θ`, VU, direction, extreme index/timestamp/price, confirmation
index/timestamp/price, theoretical trigger price, DC magnitude, run start
(= previous confirmation) index/timestamp/price, total move and its duration,
event duration, trades and volume over the run, velocity, previous direction,
previous DC magnitude, previous overshoot and its ratio to θ, plus the
overshoot fields filled in when the **next** event confirms (extreme
index/timestamp/price, magnitude, duration, ratio).

### Overshoot, and the identity DC-C relies on

After a downward DC confirms at `conf_price`, price may keep falling; the low it
reaches is the extreme the *next* (upward) DC will confirm. So

```
overshoot(k) = |ext_price(k+1) − conf_price(k)| = total_move(k+1)
```

The overshoot of event *k* is therefore **complete and known at the moment event
*k+1* confirms**, which is precisely when DC-C consults it. The final event of
each day has an unfinished overshoot and it is left `NaN`, so no strategy can
consume an incomplete measurement.

---

## 4. The three pre-registered hypotheses

All three trade **in the direction of the confirmed change** (`direction = +1`
for an upward DC, `−1` for a downward DC) and share one risk geometry.

### DC-A — directional-change signal

Enter at the confirmation itself. *Does a confirmed directional change keep
going far enough to be tradeable?*

### DC-B — overshoot continuation

After the confirmation, wait for the move to **extend a further `β × θ` beyond
the confirming print**, then join it in the same direction. The extension must
occur before the opposite DC confirms, so one event yields at most one DC-B
signal.

```
β = 0.50
```

*Consolidation note, made before any outcome was computed.* The brief describes
DC-B as "closely related to Family A". Under the mathematical event definition
they would be **literally the same trade** if DC-B also entered at the
confirmation. To make DC-B a genuinely distinct hypothesis it must have a
distinct entry, so it waits for the overshoot to establish itself. `β = 0.50`
is chosen because the confirmation already required a full θ move from the
extreme; asking for a further half-θ is a meaningful "this is extending"
statement while still leaving the trade inside the same event. DC-B is
structurally disadvantaged relative to DC-A — it pays a worse price for the
same R — and that is exactly the comparison being made: *is joining an
extending move worth the price paid for the confirmation?*

### DC-C — overshoot exhaustion

Enter at a confirmation **only when the just-completed run extended at least
`γ × θ`** — i.e. the previous event's overshoot was unusually large.

```
γ = 2.00
```

An overshoot of twice the threshold that defines a directional change is
"unusually extended" in the system's own natural scale, and 2.0 is the roundest
such multiple. **DC-C is by construction a SUBSET of DC-A** and is reported as
a conditioned hypothesis, not an independent one; its result is not
statistically independent of DC-A's.

---

## 5. Entry

1. The signal exists only at its confirmation (DC-A, DC-C) or extension trigger
   (DC-B).
2. A market order is assumed to reach the exchange after **250 ms** — identical
   to Phases 1 and 2.
3. **Entry = the price of the first real trade print with
   `ts_event ≥ signal_ts + 250 ms`.** Never the event extreme, never the
   theoretical threshold price, never a hindsight midpoint.
4. No print within 60 s ⇒ `NO_ENTRY_PRINT`.

Recorded: theoretical level (`ref_price`), the signalling print, the modelled
entry, `entry_slippage = (entry − ref_price) × −direction`, and the slippage
from the signalling print.

---

## 6. Stop, target, first passage

```
R = θ   (the θ that governed the run just ended)
stop   = entry − direction × R
target = entry + direction × R      (primary, 1R)
```

The stop is a **pure distance from the entry**, never a historical extreme, so
nothing about it requires hindsight and everything is known at entry time.
Rails: `1.00 ≤ R ≤ 50.0` points (the lower bound is the θ floor; the upper is an
absurdity check).

**First passage** reuses the Phase-1 rules exactly: a stop-market triggers on a
print at or beyond the stop and fills at that print; a resting limit needs the
tape to trade **through** it by ≥ 1 tick and fills at the limit price — a touch
is not a fill. Ties are impossible because a single print cannot be on both
sides of the entry. Resolution is chronological over raw prints; **no OHLC
inference anywhere**. `src/nqr/p3/fastpass.py` is a chunked implementation that
is asserted equal to the frozen engine on 40 randomised tapes.

**Timeout:** the earlier of entry + 1800 s and 16:00 ET.

**Secondary targets** on the *same* entries, diagnostic only: 0.75R, 1.25R,
1.5R, 2R, plus MFE and MAE. **The primary is 1R and is not reselected
afterwards.**

---

## 7. Portfolio, reset, session, costs

* **One open position at a time, per family.** The three families are separate
  books and are never combined into a composite. A signal arriving while that
  family's position is open is logged `SKIPPED_OVERLAP` and never stacked.
* **Deduplication is structural**: DC-A and DC-C emit at most one signal per
  confirmed event; DC-B's search window ends at the next confirmation, so it
  emits at most one per event. No repeated entry from the same extreme is
  possible.
* **Session**: the engine runs from 08:00 ET (warm-up, no signals). Entries are
  permitted only when *executable* between **09:30:00 and 16:00:00 ET**; a
  signal whose fill lands outside that is logged `OUTSIDE_RTH` and not traded.
* **Costs** reported at **0.0 / 0.5 / 1.0 / 2.0** points round trip, always all
  four. The **primary** verdict uses **1.0 point**.

### Disclosed in advance: the cost arithmetic of this θ

For a symmetric ±R bracket with round-trip friction *f*, the break-even win rate
is `p = 0.5 + f/(2R)`. Measured on development (event geometry only, **no P&L**),
the median θ in the 09:30–11:30 window is **≈ 4.8 points**, so at the primary
friction of 1.0 point a family needs a **gross win rate near 60 %** merely to
reach zero expectancy.

This is stated *before* any P&L is computed. **θ is left at the brief's named
0.50 × VU and the gate is not moved** — adjusting either after noticing the cost
hurdle would be selecting the design for profitability. The consequence is
instead made explicit so the results can be read correctly, and the
pre-authorised θ sensitivity grid (§10) directly shows whether a larger, cheaper
scale changes the conclusion. Gross results are reported alongside every
friction level, so the *directional-information* question is answered
independently of the cost question.

---

## 8. Reporting windows

**PRIMARY: entries executable 09:30:00–11:30:00 ET.** Diagnostics only:
09:30–10:30, 10:30–11:30, 09:30–12:00, 09:30–16:00. **The best-performing window
is not selected afterwards.**

Frequency is reported explicitly: trades/day, median trades/day, share of days
with 0 / 1 / 2 / 3–4 / 5+ trades, first-hour and second-hour counts,
signals/hour, and time between trades.

---

## 9. Pre-registered controls

Defined here, before running.

**C1 — matched random entries (this is also the event-time vs clock-time test).**
For each accepted trade draw `K = 3` control entries matched on trading day,
direction, 30-minute time-of-day bucket and **R in points**, with the entry
print drawn uniformly from that bucket and resolved by the identical
first-passage engine. Answers: *is event-time selection more informative than
entering at a comparable random clock moment?* Reported with a percentile
bootstrap CI on the difference and a permutation p-value.

**C2 — direction control.** At every real signal, resolve the **opposite**
direction from the same entry with the same R. If both directions perform alike
there is no directional information. If the opposite is better, that is recorded
as **evidence against the hypothesis**, not silently traded — an inverse
strategy would be a new pre-registered hypothesis with its own validation.

**C3 — no-edge baseline.** A symmetric ±1R first passage has a 50 % no-edge
baseline by construction, and each asymmetric diagnostic target `m` has
break-even `1/(1+m)`. A high hit rate at a small target is never reported as an
edge without its own baseline alongside.

---

## 10. Pre-authorised diagnostics (after the baseline result is known)

* **θ sensitivity**: 0.25 / 0.50 / 0.75 / 1.00 × VU, development only. These
  are **not** alternative strategies; all of them are reported, including bad
  ones. The baseline stays 0.50 × VU whatever they show.
* **Stability**: by year, by month, long vs short, 09:30–10:30 vs 10:30–11:30,
  volatility quartile, event-size bucket, overshoot-size bucket.

Anything that looks good post hoc goes to `reports/FUTURE_HYPOTHESES.md` marked
`POST-HOC — NOT VALIDATED`, never into this baseline.

---

## 11. Pre-registered PASS gate

Evaluated on **fresh validation 2025-07-01 … 2025-12-31**, **09:30–11:30 ET**,
**1R**, **1.0 point round-trip friction**, **for each family separately**.

A family **PASSES** only if all six hold:

1. executed trades ≥ 100
2. win rate > 50 %
3. win-rate 95 % binomial CI lower bound > 50 %
4. net expectancy > 0 R
5. profit factor > 1.10
6. one-sided binomial p-value vs 50 % < 0.05

**If no family passes, PHASE 3 = FAIL.** Failing families are never combined
into a composite to manufacture a pass.

**PROMISING BUT INCONCLUSIVE** — positive expectancy with a sensible effect size
but insufficient sample, or a confidence interval that includes 50 %/zero. Not
awarded merely because some subgroup was profitable.

Because three families are tested, the multiplicity is reported alongside the
result (a Bonferroni-adjusted threshold of 0.0167 is quoted for reference); the
gate itself is applied exactly as written above.

---

## 12. Integrity commitments

1. This document and `config/baseline.yaml` were completed **before any P&L**.
2. Development (2021–2023) is for engine validation, causality verification and
   diagnostics. **A weak development result does not license a rule change.**
3. 2024 is run **only** as a contaminated diagnostic and is labelled as such
   everywhere. It can never satisfy a PASS criterion and is never used to tune.
4. Fresh validation (2025-H2) is unlocked only after the freeze, and run
   **exactly once**.
5. A genuine implementation **bug** may be fixed: document it, add a regression
   test, bump the implementation version, and rerun everything. **Changing a
   rule because results are poor is not a bug fix.**
6. **2025-H1 and 2026 are never accessed.** There is no code path to them in
   Phase 3.
