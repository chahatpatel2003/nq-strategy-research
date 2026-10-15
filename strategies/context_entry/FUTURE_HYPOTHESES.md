# FUTURE_HYPOTHESES.md — Phase 6

Everything here is

# POST-HOC — REQUIRES NEW UNTOUCHED DATA

Observed after the six mechanics had already been rejected by the preregistered
gates, on data that has been used repeatedly. None of it changed Phase 6 and none
of it may become a strategy on 2021–2025.

Untouched data remaining after Phase 6: **2026-Q1** (Trades — never opened by
Phase 4, 5 or 6), **2025-H1** (Trades **and** MBP-1) and **2026-04-01 onward**.
That is the whole remaining budget across the project.

---

## H6-1 — the most important carry-forward is a process finding, not a market one

**A control that is allowed to see the future will beat a strategy that is not,
and the result will look like a discovery.**

Phase 5 concluded that its model found good context and timed entries badly. That
conclusion came from a control whose entries preceded the signal supplying their
direction **44.1 % of the time**, by a median of 6–8 minutes. Removing only that
leak halved the apparent context return (+0.1034 → +0.0521 R) and flipped the
strategy-versus-control count from 2-of-5 to 3-of-5 periods.

The whole of Phase 6 — a new module, six mechanics, 502 contexts, ~9,000 control
trades — exists because of an artefact in one line of control-sampling code.

**Rule for every future phase:** a control must be constructible in real time at
its own entry timestamp. Write the test that asserts
`control_entry_ts ≥ signal_ts` *before* running the control, not a phase later.
`tests/test_p6_context.py::test_random_control_entries_are_never_before_activation`
is the template.

## H6-2 — pullback entries beat random *within the contexts that pull back*

Restricting `CONTROL_RANDOM` to only the contexts each mechanic actually entered
(a like-for-like the preregistered gate deliberately did not use):

| method | contexts | mechanic E[R] | random on the same contexts | diff | 95 % day-block CI |
|---|---:|---:|---:|---:|---|
| E3 | 323 | +0.0641 | +0.0029 | +0.0612 | [−0.0083, +0.1325] |
| **E4** | 227 | **−0.0197** | −0.1098 | **+0.0901** | **[+0.0028, +0.1795]** |
| E5 | 321 | +0.0464 | −0.0021 | +0.0485 | [−0.0200, +0.1175] |
| E6 | 221 | −0.0219 | −0.0958 | +0.0739 | [−0.0119, +0.1594] |
| E1 | 369 | +0.0270 | +0.0518 | −0.0248 | [−0.0796, +0.0306] |
| E2 | 328 | +0.0043 | +0.0192 | −0.0149 | [−0.0741, +0.0432] |

All four pullback mechanics are positive here and E4's interval excludes zero,
while both clock delays are negative. **But note E4's and E6's absolute
expectancy is still negative**: they lose *less* than a random entry in contexts
that have already gone against them. That is loss mitigation inside bad contexts,
not an edge.

**Hypothesis:** conditional on an adverse excursion having occurred, entering on
the pullback is better than entering at a random later minute. Untested as a
standalone claim, and it needs a *positive* base context to be worth anything.

## H6-3 — the context is wildly asymmetric by half-hour and direction

Unconditional random entries inside activated contexts, 8 cells, development
years only:

| bucket | side | n | WR | net E[R] | PF(R) |
|---|---|---:|---:|---:|---:|
| 09:30–10:00 | LONG | 54 | 0.6481 | **+0.2526** | 1.811 |
| 09:30–10:00 | SHORT | 898 | 0.5367 | +0.0348 | 1.073 |
| 10:00–10:30 | LONG | 97 | 0.6186 | +0.0179 | 1.065 |
| 10:00–10:30 | SHORT | 306 | 0.6340 | +0.1723 | 1.572 |
| 10:30–11:00 | LONG | 449 | 0.5546 | +0.1148 | 1.405 |
| 10:30–11:00 | SHORT | 596 | 0.5805 | +0.0968 | 1.269 |
| **11:00–11:30** | **LONG** | 549 | **0.6412** | **+0.2554** | **2.115** |
| **11:00–11:30** | SHORT | 1,535 | 0.4906 | **−0.0194** | 0.952 |

The last bucket splits violently: longs at PF(R) 2.115, shorts at 0.952 — and
**shorts are 74 % of the volume there**. The model is issuing mostly short
contexts in the one window where its longs are best.

This echoes Phase 5's H5-6 (11:00–11:30 was the only positive time bucket in the
unconditional data) from an independent direction, which makes it more
interesting than a lone subgroup. It is still 8 cells on used data, and the
09:30–10:00 LONG cell has n = 54.

**Do not narrow the session to it.** If anything it argues for testing a *later*
window on new data, and for asking why the direction model is short-biased
(**70% short overall**) in a market that drifted up.

## H6-4 — earlier is better, monotonically, inside a context

Random entries by wait after activation:

| wait | n | WR | net E[R] | PF(R) |
|---|---:|---:|---:|---:|
| 0–5 min | 1,278 | 0.5603 | **+0.0770** | 1.217 |
| 5–10 | 1,025 | 0.5522 | +0.0701 | 1.192 |
| 10–15 | 767 | 0.5567 | +0.0716 | 1.195 |
| 15–20 | 596 | 0.5403 | +0.0637 | 1.173 |
| 20+ | 818 | 0.5379 | +0.0683 | 1.177 |

Whatever the context is worth, it decays mildly with time. This is *why* every
delay mechanic lost: E1 and E2 systematically trade a decaying edge for nothing.

**Hypothesis:** if the context has any value it is front-loaded, so a successor
should test entry *mechanics that fire fast* — not slower ones. Note this cuts
directly against the Phase-5 premise that motivated Phase 6.

## H6-5 — adverse selection offsets price improvement almost exactly

| method | price improvement (R) | adverse excursion before entry (R) | net |
|---|---:|---:|---:|
| E1 | +0.0372 | 0.4901 | −0.4529 |
| E2 | +0.0733 | 0.6965 | −0.6232 |
| **E3** | **+0.2573** | **0.2786** | **−0.0213** |
| **E4** | **+0.5036** | **0.5296** | **−0.0260** |
| E5 | +0.2542 | 0.3837 | −0.1295 |
| E6 | +0.5084 | 0.6346 | −0.1261 |

At both pullback depths the discount bought is within **0.03 R** of the adverse
excursion suffered to obtain it. That is not a coincidence to be optimised
around; it is what an efficient market looks like at this timescale, and it
predicts that *no* pullback depth will help. Which is why the budget forbade
testing more of them.

**Hypothesis (for a genuinely different phase):** to profit from a better entry
price you need a mechanism that is *not* "wait for the market to move against
you" — e.g. a resting limit that is filled by someone else's urgency rather than
by an adverse trend. That requires MBP-1 queue and imbalance data, which is
exactly what 2025-H1 was sealed for.

## H6-6 — the context model is 70 % short and that may be the real problem

Across all five periods: **353 short contexts vs 149 long** (70% short), in a
market that rose substantially over 2021–2025. The long contexts outperform in
five of the eight bucket × direction cells and dominate the best ones.

This is a **direction-model** observation, and Phase 6 was explicitly forbidden
from touching the direction model — correctly. But it points at the more
promising target: the asymmetry between the long and short branches of
`r4p0:A_logit`, which Phase 5 also flagged (H5-3, "the most confident short
bucket is the worst bucket in all five periods").

**Two independent phases have now found the same thing from different angles.**
A successor should test whether the model has *any* short-side skill, as a fresh
preregistered hypothesis on untouched data.
