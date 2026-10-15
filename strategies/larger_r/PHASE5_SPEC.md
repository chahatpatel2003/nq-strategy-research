# PHASE5_SPEC.md — NQ Larger-R Causal State Strategy

**Spec version:** `largerr-1.0.0`
**Written and fixed BEFORE any Phase-5 label, outcome or P&L was computed.**

Everything in this file was decided from a-priori reasoning or from
**feature-side statistics on development data only** (volatility levels,
first-passage *resolution rates*). No win rate, expectancy or P&L of any kind
was computed before it was written.

---

## 1. Hypothesis

Phase 4 established two things. There was **no gross edge** at R ≈ 7 points
(zero-friction expectancy −0.013 to −0.030 R in four of five periods), yet the
55-feature causal state **did** carry real directional information: control C4,
which permutes the training target within trading days and refits, put the null
at −0.1592 ± 0.0043 R against an observed −0.1395 R with 0 of 20 permutations
reaching it — a signal worth roughly **0.02 R per trade** against friction
costing **0.14 R per trade**.

> **H5: the same causal state becomes economically tradable when expressed over
> a materially larger price horizon — larger R, longer holds, lower turnover —
> because friction shrinks from ~14 % of R to ~2–5 % of R.**

This is explicitly a **post-Phase-4 hypothesis**. It did not exist before Phase 4
and this document does not pretend otherwise. That is precisely why it must be
validated on data untouched by Phase 4, and why the budget below is tight.

## 2. What Phase 5 is *not* testing

Not a new feature set, not a new session, not a new RR, not a new execution
model, not a new instrument. Exactly one thing changes: **the price horizon at
which the state is asked to predict.**

## 3. Data

NQ **Trades only**, Databento GLBX MDP-3, read-only from the Samsung T9.
MBP-1 is never opened — `holdout5.assert_path_allowed` refuses any path
containing `mbp1` and any raw `.dbn`/`.dbn.zst` archive. No external series of
any kind: no ES, QQQ, VIX, options, news, sentiment or economic calendar.

Front contract: highest volume on the previous trading day (frozen Phase-1
rule). Roll days excluded. No back-adjustment.

| period | role |
|---|---|
| 2021-01-01 .. 2021-12-31 | DISCOVERY_TRAIN — model fit, scaler fit, baseline and threshold calibration |
| 2022-01-01 .. 2022-12-31 | SELECTION — the 18 configurations compared here, once |
| 2023-01-01 .. 2023-12-31 | INTERNAL_TEST — scored once, after the choice |
| 2024-01-01 .. 2024-12-31 | CONTAMINATED diagnostic only |
| **2025-01-01 .. 2025-06-30** | **SEALED. No unlock path exists.** |
| 2025-07-01 .. 2025-12-31 | CONTAMINATED diagnostic only |
| 2026-01-01 .. 2026-03-31 | FRESH VALIDATION — one shot, only if eligible |
| **2026-04-01 ..** | **SEALED FINAL HOLDOUT. No unlock path exists.** |

`2026_H1.parquet` physically runs to 2026-06-17, so it contains sealed April+
rows. Every Phase-5 read of it must go through `holdout5.sql_window_guard`,
which refuses outright any range reaching 2026-04-01 *before* emitting a
predicate. Row-group statistics are present, so the predicate also prunes at
file level. April+ never enters RAM, cache, derived file, model, statistic, log,
chart or summary.

## 4. Session and decision clock

Official signal-generation window **09:30:00–11:30:00 America/New_York**.
Decisions every **60 seconds**, first at 09:30:00, last at 11:29:00 —
**120 decisions per day**. DST follows the tz database.

A trade entered before 11:30 may remain open past 11:30 under the maximum-hold
rule in §8.

Diagnostics are reported for 09:30–10:30 and 10:30–11:30, and in fifteen-minute
buckets. **The entry session is not changed after seeing performance.**

Grid convention, inherited from Phase 4: grid second `[T0+i, T0+i+1)` is index
`i`; the decision stamped `T0+i+1` reads `grid[i]`, so every input second has
closed before it is used. `c[t]` is the last trade price strictly before `t`.

