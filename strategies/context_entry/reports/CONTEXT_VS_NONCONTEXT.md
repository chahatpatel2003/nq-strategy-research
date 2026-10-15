# CONTEXT_VS_NONCONTEXT.md — Phase 6

*Context model: the FROZEN Phase-5 `r4p0:A_logit:top2`, τ = 0.179938, R = 4.0 × ATR14(1-min), 1R/1R, 60-minute hold. Phase 6 changes only the entry moment.*

> **Phase 6 FAILED before validation.** No entry mechanic passed the
> preregistered development gates, and the causal context itself does not
> beat non-context moments. 2026-Q1 was never opened.

**Is the causally activated context worth anything at all?** This is logically
prior to any entry question, and `PHASE6_SEARCH_BUDGET.md` §6 makes a negative
answer an independent failure condition.

Both arms are random minutes under identical execution. The only difference is
whether a context was active.

| period | contexts | in-context E[R] | n | WR | non-context E[R] | n | WR | diff | 95 % day-block CI |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2021 | 121 | +0.2230 | 1,096 | 0.6332 | -0.1769 | 1,130 | 0.4283 | +0.3999 | [+0.2242, +0.5768] |
| 2022 | 139 | +0.0510 | 1,276 | 0.5408 | +0.0783 | 1,150 | 0.5409 | -0.0273 | [-0.2094, +0.1561] |
| 2023 | 93 | +0.0675 | 803 | 0.5405 | -0.0272 | 930 | 0.5065 | +0.0947 | [-0.1486, +0.3303] |
| 2024 | 89 | +0.0230 | 790 | 0.5304 | +0.1871 | 850 | 0.6106 | -0.1642 | [-0.3945, +0.0857] |
| 2025-H2 | 60 | -0.1210 | 519 | 0.4509 | -0.0711 | 600 | 0.4767 | -0.0499 | [-0.3112, +0.2281] |
| **pooled** | **502** | **+0.0711** | 4,484 | 0.5511 | **-0.0040** | 4,660 | 0.5112 | **+0.0752** | **[-0.0234, +0.1721]** |

Win-rate difference pooled: +0.0399, CI [-0.0137, +0.0925].

## The pooled interval contains zero

In-context is positive in absolute terms (+0.0711 R,
PF(R) 1.194) but is **not** statistically
distinguishable from trading a no-context half-hour on the same day.

## And the entire effect is the model's own training year

| | in-context | non-context | diff | 95 % CI |
|---|---:|---:|---:|---|
| all five periods | +0.0711 | −0.0040 | +0.0752 | [−0.0234, +0.1721] |
| **excluding 2021** | **+0.0220** | **+0.0513** | **−0.0293** | [−0.1440, +0.0848] |

2021 is where the Phase-5 context model was fitted. It is the only period whose
interval excludes zero (+0.3999, [+0.2242, +0.5768]). Outside it, **no-context
moments are better than in-context moments**, and 2024 and 2025-H2 are both
negative for the context.

**The causal context does not survive out of sample.** See
`CONTEXT_CAUSALITY_AUDIT.md` for why the Phase-5 version appeared to.

## Context frequency

| period | trading days | contexts | contexts/day (of 4 possible) | long | short |
|---|---:|---:|---:|---:|---:|
| 2021 | 254 | 121 | 0.48 | 36 | 85 |
| 2022 | 254 | 139 | 0.55 | 34 | 105 |
| 2023 | 254 | 93 | 0.37 | 29 | 64 |
| 2024 | 255 | 89 | 0.35 | 32 | 57 |
| 2025-H2 | 128 | 60 | 0.47 | 18 | 42 |
| **total** | **1145** | **502** | **0.44** | 149 | 353 |

A top-2 % threshold fires in roughly one bucket in nine, and the contexts are
**70% short**.
