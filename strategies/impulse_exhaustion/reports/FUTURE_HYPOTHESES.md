# FUTURE_HYPOTHESES.md — Phase 2 post-hoc observations

> ## ⚠ OBSERVED POST-HOC — REQUIRES NEW VALIDATION DATA

Nothing on this page influenced the Phase-2 baseline and nothing here may be
added to it. Each item, if pursued, becomes its **own separately pre-registered
hypothesis** with its own frozen spec and its own untouched validation period —
and it may **not** inherit 2024, which Phase 2 has now consumed.

This file exists so that interesting-looking structure is *recorded rather than
acted on*. Phase 1 supplied the cautionary example: an engulfing subgroup at
56.7 % on development collapsed to 45.0 % out of sample. Phase 2 supplied a
second: the 09:30–11:30 window looked like the best subgroup on development
(56.1 %) and was the **worst** on validation (26.7 %).

Every number below is development-only (2021–2023), 09:30–16:00 ET, 1R, 1.0 pt
friction, and every one of them has a sample size small enough that the
confidence intervals overlap the whole table.

---

## H2-01 · Stop placement, not the signal, may be the binding constraint

**Observation.** Ablation A measured a naked impulse reversal at 1R across
**39 035 trades**: win rate 48.15 %, CI [0.4766, 0.4865]. Placing the stop four
ticks beyond a fresh extreme and targeting 1R is *reliably* worse than a coin
flip, gross. The sample is large enough that this is a real effect, not noise.

**Why it might be mechanical.** A fresh extreme is exactly where resting stop
orders cluster. Four ticks beyond it is inside the sweep zone, so the stop is
reached slightly more often than the symmetric target.

**What a pre-registered follow-up would look like.** Treat stop distance as a
first-class design variable rather than inheriting the paper's convention —
e.g. a volatility-scaled stop placed beyond the *quote* rather than beyond the
last print, or a stop derived from the impulse leg rather than from the extreme.
This is the single most promising thread Phase 2 produced, and it is **not** an
adjustment to Phase 2: it is a different hypothesis.

**Status:** `OBSERVED POST-HOC — REQUIRES NEW VALIDATION DATA`

---

## H2-02 · Efficiency deterioration and the absorption proxy are near-redundant

**Observation.** Stage D rejected only 26 of 61 348 candidates, and variant B
(no absorption) versus variant C (with absorption) differ by 0.5 pp of win rate
on 302 vs 208 trades. The two gates are arithmetically near-reciprocal: points
of progress per aggressive contract falling ⇔ aggressive volume per point of
progress rising.

**Implication for later order-flow work.** Do not spend two independent gates on
one measurement. A future candidate should pick one and use the freed degree of
freedom on something orthogonal — e.g. queue replenishment at the touch, or
trade-size distribution rather than trade-size total.

**Status:** `OBSERVED POST-HOC — REQUIRES NEW VALIDATION DATA`

---

## H2-03 · Structure seen in development subgroups (recorded, not acted on)

All development-only, all with overlapping confidence intervals, all n small.

| subgroup | n | WR | exp R | PF |
|---|---|---|---|---|
| SHORT only | 90 | 50.0 % | −0.241 | 0.729 |
| LONG only | 71 | 42.3 % | −0.363 | 0.591 |
| 09:30–10:00 ET (hour 9) | 11 | 72.7 % | +0.308 | 1.721 |
| 15:00–16:00 ET (hour 15) | 29 | 31.0 % | −0.625 | 0.501 |
| impulse 1.75–2.5 × VU | 6 | 50.0 % | −0.131 | 1.361 |
| stop < 0.30 × VU | 4 | 75.0 % | +0.212 | 1.842 |
| stop ≥ 0.75 × VU | 3 | 66.7 % | +0.187 | 1.013 |
| absorption pct ≥ 0.96 | 19 | 36.8 % | −0.517 | 0.376 |

**Read these as noise.** The two positive-expectancy rows have n = 4 and n = 3.
The hour-9 row has n = 11. Not one of them survives a multiple-comparison
correction, and Phase 2 has already demonstrated twice over that a flattering
development subgroup is the least reliable object in this project.

Note in particular that the **highest** absorption bucket has the **worst**
outcome (36.8 %, n = 19) — the opposite of the hypothesis's prediction. That is
weak evidence, but it points the same way as the ablation.

**Status:** `OBSERVED POST-HOC — REQUIRES NEW VALIDATION DATA`

---

## H2-04 · Signal frequency is structurally low

**Observation.** Requiring three strictly increasing confirmed directional-change
peaks after an impulse is what makes this family rare: 71 % of candidates die at
`NOT_A_NEW_EXTREME`. The result is 0.2 trades/day across full RTH and trades on
only 6–7 % of days in the primary window.

**Implication.** Any future candidate intended as a *primary* automated NQ
strategy on the 09:30–11:30 window needs a signal that fires on a meaningful
fraction of days. Frequency should be a design constraint stated up front, and
checked on counts alone before the spec is frozen — as was done here.

**Status:** `OBSERVED POST-HOC — REQUIRES NEW VALIDATION DATA`
