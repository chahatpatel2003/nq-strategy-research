# SEARCH_BUDGET.md — Phase 7

**Declared BEFORE any Phase-7 label, outcome or P&L was computed.**

Phase 7 spends the last untouched MBP-1 window in the project — and the last one
that exists, since MBP-1 coverage stops at 2025-H1. The budget is correspondingly
tight.

---

## 1. The twelve configurations, enumerated

# 2 R scales × 2 model families × 3 selectivity levels = 12

| # | id | R | model | selectivity |
|---:|---|---|---|---|
| 1 | `R15:A_logit:top1p0` | 15 pt | elastic-net logistic | top/bottom 1.0 % |
| 2 | `R15:A_logit:top0p5` | 15 pt | elastic-net logistic | top/bottom 0.5 % |
| 3 | `R15:A_logit:top0p2` | 15 pt | elastic-net logistic | top/bottom 0.2 % |
| 4 | `R15:B_tree:top1p0` | 15 pt | depth-3 decision tree | top/bottom 1.0 % |
| 5 | `R15:B_tree:top0p5` | 15 pt | depth-3 decision tree | top/bottom 0.5 % |
| 6 | `R15:B_tree:top0p2` | 15 pt | depth-3 decision tree | top/bottom 0.2 % |
| 7 | `R25:A_logit:top1p0` | 25 pt | elastic-net logistic | top/bottom 1.0 % |
| 8 | `R25:A_logit:top0p5` | 25 pt | elastic-net logistic | top/bottom 0.5 % |
| 9 | `R25:A_logit:top0p2` | 25 pt | elastic-net logistic | top/bottom 0.2 % |
| 10 | `R25:B_tree:top1p0` | 25 pt | depth-3 decision tree | top/bottom 1.0 % |
| 11 | `R25:B_tree:top0p5` | 25 pt | depth-3 decision tree | top/bottom 0.5 % |
| 12 | `R25:B_tree:top0p2` | 25 pt | depth-3 decision tree | top/bottom 0.2 % |

**There is no 13th configuration.** `enumerate_configs()` raises if the count is
anything other than 12, and `SEARCH_BUDGET_COMPLETION.md` records what was
actually evaluated.

## 2. What is fixed and may not be searched

| dimension | permitted | value |
|---|---:|---|
| base features | **≤ 40** | **40**, listed in `FEATURE_REGISTRY.md` before any label existed |
| feature windows | 3 | 1 s, 5 s, 15 s |
| decision clock | 1 | every 5 s, 09:30–11:30 ET |
| session | 1 | 09:30–11:30 America/New_York |
| R scales | **2** | **15 pt and 25 pt** (fixed points, not volatility-scaled) |
| RR | 1 | 1R target / 1R stop |
| maximum hold | 1 | **15 minutes** |
| timeout rule | 1 | first executable print at or after the cutoff |
| execution model | 1 | first print at/after signal + 250 ms; identical for signals and controls |
| model families | **2** | A = elastic-net logistic, B = depth-3 tree |
| hyperparameter settings per family | **1** | fixed in §3; no grid, no search |
| selectivity levels | **3** | top/bottom 1.0 % / 0.5 % / 0.2 % of the 2021 confidence distribution |
| production candidates frozen | **≤ 1** | may be **0** |
| fresh-validation runs | **≤ 1** | may be **0** |

Explicitly forbidden: Optuna, grid search, random search, Bayesian optimisation,
genetic algorithms, AutoML, feature-subset combinatorics, neural networks,
reinforcement learning, random forests, boosting. No nearby R value
(5/10/20/30/40). No extra window. No extra threshold. No new session.

## 3. The two model families, fully specified

    A_logit  LogisticRegression(penalty="elasticnet", l1_ratio=0.5, C=0.1,
                                solver="saga", max_iter=1000, tol=1e-4,
                                random_state=0)

    B_tree   DecisionTreeClassifier(max_depth=3,
                                    min_samples_leaf=int(0.02 * n_train),
                                    random_state=0)

One setting each. No class weighting: the target is near-balanced by
construction and any reweighting would be an unpreregistered choice.

## 4. Friction and the R/friction ratio

Official evaluation at **1.0 NQ point round trip**; 0.0, 0.5 and 2.0 also
reported everywhere.

| R | friction / R at 1.0 pt |
|---|---:|
| 15 pt | **0.0667** |
| 25 pt | **0.0400** |

Both are far below Phase 4's 0.1435 and modestly above Phase 5's 0.0296 — chosen
to stay close enough to the microstructure horizon that book information could
plausibly matter, while not repeating Phase 4's tiny-R mistake.

