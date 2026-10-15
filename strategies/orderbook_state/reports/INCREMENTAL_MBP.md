# INCREMENTAL_MBP.md — Phase 7

# Does MBP-1 add anything over trades and price?

> **Phase 7 FAILED at the 2022 gate** — no candidate was selected, 2023 was
> never scored, and 2025-H1 stays sealed. The "reference configuration"
> below is `R25:A_logit:top1p0`, the **least-bad of the 12**, used only so the
> mandatory diagnostics have something concrete to run on. It is not a
> candidate and was never frozen.

This is the mandatory test and the central research question. Each arm gets its
**own** 2021-fitted scaler and its **own** 2021 selectivity threshold, on identical
dates, R, model family, selectivity level and execution.

| arm | features | train acc | n | WR | gross E[R] | net E[R] | PF(R) | vs matched random |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **A0 full** | 40 | 0.5204 | 2,229 | 0.4989 | +0.0011 | -0.0389 | 0.924 | -0.0032 |
| A1 quote-only | 32 | 0.5200 | 2,319 | 0.4894 | -0.0211 | -0.0611 | 0.883 | -0.0346 |
| A2 trades + context | 8 | 0.5111 | 563 | 0.4565 | -0.0773 | -0.1173 | 0.789 | -0.0665 |

| comparison | Δ E[R] | 95 % day-block CI | Δ WR | 95 % CI |
|---|---:|---|---:|---|
| **A0 full − A2 trades+context** | **+0.0784** | **[+0.0082, +0.1605]** | +0.0424 | [+0.0061, +0.0854] |
| A0 full − A1 quote-only | +0.0221 | [+0.0029, +0.0420] | | |

## The naive reading, and why it is wrong

Taken alone, `A0 − A2 = +0.0784 R` with an interval excluding zero looks
like a positive finding: *MBP-1 adds information*. **It is not**, and reporting it
that way would be misleading. The comparison is against an arm that is worse than
doing nothing.

Against the unconditional 2022 baseline of **−0.0448 R** (every decision, both
directions, net at 1.0 pt):

| arm | net E[R] | **vs doing nothing** |
|---|---:|---:|
| A0 full (40) | −0.0389 | **+0.0059** |
| A1 quote-only (32) | −0.0611 | −0.0162 |
| A2 trades + context (8) | −0.1173 | −0.0724 |
| *(no model at all)* | *−0.0448* | *0* |

> The full model lands **+0.006 R** from doing nothing — noise. The apparent
> "+0.078 R of incremental MBP value" is the book features **undoing the damage**
> the trades-only arm does, not creating edge above the baseline.

That the trades-only arm is actively harmful is itself consistent with Phases 4–6,
which found trades-derived flow uninformative at two other horizons.

## Verdict on the central question

> **Phase 7 did not establish incremental tradable information from MBP-1.** The
> book features measurably outperform a trades-and-price model, but only by
> returning it to the level of no model at all.
