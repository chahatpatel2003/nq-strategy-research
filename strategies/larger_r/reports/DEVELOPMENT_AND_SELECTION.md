# DEVELOPMENT_AND_SELECTION.md — Phase 5

*Candidate `r4p0:A_logit:top2` — R = 4.0 × ATR14(1-min), 60-second clock, 60-minute hold, τ = 0.179938 (top 2 % of the edge score on 2021)*

> **This candidate was REJECTED.** It failed the preregistered Gate F on the
> 2023 internal out-of-sample test, so it was never frozen and 2026-Q1 was
> never opened. Everything below describes a rejected candidate.

## The budget, fully spent

**TOTAL CONFIGURATIONS EVALUATED: 18** of a ceiling of 18
(3 R scales × 2 model families × 3 selectivity levels). Every one was scored
against **2022 only**, on the criterion fixed in `PHASE5_SEARCH_BUDGET.md` §5
before any outcome existed: highest 2022 net expectancy in R at 1.0 pt friction,
subject to ≥ 100 executed trades.

Unlike Phase 4, the budget was spent on **R scale**, because R scale is the
hypothesis. Each family therefore had exactly one hyperparameter setting.

## All 18 on 2022

| rank | configuration | n | /day | WR | gross E[R] | net E[R] | PF(R) | control E[R] | advantage | Gate E |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | `r4p0:A_logit:top2` | 128 | 0.5 | 0.5625 | +0.1173 | **+0.0943** | 1.262 | +0.0367 | +0.0576 | **PASS** |
| 2 | `r2p0:B_tree:top5` | 263 | 1.0 | 0.5665 | +0.1282 | **+0.0897** | 1.251 | +0.0974 | -0.0077 | — |
| 3 | `r4p0:B_tree:top5` | 106 | 0.4 | 0.5472 | +0.0883 | **+0.0711** | 1.114 | +0.0701 | +0.0010 | **PASS** |
| 4 | `r3p0:B_tree:top5` | 140 | 0.6 | 0.5429 | +0.0836 | **+0.0600** | 1.090 | +0.0680 | -0.0080 | — |
| 5 | `r2p0:B_tree:top10` | 369 | 1.5 | 0.5420 | +0.0795 | **+0.0412** | 1.096 | +0.0824 | -0.0412 | — |
| 6 | `r4p0:A_logit:top5` | 231 | 0.9 | 0.5195 | +0.0547 | **+0.0325** | 1.118 | +0.0449 | -0.0124 | — |
| 7 | `r4p0:A_logit:top10` | 423 | 1.7 | 0.5414 | +0.0381 | **+0.0171** | 1.040 | +0.1102 | -0.0932 | — |
| 8 | `r3p0:B_tree:top10` | 249 | 1.0 | 0.5181 | +0.0347 | **+0.0136** | 1.006 | +0.0239 | -0.0103 | — |
| 9 | `r4p0:B_tree:top10` | 168 | 0.7 | 0.5298 | +0.0292 | **+0.0099** | 1.032 | +0.0730 | -0.0631 | — |
| 10 | `r2p0:A_logit:top2` | 276 | 1.1 | 0.5217 | +0.0468 | **+0.0002** | 0.908 | +0.0801 | -0.0799 | — |
| 11 | `r3p0:A_logit:top10` | 564 | 2.2 | 0.5000 | -0.0063 | **-0.0339** | 0.929 | +0.0613 | -0.0951 | — |
| 12 | `r2p0:A_logit:top10` | 1013 | 4.0 | 0.5005 | +0.0022 | **-0.0384** | 0.899 | -0.0130 | -0.0253 | — |
| 13 | `r3p0:B_tree:top2` | 69 | 0.3 | 0.4928 | -0.0177 | **-0.0403** | 0.840 | +0.0409 | -0.0812 | — |
| 14 | `r2p0:A_logit:top5` | 600 | 2.4 | 0.5000 | +0.0001 | **-0.0434** | 0.887 | +0.0467 | -0.0901 | — |
| 15 | `r3p0:A_logit:top2` | 164 | 0.6 | 0.5061 | -0.0139 | **-0.0439** | 0.848 | +0.0080 | -0.0519 | — |
| 16 | `r2p0:B_tree:top2` | 4 | 0.0 | 0.5000 | +0.0004 | **-0.0572** | 1.014 | +0.2893 | -0.3465 | — |
| 17 | `r4p0:B_tree:top2` | 53 | 0.2 | 0.4906 | -0.0467 | **-0.0620** | 0.790 | +0.0588 | -0.1208 | — |
| 18 | `r3p0:A_logit:top5` | 339 | 1.3 | 0.4838 | -0.0367 | **-0.0651** | 0.880 | +0.0060 | -0.0711 | — |

## By R scale — the hypothesis under test

| R scale | mean net E[R] | mean gross E[R] | mean advantage | Gate E passes |
|---|---:|---:|---:|---:|
| `r2p0` (2.0× ATR1m) | -0.0013 | +0.0429 | -0.0985 | 0/6 |
| `r3p0` (3.0× ATR1m) | -0.0183 | +0.0073 | -0.0529 | 0/6 |
| `r4p0` (4.0× ATR1m) | +0.0271 | +0.0468 | -0.0385 | 2/6 |

The largest scale is the only one producing a Gate-E pass, which is directionally
consistent with the hypothesis. But note the third column: **the average advantage
over matched random is negative at every R scale.**

## What changed versus Phase 4, and what did not

**Changed — gross expectancy turned positive.** 12 of the 18 configurations have
positive zero-friction expectancy on 2022. In Phase 4, gross was ≈ 0 or negative
in every period. Enlarging R did what it was supposed to do mechanically.

**Did not change — the model still does not beat its control.** The matched-random
advantage is negative for **16 of 18** configurations. Only 2 of 18 clear Gate E,
and the winner's advantage (+0.0576 R) has a
day-block CI of
[-0.0272,
+0.1475] — it **contains
zero**. Gate E was passed on a point estimate with no statistical support, which
is exactly what the 2023 test then exposed.

## The selected candidate

`r4p0:A_logit:top2`: 2022 n=128, WR 0.5625,
net E[R] +0.0943, PF(R) 1.261.

**A structural caution, recorded here rather than after the fact:** ranking on
expectancy alone systematically favours the *smallest* sample, because small
samples have the widest spread. The winner is the most selective setting
(top 2 %) on the largest R — 128 trades from 30,480 decision rows, 0.5 trades a
day. That is the configuration most exposed to noise, and it is the one the
preregistered criterion picked.
