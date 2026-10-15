# PHASE7_SPEC.md — NQ MBP-1 Order-Book State Discovery

**Spec version:** `obstate-1.0.0`
**Written and fixed BEFORE any Phase-7 label, outcome or P&L was computed.**

Everything below was decided a priori or from **schema inspection on 2021
development rows and parquet footers**. No 2025-H1 market row was decoded, and no
win rate, expectancy or P&L existed when this file was written.

---

## 1. Hypothesis

Six phases of trades-and-price research have failed, and trades-derived
delta/order-flow specifically failed at two independent horizons (Phase 4:
5 s clock / 30 min; Phase 5: 60 s clock / 60 min). That says nothing about the
**quote state**, which no phase has ever looked at.

> **H7: causal top-of-book state and its evolution — persistent imbalance,
> microprice pressure, order-flow imbalance, size depletion and replenishment,
> and the interaction between aggressive trades and displayed liquidity — carry
> directional information beyond price and trades alone, enough to be tradable
> after realistic execution.**

This is not assumed. The mandatory ablation in §12 exists precisely to answer
whether MBP-1 adds anything at all.

## 2. Data

**NQ MBP-1 + NQ Trades only**, read-only from the Samsung T9. No downloads, no
external series (no ES, QQQ, VIX, options, news, calendar, sentiment).

MBP-1 is standard single-level: `bid/ask_px_00`, `bid/ask_sz_00`,
`bid/ask_ct_00`, plus `action`, `side`, `sequence`, `depth` (always 0) — see
`MBP1_SCHEMA_AUDIT.md`. **No depth beyond the touch, no order IDs, no queue
position, no hidden liquidity.** Nothing in this spec pretends otherwise.

| period | role |
|---|---|
| 2021 | TRAIN — scaler, models, selectivity quantiles, control quartile edges |
| 2022 | SELECT — the 12 configurations, once |
| 2023 | INTERNAL DEVELOPMENT OOS — the selected candidate only, unchanged |
| 2024 | CONTAMINATED diagnostic, post-freeze, as a stress gate |
| **2025-01-01 … 2025-06-30** | **FRESH VALIDATION — the last untouched MBP-1 window, and the last that exists** |
| 2025-H2, 2026 | **no MBP-1 exists; `holdout7` refuses the paths regardless, with no unlock** |

MBP-1 coverage stops at 2025-H1. 2026-Q1 stays an independent untouched
Trades-only reserve and Phase 7 has **no code path to it at all**.

## 3. Event ordering and causal alignment

    ORDER BY ts_event, sequence, file_row_number

`sequence` is monotone in `ts_event` (0 decreases over a sampled RTH day) but is
**not unique** — 12,283 of 592,404 sampled timestamps have ties it cannot break,
because a multi-message exchange packet shares both fields. File row order is the
exchange's within-packet order and is the deterministic final tie-break.

Only backward/as-of alignment is used. A decision at `t` reads the book state
implied by events at or before `t`; no nearest-neighbour join and no forward fill
from a later second exists anywhere in the pipeline.

## 4. The per-second cache

Every event-level quantity — OFI, size increases/decreases at an unchanged best
price, best-price steps, adds, cancels, aggressive volume — is computed **event
by event in the scan**, from the ordered stream, and only then aggregated to one
row per `(trading_date, symbol, second)` over the **09:00–12:00 ET** band. The
raw corpus (7.89 bn rows, 222 GB) is scanned once per period; nothing is
approximated from a snapshot.

Seconds with no book event carry the **last known** quote forward (causal); their
event counters are zero.

## 5. Decision clock and session

Official session **09:30:00–11:30:00 America/New_York**, decisions every
**5 seconds** — 1,440 per day. Grid index `i` is the second `[T0+i, T0+i+1)`; a
decision stamped `T0+i+1` reads `grid[i]`, so every input second has closed.

Diagnostics are reported for 09:30–10:30 and 10:30–11:30 and in fifteen-minute
buckets. **The session is not optimised.** No Asia, no London, no afternoon.

## 6. Features

The **40** registered features of `FEATURE_REGISTRY.md` — the hard cap, exactly
reached. Eleven families, windows of 1 s / 5 s / 15 s, all trailing and closed at
the decision. Microprice is `(a·B + b·A)/(B+A)`; OFI is the Cont–Kukanov–Stoikov
top-of-book form. Both are unit tested, including all nine OFI transition cases
and the microprice sign.

## 7. Risk geometry — fixed points, not volatility-scaled

    R      15 pt  (R15)   and   25 pt  (R25)      -- exactly two, no others
    target entry + direction x R      (resting limit, trade THROUGH by >= 1 tick)
    stop   entry - direction x R      (stop-market, fills at the triggering print)
    hold   15 minutes
    timeout first executable print at or after the cutoff; P&L counts in full
    rail   16:00 ET (never binding)

| R | friction / R at 1.0 pt |
|---|---:|
| 15 pt | 0.0667 |
| 25 pt | 0.0400 |

Fixed points rather than an ATR multiple because Phase 7 is testing a
*microstructure* horizon where the relevant scale is the tick and the spread, not
the day's volatility — and because holding R constant keeps the label identical
across regimes, which makes the MBP ablation clean. Documented here before any
outcome; not revisited.

## 8. Label

For every decision and each R, both directions are resolved on the raw trade
tape. The modelling target is

    y = 1 (UP)  iff the LONG 1R bracket finishes with GROSS points > 0

