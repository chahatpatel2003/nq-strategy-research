# PHASE 3 VERDICT — NQ directional-change / event-time strategy

    frozen baseline   dcevent-1.0.0.impl3+d33e5d5d116f1adb
    theta             0.50 x VU  (VU = ATR14 of completed 1-minute bars)
    fresh validation  2025-07-01 .. 2025-12-31   (128 trading days, run once)
    gate              09:30-11:30 ET · 1R · 1.0 pt round-trip friction · per family

# VERDICT: FAIL

Produced by `scripts/p3_10_verdict.py`, applying the rule written in
`DIRECTIONAL_CHANGE_SPEC.md` §11 **before any P&L existed**. No judgement is
involved. **No family passed, and failing families were not combined into a
composite.**

| gate | required | DC-A | DC-B | DC-C |
|---|---|---|---|---|
| executed trades | ≥ 100 | 15,583 ✅ | 14,603 ✅ | 4,182 ✅ |
| win rate | > 50 % | 48.21 % ❌ | 48.26 % ❌ | 46.99 % ❌ |
| 95 % CI lower bound | > 50 % | 47.42 % ❌ | 47.45 % ❌ | 45.48 % ❌ |
| net expectancy | > 0 R | −0.214 ❌ | −0.215 ❌ | −0.245 ❌ |
| profit factor | > 1.10 | 0.709 ❌ | 0.713 ❌ | 0.674 ❌ |
| one-sided binomial p | < 0.05 | 1.000 ❌ | 1.000 ❌ | 1.000 ❌ |
| **family verdict** | | **FAIL** | **FAIL** | **FAIL** |

Three families were tested; a Bonferroni-adjusted threshold would be 0.0167.
The gate was applied exactly as pre-registered — the adjustment is academic
here, since no family came close.

---

## 1. Sample size was never the problem

Phases 1 and 2 were sample-limited. Phase 3 is not, by two orders of magnitude:

| | Phase 1 | Phase 2 | **Phase 3 (DC-A)** |
|---|---|---|---|
| trades/day, primary window | 0.58 | 0.06 | **120.4** |
| development trades | 449 | 161 | **91,782** |
| fresh-validation trades | 159 | 45 | **15,583** |

At n = 15,583 the validation win-rate confidence interval is ±0.8 pp. This is a
**decisive** measurement, not an inconclusive one.

---

## 2. What the numbers are

### Primary hypothesis, 09:30–11:30 ET, 1R, 1.0 pt friction

| | dev 2021-23 | 2024 ⚠ diagnostic | **2025-H2 fresh** |
|---|---|---|---|
| **DC-A** trades | 91,782 | 29,852 | **15,583** |
| win rate | 48.41 % | 48.86 % | **48.21 %** |
| 95 % CI | [48.08, 48.73] | [48.29, 49.42] | **[47.42, 48.99]** |
| break-even WR at 1.0 pt | 58.19 % | 58.06 % | **56.74 %** |
| expectancy, gross | −0.030 R | −0.016 R | **−0.040 R** |
| expectancy, 1.0 pt | −0.245 R | −0.209 R | **−0.214 R** |
| profit factor | 0.685 | 0.714 | **0.709** |
| **DC-B** WR / exp @1 pt | 48.39 % / −0.247 | 48.51 % / −0.227 | **48.26 % / −0.215** |
| **DC-C** WR / exp @1 pt | 48.16 % / −0.257 | 48.81 % / −0.222 | **46.99 % / −0.245** |

**⚠ 2024 IS NOT FRESH VALIDATION.** It was consumed as the validation split in
Phases 1 and 2 and is shown only as historical diagnostic evidence. It never
entered the verdict.

The result reproduced almost exactly on data never previously touched: gross win
rate 48.4 % → 48.9 % → 48.2 % across four years and three splits, with every
confidence interval excluding 50 %.

### Every target fails against its own no-edge baseline

Same entries, development DC-A, primary window. A high hit rate at a small
target is not an edge:

| target | win rate | no-edge break-even | excess | expectancy @1 pt |
|---|---|---|---|---|
| 0.75R | 55.42 % | 57.14 % | **−1.72 pp** | −0.247 R |
| **1R (primary)** | 48.61 % | 50.00 % | **−1.39 pp** | −0.245 R |
| 1.25R | 43.41 % | 44.44 % | **−1.04 pp** | −0.241 R |
| 1.5R | 39.18 % | 40.00 % | **−0.82 pp** | −0.238 R |
| 2R | 32.69 % | 33.33 % | **−0.64 pp** | −0.237 R |

---

## 3. The controls answer the research question directly

The research question was *does event-time price structure itself carry
directional information?* Two pre-registered controls answer it.

### C2 — direction control (the decisive test)

Every real signal resolved a second time in the **opposite** direction, same
entry, same R. If the events carried directional information, trading with the
change should beat trading against it.

| | development | **2025-H2 fresh** |
|---|---|---|
| DC-A signal vs opposite | +0.09 pp, CI [−0.91, +1.04] | **−1.54 pp, CI [−2.64, −0.46]** |
| DC-B signal vs opposite | −0.30 pp, CI [−1.27, +0.67] | **−1.25 pp, CI [−2.40, −0.06]** |
| DC-C signal vs opposite | −0.62 pp, CI [−1.63, +0.33] | **−3.63 pp, CI [−5.72, −1.43]** |

On development the difference straddled zero — **no directional information**.
On fresh validation all three intervals exclude zero on the *negative* side:
trading the confirmed direction was significantly **worse** than trading against
it. Per §9 of the spec that is recorded as **evidence against the hypothesis**,
not silently flipped; it is logged as `H3-01` in `FUTURE_HYPOTHESES.md`. Note
that even the opposite direction (50.6 % at best) sits far below the 56.7 %
break-even, so an inverse strategy would still lose money at this scale.

### C1 — matched random entries (also the event-time vs clock-time test)

Controls matched on trading day, direction, 30-minute bucket and R:

| | development | **2025-H2 fresh** |
|---|---|---|
| DC-A signal vs random | +0.75 pp, p = 0.031 | **+0.18 pp, p = 0.353** |
| DC-B signal vs random | −0.91 pp, p = 0.990 | **−1.62 pp, p = 1.000** |
| DC-C signal vs random | +1.13 pp, p = 0.003 | **+0.03 pp, p = 0.494** |

The marginal development effects vanished out of sample. **Event-time selection
is not more informative than entering at a comparable random clock moment.**

---

## 4. Why the win rate sits near 48 %, not 50 %

Almost the entire gap is the deliberately conservative execution model, not the
market:

* modelled entry slippage **+0.126 pt adverse** (2.07 % of the mean R of 6.10 pt);
* a resting limit must trade **through** by one tick, while the stop fills on touch.

Under a driftless walk those asymmetries predict

```
P(TP first) ≈ 5.978 / (5.978 + 6.354) = 48.47 %
```

against an observed development DC-A rate of **48.61 %**, and the matched random
control lands at **47.8 %**. So the empirical no-edge baseline under this
execution model is ≈ 48 %, and the events sit essentially exactly on it.

**This matters for the whole project** and is logged as `H3-02`: a symmetric ±1R
bracket does *not* have a 50 % no-edge baseline once realistic fills are
modelled. Future pre-registrations should make the matched-random control the
primary comparator.

---

## 5. θ sensitivity — pre-authorised, and it changes nothing

All four grid points on the same 254-day development sample:

| θ | trades/day | median R | gross WR | 95 % CI | expectancy @1 pt | break-even WR |
|---|---|---|---|---|---|---|
| 0.25 × VU | 427.8 | 2.84 pt | 47.96 % | [47.66, 48.25] | −0.449 R | 66.1 % |
| **0.50 × VU (baseline)** | **120.4** | **5.54 pt** | **48.40 %** | **[47.84, 48.96]** | **−0.251 R** | **58.3 %** |
| 0.75 × VU | 55.6 | 8.17 pt | 48.70 % | [47.88, 49.53] | −0.175 R | 55.6 % |
| 1.00 × VU | 32.2 | 10.84 pt | 49.27 % | [48.19, 50.36] | −0.127 R | 54.2 % |