## 5. Selectivity thresholds — derived from 2021 only, then frozen

The model outputs `p = P(UP)`. Confidence is `|p − 0.5|`. The three thresholds
are the **99.0th, 99.5th and 99.8th percentiles of `|p − 0.5|` computed on the
2021 training rows inside 09:30–11:30**, then **frozen as numbers** and applied
unchanged to 2022, 2023, 2024 and 2025-H1. They are never recomputed on a later
year.

Direction: `p` above the upper tail → **LONG**; `p` below the lower tail →
**SHORT**. Ties at the threshold are kept and the realised selection rate is
reported alongside the nominal one.

## 6. Chronology

**2021 — TRAIN.** Fit the scaler, the model coefficients/tree, and the
selectivity quantiles. Nothing else touches 2021 outcomes.

**2022 — SELECT.** Evaluate all 12 configurations once.

**2023 — INTERNAL DEVELOPMENT OOS.** The selected candidate only, unchanged.
2023 may not retune anything.

**2024 — CONTAMINATED DIAGNOSTIC**, post-freeze only, as a stress gate before
spending 2025-H1.

**2025-H1 — FRESH VALIDATION**, once, only if every prior gate passes.

## 7. 2022 eligibility gate — all six required

| gate | requirement |
|---|---|
| G1 | ≥ **200** executed trades |
| G2 | net expectancy at 1.0 pt friction **> 0 R** |
| G3 | **PF(R) > 1.10** (R units; the points figure is reported but never gates) |
| G4 | strategy expectancy exceeds matched random |
| G5 | matched-random expectancy difference point estimate **> 0** |
| G6 | **zero-friction expectancy > 0** |

## 8. Selection among survivors

If more than one configuration passes §7, exactly one is chosen by:

1. **highest trading-day median advantage vs matched random** — the median across
   trading days of (strategy daily mean R − matched-random daily mean R), *not*
   raw per-trade expectancy. This is the direct correction of the Phase-5 defect
   where ranking on expectancy alone selected the smallest book;
2. tie-break: larger sample;
3. tie-break: lower max drawdown in R.

**If none passes §7, Phase 7 FAILS before 2023 and 2025-H1 stays sealed.** The
second-best configuration is not promoted.

## 9. 2023 internal-OOS gate — all six required

| gate | requirement |
|---|---|
| F1 | ≥ **150** trades (or a frequency-adjusted minimum declared before 2023 is read, if 150 is arithmetically unreachable) |
| F2 | net expectancy **> 0 R** |
| F3 | **PF(R) > 1.10** |
| F4 | matched-random expectancy advantage **> 0** |
| F5 | 95 % **trading-day block-bootstrap** CI for `strategy E[R] − matched random E[R]`, **lower bound > 0** |
| F6 | **gross (zero-friction) expectancy > 0** |

**If the candidate fails, Phase 7 FAILS before 2024 and 2025-H1 stays sealed.**

## 10. 2024 eligibility to spend 2025-H1 — all five required

Declared here, before 2024 is read:

| gate | requirement |
|---|---|
| D1 | net expectancy **> 0 R** |
| D2 | **PF(R) > 1.05** |
| D3 | matched-random advantage point estimate **> 0** |
| D4 | **gross expectancy > 0** |
| D5 | `2024 max drawdown (R) ≤ 2.0 × max(2022 max DD, 2023 max DD)` |

2024 may not change anything. It is a stress gate and nothing else. **If it
fails, STOP and keep 2025-H1 sealed.**

## 11. Fresh-validation gates (2025-H1)

V1 sample (minimum frozen from development frequency **before** the unlock,
preferring ≥ 100 trades) · V2 net E[R] > 0 · V3 PF(R) > 1.10 · V4 gross E[R] > 0 ·
V5 matched-random advantage with 95 % day-block CI lower bound > 0 · V6 average
daily R > 0 · V7 profit concentration: `total_net_R − best_ISO_week_net_R > 0` ·
V8 full-MBP model beats the A2 trades+context ablation on a positive point
estimate · V9 long and short reported separately, with a flag if essentially all
edge comes from one side.

## 12. Ablations are diagnostics, never candidates

A0 (all 40) vs A1 (quote-only, 32) vs A2 (trades + context, 8). These measure
whether MBP-1 adds anything. They may **not** be used to select a different model
after the primary candidate is frozen.

## 13. Reporting obligation

`SEARCH_BUDGET_COMPLETION.md` records configurations planned, configurations
evaluated, failures and the total. This file is hashed at freeze time and is
never edited to carry the count.
