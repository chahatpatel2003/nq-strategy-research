# PHASE 2 VERDICT — impulse exhaustion / absorption reversal

    frozen baseline     impexh-1.0.0.impl2+48c76a0e68b88947
    primary hypothesis  09:30-11:30 ET · 1R target · 1.0 pt round-trip friction
    validation split    2024-01-01 .. 2024-12-31   (run once, after the freeze)

# VERDICT: FAIL

Produced by `scripts/p2_08_verdict.py`, applying the rule written in
`IMPULSE_EXHAUSTION_SPEC.md` §14 **before any P&L existed**. No judgement is
involved.

| # | pre-registered gate | required | observed | pass |
|---|---|---|---|---|
| 1 | executed trades | ≥ 100 | **15** | ❌ |
| 2 | net expectancy | > 0 R | **−0.668 R** | ❌ |
| 3 | profit factor | > 1.10 | **0.288** | ❌ |
| 4 | win rate | > 50 % | **26.7 %** | ❌ |
| 5 | win-rate 95 % CI lower bound | > 50 % | **10.9 %** | ❌ |
| 6 | one-sided binomial p vs 50 % | < 0.05 | **0.982** | ❌ |

All six gates fail. `FAIL` is reached through the rule's own clause — negative
expectancy and PF ≤ 1 — not merely through the sample-size gate.

---

## 1. The sample-size problem was disclosed before validation, not after

`IMPULSE_EXHAUSTION_SPEC.md` §14.1 recorded, before validation was run, that the
specification produces ~20 signals per year in the primary window, so **gate 1
was known to be unreachable in one year**. The gate was left unchanged rather
than moved. That is why the substantive evidence below rests on the wider
09:30–16:00 diagnostic window and on the three-year development sample, both of
which are clearly labelled diagnostics and can never produce a `PASS`.

The frequency is not a tuning artefact: the pre-freeze count check
(`results/p2_count_calibration.json`, counts only) showed signal frequency is
**insensitive to the impulse threshold across the brief's entire suggested
region** — 0.75–1.25 VU and 30–120 s all yield 60–65 signals in 2021. The
binding constraints are Stage B (three strictly increasing confirmed peaks) and
Stage C (double deterioration), both mandated by the hypothesis and therefore
not relaxed.

---

## 2. What the numbers are

### Primary hypothesis — 09:30–11:30 ET, 1R, 1.0 pt friction

| | development 2021–2023 | validation 2024 |
|---|---|---|
| trades | 57 | **15** |
| win rate | 56.1 % | **26.7 %** |
| 95 % CI | [0.433, 0.682] | [0.109, 0.520] |
| expectancy | −0.057 R | **−0.668 R** |
| profit factor | 0.895 | **0.288** |
| max drawdown | 10.2 R | 10.0 R |
| longest losing streak | 5 | 5 |

### Diagnostic window — 09:30–16:00 ET, 1R, 1.0 pt friction

| | development 2021–2023 | validation 2024 |
|---|---|---|
| trades | **161** | **45** |
| win rate | **46.6 %** | **46.7 %** |
| 95 % CI | [0.390, 0.543] | [0.329, 0.609] |
| expectancy, gross | −0.069 R | −0.067 R |
| **expectancy, 1.0 pt** | **−0.295 R** | **−0.301 R** |
| profit factor | 0.660 | 0.504 |
| trades / day | 0.211 | 0.176 |
| avg MFE / MAE (pts) | 4.22 / 3.78 | 3.76 / 3.83 |
| median hold | 27 s | 22 s |

**The out-of-sample reproduction is the informative result.** Full-RTH win rate
was 46.6 % on three years of development and 46.7 % on validation; expectancy at
1.0 point friction was −0.295 R and −0.301 R. The strategy did not decay — it
reliably reproduced a small negative edge.

### Development by year (09:30–16:00, 1R, 1.0 pt)

| year | trades | win rate | expectancy R | PF |
|---|---|---|---|---|
| 2021 | 47 | 55.3 % | −0.153 | 0.856 |
| 2022 | 67 | 41.8 % | −0.342 | 0.666 |
| 2023 | 47 | 44.7 % | −0.369 | 0.494 |

### Target sensitivity on the SAME entries (09:30–16:00, 1.0 pt)

Every target loses on both splits, and each sits below its own break-even.