Gross win rate rises with θ by exactly the amount §4 predicts — a larger R
dilutes the fixed one-tick and slippage penalties — while the break-even bar
falls more slowly, so expectancy is negative at every point. **The baseline was
not changed and could not have been improved into a pass by any grid point.**

---

## 6. Frequency: the one part of the thesis that held

DC-A, primary window, development:

| | value |
|---|---|
| trades / day (mean, median) | 120.4, 120.0 |
| % days with 5+ trades | 99.74 % |
| % days with 0 trades | 0.26 % |
| trades/day 09:30–10:30 | 74.7 |
| trades/day 10:30–11:30 | 45.7 |
| median minutes between trades | 0.76 |
| median hold | 19 s |

Event-time genuinely delivers the opportunity density Phases 1 and 2 lacked.
It just does not deliver direction. Logged as `H3-03`.

---

## 7. Implementation confidence

* **218 tests pass**, including the full Phase-1 and Phase-2 suites unchanged.
* `reports/PHASE3_INTEGRITY_AUDIT.md`: **all checks pass**.
* The causal engine is verified three independent ways — truncating the price
  path at each confirmation reproduces the identical event; overwriting all
  later prices leaves earlier events unchanged; `conf_idx > ext_idx` holds on
  100 % of 643,758 development events.
* `src/nqr/p3/fastpass.py` is asserted **equal to the frozen Phase-1 engine** on
  40 randomised tapes.
* Randomly sampled charts draw the extreme as a hollow marker at the time it
  printed and shade the interval before confirmation, so a lookahead entry would
  be visually obvious. 246 charts were generated across raw DC sequences and
  per-family winners/losers.

### Two bugs found and fixed

| version | bug | effect on P&L |
|---|---|---|
| `impl2` | polars schema-inference crash: skipped rows omitted the target columns, so an all-null prefix typed `Null` and a real int64 timestamp could not be appended | **none** — the crash was at the write step; no P&L was ever observed |
| `impl3` | `entry_slippage` sign inverted, reporting favourable slippage as positive instead of the project-wide adverse-positive convention | **none — verified byte-identical**: dev and 2024 trade fingerprints matched exactly before and after |

Each was documented, given a regression test, bumped the implementation version,
and forced a full rerun. **No strategy rule was changed at any point**, and both
fixes landed before 2025-H2 was unlocked.

---

## 8. Conclusion

**NQ shows no repeatable directional edge after directional-change events or
their overshoots, at the pre-registered scale.** The answer to the research
question — *continuation, reversal, or neither?* — is:

> **Neither.** On development the events are directionally indistinguishable
> from random comparable entries. On fresh validation the confirmed direction is
> significantly *worse* than its own opposite, which is a mild mean-reversion
> tendency — but one too small to overcome friction, and one that was absent in
> development.

The evidence is decisive rather than marginal:

* 15,583 fresh-validation trades put the win-rate CI at ±0.8 pp, and it excludes
  50 %;
* the result reproduced across 2021, 2022, 2023, 2024 and 2025-H2;
* every target from 0.75R to 2R sits below its own no-edge break-even;
* every θ in the pre-authorised grid is negative;
* the matched-random control shows event-time selection adds nothing;
* the direction control shows the events point mildly the wrong way.

This closes candidate #3. It says nothing about whether NQ has an exploitable
edge — only that *this* directional-change specification does not have one.

**2025-H1 was never accessed** and remains the only untouched period holding
both Trades and MBP-1. **2026 was never accessed** and remains the final
holdout. Phase 1's and Phase 2's frozen ids are unchanged and all their
deliverables are intact.

Preserved and reusable for candidate #4: the causal DC event engine and its
643,758-event development log, the verified fast first-passage resolver, the
narrow three-way period guard, the matched-random and direction-control harness,
the event-time frequency layer, and the lookahead-visible chart apparatus.

**A note on what is left.** Validation data is now scarce: 2024 is contaminated,
2025-H2 is consumed. Candidate #4 must either be tested on 2025-H1 — spending
the order-flow reserve — or wait for new data. That argues for fewer, better
motivated hypotheses from here, and for making `H3-02`'s corrected no-edge
baseline standard practice so that future results are read correctly the first
time.
