# FUTURE_HYPOTHESES.md — Phase 3 post-hoc observations

> ## ⚠ POST-HOC — NOT VALIDATED

Nothing on this page influenced the Phase-3 baseline and nothing here may be
added to it. Each item, if pursued, becomes its **own separately pre-registered
hypothesis** with its own frozen spec and its own untouched validation period.

**Validation data is now nearly exhausted.** 2024 was consumed by Phases 1–2,
2025-H2 by Phase 3. The only untouched periods left are **2025-H1** (sealed for
order-flow research; the last window with both Trades and MBP-1) and
**2026 onward** (the final holdout). Any follow-up must budget for that
scarcity — which is itself an argument for testing fewer, better-motivated
hypotheses from here.

---

## H3-01 · The events carry directional information — pointing the WRONG way

**Observation.** The pre-registered direction control (C2) resolves every real
signal a second time in the **opposite** direction from the same entry with the
same R. On fresh 2025-H2 validation:

| family | signal WR | opposite WR | difference | 95 % CI of difference |
|---|---|---|---|---|
| DC-A | 48.21 % | **49.75 %** | −1.54 pp | [−2.64, −0.46] |
| DC-B | 48.26 % | **49.51 %** | −1.25 pp | [−2.40, −0.06] |
| DC-C | 46.99 % | **50.62 %** | −3.63 pp | [−5.72, −1.43] |

All three intervals exclude zero: trading *with* a confirmed directional change
was significantly **worse** than trading against it. Read plainly, NQ shows mild
**mean reversion** at this event scale — a confirmed θ move tends to be given
back rather than extended.

**Why this is recorded and not traded.** The spec (§9, C2) committed in advance
that a better-performing opposite direction is *evidence against the
hypothesis*, not a strategy to flip into. Three further reasons to be careful:

1. On development the same comparison **straddled zero** (DC-A +0.09 pp, CI
   [−0.91, +1.04]). The effect is not stable across periods.
2. Even at 50.62 %, the best opposite-direction figure is far below the
   **56.8 %** break-even that 1.0 pt friction demands at this θ. An inverse
   strategy would still lose money.
3. It is a single post-hoc comparison on the one fresh period we had.

**A pre-registered follow-up would need** a different scale (θ large enough that
friction is not decisive), an explicit mean-reversion framing, and a fresh
validation window that does not yet exist.

**Status:** `POST-HOC — NOT VALIDATED`

---

## H3-02 · The fill model, not the market, explains most of the sub-50 % result

**Observation.** Every family, every θ, every split lands at 47–49.4 % gross
against a nominal 50 % baseline. That gap is almost entirely accounted for by
two deliberately conservative modelling choices, not by market behaviour:

* **modelled entry slippage** of +0.126 pt (adverse), = 2.07 % of the mean
  R of 6.10 pt;
* **the resting limit must trade THROUGH by one tick** while the stop fills on
  touch.

Predicted win rate under a driftless walk with those asymmetries:

```
P(TP first) ≈ (R − slip) / ((R − slip) + (R + slip + 1 tick))
            = 5.978 / (5.978 + 6.354) = 48.47 %
```

Observed DC-A development: **48.61 %**. The matched random control (C1) lands at
**47.8 %** — i.e. the empirical no-edge baseline under this execution model is
about 48 %, not 50 %.

**Implication for every future candidate in this project.** A symmetric ±1R
bracket does **not** have a 50 % no-edge baseline once realistic fills are
modelled. Future pre-registrations should either state the empirical no-edge
baseline up front, or make the C1 matched-random control the primary comparator
rather than the theoretical 50 %.

**Status:** `POST-HOC — NOT VALIDATED` (as a modelling recommendation, not a
trading idea)

---

## H3-03 · Event-time delivers frequency, which is worth keeping

**Observation.** The one part of the event-time thesis that clearly held: DC
events produce **120 trades/day** in the 09:30–11:30 window with a median 0.76
minutes between trades, and 99.7 % of days have 5 or more opportunities. That is
two orders of magnitude more signal than Phase 1 (0.58/day) or Phase 2
(0.06/day).

Frequency was never the problem in Phase 3 — direction was. A future candidate
that finds genuine directional information could inherit this event
segmentation as its sampling layer and immediately have the statistical power
that Phases 1 and 2 lacked.

**Status:** `POST-HOC — NOT VALIDATED` (infrastructure observation)

---

## H3-04 · Subgroups looked at post hoc on 2025-H2 (all noise)

Fresh-validation DC-A, primary window, 1.0 pt friction. **Not one subgroup has
positive expectancy**, and the only win rate above 50 % has n = 42.

| subgroup | n | WR | 95 % CI | expectancy R |
|---|---|---|---|---|
| SHORT only | 7,738 | 48.75 % | [47.63, 49.86] | −0.203 |
| LONG only | 7,845 | 47.67 % | [46.57, 48.78] | −0.226 |
| 10:00–11:00 ET | 5,935 | 48.36 % | [47.09, 49.63] | −0.184 |
| VU ≥ 16 pt (high vol) | 5,534 | 48.14 % | [46.82, 49.46] | −0.131 |
| prior overshoot 1–2 × θ | 6,550 | 49.48 % | [48.27, 50.69] | −0.185 |
| **DC magnitude ≥ 1.5 × θ** | **42** | **61.90 %** | **[46.81, 75.00]** | **−0.010** |
| August 2025 | 2,646 | 49.77 % | [47.87, 51.68] | −0.188 |

The 61.9 % row is exactly the trap this project has now demonstrated three
times: it has 42 observations, a confidence interval spanning 47–75 %, and
*still* negative expectancy. Phase 1's engulfing subgroup (56.7 % → 45.0 %) and
Phase 2's 09:30–11:30 window (56.1 % → 26.7 %) are the precedents.

**Status:** `POST-HOC — NOT VALIDATED`

---

## H3-05 · Larger θ is cheaper but no more informative

**Observation.** The pre-authorised θ grid on development (all four run on the
same 254-day sample):

| θ | DC-A trades/day | median R | gross WR | 95 % CI | break-even WR @1 pt |
|---|---|---|---|---|---|
| 0.25 × VU | 427.8 | 2.84 pt | 47.96 % | [47.66, 48.25] | 66.1 % |
| **0.50 × VU** | **120.4** | **5.54 pt** | **48.40 %** | **[47.84, 48.96]** | **58.3 %** |
| 0.75 × VU | 55.6 | 8.17 pt | 48.70 % | [47.88, 49.53] | 55.6 % |
| 1.00 × VU | 32.2 | 10.84 pt | 49.27 % | [48.19, 50.36] | 54.2 % |

Gross win rate rises monotonically with θ — but by precisely the amount H3-02
predicts, because a larger R dilutes the fixed one-tick trade-through penalty
and the fixed slippage. It is **not** emerging directional information: the
break-even bar falls more slowly than the win rate rises, so expectancy stays
negative at every grid point (−0.449 → −0.251 → −0.175 → −0.127 R).

Extrapolating, θ would have to be far outside the brief's grid before friction
stopped dominating — at which point the strategy is no longer an event-time
strategy in any meaningful sense.

**Status:** `POST-HOC — NOT VALIDATED`