| target | break-even WR | dev WR | dev exp R | val WR | val exp R |
|---|---|---|---|---|---|
| **1R (primary)** | 50.0 % | 46.6 % | −0.295 | 46.7 % | −0.301 |
| 1.25R | 44.4 % | 40.4 % | −0.318 | 40.0 % | −0.334 |
| 1.5R | 40.0 % | 34.8 % | −0.357 | 35.6 % | −0.346 |
| 2R | 33.3 % | 30.4 % | −0.314 | 31.1 % | −0.321 |

---

## 3. Component ablation — which part carries information?

Development, 1.0 pt friction. **D is the strategy**; A/B/C are diagnostics.

| variant | gates | window | trades | win rate | 95 % CI | expectancy R | PF |
|---|---|---|---|---|---|---|---|
| **A** impulse only | A | 09:30–16:00 | **39 035** | **48.15 %** | [0.4766, 0.4865] | −0.427 | 0.452 |
| **B** + deterioration | A+B+C | 09:30–16:00 | 302 | 49.01 % | [0.434, 0.546] | −0.308 | 0.626 |
| **C** + absorption | A+B+C+D | 09:30–16:00 | 208 | 49.52 % | [0.428, 0.563] | −0.297 | 0.629 |
| **D** full baseline | all | 09:30–16:00 | 161 | 46.58 % | [0.390, 0.543] | −0.295 | 0.660 |

Three things follow, and only the first is statistically strong:

1. **A naked impulse reversal at 1R is a reliable small loser.** With 39 035
   trades the CI is [0.4766, 0.4865] — decisively below 50 %. Placing the stop
   four ticks beyond the impulse extreme and targeting 1R is *worse* than a coin
   flip, gross, before any commission. The extreme gets swept slightly more often
   than the symmetric target gets reached.
2. **The exhaustion filters add nothing detectable.** 48.15 % → 49.01 % → 49.52 %
   is a ~1.4-point drift across three stacked filters, each step well inside its
   own confidence interval, while the sample collapses by two orders of
   magnitude. There is no evidence that aggression deterioration or the
   absorption proxy carries directional information.
3. **The failed-continuation trigger did not help either**; D is not better than
   B or C on the diagnostic window.

### Absorption and efficiency measure nearly the same thing

The absorption gate rejected only **26 of 61 348** candidates. This is structural,
not a bug: Stage C's efficiency test (points of progress per aggressive contract,
falling) and Stage D's absorption proxy (aggressive volume per tick of
best-price advance, rising) are near-reciprocal. Once a candidate has passed
Stage C it has almost always passed Stage D. This was found from a **count**
diagnostic before the freeze, disclosed in the spec, and deliberately **not**
engineered away — variant B vs C is the instrument that measures it, and it
measures ≈ nothing.

---

## 4. Random-control and null tests (pre-registered §13)

Controls match each signal on trading day, direction, 30-minute time-of-day
bucket and **R in points**, drawing 5 control entries per signal from traded
seconds, resolved by the identical first-passage engine.

| | development | validation |
|---|---|---|
| signal WR | 56.1 % (n=57) | **26.7 % (n=15)** |
| control WR | 44.6 % (n=285) | **56.0 % (n=75)** |
| difference | +11.6 pp | **−29.3 pp** |
| bootstrap 95 % CI of difference | [−2.1, +25.3] pp | **[−53.3, −4.0] pp** |
| permutation p (signal > control) | 0.076 | 0.991 |
| expectancy difference | +0.233 R, CI [−0.053, +0.515] | −0.583 R, CI [−1.045, −0.069] |

On development the signal did not significantly beat a comparable random entry
(p = 0.076, CI straddling zero). **On validation it was significantly *worse*
than random**: the CI of the difference excludes zero on the negative side.

**Label-shuffle null** (2 000 replications; entry time, entry price and R held
fixed, direction labels randomly reassigned preserving the long/short mix):

| | development | validation |
|---|---|---|
| null WR mean | 50.3 % | 49.8 % |
| real WR percentile in null | 0.779 | **0.023** |
| real expectancy percentile in null | 0.281 | **0.005** |

On development the real result sits in the middle of the null distribution — no
edge. On validation it sits in the bottom 2 % of it.

---

## 5. Prop-firm profile (09:30–11:30, 1R, 1.0 pt)

