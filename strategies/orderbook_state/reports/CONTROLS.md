# CONTROLS.md — Phase 7

> **Phase 7 FAILED at the 2022 gate** — no candidate was selected, 2023 was
> never scored, and 2025-H1 stays sealed. The "reference configuration"
> below is `R25:A_logit:top1p0`, the **least-bad of the 12**, used only so the
> mandatory diagnostics have something concrete to run on. It is not a
> candidate and was never frozen.

All controls read the same tick-resolved labels as the strategy, so execution,
bracket, horizon, timeout and friction are identical by construction. Control
causality is asserted at **runtime** and raises `ControlCausalityViolation` on any
breach — the direct fix for the defect Phase 6 found in Phase 5.

## Matched random — the primary null

| variant | control n | control E[R] | control WR | Δ E[R] | 95 % day-block CI | verdict |
|---|---:|---:|---:|---:|---|---|
| **cross-day (primary)** | 22,290 | -0.0357 | 0.5004 | **-0.0032** | [-0.0448, +0.0396] | contains 0 |
| same-day-forward (secondary) | 20,396 | -0.0461 | 0.4965 | +0.0072 | [-0.0257, +0.0399] | contains 0 |

Win-rate difference (cross-day): -0.0016,
CI [-0.0230, +0.0204].

**Both variants contain zero**, and the primary one is negative. The model's
selection of *which* 5-second book state to trade adds nothing over a random
comparable state.

Two independently-constructed causal controls agreeing is worth more than one:
cross-day matches time-of-day exactly and gives up the day; same-day-forward
matches the day and gives up exact time-of-day. Neither shows an effect.

## Opposite direction

| | E[R] | WR |
|---|---:|---:|
| strategy | -0.0389 | 0.4989 |
| flipped | -0.0630 | 0.4890 |
| difference | +0.0241 | +0.0099 |
| 95 % CI | [-0.0528, +0.1056] | [-0.0292, +0.0506] |

The flip is worse, but the interval contains zero — the direction call is not
distinguishable from its own inverse. Nothing is flipped.

## Friction sweep — is there a gross edge?

| friction | E[R] | PF(R) | WR |
|---|---:|---:|---:|
| 0.0 pt | +0.0011 | 1.002 | 0.5002 |
| 0.5 pt | -0.0189 | 0.962 | 0.4993 |
| 1.0 pt | -0.0389 | 0.924 | 0.4989 |
| 2.0 pt | -0.0789 | 0.851 | 0.4984 |

**At zero friction the reference configuration returns +0.0011 R** — indistinguishable
from nothing, against an unconditional baseline of −0.0448 R. So Phase 7 is not a
case of "edge destroyed by cost": there is no gross edge to destroy. Friction at
these R scales is only 0.040–0.067 R, the smallest of any phase except Phase 5.
