# FEATURE_IMPORTANCE.md — Phase 7

> **Phase 7 FAILED at the 2022 gate** — no candidate was selected, 2023 was
> never scored, and 2025-H1 stays sealed. The "reference configuration"
> below is `R25:A_logit:top1p0`, the **least-bad of the 12**, used only so the
> mandatory diagnostics have something concrete to run on. It is not a
> candidate and was never frozen.

Elastic-net logistic (C = 0.1, l1_ratio = 0.5), 2021-fitted, standardised
features so coefficients are directly comparable.

## Top 15 by |coefficient|

| feature | coefficient | family |
|---|---:|---:|
| `bid_px_chg_per_s_15` | -0.10611 | 4 |
| `atr_pct_rank` | +0.05615 | 11 |
| `imb` | +0.04932 | 1 |
| `imb_dev_1_15` | -0.04656 | 2 |
| `bid_sz` | -0.03447 | 1 |
| `secs_since_open` | -0.03233 | 11 |
| `ask_step_asym_15` | -0.03039 | 7 |
| `ask_sz` | -0.02878 | 1 |
| `repl_ratio_ask_15` | -0.02535 | 6 |
| `spread_ticks` | +0.02533 | 1 |
| `bid_repl_per_sell_15` | -0.02312 | 9 |
| `atr1m_ticks` | -0.02307 | 11 |
| `bbo_sz_total` | +0.01922 | 1 |
| `imb_mean_15` | -0.01882 | 2 |
| `repl_ratio_bid_15` | +0.01833 | 6 |

## Share of total |coefficient| mass by family

| family | share |
|---|---:|
| BBO state | 25.2% |
| quote update intensity | 19.9% |
| minimal context | 18.2% |
| imbalance persistence | 12.3% |
| size decrease/increase | 8.5% |
| price-level steps | 5.0% |
| replenishment after aggression | 4.3% |
| microprice pressure | 3.8% |
| trade aggression | 1.3% |
| OFI | 1.2% |
| failure to advance | 0.2% |

**Pure order-book families (1–7) carry 75.9% of the coefficient
mass**, so the model genuinely leans on the book rather than on the price/trade
context. It just does not help.

## What the model actually weighted

* **`bid_px_chg_per_s_15` is the single largest coefficient (−0.106)** — the rate
  at which the best bid changes price. A quote-churn / instability measure, not a
  directional one.
* **BBO state (25.2 %) and quote-update intensity (19.9 %) dominate**; imbalance
  persistence adds 12.3 %.
* **OFI carries just 1.2 %** of the mass. This is the striking one: order-flow
  imbalance is the canonical top-of-book predictor in the microstructure
  literature, and an L1-regularised model with 40 features to choose from very
  nearly discarded all three of its horizons.
* **Trade aggression 1.3 % and failure-to-advance 0.2 %** — the trades-derived
  families are again near-zero, now for the third independent time (Phases 4, 5, 7).

`secs_since_open` appears at −0.032, well down the list — unlike Phase 4, where it
was among the features the tree leaned on hardest.
