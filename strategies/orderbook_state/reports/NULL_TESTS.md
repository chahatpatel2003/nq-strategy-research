# NULL_TESTS.md — Phase 7

> **Phase 7 FAILED at the 2022 gate** — no candidate was selected, 2023 was
> never scored, and 2025-H1 stays sealed. The "reference configuration"
> below is `R25:A_logit:top1p0`, the **least-bad of the 12**, used only so the
> mandatory diagnostics have something concrete to run on. It is not a
> candidate and was never frozen.

## N1 — label permutation within trading days (50 refits)

The target is permuted **inside each training day**, preserving day structure and
feature marginals; the identical model is refitted, thresholds recomputed by the
same rule, and 2022 rescored.

| quantity | value |
|---|---:|
| observed 2022 E[R] | **-0.0389** |
| null E[R], mean ± sd | -0.0266 ± 0.0114 |
| null E[R] range | -0.0496 … +0.0020 |
| observed WR | 0.4989 |
| null WR mean | 0.5061 |
| **p(null ≥ observed), E[R]** | **0.840** |
| p(null ≥ observed), WR | 0.840 |

The real model is **-1.1 standard
deviations from the null mean — on the wrong side.** A model trained on scrambled
labels does *better* than the real one, 84 % of the time. There is no skill here
to detect.

Contrast Phase 4, where the same test gave p = 0.00 and the model beat its
permutation null by 5 σ. That was a real (if tiny) signal. This is not.

## N2 — temporal shift (+7 trading days)

Each decision's features are paired with the labels of the **same time-of-day slot
7 trading days later**, preserving both marginal distributions and destroying only
the causal link.

| | observed | temporally shifted |
|---|---:|---:|
| n | 2,229 | 1,637 |
| WR | 0.4989 | 0.4973 |
| E[R] | -0.0389 | -0.0390 |
| **difference** | | **+0.0001 R** |

1,097,280 rows were shifted. **Destroying the causal feature→outcome
relationship changes the result by 0.0001 R.** Whatever the model is doing is
entirely explained by structure that survives a week-long displacement — that is,
by nothing causal at all.

Taken together, N1 and N2 are more informative than the gates: the gates say the
strategy is unprofitable, the nulls say there was never a relationship to trade.