| | development | validation |
|---|---|---|
| trades / day | 0.075 | 0.059 |
| % days with zero trades | 93.0 % | 94.1 % |
| % days with 1 trade | 6.4 % | 5.9 % |
| % days with 2 trades | 0.5 % | 0.0 % |
| % days with 3+ trades | 0.0 % | 0.0 % |
| % profitable days | 54.7 % | 26.7 % |
| worst day | −2.35 R | −1.33 R |
| daily R 5th percentile | −1.23 R | −1.30 R |
| max drawdown | 10.2 R | 10.0 R |
| longest stretch below equity peak | 24 days | 15 days |

Even setting profitability aside, **the strategy trades on 6–7 % of days**. That
alone makes it unusable as a primary automated NQ strategy on this window.

---

## 6. Implementation confidence

* **130 tests pass**, 50 of them Phase-2-specific; the full Phase-1 suite is
  untouched and still green.
* `reports/PHASE2_LEAKAGE_AUDIT.md` verifies all ten required properties, with
  automated tests behind each.
* Every accepted trade in both runs satisfies: entry ≥ signal + 250 ms; exit ≥
  entry; signal ≥ arm ≥ impulse end; every leg confirmation ≤ arm; stop exactly
  4 ticks beyond the exhaustion extreme; `R = (entry − stop) × direction`.
* **Aggressor classification was verified, not assumed**: the native Databento
  `side` field agrees with a causal quote rule rebuilt from MBP-1 on
  **99.998 % of 3 882 344 unambiguous trades** across 12 development days
  (62 disagreements). Inside-spread trades are 0.013 % and are left UNKNOWN — no
  tick-rule guessing.
* Randomly sampled charts (20 winners, 20 losers, 20 highest-absorption, 20
  lowest-qualifying-absorption, plus skipped) show the state machine identifying
  exactly the structure it is specified to identify.

### One bug found and fixed

`compute()` derived the break-even win rate from the target tag and only
recognised Phase-1's `r1`/`r2`. Phase-2's tags (`r1p0`, `r1p25`, `r1p5`, `r2p0`)
fell through to a 1/3 null, so reported binomial p-values tested the wrong
hypothesis. This affected **reporting only**. It was fixed, given a regression
test, the implementation version was bumped `impl1 → impl2`, and everything was
re-run: the dev and validation trade sets are **byte-identical**
(fingerprints `3562a911…` and `39c08e6b…` before and after). The corrected
validation p-value is 0.982 rather than 0.791; the verdict is unchanged.

---

## 7. Conclusion

**The Širc-style impulse exhaustion / absorption reversal concept, implemented
mechanically and tested honestly, shows no directional edge on NQ over
2021–2024.**

The evidence is consistent rather than marginal:

* the full-RTH win rate reproduced almost exactly out of sample (46.6 % → 46.7 %)
  and is below the 50 % break-even at 1R;
* every target from 1R to 2R sits below its own break-even on both splits;
* the ablation shows the naked impulse is already a slight loser at n = 39 035,
  and the three exhaustion filters add nothing measurable;
* the strategy did not beat matched random entries on development and was
  significantly worse than them on validation;
* the label-shuffle null places the development result at the middle of the null
  distribution.

Two secondary findings are worth carrying forward:

1. **The stop placement is probably the mechanical culprit.** Four ticks beyond
   a fresh extreme is exactly where a resting-stop cluster sits; with a symmetric
   1R target the extreme is swept slightly more often than the target is reached.
   Any future reversal family should treat stop placement as a first-class design
   variable rather than inheriting the paper's convention.
2. **Efficiency deterioration and the absorption proxy are near-redundant.** A
   future order-flow candidate should not spend two independent gates on what is
   arithmetically one measurement.

This closes candidate #2. It says nothing about whether NQ has an exploitable
edge — only that this particular microstructure story, with this stop and this
target, is not it.

**The 2025-01-01 → 2025-06-30 sealed holdout and the 2025-07-01+ extra holdout
remain untouched.** Phase 1's frozen id is unchanged and all its deliverables are
intact.

Preserved and reusable for candidate #3: the verified trade-signing engine, the
1.8 GB signed front-contract tick cache, the 655 MB 1-second MBP-1 BBO cache
(48 months), the causal VU and directional-change machinery, the absorption
framework, the state-machine scaffold, the control/null test harness, the
prop-firm metrics, and the leakage-audit apparatus.
