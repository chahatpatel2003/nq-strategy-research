# FUTURE_HYPOTHESES.md — Phase 4

Everything in this file is

# POST-HOC — REQUIRES NEW UNTOUCHED DATA

It was observed *after* the production strategy was frozen, on data that has
already been used. None of it changed Phase 4, none of it is evidence, and none
of it may be turned into a strategy on 2021–2025 or on 2026-Q1. Anything
pursued here needs a fresh preregistration and data that has not been touched —
which, after Phase 4, means **2025-H1 (Trades + MBP-1, still sealed)** or
**2026-04-01 onward (still sealed)**, and neither should be spent lightly.

---

## H4-1 — R is roughly an order of magnitude too small for the friction

**The single most useful thing Phase 4 produced.**

`R = 0.50 × ATR14(1-minute)` averages **6.97 points** across the five periods.
A 1.0 point round trip is therefore **0.143 R of pure cost per trade**, and the
bracket resolves in a median of **24–37 seconds**, so the book turns over ~140
times per day.

For a 1R/1R bracket to clear 1.0 pt of friction it needs a gross edge above
`1.0 / R_points`. Observed gross edge is ≈ 0. Even granting the strongest signal
Phase 4 measured — the **+0.020 R per trade** by which the real model beat a
scrambled-label refit (control C4) — break-even against 1.0 pt friction would
require

    0.020 × R_points > 1.0   ⇒   R ≈ 50 points

against the 7 points actually used. The friction-to-R ratio, not the feature
set, is the binding constraint.

**Hypothesis for a later phase:** the same causal state universe evaluated at a
structurally larger R — a multi-minute or daily ATR basis, holds measured in
tens of minutes, a handful of trades per day. This is a different strategy, not
a tuning of this one, and it must be preregistered from scratch.

## H4-2 — a real state signal exists; it is just far too small

Control C4 (permute the 2021 target within trading days, refit, recalibrate,
rescore 2022) gives a null of **−0.1592 ± 0.0043 R** against an observed
**−0.1395 R** — about 5 null standard deviations, with 0 of 20 permutations
reaching it. The 55-feature causal state genuinely carries directional
information.

It is worth roughly **0.02 R per trade**. Friction at this R scale costs
**0.14 R**. The signal is real and about one seventh of what it would need to be.

**Caveat that must travel with this:** C4 was measured on 2022, the selection
year. On 2023, control C3 cannot distinguish the model from a coin flip
(p = 0.283), and the matched-random comparison straddles zero. The honest
reading is "a small real effect on 2021–2022 that does not clearly persist",
not "a proven small edge".

## H4-3 — high model confidence on the short side is an anti-signal

Consistent across all five periods, without exception:

| `\|score\|` bucket | direction | E[R] vs its own matched control |
|---|---|---|
| 0.051059 | short | **worse** in 5 of 5 periods (−0.01 to −0.23 R) |
| 0.048440 | long | worse in 5 of 5 |
| 0.017941 | mixed | better in 5 of 5 (+0.03 to +0.06 R) |
| 0.062383 | long | better in 5 of 5 (+0.01 to +0.11 R) |

The model's *most confident short* leaf is systematically worse than random,
and its *most confident long* leaf is systematically better than random — yet
still net-negative. Confidence does not order realised outcomes.

**Hypothesis:** the leaf structure is capturing two different regimes with
opposite reliability, and a confidence score built as `P(y=1) − 0.5` is the
wrong summary for a model whose long and short branches are not mirror images.

## H4-4 — the model is a volatility-regime detector, not a direction model

`atr1m` alone carries **39.7 %** of the tree's importance, `dist_pdh_norm`
26.9 %. Only 5 of the 55 registered features are used at all. Families 1
(returns), 2 (velocity), 5 (trade intensity), 6 (trade side / delta), 7 (time)
and 9 (DC events) contribute **nothing**.

**Hypothesis:** volatility level and previous-day location belong in a *regime
filter* that decides whether to trade at all, with direction supplied by a
separate mechanism. Phase 4 asked one model to do both jobs.

## H4-5 — trade side / delta contributed nothing at this horizon

Family 6 was kept deliberately, on the strength of the Phase-2 verification of
the native Databento `side` field (99.998 % agreement over 3.88 M trades). Given
a causal 1-second signed-volume state, a depth-3 tree chose volatility level and
previous-day location every time. Six order-flow features, zero importance.

This is a **clean negative on trades-derived order flow at a 5-second decision
clock with a 30-minute horizon** — not on order flow generally. Real book
imbalance, queue dynamics and spread state live in MBP-1, which Phase 4 never
opened. That question is exactly what 2025-H1 was sealed for.

## H4-6 — direction imbalance

The tree is **93 % short** (32,929 shorts vs 3,216 longs on 2023). Its long
calls beat its short calls on win rate in four of the five periods (2021:
0.5150 vs 0.4889; 2022: 0.5151 vs 0.5007; 2023: 0.4944 vs 0.4814; 2024: 0.4966
vs 0.4891; reversed in 2025-H2: 0.4784 vs 0.4964).

**Not actionable.** Splitting a frozen strategy by direction after seeing the
results is the textbook post-hoc error, and the 2025-H2 reversal is exactly what
one expects if it is noise.

## H4-7 — no time window rescues it

09:30–10:30, 10:30–11:30, 09:30–12:00 and 09:30–16:00 are all negative in all
five periods. The two hours are within 0.01 R of each other in every period and
swap order between periods. Extending to 16:00 makes every period worse. There
is no profitable pocket of the day to promote, which is the useful negative
result: the failure is not a session-selection problem.

## H4-8 — the tie-group threshold made the strategy far less selective than intended

The nominal top-20 % threshold admitted **75 %** of rows, because a depth-3 tree
emits ≤ 8 distinct scores and the quantile fell inside a tie group. A model
family with a continuous score, or a threshold defined on leaf identity rather
than on a quantile of `|score|`, would make "top 5 %" mean what it says.

**Hypothesis for a later phase:** the same test with genuinely selective
thresholds might trade 5–10 times a day instead of 140, which interacts directly
with H4-1. Note this cannot be checked on existing data without re-opening the
budget.
