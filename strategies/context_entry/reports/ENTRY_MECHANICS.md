# ENTRY_MECHANICS.md — Phase 6

*Context model: the FROZEN Phase-5 `r4p0:A_logit:top2`, τ = 0.179938, R = 4.0 × ATR14(1-min), 1R/1R, 60-minute hold. Phase 6 changes only the entry moment.*

> **Phase 6 FAILED before validation.** No entry mechanic passed the
> preregistered development gates, and the causal context itself does not
> beat non-context moments. 2026-Q1 was never opened.

## TOTAL ENTRY CONFIGURATIONS EVALUATED: 6 of a ceiling of 6

All six were fixed in `PHASE6_SEARCH_BUDGET.md` §2 before any outcome existed.
No seventh mechanic and no nearby parameter value was tried.

## All six against the primary null, pooled 2021–2025-H2

| method | n | WR | gross E[R] | net E[R] | PF(R) | periods +ve | median advantage | pooled advantage | 95 % day-block CI | median wait (min) | mean fill improvement (R) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| E1 | 369 | 0.5149 | +0.0567 | +0.0270 | 1.067 | 3/5 | -0.0627 | -0.0442 | [-0.1064, +0.0173] | 5.0 | +0.0372 |
| E2 | 328 | 0.5091 | +0.0344 | +0.0043 | 1.010 | 2/5 | -0.0741 | -0.0669 | [-0.1350, -0.0006] | 10.0 | +0.0733 |
| E3 | 323 | 0.5387 | +0.0945 | +0.0641 | 1.161 | 3/5 | -0.0096 | -0.0070 | [-0.0846, +0.0712] | 1.6 | +0.2573 |
| E4 | 227 | 0.4890 | +0.0123 | -0.0197 | 0.957 | 2/5 | -0.1043 | -0.0909 | [-0.1960, +0.0110] | 4.4 | +0.5036 |
| E5 | 321 | 0.5358 | +0.0772 | +0.0464 | 1.115 | 3/5 | -0.0029 | -0.0247 | [-0.1002, +0.0511] | 2.1 | +0.2542 |
| E6 | 221 | 0.4887 | +0.0103 | -0.0219 | 0.952 | 1/5 | -0.1076 | -0.0931 | [-0.1982, +0.0099] | 4.6 | +0.5084 |
| CONTROL_IMMEDIATE | 409 | 0.5550 | +0.0977 | +0.0680 | 1.181 | 4/5 | -0.0081 | -0.0032 | [-0.0728, +0.0671] | 0.0 | +0.0000 |
| **CONTROL_RANDOM** | 4,484 | 0.5511 | +0.1005 | **+0.0711** | 1.194 | — | — | — | *(the primary null)* | — | — |

**Every one of the six has a negative advantage over random timing inside the
same context.** So does `CONTROL_IMMEDIATE`. Random entry beats deliberate entry.

For E2 the interval [-0.1350, …] excludes zero **on the wrong
side** — a fixed 10-minute delay is significantly worse than random.

## Per-period net expectancy at 1.0 pt

| method | 2021 | 2022 | 2023 | 2024 | 2025-H2 |
|---|---|---|---|---|---|
| E1 | +0.1533 | -0.0628 | +0.0048 | -0.0314 | +0.0868 |
| E2 | +0.2116 | -0.0231 | +0.0339 | -0.0838 | -0.3152 |
| E3 | +0.2059 | -0.0015 | +0.0730 | +0.0133 | -0.0313 |
| E4 | +0.0278 | -0.0533 | -0.0560 | -0.0232 | +0.0325 |
| E5 | +0.1727 | -0.0046 | +0.0646 | +0.0346 | -0.1160 |
| E6 | +0.0704 | -0.0000 | -0.0785 | -0.0847 | -0.0926 |
| CONTROL_IMMEDIATE | +0.1347 | +0.0429 | -0.0128 | +0.0937 | +0.0812 |
| **CONTROL_RANDOM** | +0.2230 | +0.0510 | +0.0675 | +0.0230 | -0.1210 |

## Preregistered development gates

