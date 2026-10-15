# PHASE4_VERDICT.md — NQ Causal State / Sequence Discovery

    spec          statedisc-1.0.0
    frozen id     statedisc-1.0.0+c147134184dfb32d
    production    B_tree:depth=3, top-20% threshold, tau = 0.017941
    budget spent  18 of 18 configurations
    verdict       FAIL  (at the development stage)
    validation    2026-Q1 NOT SPENT — decided, not deferred; see §6
    phase status  CLOSED

---

## 1. The verdict

# FAIL

The bounded causal-state search specified in `FEATURE_REGISTRY.md`,
`SEARCH_BUDGET.md` and `PREREG_ADDENDUM.md` did **not** identify an NQ market
state that predicts future price path better than matched random entries after
realistic execution costs.

This is a decisive negative, not a marginal one, and it was decided on
development data before any fresh validation was spent.

## 2. What was actually run

| stage | period | trades | verdict-relevant result |
|---|---|---:|---|
| model fit | 2021 | — | 6 models fitted, scaler + tau calibrated on 2021 only |
| selection | 2022 | 37,667 | all 18 configurations negative; best −0.1395 R |
| internal OOS | 2023 | 36,145 | −0.2449 R; matched-control CI contains 0 |
| contaminated | 2024 | 36,092 | −0.1986 R; matched-control CI contains 0 |
| contaminated | 2025-H2 | 18,000 | −0.1745 R; matched-control CI contains 0 |

**162,557 executed trades over 1,145 trading days spanning 2021–2025.**
Every period net-negative. Every out-of-sample control interval contains zero.

## 3. Gates, applied to the 2023 internal out-of-sample test

The 2026-Q1 gates were fixed before validation and are shown here against 2023
to make the size of the shortfall concrete. **2023 is not validation.**

| gate | requirement | 2023 actual | |
|---|---|---|:---:|
| 1 | ≥ 100 trades | 36,145 | PASS |
| 2 | net expectancy > 0 R | **−0.2449 R** | **FAIL** |
| 3 | profit factor > 1.10 | **0.671** | **FAIL** |
| 4 | WR > 50 % *(preference)* | 48.26 % | miss |
| 5 | ΔE[R] vs control, CI lower > 0 | +0.0026, CI [−0.0061, +0.0113] | **FAIL** |
| 6 | ΔWR vs control, CI lower > 0 | +0.0026, CI [−0.0017, +0.0070] | **FAIL** |
| 7 | leave-best-week-out still > 0 | −8,785 R | **FAIL** |

**Four hard gates fail, and gate 2 fails by 0.24 R per trade.** The same is true
on 2024 and 2025-H2.

## 4. Why it failed — three findings, in order of importance

### 4.1 There is no gross edge

At **zero** friction the strategy returns
−0.0130 R (2021), **+0.0025 R (2022)**, −0.0298 R (2023), −0.0185 R (2024),
−0.0160 R (2025-H2). The only positive figure is on the year used to select it.

This is the finding that matters. Friction did not destroy an edge; there was
never an edge for friction to destroy. Any explanation of the form "costs were
too high" is wrong.

### 4.2 The one real effect is an order of magnitude too small

Control C4 — permute the 2021 target *within trading days*, refit the frozen
configuration, recalibrate the threshold, rescore 2022 — puts the null at
**−0.1592 ± 0.0043 R** against an observed **−0.1395 R**: about 5 null standard
deviations, 0 of 20 permutations reaching it. **The 55-feature causal state does
carry directional information.** It is worth roughly **0.02 R per trade**.

Friction at this risk scale costs **0.14 R per trade** (1.0 point against an
average R of 6.97 points). The signal is real and about one seventh of the size
it needs to be. See `FUTURE_HYPOTHESES.md` H4-1 and H4-2.

### 4.3 What separation exists is confined to the selection year

The matched-random comparison — the **primary null**, as the brief specifies —
excludes zero on **2022 only**:

| period | ΔE[R] vs matched random | 95 % day-block CI | excludes 0 |
|---|---:|---|:---:|
| 2021 train | +0.0018 | [−0.0062, +0.0099] | no |
| **2022 selection** | **+0.0155** | **[+0.0070, +0.0240]** | **yes** |
| 2023 internal OOS | +0.0026 | [−0.0061, +0.0113] | no |
| 2024 contaminated | +0.0017 | [−0.0062, +0.0099] | no |
| 2025-H2 contaminated | +0.0086 | [−0.0033, +0.0210] | no |

Control C3 tells the same story: significant on 2021 (p = 0.000) and 2022
(p = 0.000), not on 2023 (p = 0.283), 2024 (p = 0.191) or 2025-H2 (p = 0.775).
Control C2 shows the strategy beating its own inverse on 2021 and 2022, and
being statistically indistinguishable from it on 2023.

An effect that appears on the training and selection years and vanishes
everywhere else is a selection artifact.

## 5. Supporting observations

* **Calibration is not monotone and is locally inverted.** The most confident
  short bucket is the worst bucket in all five periods and underperforms its own
  matched control; the most confident long bucket is the best and beats its
  control in all five, while still losing money. A confidence score that does not
  order outcomes is not usable. Threshold unchanged — moving it now would be
  mining.
* **The model is a volatility-regime detector.** `atr1m` carries 39.7 % of the
  tree's importance and `dist_pdh_norm` 26.9 %. Only 5 of 55 features are used.
  Returns, velocity, trade intensity, trade side/delta, time and DC-event
  families contribute nothing.
