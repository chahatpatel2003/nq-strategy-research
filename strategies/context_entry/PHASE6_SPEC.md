# PHASE6_SPEC.md — NQ Context + Entry-Timing Research

**Spec version:** `ctxentry-1.0.0`

Consolidates what was fixed, before any entry mechanic had an outcome computed
against it, in `PHASE6_SEARCH_BUDGET.md` (the budget, the geometry, the gates)
and `CONTEXT_CAUSALITY_AUDIT.md` (the context activation rule). Neither of those
files was edited afterwards.

---

## 1. The question

Phase 5's decomposition suggested the direction model finds useful *context* and
times its entry badly. **That decomposition turned out not to be causal** — see
`CONTEXT_CAUSALITY_AUDIT.md`. Phase 6 therefore asks the question properly:

> Given a **causally activated** context and a locked direction, can a simple
> deterministic entry mechanic beat entering at a random minute inside that same
> context?

Phase 6 does **not** build a direction model, does not re-optimise risk, and does
not search for a new session or filter. It changes exactly one thing: **when, and
at what price, the position is opened.**

## 2. Data

NQ **Trades only**, read-only from the Samsung T9. MBP-1 is never opened —
`holdout6.assert_path_allowed` refuses any path containing `mbp1` and any raw
`.dbn`. No external series of any kind.

Because the hypothesis is post-hoc, **every pre-2026 period is development**:

| period | Phase-6 role |
|---|---|
| 2021 | development — also in-sample for the context model |
| 2022 | development |
| 2023 | development (contaminated) |
| 2024 | development (contaminated) |
| 2025-H2 | development (contaminated) |
| **2025-01-01 … 2025-06-30** | **SEALED. No unlock path.** |
| **2026-01-01 … 2026-03-31** | the only fresh validation |
| **2026-04-01 …** | **SEALED. No unlock path.** |

`2026_H1.parquet` physically runs to 2026-06-17, so any read of it must go
through `holdout6.sql_window_guard`, which raises before emitting a predicate for
a window reaching 2026-04-01.

## 3. Session and buckets

**09:30–11:30 America/New_York**, split into four fixed 30-minute buckets:
09:30–10:00, 10:00–10:30, 10:30–11:00, 11:00–11:30. DST follows the tz database.

## 4. Context activation — the causal rule

Inside each bucket:

1. the **first** decision timestamp on the frozen 60-second clock whose Phase-5
   edge score clears `τ = 0.179938` **activates** the context;
2. its predicted direction is **locked** for the remainder of that bucket —
   later flips *and later higher scores* are ignored;
3. `R` is locked at activation from the frozen `r4p0` rule;
4. the **activation price** is the first executable print after
   `activation + 250 ms`; this is also `CONTROL_IMMEDIATE`'s fill and the
   reference for the pullback mechanics;
5. at most **one** context per bucket; if nothing qualifies there is **no**
   context;
6. an unentered context **expires** at bucket end and never carries forward.

Nothing about a context depends on anything after its activation timestamp.
Asserted by
`test_context_uses_no_information_after_its_activation_timestamp` (delete the
entire future, require an identical context) and
`test_context_activates_on_the_FIRST_qualifying_signal_in_a_bucket` (plant a
higher score later in the bucket, require it to be ignored).

The direction model itself is the **frozen Phase-5 `r4p0:A_logit:top2`**, loaded
read-only from `strategies/larger_r/models/production_model.pkl`: the same 55
Phase-4 causal features, the same 2021-fitted preprocessing, the same
elastic-net logistic (C = 0.1, l1_ratio = 0.5), the same edge-over-training-
baseline direction logic, the same τ. **Not retrained, not rescored, not
filtered.**

## 5. Trade geometry — inherited frozen from Phase 5

    R          clip(4.0 × ATR14(completed 1-min, floor 2.0), 5.0, 200.0) pt,
               evaluated and LOCKED at context activation
    target     entry + direction × R      (resting limit, must trade THROUGH by ≥ 1 tick)
    stop       entry − direction × R      (stop-market, fills at the triggering print)
    max hold   60 minutes from entry
    timeout    first executable print at or after the cutoff
    hard rail  16:00 ET (never binding)
    friction   1.0 pt round trip primary; 0.0 / 0.5 / 2.0 also reported

Target and stop hang off the **realised entry price**, never the activation
price. R is *not* re-optimised, RR is *not* re-optimised, and no alternative
bracket is tested.

## 6. Entry eligibility window

