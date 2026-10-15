# SELECTION_2022.md — Phase 7

> **Phase 7 FAILED at the 2022 gate.** None of the 12 configurations passed,
> so no candidate was frozen, 2023 was never scored, and **2025-H1 stays
> sealed**. Everything below describes a rejected search.

## 2021 training

Scaler and both model families fitted on **364,320 2021 rows only**.
Selectivity thresholds are quantiles of `|p − 0.5|` on those same 2021 rows and
were then frozen as numbers. Control matching quartile edges likewise come from
2021 alone: ATR [31.21, 42.21, 57.79] ticks, spread
[2.0, 2.0, 2.0] ticks.

**Training accuracy was 0.5111–0.5215** across arms — barely above a coin flip on
in-sample data, which is the first sign of what follows.

## All 12 configurations on 2022

**TOTAL CONFIGURATIONS EVALUATED: 12 of 12.**

| # | configuration | n | /day | WR | gross E[R] | net E[R] | PF(R) | control E[R] | advantage | G1–G6 |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | `R25:A_logit:top1p0` | 2,229 | 8.78 | 0.4989 | +0.0011 | **-0.0389** | 0.924 | -0.0357 | -0.0032 | ✓····✓ |
| 2 | `R25:A_logit:top0p5` | 1,572 | 6.19 | 0.4892 | -0.0226 | **-0.0626** | 0.880 | -0.0192 | -0.0434 | ✓····· |
| 3 | `R25:A_logit:top0p2` | 1,055 | 4.15 | 0.4882 | -0.0239 | **-0.0639** | 0.878 | -0.0043 | -0.0596 | ✓····· |
| 4 | `R15:A_logit:top1p0` | 2,816 | 11.09 | 0.4954 | -0.0093 | **-0.0760** | 0.858 | -0.0620 | -0.0139 | ✓····· |
| 5 | `R25:B_tree:top1p0` | 1,021 | 4.02 | 0.4770 | -0.0457 | **-0.0857** | 0.839 | -0.0424 | -0.0433 | ✓····· |
| 6 | `R25:B_tree:top0p5` | 1,021 | 4.02 | 0.4770 | -0.0457 | **-0.0857** | 0.839 | -0.0424 | -0.0433 | ✓····· |
| 7 | `R25:B_tree:top0p2` | 1,021 | 4.02 | 0.4770 | -0.0457 | **-0.0857** | 0.839 | -0.0424 | -0.0433 | ✓····· |
| 8 | `R15:A_logit:top0p5` | 1,608 | 6.33 | 0.4832 | -0.0295 | **-0.0962** | 0.822 | -0.0659 | -0.0303 | ✓····· |
| 9 | `R15:A_logit:top0p2` | 758 | 2.98 | 0.4763 | -0.0379 | **-0.1046** | 0.806 | -0.0763 | -0.0283 | ✓····· |
| 10 | `R15:B_tree:top1p0` | 49 | 0.19 | 0.3878 | -0.1622 | **-0.2289** | 0.523 | -0.0279 | -0.2010 | ······ |
| 11 | `R15:B_tree:top0p5` | 49 | 0.19 | 0.3878 | -0.1622 | **-0.2289** | 0.523 | -0.0279 | -0.2010 | ······ |
| 12 | `R15:B_tree:top0p2` | 49 | 0.19 | 0.3878 | -0.1622 | **-0.2289** | 0.523 | -0.0279 | -0.2010 | ······ |

Gates: **G1** n ≥ 200 · **G2** net E[R] > 0 · **G3** PF(R) > 1.10 · **G4/G5**
advantage over matched random > 0 · **G6** gross E[R] > 0.

| gate | configurations passing |
|---|---:|
| G1 sample ≥ 200 | 9 / 12 |
| **G2 net expectancy > 0** | **0 / 12** |
| **G3 PF(R) > 1.10** | **0 / 12** |
| **G4/G5 beats matched random** | **0 / 12** |
| G6 gross expectancy > 0 | 1 / 12 |

**Eligible: none.** Per `SEARCH_BUDGET.md` §7 there is no least-bad candidate:
Phase 7 fails before 2023, and 2023 was never scored.

## The depth-3 tree collapses its three selectivity levels

`R15:B_tree` and `R25:B_tree` give identical results at top-1.0 %, top-0.5 % and
top-0.2 %. A depth-3 tree emits at most 8 distinct probabilities, so all three
quantiles land inside the same tie group, and the preregistered rule keeps ties.
Disclosed, not adjusted — changing the tie rule after seeing outcomes is exactly
what the preregistration exists to prevent. It also means the tree arms
effectively contributed 2 distinct strategies, not 6.

## The spread is a degenerate conditioning variable for NQ

The 2021 spread quartile edges are **[2, 2, 2] ticks** — the NQ top-of-book spread
is 2 ticks at the 25th, 50th *and* 75th percentile. "Spread regime" therefore
cannot separate anything in this market, which is itself a useful negative and is
why the matched control effectively conditions on day/time/direction/volatility
only.
