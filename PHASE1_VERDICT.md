# PHASE 1 VERDICT — Fast-Slow Nasdaq-100

    frozen baseline   fastslow-1.0.0+5980044a44eebf7b
    primary hypothesis  variant ANY, target 1R, 1.0 pt round-trip friction
    validation split    2024-01-01 .. 2024-12-31   (run once, after the freeze)

# VERDICT: FAIL

Produced by `scripts/06_verdict.py`, which applies the rule written in
`FAST_SLOW_SPEC.md` §12 **before any result existed**. No judgement is involved.

| pre-registered gate | required | observed | pass |
|---|---|---|---|
| trades | ≥ 100 | **159** | ✅ |
| win-rate 95 % CI lower bound | > 0.500 | **0.377** | ❌ |
| expectancy (R) | > 0 | **−0.184** | ❌ |
| profit factor | > 1.10 | **0.824** | ❌ |
| one-sided binomial p vs 50 % | < 0.05 | **0.898** | ❌ |

`FAIL` is triggered by the rule's first clause: **expectancy ≤ 0 at 1.0 point
friction.** Four of five gates fail; the fifth (trade count) is the only one met.

---

## 1. What the numbers are

### Primary hypothesis — `ANY` trigger, 1R target

| | development 2021-2023 | validation 2024 |
|---|---|---|
| Globex trading days | 775 | 259 |
| A-B-C instances examined | 27,238 | 9,336 |
| A-B-C patterns passing every gate | 1,830 | 651 |
| …of those, producing a valid reversal trigger | 466 | 166 |
| signals | 466 | 166 |
| **executed trades** | **449** | **159** |
| trades / day | 0.579 | 0.614 |
| long / short | 213 / 236 | 62 / 97 |
| **win rate (gross)** | **0.492** | **0.453** |
| 95 % CI | [0.446, 0.538] | [0.377, 0.530] |
| expectancy, gross | −0.014 R / +0.008 pt | −0.096 R / −0.456 pt |
| expectancy, 0.5 pt friction | −0.063 R / −0.492 pt | −0.140 R / −0.956 pt |
| **expectancy, 1.0 pt friction** | **−0.113 R / −0.992 pt** | **−0.184 R / −1.456 pt** |
| expectancy, 2.0 pt friction | −0.211 R / −1.992 pt | −0.272 R / −2.456 pt |
| profit factor, gross | 1.001 | 0.941 |
| total points, gross | +3.5 | −72.5 |
| max drawdown | 20.8 R | 18.3 R |
| avg / median hold | 8.0 / 4.1 min | 8.3 / 4.6 min |
| avg MAE / MFE | 10.1 / 10.4 pt | 10.8 / 10.5 pt |
| t-stat of mean R (gross) | −0.30 | −1.22 |

Secondary 2R target is worse on both splits (validation: 25.8 % hit rate against
a 33.3 % break-even, −0.268 R gross).

**Gross expectancy on development was +0.008 points per trade.** That is not a
small edge — it is a coin flip measured to three decimal places, and it is
already negative before a single cent of commission.

### The published claim, tested

| | published | development | validation |
|---|---|---|---|
| observations | ≈ 541 | 449 | 159 |
| success at 1:1 | 71.72 % | **49.2 %** | **45.3 %** |
| success at 1:2 | 52.68 % | **33.0 %** | **25.8 %** |

Our sample size is the right order of magnitude, so this is a like-for-like test
rather than a comparison of a big number against a small one. Both published
figures land far outside the 95 % confidence interval of what modern NQ
produced — 71.7 % versus a CI of [0.377, 0.530]. At 1:1 with a 4-tick stop,
**a 71.7 % hit rate is not what this pattern does on NQ in 2021-2024.**

Note also that 33.0 % / 25.8 % at the 2R target are *close to* what pure
randomness gives (33.3 %), which is the signature of a structure with no
directional information, not of a broken implementation.

---

## 2. Why it fails — the diagnosis

**The A-B-C structure fires often enough and is found correctly, but the
reversal at C carries no directional information.**

Evidence:

1. **MAE ≈ MFE, on both splits.** Development 10.09 / 10.44 pt; validation
   10.82 / 10.53 pt. After entry, price travels about as far against the trade
   as with it. A real edge shows MFE > MAE.
2. **Symmetry across direction.** Development longs 51.6 %, shorts 47.0 %;
   validation longs 43.5 %, shorts 46.4 %. Both sides sit on the same coin
   flip and they swap places between splits — nothing systematic.
3. **Stability of the coin flip.** Yearly win rate in development: 49.0 %,
   49.7 %, 49.0 %. This is not a regime that decayed — it never worked in the
   first place.
4. **Costs decide it.** Gross development expectancy is +0.008 pt/trade.
   A single tick of NQ friction (0.25 pt) is 30× that. There is no realistic
   cost assumption under which this is tradeable.
5. **Timeouts are ~0** (2 of 449, 1 of 159), so the result is not an artefact of
   the end-of-day flat rule. Trades resolve, quickly, at close to 50/50.

