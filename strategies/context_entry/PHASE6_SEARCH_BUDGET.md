# PHASE6_SEARCH_BUDGET.md

**Declared BEFORE any Phase-6 expectancy, win rate or P&L was examined.**

Phase 6 is a post-hoc hypothesis born from Phase-5 diagnostics, which makes the
budget tighter than any previous phase, not looser.

---

## 1. What is fixed and may not be touched

Everything except the entry moment. All of the following is **inherited frozen
from Phase 5** and reused read-only:

| dimension | frozen value | source |
|---|---|---|
| direction model | `r4p0:A_logit:top2` — elastic-net logistic, C=0.1, l1_ratio=0.5 | `strategies/larger_r/models/production_model.pkl` |
| features | the 55 Phase-4 causal features, unchanged | `nqr.p4.features4` |
| preprocessing | winsorise 0.1/99.9 + standardise, 2021-fitted | frozen `Preprocessor` |
| direction logic | edge over the training-only per-bucket control baseline | `nqr.p5.model5.edge_and_direction` |
| threshold | `tau = 0.179938` (top 2 % on 2021) | frozen |
| R | `clip(4.0 × ATR14(completed 1-min, floor 2.0), 5.0, 200.0)` pt | `nqr.p5.dataset5` |
| RR | 1R target / 1R stop, off the **realised entry price** | frozen |
| maximum hold | 60 minutes from entry | frozen |
| timeout | first executable print at or after the cutoff | `nqr.p5.labels5.resolve_p5` |
| hard rail | 16:00 ET | frozen |
| execution | first print at or after trigger + 250 ms, 60 s abandon | frozen |
| session | 09:30–11:30 ET, four 30-minute buckets | frozen |
| friction | 1.0 pt round trip primary; 0.0 / 0.5 / 2.0 reported | frozen |

**R is not re-optimised. RR is not re-optimised. The direction model is not
retrained, rescored or filtered. No feature is added.**

## 2. The budget

# EXACTLY SIX ENTRY CONFIGURATIONS

| id | mechanic | fixed parameter |
|---|---|---|
| **E1** | fixed delay | 5 minutes after activation |
| **E2** | fixed delay | 10 minutes after activation |
| **E3** | adverse pullback | 0.25 R from the activation price |
| **E4** | adverse pullback | 0.50 R from the activation price |
| **E5** | pullback + resumption | 0.25 R adverse, then 0.125 R recovery off the causal running extreme |
| **E6** | pullback + resumption | 0.50 R adverse, then 0.125 R recovery off the causal running extreme |

No hyperparameter tuning inside them. **No nearby values are tested** — not
3 or 7 minutes, not 0.3 R or 0.4 R, not a 0.1 R or 0.15 R resumption.

## 3. Controls — not strategy candidates

| id | definition |
|---|---|
| `CONTROL_RANDOM` | **the primary null.** Up to 10 entries per context, drawn without replacement from the 60-second decision grid in `[activation, bucket_end)`, same context / day / bucket / direction / R / bracket / horizon / execution / friction |
| `CONTROL_IMMEDIATE` | entry at the first executable print after activation |
| `CONTROL_NONCONTEXT` | same day, a 30-minute bucket where **no** context activated, random minutes inside it, direction drawn from the observed context direction distribution, same R scale |

Controls may not be selected as the strategy. `CONTROL_IMMEDIATE` is subject to
the one-position rule (it is a tradable alternative); `CONTROL_RANDOM` and
`CONTROL_NONCONTEXT` are independent hypothetical entries and are deliberately
**not**, which is stated wherever they are compared.

## 4. Explicitly forbidden

* Any seventh entry mechanic. If one looks interesting it goes to
  `FUTURE_HYPOTHESES.md`.
* VWAP retest, PDH/PDL retest, breakout retest, engulfing, swing/BOS,
  FVG, ICT constructs, limit-order optimisation, ATR entry thresholds,
  order-flow entry logic.
* Any new direction filter: trend, volatility, weekday, session-extreme,
  delta, or model feature.
* Re-optimising R, RR, the horizon, the session, the bucket size or `tau`.
* Promoting a post-hoc subgroup (time-within-context, half-hour, long/short)
  into the strategy.
* MBP-1, in any form. 2025-H1, in any form. 2026-04-01 onward, in any form.

## 5. Development data — all of it is contaminated

The hypothesis came from Phase-5 diagnostics, so **2021, 2022, 2023, 2024 and
2025-H2 are all development evidence for Phase 6.** None of them is out-of-sample
here and none may be described as such. 2021 is additionally in-sample for the
context model itself, which was fitted there in Phase 5.

The only fresh data is **2026-Q1**, and it stays sealed until a candidate has
passed every gate in §6 and the spec is frozen.

## 6. Development eligibility gates — all must pass

Fixed now, before any outcome was examined. Phase 5's two preregistration
defects are corrected here explicitly.

### G1 — sample floor (corrects Phase-5 defect #1)

**≥ 300 executed trades** pooled across the five development periods.

If context frequency makes 300 unreachable for *every* mechanic, the floor is
recomputed once — before any P&L is read — as
`round(0.6 × median accepted trades across E1–E6)`, and the shortfall is
disclosed. It may not be lowered a second time.

### G2 — period stability (corrects Phase-5 defect #1)

Net expectancy at 1.0 pt friction **> 0 in at least 4 of the 5** development
periods (2021, 2022, 2023, 2024, 2025-H2), **and** combined net expectancy > 0.

A mechanic that is carried by one spectacular year fails here.

### G3 — profit factor

Combined **PF(R) > 1.10**, in **R units** (corrects Phase-5 defect #2). The
points-based figure is reported alongside and labelled, but never used for a
gate.

### G4 — the primary entry-edge gate

    candidate E[R] − CONTROL_RANDOM E[R]

on pooled development data, with a **trading-day block bootstrap** (10 000
resamples, strategy and control resampled together):

# 95 % CI lower bound > 0

This is the most important gate. Phase 6 tests **entry improvement**, not
context quality, so beating a random entry *inside the same context* is the
whole claim.

### Selection among survivors

If more than one of E1–E6 passes G1–G4, exactly one is chosen by:

1. **highest median across the five periods of (candidate E[R] − CONTROL_RANDOM E[R])** — median, not mean, and not any single period's expectancy;
2. tie-break: larger total sample;
3. tie-break: lower max drawdown in R.

No other criterion participates.

### No least-bad candidate

**If no mechanic passes G1–G4, Phase 6 FAILS before validation and 2026-Q1 stays
sealed.** The best loser is not promoted. This is not a discretionary call.

### Additional failure condition

If the **causal context itself** is not positive — i.e. `CONTROL_RANDOM` inside
activated contexts does not beat `CONTROL_NONCONTEXT`, or is itself negative —
that is reported prominently and Phase 6 fails on its premise regardless of how
the six mechanics rank against each other.

## 7. Reporting obligation

At completion: **TOTAL ENTRY CONFIGURATIONS EVALUATED**, counting every mechanic
that ever had an outcome computed against it, on any period. The ceiling is 6.
