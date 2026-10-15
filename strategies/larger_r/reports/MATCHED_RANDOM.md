# MATCHED_RANDOM.md — Phase 5 controls

*Candidate `r4p0:A_logit:top2` — R = 4.0 × ATR14(1-min), 60-second clock, 60-minute hold, τ = 0.179938 (top 2 % of the edge score on 2021)*

> **This candidate was REJECTED.** It failed the preregistered Gate F on the
> 2023 internal out-of-sample test, so it was never frozen and 2026-Q1 was
> never opened. Everything below describes a rejected candidate.

Both controls were defined in `PHASE5_SPEC.md` §15 before any outcome existed and
read the **same** tick-resolved labels as the strategy, so execution, bracket,
horizon, timeout and friction are identical by construction.

## C1 — matched random (the primary null)

Same trading day, same 30-minute time-of-day bucket, same direction, control R
within [0.80, 1.25] × the signal's R, up to 10 per trade, seed 20260820.

| period | n | strategy E[R] | control E[R] | Δ | 95 % day-block CI | verdict | opposite E[R] | Δ CI vs opposite |
|---|---:|---:|---:|---:|---|:---:|---:|---|
| 2021 train | 105 | +0.1875 | +0.2689 | -0.0813 | [-0.1929, +0.0272] | indistinguishable | -0.2607 | [+0.1208, +0.7492] |
| 2022 selection | 128 | +0.0943 | +0.0367 | +0.0576 | [-0.0272, +0.1475] | indistinguishable | -0.1404 | [-0.0559, +0.5182] |
| 2023 internal OOS | 93 | -0.0379 | +0.0928 | -0.1307 | [-0.2471, -0.0017] | **worse** | -0.0500 | [-0.3678, +0.3876] |
| 2024 CONTAMINATED | 83 | +0.0826 | +0.0791 | +0.0034 | [-0.1279, +0.1370] | indistinguishable | -0.1413 | [-0.1540, +0.5995] |
| 2025-H2 CONTAMINATED | 56 | +0.0292 | +0.0395 | -0.0103 | [-0.1992, +0.1595] | indistinguishable | -0.0823 | [-0.3593, +0.5925] |

**The strategy never beats its matched control with statistical support in any
period**, and on 2023 the interval lies entirely below zero.

## The decomposition that explains Phase 5

Three nested populations, all at 1.0 pt friction:

| what is being selected | 2021 | 2022 | 2023 | 2024 | 2025-H2 |
|---|---:|---:|---:|---:|---:|
| nothing (every row, either direction) | -0.029 | -0.018 | -0.027 | -0.023 | -0.020 |
| model's **day + 30-min bucket + direction**, random minute | +0.269 | +0.037 | +0.093 | +0.079 | +0.040 |
| model's day + bucket + direction **+ its chosen minute** | +0.188 | +0.094 | -0.038 | +0.083 | +0.029 |

Read down the columns. Going from *nothing* to the model's chosen context adds a
large positive amount in every period. Going from that context to the model's
chosen **minute** subtracts in 3 of 5.

> **The signal identifies favourable (day, half-hour, direction) contexts. Its
> 60-second timing inside them is not merely uninformative — it is adverse.**

That is the single most useful thing Phase 5 produced, and it is recorded as
hypothesis H5-1 in `FUTURE_HYPOTHESES.md`.

## C2 — opposite direction

The flip is worse than the strategy in every period (see the last two columns
above), significantly so on 2021. So the **direction** call does carry
information — which is consistent with the decomposition, since the matched
control inherits that direction and is also positive.

Nothing is flipped and nothing is rebuilt around this. An inverse or
direction-only strategy would be a new hypothesis requiring new data.