TP → UP, SL → DOWN, TIMEOUT → the sign of the realised move. **Nothing is
discarded**, including hard states. Friction is applied to P&L, never to the
label.

## 9. Execution

Signal complete at `t`; entry at the **first executable trade print at or after
`t + 250 ms`**, abandoned after 60 s. No midpoint fill, no passive-fill
assumption, no "the bid touched so I filled", no retroactive entry, and never the
event that generated the signal. Identical for the strategy and for every
control. First passage resolved on the raw chronological trade sequence by the
frozen `nqr.p5.labels5.resolve_p5`.

## 10. Portfolio rules

**One active position.** A signal arriving while one is open is logged
`SKIPPED_OVERLAP`. **Cooldown:** one full 5-second decision interval after an
exit. Not optimised.

## 11. Matched-random control — the primary null

Phase 6 closed on a control-causality defect (44.1 % of Phase-5's controls
entered before the signal that gave them direction). Phase 7 therefore asserts
control causality at runtime and **fails the run** on any violation.

Two strictly causal variants, both preregistered:

* **`cross_day` (PRIMARY)** — a **different** trading day, the **same 5-minute
  time-of-day bucket**, same direction, same R, and the same ATR quartile and
  spread quartile **measured at the control's own timestamp**. Quartile edges come
  from 2021 training rows only and are frozen. Nothing the control uses postdates
  the control; the direction is a design parameter imported from the strategy
  trade, and because the control sits on a different day it carries no
  information about that day's future.
* **`same_day_forward` (SECONDARY)** — the **same** day, decision timestamp at or
  after the strategy signal, same direction / R / ATR quartile / spread quartile.
  Controls for the day's regime; loses exact time-of-day matching.

Same-day **backward** sampling is not offered: assigning a later signal's
direction to an earlier minute is exactly the Phase-5 defect.

Runtime assertions, each raising `ControlCausalityViolation`:
`entry_ts > decision_ts` for every control; `decision_ts ≥ signal_ts` for
`same_day_forward`; and control day ≠ signal day for `cross_day`.

**Secondary control — opposite direction:** the mirror trade at the identical
signal timestamp. Reported, never auto-flipped.

## 12. Ablations — the incremental-MBP test

| arm | features | drops |
|---|---:|---|
| **A0 full** | 40 | — |
| **A1 quote-only** | 32 | families 8, 9, 10 (everything needing trade volume) |
| **A2 trades + context** | 8 | families 1–7, 9, 10 (everything needing the book) |

Each arm gets its **own** 2021-fitted scaler and its **own** 2021 selectivity
thresholds, on identical dates, R, model family, selectivity level and execution.
The mandatory statement is `A0 − A2` with a day-block bootstrap. If MBP adds
nothing, the report says so in those words.

Ablations are diagnostics and may never become the production candidate.

## 13. Null tests

* **N1 label permutation** — permute the training target **within trading days**,
  refit, recompute thresholds by the same rule, rescore 2022. ≥ 50 permutations.
* **N2 temporal shift** — pair each decision's features with the labels of the
  same time-of-day slot on a different day (fixed +7 trading days), preserving
  both marginals and destroying only the causal link.

Neither may tune anything.

## 14. Statistics

Every interval is a **trading-day block bootstrap**, 10 000 resamples of whole
days, strategy and control resampled together. Profit factor is always **PF(R)**,
in R units, labelled; the points figure is reported beside it and never gates.
**Theoretical 50 % is never the null** — the matched random control is.

## 15. Gates

2022 (G1–G6), 2023 (F1–F6), 2024 (D1–D5) and 2025-H1 (V1–V9) are enumerated in
`SEARCH_BUDGET.md` §§7–11 and were fixed before any outcome existed. Selection
among 2022 survivors is by **highest trading-day median advantage vs matched
random**, not raw expectancy — the direct correction of the Phase-5 defect.

**There is no least-bad candidate at any stage.** If the gates are not met,
Phase 7 fails and 2025-H1 stays sealed.

## 16. Production training before 2025-H1

Declared now, before the unlock, so it cannot be chosen on performance:

> If the candidate reaches the freeze, its **coefficients are refit on
> 2021–2023** — the full development window — using the identical architecture,
> feature set, preprocessing procedure and selectivity rule. 2024 is
> **excluded** because it is a contaminated diagnostic. Selectivity thresholds
> are recomputed by the frozen procedure on the same 2021–2023 window. Nothing
> touches 2025-H1.

The alternative (keeping the 2021-only fit) is rejected in advance: three years
of training is strictly better conditioned, and choosing between them after
seeing 2024 would be selection on the diagnostic.

## 17. Verdict vocabulary

Exactly one of **PASS** / **PROMISING BUT INCONCLUSIVE** / **FAIL**. PASS requires
every 2025-H1 gate. Development failure means FAIL before the holdout, and the
holdout stays sealed.

## 18. What may not happen

No 13th configuration, no 41st feature, no third R, no nearby parameter value, no
new model family, no session change, no retune on 2023 or 2024, no subgroup
rescue, no direction flip, no MBP-1 level beyond `_00`, no invented queue
position or cancellation attribution, and no access to 2025-H2 or 2026 in any
form. Anything interesting goes to `FUTURE_HYPOTHESES.md` marked
**POST-HOC — REQUIRES NEW UNTOUCHED DATA**.
