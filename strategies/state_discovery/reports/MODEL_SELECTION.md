# MODEL_SELECTION.md — Phase 4

*Frozen production strategy `B_tree:depth=3` top20, tau = 0.017941 · frozen id `statedisc-1.0.0+c147134184dfb32d`*

## The budget, fully spent

**TOTAL CONFIGURATIONS EVALUATED: 18** of a
ceiling of 18 (2 families x 3 hyperparameters x 3 thresholds). Every one was
scored against **2022 only**, on the single criterion declared in
`SEARCH_BUDGET.md` §4 before any outcome existed: highest 2022 net expectancy in
R at 1.0 pt friction over 09:30–11:30, subject to >= 200 executed 2022 trades,
ties broken on trade count.

No configuration outside this table ever had an outcome computed against it.
2023, 2024, 2025-H2 and 2026-Q1 took no part in the choice.

## All 18, ranked by the preregistered criterion

| rank | configuration | candidates | sel. rate | trades | WR | E[R] @1.0pt | PF | >=200 |
|---:|---|---:|---:|---:|---:|---:|---:|:---:|
| 1 | `B_tree:depth=3:top20` | 273,169 | 74.7% | 37,667 | 0.5023 | **-0.1395** | 0.798 | yes |
| 2 | `B_tree:depth=4:top20` | 209,046 | 57.2% | 34,331 | 0.5036 | **-0.1411** | 0.798 | yes |
| 3 | `B_tree:depth=2:top20` | 352,132 | 96.3% | 48,020 | 0.4982 | **-0.1472** | 0.782 | yes |
| 4 | `B_tree:depth=4:top5` | 36,373 | 9.9% | 4,805 | 0.5093 | **-0.1540** | 0.780 | yes |
| 5 | `B_tree:depth=4:top10` | 42,822 | 11.7% | 5,646 | 0.5087 | **-0.1648** | 0.765 | yes |
| 6 | `A_logit:C=1.0:top20` | 65,236 | 17.8% | 14,925 | 0.5013 | **-0.1666** | 0.763 | yes |
| 7 | `A_logit:C=0.1:top20` | 65,121 | 17.8% | 14,813 | 0.5006 | **-0.1679** | 0.759 | yes |
| 8 | `A_logit:C=0.01:top20` | 65,403 | 17.9% | 14,281 | 0.4995 | **-0.1695** | 0.756 | yes |
| 9 | `A_logit:C=0.01:top10` | 34,562 | 9.4% | 8,033 | 0.5014 | **-0.1755** | 0.751 | yes |
| 10 | `A_logit:C=0.1:top5` | 17,542 | 4.8% | 4,700 | 0.5072 | **-0.1760** | 0.750 | yes |
| 11 | `A_logit:C=1.0:top5` | 17,547 | 4.8% | 4,751 | 0.5068 | **-0.1788** | 0.752 | yes |
| 12 | `A_logit:C=0.1:top10` | 33,386 | 9.1% | 8,211 | 0.4996 | **-0.1804** | 0.741 | yes |
| 13 | `A_logit:C=0.01:top5` | 18,461 | 5.0% | 4,557 | 0.5027 | **-0.1825** | 0.733 | yes |
| 14 | `A_logit:C=1.0:top10` | 33,334 | 9.1% | 8,267 | 0.4984 | **-0.1836** | 0.737 | yes |
| 15 | `B_tree:depth=3:top10` | 40,838 | 11.2% | 6,354 | 0.5003 | **-0.2186** | 0.729 | yes |
| 16 | `B_tree:depth=3:top5` | 40,838 | 11.2% | 6,354 | 0.5003 | **-0.2186** | 0.729 | yes |
| 17 | `B_tree:depth=2:top10` | 41,690 | 11.4% | 6,475 | 0.5008 | **-0.2220** | 0.727 | yes |
| 18 | `B_tree:depth=2:top5` | 41,690 | 11.4% | 6,475 | 0.5008 | **-0.2220** | 0.727 | yes |

## The result that matters more than the ranking

**Every one of the 18 configurations has negative 2022 net expectancy.** The
spread runs from -0.1395 R to -0.2220 R
per trade; not one is above zero. The winner is the least-negative member of a
uniformly losing set, and `SEARCH_BUDGET.md` §4 selects on rank, not on sign.

The candidate carried forward is therefore `B_tree:depth=3:top20` —
2022 expectancy **-0.1395 R** over
37,667 trades, PF 0.798.

### A note on the realised selection rate

The threshold is the nominal top 20 % of `|score|`
calibrated on 2021. A depth-3 tree emits at most 8 distinct scores, so the 80th
percentile falls **inside a tie group**, and PREREG A7 (written before any
outcome) says ties are kept. The realised 2022 selection rate is therefore
74.7%, not 20 %. This is disclosed rather
than corrected: changing the tie rule after seeing the outcome is precisely
what the preregistration exists to prevent.