## 5. Features

The 55 registered causal features of `PHASE5_FEATURE_REGISTRY.md`, which are the
Phase-4 features unchanged, computed by the frozen `nqr.p4.features4` imported
read-only. None added, none removed.

**Known risk, recorded in advance:** `atr1m` is the only raw-points feature and
carries a regime component (session median 10.54 → 16.75 → 11.54 across
2021–2023). It dominated the Phase-4 tree and that model did not generalise.
It is kept because the brief requires the bounded model to decide; its
stationary companion `atr_pct_rank` is available for the model to prefer.

## 6. R architecture — volatility-normalised, decided before P&L

    R = clip(mult × ATR14(completed 1-minute bars, floor 2.0 pt), 5.0, 200.0)  points

evaluated at the decision timestamp, with **mult ∈ {2.0, 3.0, 4.0}**. The ATR is
the frozen `nqr.p2.features.causal_atr_minutes` — the same volatility unit
Phases 2, 3 and 4 used.

### Why volatility-normalised rather than fixed-point

| dev year | session median ATR14(1m) | 25 pt would be | 40 pt would be | 60 pt would be |
|---|---:|---:|---:|---:|
| 2021 | 10.54 pt | 2.37 × ATR | 3.80 × ATR | 5.69 × ATR |
| 2022 | 16.75 pt | 1.49 × ATR | 2.39 × ATR | 3.58 × ATR |
| 2023 | 11.54 pt | 2.17 × ATR | 3.47 × ATR | 5.20 × ATR |

A fixed 25-point R is a 2.37× ATR bet in 2021 and a 1.49× ATR bet in 2022 — a
59 % difference in what is actually being tested — while the price level moves
only 1.19× across the same years and the 2022 intraday decile range alone spans
2.6×. A fixed-point R would confound the horizon hypothesis with regime
exposure, which is the specific way Phase 4 failed. Normalising removes that
confound and makes the three scales mean the same thing in every regime.

### Why the 1-minute basis rather than the 5-minute basis

Both were measured on 70 sampled development days. Both read ≈ 0.5 × their
session median at 09:30, because the pre-market window is quiet. They differ in
how fast they recover: **ATR14(1m) is fully RTH by 09:44 (14 minutes), while
ATR14(5m) needs until 10:40 (70 minutes)** — more than half of a 120-minute
session, during which it would misprice R systematically low. At 11:00 the
1-minute basis reads 0.88 × its session median and the 5-minute basis 1.09 ×.
The 5-minute basis also failed to produce a finite value for a full session on
1 of the 70 sampled days; the 1-minute basis failed on none.

The 1-minute basis is additionally the already-audited unit shared with Phases
2–4, which keeps the Phase-4 comparison exact: Phase 5's scales are simply
**4× / 6× / 8× Phase 4's R**.

### Rails

`5.0` and `200.0` points are absurdity rails, not tuning. Measured on the 2021
training sample, the floor binds on **0.139 %** of the smallest scale and the
cap on **0.000 %**.

### Friction / R — the central economic quantity

Measured on 24 sampled 2021 training days, at the official **1.0 NQ point
round-trip friction**:

| scale | mult | R median | **friction / R** | vs Phase 4 |
|---|---:|---:|---:|---|
| `r2p0` | 2.0 × ATR1m | 21.1 pt | **4.74 %** | 4× the R |
| `r3p0` | 3.0 × ATR1m | 31.7 pt | **3.16 %** | 6× the R |
| `r4p0` | 4.0 × ATR1m | 42.2 pt | **2.37 %** | 8× the R |
| *Phase 4* | *0.5 × ATR1m* | *7.0 pt* | *14.35 %* | — |

## 7. Reward:risk

**Primary: 1R target / 1R stop.** The same decision timestamp is evaluated LONG
and SHORT under identical execution, and both are stored for every row.

