# PREREG_ADDENDUM.md — Phase 4

**Written BEFORE any Phase-4 label, outcome or model was computed.**
Timestamped by its inclusion in `STATE_DISCOVERY_SPEC_FROZEN.md`.

`FEATURE_REGISTRY.md` fixes the feature universe and `SEARCH_BUDGET.md` fixes
the search. Neither of them pins down a handful of decisions that must be fixed
before outcomes exist, or the outcome could influence them. This file pins them
down. Nothing here widens the budget or the feature set.

---

## A1. Decision clock and session

Decision timestamps every **5 s**. The official Phase-4 session is
**09:30:00–11:29:55 ET** (1440 decisions/day). Rows are *also* generated out to
15:59:55 ET so the required extended-window diagnostics
(09:30–12:00, 09:30–16:00) can be reported, but **model fitting, configuration
selection, threshold calibration and validation use 09:30–11:30 only**. This is
enforced in code, not by convention.

Roll days are excluded, exactly as in Phase 3 (`front_map.is_roll_day`).

## A2. Causality convention on the grid

Features live on a dense 1-second grid; index `i` is the second `[T0+i, T0+i+1)`.
The decision stamped at wall-clock `T0+i+1` reads `grid[i]`, so every input
second has closed before it is used. `c[t]` is therefore the last trade price
**strictly before** `t` — one notch more conservative than "at or before".

## A3. R

`R = clip(0.50 × ATR14(completed 1-min, floor 2.0 pt), 1.0, 25.0)` points,
evaluated at the decision timestamp. Stop and target are placed symmetrically
around the **realised entry price**, never around the decision price:

    stop   = entry − direction × R
    target = entry + direction × R

## A4. Entry execution

Identical to Phases 1–3 and identical for strategy trades and every control:
market order at the decision timestamp, latency **250 ms**, filled at the
**first trade print at or after `t + 250 ms`**, abandoned if no print inside
60 s. Stop = touch-then-market. Target = resting limit, needs the tape to trade
**through** by ≥ 1 tick. No midpoint fills, no retroactive entries.

## A5. Maximum hold and TIMEOUT handling

Maximum hold **30 minutes**, plus a hard exit at 16:00 ET (never binding inside
the official session). A trade that reaches neither level is **not discarded**:
it exits at the last print before the cutoff and its realised points count in
full, at every friction level.

## A6. Classification target

    y = 1  if the hypothetical LONG 1R/1R bracket opened at this decision
           finishes with gross points > 0
    y = 0  otherwise

`y` is a property of the tape alone, so one model covers both directions. The
SHORT bracket is resolved and stored for every row as well, and is the basis of
control C2. `y` is defined on **gross** points; friction is applied to P&L, never
to the label.

## A7. Score, direction, threshold

    p     = model P(y = 1 | x)
    score = p − 0.5
    direction = +1 (long) if score > 0, −1 (short) if score < 0

A decision becomes a candidate trade iff `|score| ≥ τ`. The three preregistered
thresholds are the top **20 % / 10 % / 5 %** of `|score|`, and `τ` is fixed as
the corresponding quantile of `|score|` **on the 2021 training rows inside
09:30–11:30 only**. It is then frozen as a number and applied unchanged to 2022,
2023, 2024, 2025-H2 and 2026-Q1. Ties at `τ` are kept (no arbitrary tie-break);
the realised selection rate is reported alongside the nominal one.

## A8. Preprocessing

Fitted on the 2021 training rows only, then applied unchanged everywhere:

1. winsorise each feature at its 2021 0.1 % / 99.9 % quantiles;
2. standardise with the 2021 mean/σ.

Rows with any non-finite feature are dropped before fitting and are recorded as
`SKIPPED_NONFINITE` at backtest time rather than silently traded.

## A9. Overlap

Adjacent rows share up to 30 minutes of future tape. Overlap is **not** removed
for model fitting (documented, and it costs only effective sample size). It is
handled where it would otherwise mislead:

* performance is measured on **actual non-overlapping trades** produced by the
  one-position-at-a-time rule, never on the row population;
* all uncertainty is **day-block bootstrap** (resample trading days with
  replacement, 10 000 draws), never i.i.d. resampling of trades;
* splits are whole calendar years and no label spans a day boundary
  (max horizon 30 min inside a 09:30–16:00 window), so no purge or embargo is
  needed at a split boundary. This is asserted in the leakage audit.

## A10. One position at a time

The backtest holds **at most one** position. A candidate arriving while a
position is open is logged `SKIPPED_OVERLAP` and never becomes a second
position. Controls are independent hypothetical entries and are deliberately
**not** subject to this rule; that is stated wherever they are compared.

## A11. Matched-random control (primary null)

For each executed strategy trade, up to **K = 10** control entries are drawn:

* same trading day;
* same 30-minute time-of-day bucket;
* same direction;
* control R taken at the control's own decision timestamp, accepted only if
  `R_control / R_signal ∈ [0.80, 1.25]` (volatility matching);
* drawn uniformly without replacement from the eligible 5-second decision
  timestamps of that bucket, seeded once (`seed = 20260819`);
* identical entry model, bracket, 30-minute horizon, hard exit and friction.

The strategy's own decision timestamps are **not** excluded from the control
pool. Excluding them would make the control weaker and the comparison flatter;
including them is the conservative choice.

## A12. Null controls

* **C2 — opposite direction.** Same signal timestamps, direction flipped,
  everything else identical. Reported honestly, never auto-flipped.
* **C3 — shuffled labels.** Every executed trade re-resolved with a randomly
  reassigned direction preserving the realised long fraction; 1 000 repetitions.
* **C4 — randomised feature relationship.** The target is permuted **within
  trading-day blocks** in the 2021 training partition (feature marginals and
  day structure intact, feature→target association destroyed), the frozen
  production configuration is refitted, thresholds are recalibrated by the same
  A7 procedure, and the 2022 selection statistic is recomputed. 20 repetitions,
  giving a null distribution for the number that chose the production model.

## A13. Selection

Exactly as `SEARCH_BUDGET.md` §4: among the ≤ 18 configurations, the highest
**2022 net expectancy in R at 1.0 pt friction, 09:30–11:30**, subject to ≥ 200
executed 2022 trades; ties break on trade count. 2023 is looked at once, after
the choice, and cannot change it.

## A14. Gate 7 — profit concentration (fixed now, before validation)

Group the 2026-Q1 trade log by ISO calendar week and sum net R at 1.0 pt.

**Gate 7 passes iff `total_net_R − best_week_net_R > 0`** — i.e. deleting the
single most profitable week leaves the strategy still profitable over the
validation period. The best week's share of total net R is reported alongside.

## A15. Gate 4 status

The brief states plainly that theoretical 50 % is **not** the primary null, so
Gate 4 (raw WR > 50 %) is recorded as a **preference, not a hard gate**. Gates
1, 2, 3, 5, 6 and 7 are hard. A candidate that clears all hard gates but not
Gate 4 is reported as **PASS with the win-rate shortfall disclosed in the
verdict headline**. A candidate failing any hard gate cannot be a PASS.

## A16. What may not happen after this file

No new feature, horizon, threshold, model family, hyperparameter, session,
R rule, holding horizon, direction rule or gate. Anything interesting that turns
up goes to `FUTURE_HYPOTHESES.md` marked **POST-HOC — REQUIRES NEW UNTOUCHED
DATA**.
