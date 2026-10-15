# SEARCH_BUDGET.md — Phase 4

**Declared BEFORE any feature was computed and before any outcome was modelled.**

Phases 1–3 tested predefined ideas, so data snooping was bounded by construction.
Phase 4 is allowed to *discover*, which makes an explicit, auditable budget the
only thing standing between "research" and "mining". This document is that
budget. It is hashed into `STATE_DISCOVERY_SPEC_FROZEN.md`.

---

## 1. The budget

| dimension | permitted | notes |
|---|---|---|
| **base features** | **≤ 60** | 9 pre-specified families; every one listed in `FEATURE_REGISTRY.md` before any label existed |
| **return / velocity horizons** | **6** | 5, 15, 30, 60, 120, 300 s — fixed set, no others tried |
| **derived interactions** | **0** | none hand-built; only what the tree finds internally within its depth limit |
| **decision clocks** | **1** | every 5 s during 09:30–11:30 ET |
| **R definitions** | **1** | `R = 0.50 × ATR14(completed 1-min)`, floor 1.0 pt, cap 25.0 pt |
| **holding horizons** | **1** | 30 minutes |
| **execution models** | **1** | the Phase-3 convention, applied identically to signals and controls |
| **model families** | **2** | A = regularised logistic regression, B = shallow decision tree |
| **hyperparameter combinations** | **≤ 6** | A: 3 (C ∈ {0.01, 0.1, 1.0}, elastic-net l1_ratio fixed 0.5). B: 3 (max_depth ∈ {2, 3, 4}, min_samples_leaf fixed at 2 % of train) |
| **confidence thresholds** | **3** | top 20 % / top 10 % / top 5 % of |score| |
| **candidate strategies carried to selection** | **≤ 6 × 3 = 18** | evaluated on 2022 **only** |
| **production candidates frozen** | **exactly 1** | chosen on 2022, tested once on 2023 |
| **fresh-validation runs** | **exactly 1** | 2026-Q1 |

**Ceiling on the total search: 2 families × 3 hyperparameter settings ×
3 thresholds = 18 configurations.** Nothing outside this may be evaluated
against any outcome.

## 2. What is explicitly forbidden

* No deep learning, reinforcement learning, genetic algorithms, Optuna, or any
  automated hyperparameter search.
* No random forests or unrestricted ensembles.
* No re-opening the budget if the 18 configurations fail. **If the budget fails,
  Phase 4 FAILS.** Post-hoc discoveries go to `FUTURE_HYPOTHESES.md`.
* No feature ranking against full-sample outcomes. Screening, if any, uses the
  2021 training partition only.
* No selecting the time window, direction, weekday, or volatility regime after
  seeing results.
* No re-training on 2023 and then calling 2023 out-of-sample.

## 3. Multiple-testing treatment

The 18 configurations are compared on 2022 **on a single pre-declared criterion**
(§4), so only one comparison chain exists. For any *additional* systematic scan
run as a diagnostic — the symbolic-sequence enumeration in particular — the
number of hypotheses searched is reported alongside Benjamini–Hochberg FDR
adjustment and a minimum-support constraint, and none of it may enter Phase 4.

## 4. The single selection criterion (declared in advance)

Among the ≤ 18 configurations, the production candidate is the one with the
highest **2022 net expectancy in R at 1.0 pt friction over the 09:30–11:30
window**, subject to a minimum of **200 executed 2022 trades**. Ties break on
higher trade count. Nothing else — not win rate, not profit factor, not
drawdown, not Sharpe — participates in the choice.

If no configuration clears the 200-trade minimum, the highest-frequency
configuration is taken and the shortfall is disclosed.

## 5. Reporting obligation

At completion this document is updated with **TOTAL CONFIGURATIONS EVALUATED**,
counting every model × hyperparameter × threshold combination that ever had an
outcome computed against it, on any split.