Secondary RR diagnostics (1.25R, 1.5R, 2R) may be reported on the **same**
entries, but production selection is on the 1R objective only. RR is not
optimised after seeing results.

## 8. Maximum hold — 60 minutes

Fixed at **60 minutes**, the brief's recommended baseline. The technical review
required before choosing was run on 24 sampled 2021 training days and reported
**resolution rates only** — no win rate, no expectancy:

| scale | resolved @30m | **@60m** | @90m | @120m | median hold @60m |
|---|---:|---:|---:|---:|---:|
| `r2p0` | 90.7 % | **98.0 %** | 99.4 % | 99.8 % | 12.2 min |
| `r3p0` | 62.5 % | **82.2 %** | 89.2 % | 92.9 % | 26.9 min |
| `r4p0` | 39.5 % | **59.9 %** | 72.6 % | 79.7 % | 38.8 min |

90 minutes would raise `r4p0` resolution from 59.9 % to 72.6 %, but that is not
a strong enough reason to depart from the baseline: **timeouts are not discarded**
(§9), so an unresolved trade is a smaller-magnitude observation, not a lost one,
and a longer hold mechanically reduces the number of non-overlapping trades a
120-minute session can produce. 60 minutes already delivers holds of 12–39
minutes against Phase 4's 0.5 minutes, which is the change the hypothesis needs.

A hard 16:00 ET exit rail exists and never binds: the last entry is ~11:30 and
the horizon ends by ~12:30.

## 9. Execution

    signal    decision timestamp t on the fixed 60-second clock
    entry     first trade print at or after t + 250 ms; abandoned after 60 s
    stop      stop-market, triggers on a print at or beyond the stop, fills there
    target    resting limit, requires the tape to trade THROUGH by >= 1 tick
    timeout   at 60 minutes, exit at the FIRST print at or after the cutoff
    hard exit 16:00 ET (never binding)

Resolved on the raw chronological trade sequence. No OHLC approximation, no
candle-order guessing, no midpoint fills, no retroactive entry.

**The timeout rule is the one deliberate change from Phase 4.** Phase 4 exited at
the last print *before* the cutoff, which is not executable — at that instant the
cutoff had not arrived. Phase 5 takes the first print *at or after* it, which is
what a real timeout order gets, and is strictly the more conservative choice.
`resolve_p5` is asserted identical to the frozen `resolve_fast` on every TP and
SL outcome; it differs only on the TIMEOUT branch.

Timeout P&L, R, MFE, MAE and hold are all recorded. **Unresolved trades are never
discarded.**

## 10. Label

For every decision timestamp and every R scale, both directions are resolved:

    LONG   does entry + R print before entry − R within 60 minutes?
    SHORT  does entry − R print before entry + R within 60 minutes?

The modelling target is

    y = 1  iff the hypothetical LONG bracket finishes with GROSS points > 0

which is a property of the tape alone, so one model serves both directions.
Friction is applied to P&L, never to the label.

## 11. Signal — edge over a training-only control baseline

Phase 3 and Phase 4 both established that the realistic no-edge win rate is
**below** theoretical 50 %. Phase 5 therefore never compares the model to 0.50.

The baseline is estimated from **2021 training rows only**, per 30-minute
time-of-day bucket and per direction — which is exactly the matched-random
population, matched on day-set, time bucket and direction:

    b_long[k]  = mean(y = 1)              over 2021 rows in bucket k
    b_short[k] = mean(short gross > 0)     over 2021 rows in bucket k

Then, for a decision in bucket `k` with model probability `p`:

    edge_long  = p       − b_long[k]
    edge_short = (1 − p) − b_short[k]
    direction  = argmax(edge_long, edge_short)
    score      = max(edge_long, edge_short)
    trade iff  score ≥ τ

`τ` is the (1 − q) quantile of `score` over the **2021 training rows**, for
q ∈ {0.10, 0.05, 0.02}, then frozen as a number and applied unchanged to every
later period. Ties at `τ` are kept; the realised selection rate is reported
alongside the nominal one.

No control information from 2022, 2023, 2024, 2025-H2 or 2026 enters `b` or `τ`.

