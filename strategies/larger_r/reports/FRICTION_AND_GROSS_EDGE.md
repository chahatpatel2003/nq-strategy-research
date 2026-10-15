# FRICTION_AND_GROSS_EDGE.md — Phase 5

*Candidate `r4p0:A_logit:top2` — R = 4.0 × ATR14(1-min), 60-second clock, 60-minute hold, τ = 0.179938 (top 2 % of the edge score on 2021)*

> **This candidate was REJECTED.** It failed the preregistered Gate F on the
> 2023 internal out-of-sample test, so it was never frozen and 2026-Q1 was
> never opened. Everything below describes a rejected candidate.

Phase 4's central lesson was that "no gross edge" and "edge destroyed by cost"
are different diagnoses and must never be confused. This report separates them.

## Expectancy in R at every friction level

| friction | 2021 train | 2022 selection | 2023 internal OOS | 2024 CONTAMINATED | 2025-H2 CONTAMINATED |
|---|---|---|---|---|---|
| **0.0 pt** | +0.2241 | +0.1173 | -0.0049 | +0.1117 | +0.0558 |
| **0.5 pt** | +0.2058 | +0.1058 | -0.0214 | +0.0972 | +0.0425 |
| **1.0 pt** | +0.1875 | +0.0943 | -0.0379 | +0.0826 | +0.0292 |
| **2.0 pt** | +0.1510 | +0.0713 | -0.0709 | +0.0534 | +0.0027 |
| *friction cost/trade* | *0.0366 R* | *0.0230 R* | *0.0330 R* | *0.0292 R* | *0.0265 R* |

## The mechanical hypothesis is CONFIRMED

| | Phase 4 | Phase 5 |
|---|---:|---:|
| average R | 7.0 pt | 45.1 pt |
| friction cost per trade | 0.1435 R | **0.0296 R** |
| median hold | 0.4 min | 26.5 min |
| trades/day | ~140 | 0.41 |

Enlarging R cut the friction burden by roughly **4.8×**,
exactly as designed. **Friction is no longer the binding constraint.**

## And gross expectancy did turn positive

Zero-friction expectancy is positive in **4 of 5** periods,
against Phase 4 where it was ≈ 0 or negative in every one. At this horizon the
state does appear to sit on a positive gross return.

**But that is not the same as an edge**, and the reason is the next section.

## The unconditional larger-R bracket is NOT structurally profitable

Computed over **every** decision row, no model involved, net at 1.0 pt:

| R scale | long E[R] | long WR | short E[R] | short WR | mean of the two |
|---|---:|---:|---:|---:|---:|
| `r2p0` (2.0× ATR1m) | −0.0566 | 0.4934 | −0.0410 | 0.5003 | **−0.0488** |
| `r3p0` (3.0× ATR1m) | −0.0329 | 0.5000 | −0.0317 | 0.4913 | **−0.0323** |
| `r4p0` (4.0× ATR1m) | −0.0192 | 0.5076 | −0.0280 | 0.4794 | **−0.0236** |

A coin-flip entry loses at every scale, so the positive strategy figures are not
an artefact of the bracket geometry. They are the product of *selecting* days,
half-hours and directions — which is real, and which the matched control shares
in full. See `MATCHED_RANDOM.md`.

## Verdict on the cost question

> **Phase 5 is not a case of "edge destroyed by cost".** Friction was reduced to
> 0.030 R
> per trade — 2–5 % of R — and the strategy still failed, because it never
> separated from a random entry placed in the same context.
