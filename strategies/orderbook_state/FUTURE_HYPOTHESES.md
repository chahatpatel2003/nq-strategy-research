# FUTURE_HYPOTHESES.md — Phase 7

Everything here is

# POST-HOC — REQUIRES NEW UNTOUCHED DATA

Observed after the 12 configurations had already failed the 2022 gates, on data
that has been used repeatedly. None of it changed Phase 7 and none of it may
become a strategy on 2021–2024.

Untouched data remaining after Phase 7: **2025-H1** (Trades **+ MBP-1** — and the
last MBP-1 that exists), **2026-Q1** (Trades only) and **2026-04-01 onward**.

---

## H7-1 — the negative is about the TOP OF BOOK, not about order flow

MBP-1 has exactly one level. Phase 7 tested none of the things that actually
distinguish order-flow research:

| untested | why |
|---|---|
| queue position | no order IDs in MBP-1 |
| individual order lifetime, order-level aggressiveness | same |
| hidden / iceberg liquidity | not represented |
| depth beyond the touch, book shape, multi-level imbalance | only `_00` exists |

**Hypothesis for a future phase:** the informative structure may live in the
*shape* of the book rather than its top, or in order-level behaviour. Testing it
requires **MBP-10 or MBO data that this project does not have.** That is a
data-acquisition decision, not a modelling one, and it is the single clearest
thing Phase 7 establishes about where to look next.

## H7-2 — OFI was available and the model nearly discarded it

Order-flow imbalance is the canonical top-of-book predictor in the microstructure
literature. All three horizons (1 s, 5 s, 15 s) were offered to an L1-regularised
model with 40 features to choose from, and OFI ended up carrying **1.2 %** of the
total coefficient mass — behind BBO state (25.2 %), quote-update intensity
(19.9 %) and imbalance persistence (12.3 %).

The one mildly interesting diagnostic cell is the **top OFI quartile at +0.0121 R
versus −0.1247 R in the worst** (558 of 2,229 trades) — directionally consistent
with OFI meaning *something*, while the model as fitted did not use it.

**Hypothesis:** OFI may matter at a horizon far shorter than 15 minutes, where
Phase 7 deliberately did not look because such an edge would not survive
execution. Testing it honestly requires an execution model for sub-second
holding, which is a different project.

## H7-3 — the model chose quote *churn*, not quote *pressure*

The single largest coefficient is `bid_px_chg_per_s_15` at **−0.106** — the rate at
which the best bid changes price. That is an instability/regime measure, not a
directional one, and the model leaning on it hardest is a sign that the
directional content of the 40 features is close to nil.

**Hypothesis:** top-of-book churn may be usable as a *regime filter* — when to
trade at all — rather than as a direction signal. Phase 4 reached the same
conclusion about `atr1m` from a completely different direction. Two phases now
suggest the same split: **volatility/instability variables predict tradeability,
not direction.**

## H7-4 — the NQ spread is degenerate as a conditioning variable

The 2021 spread quartile edges are **[2, 2, 2] ticks** — the NQ top-of-book spread
is 2 ticks at the 25th, 50th *and* 75th percentile. "Spread regime" cannot
separate anything in this market.

**Consequence for any successor:** do not spend a feature slot, a control
dimension or a subgroup axis on NQ spread. If spread-conditioned microstructure
research is wanted, it needs an instrument whose spread actually varies.

## H7-5 — the short bias is now a three-phase pattern

| phase | model | short share |
|---|---|---:|
| 5 | `r4p0:A_logit` larger-R state | ~93 % |
| 6 | same model, causal contexts | 70 % |
| **7** | **MBP-1 book state, entirely different features** | **93 %** (2,083 vs 146) |

Three independent models, two entirely different feature universes, one market
that rose substantially over 2021–2024 — and all three fire overwhelmingly short.
In Phase 7 the long arm also has the worse win rate (0.4589 vs 0.5017), so the
bias is not obviously the source of the failure.

**Hypothesis:** something in the shared *label construction* — a 1R/1R bracket
with a touch-then-market stop and a trade-through-by-a-tick target, on an
instrument with an upward drift — may systematically favour short-side
classification. This is a **methodological** hypothesis about the project's own
label, testable on synthetic data without spending any holdout, and it should be
checked before any successor phase reuses that bracket.

## H7-6 — the trade-frequency profile is the one thing that worked

8.78 trades/day, median 4, 66 % of days with 3+ trades, 12.6 % zero-trade days,
holds averaging 2.8 minutes against a 15-minute cap. That is squarely the 2–7/day
band the brief called interesting, and it is the best schedule any of the seven
phases has produced.

**Not a hypothesis about edge** — a schedule of unprofitable trades is worth
nothing. It is recorded because it establishes that a 5-second clock with a
top-2 %-tail threshold and a 15-minute horizon *sizes* correctly for an intraday
system, so a future phase with a real signal would not need to re-derive the
cadence.

## H7-7 — three phases have now found trades-derived flow uninformative

| phase | clock / horizon | trades-flow contribution |
|---|---|---|
| 4 | 5 s / 30 min | exactly **zero** tree importance |
| 5 | 60 s / 60 min | mean \|coef\| 0.048 vs 0.056 overall (below average) |
| **7** | **5 s / 15 min** | **1.3 % of coefficient mass; the trades-only ablation is worse than doing nothing** |

Three independent horizons, three independent feature universes, same answer.
Phase 7 adds the strongest version: an 8-feature trades+context model returns
**−0.1173 R**, i.e. **0.072 R worse than not trading**.

**This is now a firm result rather than a repeated disappointment**, and any
future proposal built on trades-derived delta should have to argue against it
explicitly.