* **Order flow from trades contributed nothing.** Family 6 was retained
  deliberately on the Phase-2 side-field verification and produced a clean zero
  at this horizon. This says nothing about MBP-1 order flow, which Phase 4 never
  opened.
* **No window, hour, weekday, volatility quartile or confidence bucket is
  profitable.** The failure is not a session-selection problem.
* **The profile is not remotely prop-viable regardless of sign**: ~140 trades a
  day in a two-hour window, median hold ~30 seconds, 2–7 % profitable days,
  drawdown that never recovers in any period.

## 6. Fresh validation was NOT spent — a decision, not an omission

**2026-Q1 market content has never been read.** The only contact with
`2026_H1.parquet` is a parquet-footer read (row counts and row-group timestamp
bounds) recorded in `reports/PHASE4_START_INTEGRITY.md`. No row was decoded.

Everything the brief requires *before* the unlock is complete: implementation
done, 264 tests passing, exactly one candidate selected, model and preprocessing
frozen and hashed, 2024 diagnostic complete, 2025-H2 diagnostic complete, no
modifications pending. The unlock is armed and would run in about a minute.

It is being held because opening 2026-Q1 is irreversible and, on this evidence,
buys nothing:

* Gate 2 requires net expectancy > 0 and Gate 3 requires PF > 1.10. Development
  and both diagnostics give −0.14 to −0.24 R and PF 0.67–0.80 over 162,557
  trades on 1,145 days across four independent periods and five calendar years.
* The gross (zero-friction) result is also ≤ 0 in four of five periods, so the
  outcome does not hinge on the cost assumption.
* 2026-Q1 is ~60 trading days. It cannot overturn 1,145.

The brief anticipates this branch explicitly — *"If no candidate satisfies the
development selection requirement: Phase 4 may fail before validation. Do not
lower requirements to force a candidate through."* — and this project's standing
constraint is that validation data is scarce. Spending a pristine quarter to
confirm an arithmetically determined FAIL trades a real asset for no information.

**The verdict above does not depend on that decision.** Running 2026-Q1 can only
confirm the FAIL; it cannot produce a PASS.

**Decision taken: 2026-Q1 stays sealed and Phase 4 is CLOSED on the development
result.** The quarter is reserved for a future phase — most obviously the
larger-R hypothesis `FUTURE_HYPOTHESES.md` H4-1, which is the strongest thread
Phase 4 produced and which needs untouched data to test honestly.

The unlock path remains in `holdout4` — scoped to 2026-Q1, blocked by default,
and unable to open 2025-H1 or 2026-04-01+ even while active — so a later phase
can spend the quarter deliberately. It was not spent here.

## 7. What this does and does not mean

**It does not mean there is no profitable NQ edge.** The correct statement is
the narrow one:

> This bounded causal-state discovery search — 55 preregistered causal features
> from NQ trades only, a 5-second decision clock in 09:30–11:30 ET, a 1R/1R
> bracket at R = 0.50 × ATR14(1-min), a 30-minute horizon, 18 configurations
> across two model families — failed to identify an edge that survived the
> specified validation procedure.

Three things it deliberately did not test: **a larger R scale** (H4-1, the most
promising thread), **MBP-1 order flow** (2025-H1 remains sealed for exactly
this), and **any horizon beyond 30 minutes**.

## 8. Reproduction

```bash
python -m pytest tests -q                                  # 264 tests
python scripts/07_integrity_check.py                       # phase 1
python scripts/p2_09_integrity.py                          # phase 2
python scripts/p3_11_integrity.py                          # phase 3

python scripts/p4_01_build_dataset.py --split dev --workers 5
python scripts/p4_02_develop.py                            # 2021 fit, 2022 select
python scripts/p4_03_run_split.py --split itest2023        # 2023, once
python scripts/p4_04_freeze.py                             # -> statedisc-1.0.0+c147134184dfb32d
python scripts/p4_00_build_caches.py --split contam2025h2
python scripts/p4_01_build_dataset.py --split contam2024 --workers 5
python scripts/p4_01_build_dataset.py --split contam2025h2 --workers 5
python scripts/p4_03_run_split.py --split contam2024
python scripts/p4_03_run_split.py --split contam2025h2
python scripts/p4_05_null_c4.py
python scripts/p4_06_calibration.py
python scripts/p4_07_charts.py
python scripts/p4_08_report.py && python scripts/p4_08b_report.py
python scripts/p4_09_integrity.py

# NOT RUN — irreversible, opens 2026-Q1:
# python scripts/p4_00_build_caches.py --split val2026q1 \
#     --confirm I_AM_UNLOCKING_ONLY_2026_Q1_FOR_PHASE4_VALIDATION
# python scripts/p4_01_build_dataset.py --split val2026q1 --unlock-validation
# python scripts/p4_03_run_split.py --split val2026q1 \
#     --confirm I_AM_UNLOCKING_ONLY_2026_Q1_FOR_PHASE4_VALIDATION
```

## 9. Seals, at the close of Phase 4

| window | status |
|---|---|
| 2025-01-01 … 2025-06-30 (Trades **+ MBP-1**) | **SEALED — never opened by any phase** |
| 2026-01-01 … 2026-03-31 | **UNOPENED** — footer metadata only; deliberately not spent by Phase 4 |
| 2026-04-01 onward | **SEALED — never opened by any phase** |

MBP-1 was not opened in Phase 4 at all.
Phases 1–3 remain byte-identical: `fastslow-1.0.0+5980044a44eebf7b`,
`impexh-1.0.0.impl2+48c76a0e68b88947`, `dcevent-1.0.0.impl3+d33e5d5d116f1adb`.