A mechanic may trigger only in `[activation, bucket_end)`, and the **fill** must
also land before bucket end. If no valid entry occurs, the context is
`NO_ENTRY_IN_BUCKET`. A position that was opened may run past 11:30 under the
60-minute rule.

## 7. The six entry mechanics

| id | rule |
|---|---|
| **E1** | enter 5 minutes after activation |
| **E2** | enter 10 minutes after activation |
| **E3** | enter after price trades 0.25 R adverse to the activation price |
| **E4** | enter after price trades 0.50 R adverse |
| **E5** | E3, then a 0.125 R recovery measured off the **causal running extreme** |
| **E6** | E4, then a 0.125 R recovery measured off the **causal running extreme** |

"Causal running extreme" means the extreme known *so far*, never the eventual
one — asserted by `test_E5_never_uses_the_eventual_low_only_the_low_so_far`.

## 8. Execution

Every mechanic and every control fills at the **first print at or after
`trigger + 250 ms`**, abandoning after 60 s, with the fill required before bucket
end. No perfect limit fills, no entering at the threshold price if the next
traded price is worse, no retroactive entry. First passage is resolved on the raw
chronological trade sequence by the frozen `nqr.p5.labels5.resolve_p5`.

## 9. Portfolio rules

**One active position at a time, per book.** A context arriving while that book
has a position open is logged `SKIPPED_OVERLAP`. `CONTROL_IMMEDIATE` is subject
to the same rule because it is a tradable alternative; `CONTROL_RANDOM` and
`CONTROL_NONCONTEXT` are independent hypothetical entries and are deliberately
not, which is stated wherever they are compared.

## 10. Controls

| id | definition |
|---|---|
| **`CONTROL_RANDOM`** | **the primary null.** Up to 10 entries per context drawn without replacement from the 60-second grid in `[activation, bucket_end)` — same context, day, bucket, direction, R, bracket, horizon, execution, friction |
| `CONTROL_IMMEDIATE` | the activation fill itself |
| `CONTROL_NONCONTEXT` | same day, a bucket where **no** context activated, random minutes inside it, direction drawn from the observed context direction distribution, same R scale |

Random draws can never precede activation — asserted by
`test_random_control_entries_are_never_before_activation`. This is the exact
defect the Phase-5 control had.

## 11. Statistics

Every interval is a **trading-day block bootstrap**: 10 000 resamples of whole
trading days, candidate and control resampled together. A day can carry up to
four contexts, so nothing is treated as independent. Profit factor is reported in
**R units, labelled `PF(R)`**, per the Phase-5 correction; the points figure is
shown alongside and never used for a gate.

## 12. Development gates

`PHASE6_SEARCH_BUDGET.md` §6, fixed before any outcome:

* **G1** ≥ 300 executed trades pooled across the five development periods;
* **G2** net expectancy > 0 in ≥ 4 of the 5 periods, **and** combined > 0;
* **G3** combined **PF(R) > 1.10**;
* **G4** `candidate E[R] − CONTROL_RANDOM E[R]`, 95 % day-block CI **lower bound > 0**.

Selection among survivors: highest **median per-period advantage** over
`CONTROL_RANDOM`; tie-break larger sample; tie-break lower max drawdown.

**No least-bad candidate.** If none passes, Phase 6 fails before validation and
2026-Q1 stays sealed. Additionally, if the causal context does not beat
non-context, that is an independent failure condition reported prominently.

## 13. Fresh-validation gates — never reached

Recorded for completeness; no candidate qualified, so 2026-Q1 was never opened
and these were never applied.

| gate | requirement |
|---|---|
| 1 | ≥ 50 trades (threshold to be frozen from development frequency before opening Q1) |
| 2 | net E[R] > 0 at 1.0 pt |
| 3 | PF(R) > 1.10 |
| 4 | candidate − `CONTROL_RANDOM`, 95 % day-block CI lower bound > 0 |
| 5 | WR difference vs `CONTROL_RANDOM` positive, with CI reported |
| 6 | zero-friction expectancy > 0 |
| 7 | `total_net_R − best_ISO_week_net_R > 0` |

## 14. What may not happen

No seventh mechanic, no nearby parameter value, no new direction filter, no
re-optimised R or RR or horizon or session, no promoted subgroup, no MBP-1, no
2025-H1, no 2026-04-01+. Anything interesting goes to `FUTURE_HYPOTHESES.md`
marked **POST-HOC — REQUIRES NEW UNTOUCHED DATA**.
