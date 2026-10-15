# CALIBRATION.md — Phase 4

*Frozen production strategy `B_tree:depth=3` top20, tau = 0.017941 · frozen id `statedisc-1.0.0+c147134184dfb32d`*

The question: **does more model confidence correspond to more realised edge?**
The answer is no, and in the most confident bucket it is inverted.

## Trade level — realised performance by \|score\|, with the matched control beside it

| period | \|score\| | trades | WR | E[R] | control E[R] | strategy − control |
|---|---:|---:|---:|---:|---:|---:|
| 2024 CONTAMINATED | 0.017941 | 27,587 | 0.4927 | -0.1647 | -0.1904 | +0.0256 |
| 2024 CONTAMINATED | 0.048440 | 472 | 0.4767 | -0.3034 | -0.2210 | -0.0824 |
| 2024 CONTAMINATED | 0.051059 | 4,081 | 0.4651 | -0.4642 | -0.2329 | -0.2313 |
| 2024 CONTAMINATED | 0.062383 | 3,952 | 0.4990 | -0.1486 | -0.1841 | +0.0356 |
| 2025-H2 CONTAMINATED | 0.017941 | 13,349 | 0.4981 | -0.1410 | -0.1808 | +0.0399 |
| 2025-H2 CONTAMINATED | 0.048440 | 269 | 0.4535 | -0.3388 | -0.2119 | -0.1268 |
| 2025-H2 CONTAMINATED | 0.051059 | 1,599 | 0.4822 | -0.4340 | -0.2238 | -0.2103 |
| 2025-H2 CONTAMINATED | 0.062383 | 2,783 | 0.4808 | -0.1701 | -0.1795 | +0.0093 |
| 2023 internal OOS | 0.017941 | 26,390 | 0.4893 | -0.1920 | -0.2330 | +0.0411 |
| 2023 internal OOS | 0.048440 | 730 | 0.4521 | -0.3469 | -0.2514 | -0.0955 |
| 2023 internal OOS | 0.051059 | 6,539 | 0.4498 | -0.4853 | -0.2687 | -0.2166 |
| 2023 internal OOS | 0.062383 | 2,486 | 0.5068 | -0.1448 | -0.2254 | +0.0806 |
| 2022 selection | 0.017941 | 31,112 | 0.5027 | -0.1227 | -0.1559 | +0.0332 |
| 2022 selection | 0.048440 | 255 | 0.4941 | -0.2521 | -0.1613 | -0.0908 |
| 2022 selection | 0.051059 | 2,276 | 0.4741 | -0.4145 | -0.1922 | -0.2223 |
| 2022 selection | 0.062383 | 4,024 | 0.5164 | -0.1062 | -0.1479 | +0.0417 |
| 2021 train | 0.017941 | 23,598 | 0.4939 | -0.1813 | -0.2372 | +0.0559 |
| 2021 train | 0.048440 | 1,081 | 0.4986 | -0.2914 | -0.2788 | -0.0125 |
| 2021 train | 0.051059 | 8,624 | 0.4753 | -0.4271 | -0.2704 | -0.1567 |
| 2021 train | 0.062383 | 1,350 | 0.5281 | -0.1022 | -0.2143 | +0.1121 |

Rank correlation between \|score\| and realised expectancy, by period:

| period | buckets | Spearman(\|score\|, E[R]) |
|---|---:|---:|
| 2021 train | 4 | +0.20 |
| 2022 selection | 4 | +0.20 |
| 2023 internal OOS | 4 | +0.20 |
| 2024 CONTAMINATED | 4 | +0.20 |
| 2025-H2 CONTAMINATED | 4 | -0.40 |

**The relationship is not monotone in any period**, and in 2025-H2 it is
negative. Concretely and consistently across all five periods:

* the **most confident short** bucket (`|score| = 0.051059`) is the **worst**
  bucket everywhere — E[R] between -0.485
  and -0.414 R —
  and it *underperforms* its own matched control by
  0.23 R
  in the worst case. High model confidence on the short side is an anti-signal.
* the **most confident long** bucket (`|score| = 0.062383`) is the **best**
  bucket everywhere and beats its control in all five periods — yet is still
  net-negative in all five.
* the **least confident traded** bucket (`|score| = 0.017941`, which is the bulk
  of the book) sits in between and also beats its control in all five periods.

A confidence score that does not order realised outcomes is not a usable
confidence score. The threshold is **not** being adjusted in response: PREREG A7
fixed it before any outcome, and moving it now would be threshold mining.

## Row level — 2023, every usable decision row bucketed by the model's score

| score | predicted P(long wins) | rows | traded | actual P(long wins) | gross R in model's direction |
|---:|---:|---:|:---:|---:|---:|
| -0.051059 | 0.4489 | 27,585 | yes | 0.4618 | -0.0359 |
| -0.017941 | 0.4821 | 209,987 | yes | 0.4912 | -0.0242 |
| -0.006846 | 0.4932 | 30,479 | no | 0.4937 | -0.0512 |
| -0.003785 | 0.4962 | 2,632 | no | 0.4707 | -0.0316 |
| +0.003842 | 0.5038 | 67,134 | no | 0.4936 | -0.0133 |
| +0.048440 | 0.5484 | 4,813 | yes | 0.4660 | -0.0692 |
| +0.062383 | 0.5624 | 21,690 | yes | 0.5189 | +0.0369 |

Rows overlap by up to 30 minutes, so this is a shape diagnostic and not an
inference. Two things are visible anyway. The tree's predicted probability spans
only **0.449 to 0.562** — the
signal is weak by construction. And the mapping from predicted to actual is
loose: the bucket predicting 0.449
realised 0.462, while the bucket
predicting 0.562 realised
0.519. Directionally right at the
extremes, badly calibrated in between, and far too small either way.