## 12. Preprocessing

Fitted on the 2021 training rows only and applied unchanged everywhere:

1. winsorise each feature at its 2021 0.1 % / 99.9 % quantiles;
2. standardise with the 2021 mean and standard deviation.

Rows with any non-finite feature are dropped before fitting and are never traded.

## 13. Portfolio rules

**One active position at a time.** A candidate arriving while a position is open
is logged `SKIPPED_OVERLAP` and never becomes a second position.

**Cooldown.** After an exit, the next eligible decision timestamp is the first
one at or after `exit_ts + 60 s` — one full decision interval. This prevents a
cluster of near-identical states re-entering the instant a trade closes. Fixed
before any P&L.

## 14. Friction

Official evaluation at **1.0 NQ point round trip**. Every report also carries
**0.0, 0.5 and 2.0**. The zero-friction column is mandatory and is read first,
so that "no gross edge" is never confused with "edge destroyed by cost".

## 15. Controls

* **C1 — matched random (primary null).** Per executed trade, up to 10 controls:
  same trading day, same 30-minute time-of-day bucket, same direction, control R
  within [0.80, 1.25] × the signal's R, drawn without replacement, seed
  20260820, identical entry, bracket, horizon, timeout and friction. Controls are
  independent entries and are deliberately not subject to the one-position or
  cooldown rules.
* **C2 — opposite direction.** Same signal timestamps, direction flipped,
  everything else identical. Reported honestly, never auto-flipped: an inverse
  strategy would be a new hypothesis needing new data.

Uncertainty is always a **day-block bootstrap** — 10 000 resamples of whole
trading days, strategy and controls resampled together. No statistic treats
overlapping decision rows as independent.

## 16. Development chronology

2021 fits (models, scaler, baseline `b`, thresholds `τ`). 2022 selects, once,
among the ≤ 18 configurations on the single criterion in
`PHASE5_SEARCH_BUDGET.md` §5. 2023 is scored once, after the choice, and cannot
change it.

## 17. Eligibility and the right to fail

Gates E (2022) and F (2023) in `PHASE5_SEARCH_BUDGET.md` §6 must both pass
before any candidate is frozen. **If they do not, Phase 5 FAILS before
validation and 2026-Q1 stays sealed.** The least-bad candidate is not promoted.

## 18. Fresh-validation gates (2026-Q1, fixed now)

Period 2026-Q1, session 09:30–11:30, 1R, friction 1.0 pt.

| gate | requirement |
|---|---|
| 1 | ≥ 100 executed trades. If the frozen candidate's 2023 frequency implies fewer than 100 in ~60 Q1 days, the threshold is set at freeze time — **before** Q1 is opened — to `max(50, round(0.75 × 2023 trades/day × 60))`, with the reduced power disclosed. |
| 2 | net expectancy > 0 R at 1.0 pt |
| 3 | profit factor > 1.10 |
| 4 | strategy E[R] − matched-control E[R], 95 % day-block-bootstrap lower bound > 0 |
| 5 | strategy WR − matched-control WR positive, with uncertainty reported |
| 6 | **zero-friction expectancy also > 0** |
| 7 | `total_net_R − best_ISO_week_net_R > 0` — deleting the single most profitable calendar week leaves the period still profitable |

Verdict is exactly one of **PASS / PROMISING BUT INCONCLUSIVE / FAIL**.

## 19. Win-rate expectation

A high win rate is desirable but is not a gate. At 1:1 with these R scales,
57–62 % with stable positive expectancy, PF > 1.2 and low drawdown would already
be a strong result. Confidence intervals are reported throughout, and
**theoretical 50 % is reference only** — the matched control is the null.

## 20. What may not happen after this file

No new feature, R scale, RR, horizon, clock, session, threshold, model family or
gate. No direction flip. No subgroup promoted after the fact. Anything
interesting goes to `FUTURE_HYPOTHESES.md` marked
**POST-HOC — REQUIRES NEW UNTOUCHED DATA**.