| method | G1 n ≥ 300 | G2 ≥ 4/5 periods +ve | G2 combined > 0 | G3 PF(R) > 1.10 | G4 advantage CI low > 0 | result |
|---|---|---|---|---|---|---|
| **E1** | 369 ✓ | 3/5 ✗ | +0.0270 ✓ | 1.067 ✗ | -0.1064 ✗ | rejected |
| **E2** | 328 ✓ | 2/5 ✗ | +0.0043 ✓ | 1.010 ✗ | -0.1350 ✗ | rejected |
| **E3** | 323 ✓ | 3/5 ✗ | +0.0641 ✓ | 1.161 ✓ | -0.0846 ✗ | rejected |
| **E4** | 227 ✗ | 2/5 ✗ | -0.0197 ✗ | 0.957 ✗ | -0.1960 ✗ | rejected |
| **E5** | 321 ✓ | 3/5 ✗ | +0.0464 ✓ | 1.115 ✓ | -0.1002 ✗ | rejected |
| **E6** | 221 ✗ | 1/5 ✗ | -0.0219 ✗ | 0.952 ✗ | -0.1982 ✗ | rejected |

**ELIGIBLE: NONE.**
E4 and E6 additionally fail the sample floor — they only trigger on 44–45 % of
contexts. Not one mechanic reaches 4 of 5 positive periods, and not one has a
positive advantage lower bound.

Per `PHASE6_SEARCH_BUDGET.md` §6 there is no least-bad candidate:
**Phase 6 fails before validation and 2026-Q1 stays sealed.**

## Why the pullback entries do not help — the mechanism

| method | price improvement vs immediate (R) | adverse excursion before entry (R) | net | contexts entered |
|---|---:|---:|---:|---:|
| E1 | +0.0372 | 0.4901 | -0.4529 | 369 (74%) |
| E2 | +0.0733 | 0.6965 | -0.6232 | 328 (65%) |
| E3 | +0.2573 | 0.2786 | -0.0213 | 323 (64%) |
| E4 | +0.5036 | 0.5296 | -0.0260 | 227 (45%) |
| E5 | +0.2542 | 0.3837 | -0.1295 | 321 (64%) |
| E6 | +0.5084 | 0.6346 | -0.1261 | 221 (44%) |

This is the clearest result in Phase 6. A mechanic that waits for a better price
**only gets one when the market has already moved against the context**, and the
adverse excursion it must sit through is consistently larger than the discount it
buys:

* **E3** buys a +0.2573 R better fill and pays 0.2786 R of adverse excursion — almost exactly a wash.
* **E4** buys +0.5036 R and pays 0.5296 R — also a wash, on half as many contexts.
* **E1/E2** are strictly worse: a pure clock delay sits through 0.49–0.70 R of adverse excursion and is compensated with only +0.037–+0.073 R of price.

Adverse selection is not *approximately* offsetting the price improvement — it is
offsetting it almost exactly, at both pullback depths. That is what a
well-functioning market looks like at this timescale.

## A diagnostic that is NOT a gate

Restricting `CONTROL_RANDOM` to only the contexts each mechanic actually entered
(a fairer like-for-like, since E3–E6 skip contexts that never pull back):

| method | contexts | mechanic E[R] | random on the same contexts | diff | 95 % CI |
|---|---:|---:|---:|---:|---|
| E1 | 369 | +0.0270 | +0.0518 | −0.0248 | [−0.0796, +0.0306] |
| E2 | 328 | +0.0043 | +0.0192 | −0.0149 | [−0.0741, +0.0432] |
| E3 | 323 | +0.0641 | +0.0029 | +0.0612 | [−0.0083, +0.1325] |
| E4 | 227 | **−0.0197** | −0.1098 | +0.0901 | **[+0.0028, +0.1795]** |
| E5 | 321 | +0.0464 | −0.0021 | +0.0485 | [−0.0200, +0.1175] |
| E6 | 221 | **−0.0219** | −0.0958 | +0.0739 | [−0.0119, +0.1594] |

On the subset of contexts that *do* pull back, the pullback entries **do** beat a
random entry in those same contexts, and E4's interval excludes zero.

**This does not rescue anything, and it is not used as a gate.** The
preregistered comparison is against the full random-control population and was
fixed before any outcome; swapping it for this one after seeing the results is
precisely the post-hoc gate change the brief forbids. Note also that E4's and
E6's absolute expectancy is still **negative** — they lose less than random in
bad contexts, which is not a tradable edge. It is recorded as hypothesis H6-2.