The pattern is *real* as a geometric object — the randomly-sampled charts show
clean A→B→C structures on genuine session levels with correct 2×+ time ratios.
What it is not is *predictive*.

---

## 3. Subgroups — recorded, and deliberately NOT acted on

Development produced a tempting subgroup and validation destroyed it. This is
the most instructive result in Phase 1:

| trigger family | dev trades | dev win rate | val trades | val win rate |
|---|---|---|---|---|
| **ENGULFING (standalone variant)** | 194 | **56.7 %** (p = 0.036) | 60 | **45.0 %** |
| PIN (standalone variant) | 272 | 43.0 % | 105 | 46.7 % |
| STAR (standalone variant) | 16 | 50.0 % | 4 | 50.0 % |

Engulfing-only cleared a nominal 5 % significance threshold in development and
then reverted to a coin flip out of sample. Had the strategy been *defined* as
"engulfing only" after seeing development, Phase 1 would have reported a false
positive. It was not, because the primary hypothesis was fixed in advance.

The same happens with the time-of-day window the project cares about most:

| 09:30–11:30 ET subset | trades | win rate | 95 % CI | expectancy @1.0 pt |
|---|---|---|---|---|
| development | 102 | 47.1 % | [0.377, 0.567] | −0.125 R |
| validation | 34 | 58.8 % | [0.422, 0.736] | +0.110 R |

The validation figure looks attractive and **means nothing**: n = 34, the
interval spans 0.42–0.74, and the same subset was *below* 50 % in the three
development years. It is reported because the brief asked for it, and it is not
promoted, because promoting it would be exactly the error this whole protocol
exists to prevent.

Time-ratio buckets tell the same story — 2.5–3.0× looked best in development
(55.8 %) and 2.0–2.5× was the worst in validation (33.3 %) with no consistency
between them.

---

## 4. What was NOT done

* No parameter was changed after seeing development results, and nothing was
  changed after seeing validation results.
* Validation was run **once**, on the frozen configuration.
* No subgroup was promoted to "the strategy".
* No month, level family, session or trigger family was dropped.
* No cost assumption was selected — all four friction levels are printed in
  every table.
* **No 2025 or 2026 data was read, sampled, summarised, or used in any
  normalisation.** The bar cache's maximum trading date is 2024-12-31 and the
  guard is unit-tested.

## 5. Two implementation defects found during development

Both were found by Stage-A verification, both are data-plumbing rather than
strategy parameters, both now have regression tests, and the development run
reproduced identical counts after each fix:

* **Int8 overflow in the session label.** `polars`' `dt.hour()` returns `Int8`,
  so `hour*60 + minute` wrapped and every bar was labelled `ASIA`.
* **Tick cache not sorted by `ts_event`.** The source files are sorted by
  `ts_recv`; roughly 1 row in 3 million has a different `ts_event` ordering,
  which would have made the backtester's binary search over the tape subtly
  wrong.

## 6. Confidence in the implementation

Beyond 80 unit and integration tests, every accepted trade in both splits was
audited programmatically:

* entry always ≥ signal + 250 ms (observed min 250.1 ms, median 344 ms);
* `R == (entry − stop) × direction`, and stop always exactly 4 ticks beyond the
  complete trigger pattern's extreme;
* every TP exit fills at exactly the target price, giving exactly +1.000 R;
* every SL exit fills at or beyond the stop, worst case −1.043 R (real stop
  slippage, not assumed away);
* MFE ≥ R on every TP, MAE ≥ R on every SL;
* a randomly-sampled signal set reproduces identically when the bar history is
  truncated at the moment each signal became knowable — the no-lookahead test.

A worked example is checked bar by bar against the raw data in the development
chart set; the algorithm identifies exactly the structure it is supposed to.

---

## 7. Conclusion and what happens next

**Fast-Slow, implemented faithfully and tested honestly, has no edge on NQ over
2021-2024.** The published 71.72 % / 52.68 % figures do not reproduce, by a
margin far larger than sampling error.

This closes candidate #1. It does **not** close the project, and it says nothing
about whether NQ has an exploitable edge — only that this particular pattern,
with this particular stop and target, is not it.

Preserved and reusable, unchanged, for every later candidate:

* the read-only T9 audit and the front-contract/roll machinery;
* the 2.1 GB front-contract tick cache and the 708 122-bar 2-minute series;
* Globex-day / session / DST calendar and causal prior-session levels;
* the tick-exact backtester (trade-through limits, touch-fill stops, real
  MFE/MAE) and the friction sweep;
* the metrics, reporting and random-sample chart diagnostics;
* the holdout guard.

**The 2025-01-01 → 2025-06-30 sealed holdout and the 2025-07-01+ extra holdout
are untouched and remain available for the strategies that earn the right to be
tested on them.**

Next established candidates, each to be pre-registered separately before any
backtest is run: NQ impulse exhaustion / absorption, failed-continuation
reversal, directional-change / event-time strategies, automated price-sequence
discovery, and MBP-1 order-flow work.
