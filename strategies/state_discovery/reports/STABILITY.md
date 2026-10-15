# STABILITY.md — Phase 4

*Frozen production strategy `B_tree:depth=3` top20, tau = 0.017941 · frozen id `statedisc-1.0.0+c147134184dfb32d`*

## Headline, 09:30–11:30, 1R, 1.0 pt round trip

| metric | 2021 train | 2022 selection | 2023 internal OOS | 2024 CONTAMINATED | 2025-H2 CONTAMINATED |
|---|---|---|---|---|---|
| `n_trades` | 34,653 | 37,667 | 36,145 | 36,092 | 18,000 |
| `win_rate` | 0.4908 | 0.5023 | 0.4826 | 0.4900 | 0.4933 |
| `expectancy_R` | -0.2428 | -0.1395 | -0.2449 | -0.1986 | -0.1745 |
| `profit_factor` | 0.689 | 0.798 | 0.671 | 0.729 | 0.762 |
| `R_per_day` | -33.1301 | -20.6828 | -34.8549 | -28.1128 | -24.5345 |
| `trades_per_day` | 136.4 | 148.3 | 142.3 | 141.5 | 140.6 |
| `avg_hold_min` | 0.58 | 0.59 | 0.59 | 0.62 | 0.62 |
| `max_drawdown_R` | 8,417 | 5,254 | 8,859 | 7,181 | 3,141 |
| `pct_profitable_days` | 0.0514 | 0.0748 | 0.0198 | 0.0706 | 0.0547 |

## Friction sweep — expectancy in R

| friction | 2021 train | 2022 selection | 2023 internal OOS | 2024 CONTAMINATED | 2025-H2 CONTAMINATED |
|---|---|---|---|---|---|
| 0.0 pt | -0.0130 | +0.0025 | -0.0298 | -0.0185 | -0.0160 |
| 0.5 pt | -0.1279 | -0.0685 | -0.1373 | -0.1085 | -0.0952 |
| 1.0 pt | -0.2428 | -0.1395 | -0.2449 | -0.1986 | -0.1745 |
| 2.0 pt | -0.4727 | -0.2814 | -0.4601 | -0.3788 | -0.3330 |

**Read the top row first.** At *zero* friction — no commission, no slippage
beyond what the tape already imposed — the strategy is
-0.0130 R on 2021 train, +0.0025 R on 2022 selection, -0.0298 R on 2023 internal OOS, -0.0185 R on 2024 CONTAMINATED, -0.0160 R on 2025-H2 CONTAMINATED. There is no
gross edge for friction to eat. Friction is not the reason this fails; it is
what turns a flat result into an obviously losing one.

## Against the primary null — matched random entries

| period | ΔE[R] | 95 % block-bootstrap CI | excludes 0 | ΔWR | 95 % CI | excludes 0 |
|---|---:|---|:---:|---:|---|:---:|
| 2021 train | +0.0018 | [-0.0062, +0.0099] | no | +0.0018 | [-0.0021, +0.0058] | no |
| 2022 selection | +0.0155 | [+0.0070, +0.0240] | **yes** | +0.0086 | [+0.0044, +0.0128] | **yes** |
| 2023 internal OOS | +0.0026 | [-0.0061, +0.0113] | no | +0.0026 | [-0.0017, +0.0070] | no |
| 2024 CONTAMINATED | +0.0017 | [-0.0062, +0.0099] | no | +0.0020 | [-0.0019, +0.0060] | no |
| 2025-H2 CONTAMINATED | +0.0086 | [-0.0033, +0.0210] | no | +0.0051 | [-0.0008, +0.0113] | no |

The only period where the strategy separates from matched random is **2022 —
the year used to select it**. On 2021 (its own training year), on 2023
(untouched during selection), on 2024 and on 2025-H2, the confidence interval
contains zero. That is the signature of a selection artifact, not of an edge.

## Extended-window diagnostics (reported, never used to choose)

| window | 2021 train | 2022 selection | 2023 internal OOS | 2024 CONTAMINATED | 2025-H2 CONTAMINATED |
|---|---|---|---|---|---|
| 0930–1130 | -0.2428 (34,653) | -0.1395 (37,667) | -0.2449 (36,145) | -0.1986 (36,092) | -0.1745 (18,000) |
| 0930–1030 | -0.2449 (21,136) | -0.1408 (21,859) | -0.2404 (21,668) | -0.1893 (21,345) | -0.1687 (10,469) |
| 1030–1130 | -0.2386 (13,653) | -0.1372 (15,939) | -0.2511 (14,607) | -0.2127 (14,876) | -0.1815 (7,604) |
| 0930–1200 | -0.2500 (40,904) | -0.1472 (45,177) | -0.2553 (43,145) | -0.2070 (43,162) | -0.1880 (21,745) |
| 0930–1600 | -0.3131 (92,976) | -0.1758 (106,086) | -0.2859 (95,391) | -0.2368 (100,115) | -0.2260 (47,747) |

No window is profitable in any period. The official 09:30–11:30 session is not
the worst and not the best; widening to 16:00 makes every period worse.
