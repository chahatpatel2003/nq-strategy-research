# PHASE5_SEARCH_BUDGET.md

**Declared BEFORE any Phase-5 label, outcome or P&L was computed.**
Hashed into `PHASE5_SPEC_FROZEN.md` if a candidate reaches the freeze.

Phase 5 is a *post-Phase-4* hypothesis. That makes an explicit budget more
important, not less: the temptation to keep enlarging R until something works is
exactly the failure mode this document exists to prevent.

---

## 1. The budget

| dimension | permitted | notes |
|---|---:|---|
| base features | **55** | the Phase-4 universe, unchanged; cap 60, none added |
| R architecture | **1** | volatility-normalised, chosen before P&L (§3) |
| R scales | **3** | 2.0 / 3.0 / 4.0 × ATR14(completed 1-min) |
| decision clocks | **1** | every 60 s, 09:30–11:30 ET |
| maximum holds | **1** | 60 minutes |
| timeout rules | **1** | first executable print at/after the cutoff |
| execution models | **1** | the Phase-1/3/4 convention, identical for signals and controls |
| primary RR | **1** | 1R target / 1R stop |
| model families | **2** | A = regularised logistic regression, B = shallow tree |
| hyperparameter settings **per family** | **1** | fixed in §4; the budget leaves no room for a grid |
| selectivity levels | **3** | top 10 % / 5 % / 2 % of the edge score |
| **configurations scored against an outcome** | **≤ 3 × 2 × 3 = 18** | evaluated on 2022 **only** |
| production candidates frozen | **≤ 1** | may be **0** — see §6 |
| fresh-validation runs | **≤ 1** | may be **0** — see §6 |

**Ceiling on the total search: 18 configurations.** Nothing outside this may be
evaluated against any outcome, on any split.

Note the asymmetry with Phase 4: Phase 4 spent its budget on hyperparameters,
Phase 5 spends it on **R scale**, because R scale is the hypothesis.

## 2. What is explicitly forbidden

* No deep learning, reinforcement learning, genetic algorithms, Optuna, AutoML
  or any automated hyperparameter search.
* No random forests, boosting or unrestricted ensembles.
* No additional R scale if the three fail. **If the budget fails, Phase 5 FAILS.**
* No additional RR, horizon, clock, session or threshold after seeing results.
* No feature added, ever, for any reason.
* No selection using 2024 or 2025-H2.
* No direction flip because the opposite control wins.
* No subgroup (time bucket, volatility state, PDH/PDL condition, weekday)
  promoted into the strategy after the fact. Those go to `FUTURE_HYPOTHESES.md`.

## 3. R architecture — decided before P&L

**Volatility-normalised, on the frozen ATR14(completed 1-minute) basis.**
Rationale and the evidence behind it are in `PHASE5_SPEC.md` §6. In summary:
across the three development years the session-median ATR14(1m) spans
10.54 → 16.75 → 11.54 points (**1.59×**) while the price level spans only
1.19×, and within 2022 alone the decile range is **2.6×**. A fixed-point R would
therefore be a materially different bet in each regime, confounding the horizon
hypothesis with regime exposure. The 5-minute basis was measured and rejected:
its 70-minute warm-up leaves it unrepresentative for more than half of a
120-minute session, whereas the 1-minute basis is fully RTH by 09:44.

The decision was made from feature-side volatility statistics on development
data only. **No P&L, win rate or expectancy was computed before it.**

## 4. The two model families, fully specified

    A_logit   LogisticRegression(penalty="elasticnet", l1_ratio=0.5, C=0.1,
                                 solver="saga", max_iter=1000, tol=1e-4,
                                 random_state=0)

    B_tree    DecisionTreeClassifier(max_depth=4,
                                     min_samples_leaf=int(0.02 * n_train),
                                     random_state=0)

One setting each. `C = 0.1` is the midpoint of the Phase-4 grid; `max_depth = 4`
is the brief's stated hard maximum with a large minimum leaf.

## 5. The single selection criterion (declared in advance)

Among the ≤ 18 configurations, the production candidate is the one with the
highest **2022 net expectancy in R at 1.0 pt friction over 09:30–11:30**,
subject to a minimum of **100 executed 2022 trades**. Ties break on higher trade
count. Nothing else participates — not win rate, not profit factor, not
drawdown, not Sharpe.

## 6. Eligibility — Phase 5 is allowed to fail here

Ranking first is **not** sufficient. The brief is explicit that the "least bad"
candidate must not be promoted. Both gates below are checked, in order, and both
were fixed before any outcome existed.

### Gate E — 2022 selection split

* net expectancy > 0 R at 1.0 pt friction, **and**
* profit factor > 1.05, **and**
* strategy E[R] − matched-control E[R] > 0.

### Gate F — 2023 internal out-of-sample

* net expectancy > 0 R at 1.0 pt friction, **and**
* profit factor > 1.05, **and**
* strategy E[R] − matched-control E[R] > 0, **and**
* ≥ 100 executed trades.

**If no configuration passes Gate E → Phase 5 FAILS before validation.**
**If the selected configuration fails Gate F → Phase 5 FAILS before validation.**

In either case 2026-Q1 stays sealed. The 2024 and 2025-H2 contaminated
diagnostics may still be run and reported, but they cannot revive a candidate
and cannot change anything.

## 7. Multiple-testing treatment

The 18 configurations are compared on 2022 on the single pre-declared criterion
in §5, so exactly one comparison chain exists. The three R scales are not
independent hypotheses being mined — they are the pre-specified levels of the
one variable Phase 5 is testing, and all three are reported whatever they show.

Any additional systematic scan run as a **diagnostic** — the time-of-day and
market-state tables in particular — is reported with the number of cells
examined alongside it, and none of it may enter Phase 5.

## 8. Reporting obligation

At completion this budget is reported as spent, with
**TOTAL CONFIGURATIONS EVALUATED**, counting every R scale × model × selectivity
combination that ever had an outcome computed against it, on any split.
Because `PHASE5_SEARCH_BUDGET.md` is itself hashed at freeze time, the figure is
recorded in `PHASE5_SPEC.md` and in a separate completion note rather than by
editing this file.
