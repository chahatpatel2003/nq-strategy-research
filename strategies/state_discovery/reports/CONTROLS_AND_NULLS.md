# CONTROLS_AND_NULLS.md — Phase 4

*Frozen production strategy `B_tree:depth=3` top20, tau = 0.017941 · frozen id `statedisc-1.0.0+c147134184dfb32d`*

All four controls were defined in `PREREG_ADDENDUM.md` before any outcome
existed. Every control uses the identical entry model, bracket, 30-minute
horizon and friction as the strategy, because all of them read the same
tick-resolved labels.

## C1 — matched-random entries (the primary null)

Same day, same 30-minute bucket, same direction, R within [0.80, 1.25] x the
signal's R, up to 10 per trade, seed 20260819.

| period | strategy E[R] | control E[R] | Δ | 95 % CI (day-block) | excludes 0 |
|---|---:|---:|---:|---|:---:|
| 2021 train | -0.2428 | -0.2447 | +0.0018 | [-0.0062, +0.0099] | no |
| 2022 selection | -0.1395 | -0.1550 | +0.0155 | [+0.0070, +0.0240] | **yes** |
| 2023 internal OOS | -0.2449 | -0.2475 | +0.0026 | [-0.0061, +0.0113] | no |
| 2024 CONTAMINATED | -0.1986 | -0.2003 | +0.0017 | [-0.0062, +0.0099] | no |
| 2025-H2 CONTAMINATED | -0.1745 | -0.1831 | +0.0086 | [-0.0033, +0.0210] | no |

Note what the control expectancy itself says: a *random* entry with this
geometry loses ~0.15–0.27 R per trade. The 1R/1R bracket at
R = 0.50 x ATR14(1-min) is a structurally losing bet after 1.0 pt of friction,
whoever places it. The strategy's job was to overcome that, and it does not.

## C2 — opposite direction, same timestamps

| period | strategy E[R] | flipped E[R] | Δ | 95 % CI | strategy better |
|---|---:|---:|---:|---|:---:|
| 2021 train | -0.2428 | -0.2745 | +0.0317 | [+0.0092, +0.0545] | yes |
| 2022 selection | -0.1395 | -0.1833 | +0.0438 | [+0.0236, +0.0640] | yes |
| 2023 internal OOS | -0.2449 | -0.2417 | -0.0033 | [-0.0236, +0.0182] | no |
| 2024 CONTAMINATED | -0.1986 | -0.2097 | +0.0111 | [-0.0115, +0.0341] | no |
| 2025-H2 CONTAMINATED | -0.1745 | -0.1867 | +0.0122 | [-0.0164, +0.0400] | no |

The flip is **not** better overall, so there is no hidden inverse strategy here.
On 2023 the two directions are statistically indistinguishable
(-0.0033 R,
CI [-0.0236,
+0.0182]) — the model's
direction call carries no out-of-sample information. Nothing is flipped: an
inverse strategy would be a new hypothesis needing new untouched data.

## C3 — shuffled direction labels (1 000 reps per period)

Entry, R and horizon held fixed; only the sign is reassigned at random,
preserving the realised long fraction.

| period | strategy E[R] | null mean | null p95 | p(null ≥ strategy) |
|---|---:|---:|---:|---:|
| 2021 train | -0.2428 | -0.2539 | -0.2494 | 0.000 |
| 2022 selection | -0.1395 | -0.1526 | -0.1476 | 0.000 |
| 2023 internal OOS | -0.2449 | -0.2467 | -0.2415 | 0.283 |
| 2024 CONTAMINATED | -0.1986 | -0.2017 | -0.1963 | 0.191 |
| 2025-H2 CONTAMINATED | -0.1745 | -0.1706 | -0.1618 | 0.775 |

Significant on 2021 and 2022. **Not** significant on 2023 (p = 0.283),
2024 (p = 0.191) or
2025-H2 (p = 0.775).

## C4 — randomised feature/target relationship (20 refits)

The 2021 target is permuted **within trading days** — feature marginals and day
structure survive, only the feature→target link dies — the frozen configuration
is refitted, tau is recalibrated by the same rule, and 2022 is rescored.

| quantity | value |
|---|---|
| observed 2022 E[R] | **-0.1395** |
| null E[R], mean ± sd | -0.1592 ± 0.0043 |
| null E[R] range | -0.1691 … -0.1530 |
| observed 2022 WR | 0.5023 |
| null WR, mean ± sd | 0.4923 ± 0.0012 |
| p(null ≥ observed), E[R] | **0.000** |
| p(null ≥ observed), WR | **0.000** |

This is the most informative control in Phase 4, and it cuts both ways.

The model **is** materially different from chance: it beats a same-complexity
model trained on scrambled labels by
**+0.0197 R per
trade**, 5 null
standard deviations away, with no permutation reaching it.

And it is **nowhere near enough**. The learned signal is worth about
0.020 R
per trade while friction at this R scale costs roughly 0.20 R per trade. Phase 4
found a real state effect that is an order of magnitude too small to trade.

The caveat: C4 is measured on 2022, the selection year. On 2023 the C3 null
cannot distinguish the model from a coin flip at all.
