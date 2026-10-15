# STATE_DISCOVERY_SPEC.md — Phase 4 production specification

**Spec version:** `statedisc-1.0.0`
**Frozen:** before the 2024 diagnostic, before the 2025-H2 diagnostic, before
any contact with 2026-Q1.

This file is the complete definition of the ONE production candidate carried out
of Phase-4 development. It is reproducible from the repository alone.

---

## 1. Research question

Are there recurring, causally observable NQ market states that predict future
price path better than comparable random entries after realistic execution
costs?

## 2. Data

NQ **Trades only**, Databento GLBX MDP-3, from the Samsung T9, read-only.
MBP-1 is never opened. No external series of any kind.

Front contract: the outright NQ symbol with the highest volume on the previous
trading day (frozen Phase-1 rule). Roll days are excluded. No back-adjustment.

| period | role |
|---|---|
| 2021-01-01 .. 2021-12-31 | DISCOVERY_TRAIN — model fit, scaler fit, threshold calibration |
| 2022-01-01 .. 2022-12-31 | SELECTION — the 18 configurations compared here, once |
| 2023-01-01 .. 2023-12-31 | INTERNAL_TEST — looked at once, after the choice |
| 2024-01-01 .. 2024-12-31 | CONTAMINATED diagnostic |
| **2025-01-01 .. 2025-06-30** | **SEALED. No unlock path exists.** |
| 2025-07-01 .. 2025-12-31 | CONTAMINATED diagnostic (spent as Phase-3 validation) |
| 2026-01-01 .. 2026-03-31 | FRESH VALIDATION — one shot |
| **2026-04-01 ..** | **SEALED FINAL HOLDOUT. No unlock path exists.** |

## 3. Session and decision clock

Official session **09:30:00–11:30:00 America/New_York**, decisions every
**5 seconds** (1440/day, first at 09:30:00, last at 11:29:55). DST follows the
tz database. Rows are also generated to 15:59:55 for the extended-window
diagnostics; they take no part in fitting, selection, calibration or validation.

## 4. Features

The 55 registered causal features of `FEATURE_REGISTRY.md`
(families 8/5/7/9/6/6/3/6/5), implemented in `src/nqr/p4/features4.py`. Cap 60,
used 55. Every feature is a trailing aggregate closed at the decision timestamp.

Causality convention: the grid second `[T0+i, T0+i+1)` is index `i`; the decision
stamped `T0+i+1` reads `grid[i]`, so every input second has closed. Proven by
`tests/test_p4_features.py::test_features_are_invariant_to_truncating_the_future`,
which deletes the entire future tape and requires all 55 values to be identical.

Volatility unit `A` = ATR14 of **completed** 1-minute bars, floor **2.0 pt**,
from the frozen `nqr.p2.features.causal_atr_minutes`. Family 9 comes from the
frozen `nqr.p3.dc_engine` at theta = 0.50 x A, asserted event-for-event
identical to the Phase-3 runner.

## 5. Preprocessing — fitted on 2021 ONLY

Winsorise at the 2021 0.1 % / 99.9 % quantiles, then standardise with the 2021
mean and standard deviation. Fitted on **364,320** 2021 rows inside
09:30–11:30, then applied unchanged to every later period. Never refitted.

| # | feature | winsor lo | winsor hi | mean | sd |
|---|---|---|---|---|---|
| 1 | `ret_norm_5` | -4.29309 | 4.2325 | 0.00101006 | 0.728796 |
| 2 | `ret_norm_15` | -4.28464 | 4.27266 | 0.00159299 | 0.725172 |
| 3 | `ret_norm_30` | -4.11613 | 4.13062 | 0.00199312 | 0.71921 |
| 4 | `ret_norm_60` | -3.82876 | 3.89621 | 0.00276595 | 0.708034 |
| 5 | `ret_norm_120` | -3.39204 | 3.40823 | 0.00481612 | 0.692523 |
| 6 | `ret_norm_300` | -2.65432 | 2.531 | 0.0121394 | 0.667925 |
| 7 | `eff_60` | 0 | 0.551877 | 0.127998 | 0.0972347 |
| 8 | `eff_300` | 0 | 0.25 | 0.0590284 | 0.044935 |
| 9 | `vel_15_norm` | -8.56928 | 8.54533 | 0.00318598 | 1.45034 |
| 10 | `vel_60_norm` | -3.82876 | 3.89621 | 0.00276595 | 0.708034 |
| 11 | `vel_ratio_15_60` | -1.64e+09 | 1.70992e+09 | -31084.8 | 1.25533e+08 |
| 12 | `accel_15_60` | -6.94368 | 7.11038 | 0.000533127 | 1.2474 |
| 13 | `persist_60` | -0.207547 | 0.5 | 0.0820805 | 0.103116 |
| 14 | `atr1m` | 2 | 37.1071 | 11.6841 | 5.53142 |
| 15 | `rv_60_norm` | 0.305662 | 3.32105 | 0.69493 | 0.284583 |
| 16 | `rv_300_norm` | 0.387298 | 1.87581 | 0.692934 | 0.174967 |
| 17 | `vol_ratio_60_300` | 0.540279 | 1.99986 | 0.990028 | 0.172485 |
| 18 | `range_60_norm` | 0.25 | 5.82659 | 0.949976 | 0.538251 |
| 19 | `atr_pct_rank` | 0 | 1 | 0.617981 | 0.281044 |
| 20 | `vol_expansion` | 0.483682 | 6.22137 | 1.29158 | 0.915758 |
| 21 | `dist_high_300_norm` | 0 | 6.64032 | 1.07553 | 0.954214 |
| 22 | `dist_low_300_norm` | 0 | 6.28865 | 1.1505 | 0.918708 |
| 23 | `dist_high_1800_norm` | 0 | 9.80988 | 2.46597 | 1.91344 |
| 24 | `dist_low_1800_norm` | 0 | 12.5863 | 3.11808 | 2.33663 |
| 25 | `n_new_highs_300` | 0 | 51 | 7.4522 | 9.34846 |
| 26 | `n_new_lows_300` | 0 | 52 | 6.82951 | 9.13144 |
| 27 | `pullback_depth` | 0 | 1 | 0.479128 | 0.316564 |
| 28 | `secs_since_high_300` | 0 | 2185.68 | 274.968 | 312.334 |
| 29 | `secs_since_low_300` | 0 | 2191.68 | 306.302 | 346.136 |
| 30 | `trades_per_s_60` | 0.3 | 67.8394 | 16.3617 | 9.79583 |
| 31 | `vol_per_s_60` | 0.433333 | 105.645 | 25.9594 | 15.4188 |
| 32 | `avg_trade_size_60` | 1.19175 | 2.28571 | 1.5943 | 0.159148 |
| 33 | `max_trade_size_60_rel` | 1.69456 | 74.3182 | 11.9232 | 8.01993 |
| 34 | `intensity_ratio_60_300` | 0.38877 | 3.77234 | 1.01434 | 0.360624 |
| 35 | `volume_ratio_60_300` | 0.347335 | 3.7337 | 1.01461 | 0.376322 |
| 36 | `delta_60_norm` | -0.588055 | 0.596243 | -0.00115436 | 0.130449 |
| 37 | `delta_300_norm` | -0.340181 | 0.357544 | -0.000244531 | 0.0716282 |
| 38 | `delta_per_vol_60` | -0.378323 | 0.38819 | -0.00176965 | 0.112099 |
| 39 | `delta_per_vol_300` | -0.2 | 0.211231 | -0.000656962 | 0.0598477 |
| 40 | `cum_delta_norm` | -0.131782 | 0.150096 | 0.00274765 | 0.0237818 |
| 41 | `delta_accel` | -0.355153 | 0.354185 | -0.00110584 | 0.101681 |
| 42 | `secs_since_open` | 5 | 7190 | 3597.5 | 2078.45 |
| 43 | `is_second_hour` | 0 | 1 | 0.5 | 0.5 |
| 44 | `weekday` | 0 | 4 | 2.01186 | 1.40716 |
| 45 | `dist_open_norm` | -18.8621 | 29.8309 | 1.2266 | 6.80477 |
| 46 | `dist_vwap_norm` | -8.71964 | 12.8495 | 0.710228 | 3.41381 |
| 47 | `dist_pdh_norm` | -61.25 | 40.8955 | -6.59847 | 12.5459 |
| 48 | `dist_pdl_norm` | -22.9671 | 142.754 | 16.641 | 19.5362 |
| 49 | `dist_or30_hi_norm` | -19.955 | 13.2569 | -2.19088 | 4.8069 |
| 50 | `dist_or30_lo_norm` | -10.6885 | 30.8611 | 4.1615 | 6.36013 |
| 51 | `last_dc_dir` | -1 | 1 | 0.0375549 | 0.999295 |
| 52 | `last_dc_mag_norm` | 0.415254 | 0.745562 | 0.517901 | 0.0291936 |
| 53 | `last_overshoot_norm` | 0 | 3.32899 | 0.492805 | 0.489869 |
| 54 | `prev2_dc_dir` | -1 | 1 | -0.0375549 | 0.999295 |
| 55 | `secs_since_last_dc` | 0 | 350 | 34.6187 | 39.2312 |

## 6. Model

**Family B — shallow decision tree.** `B_tree:depth=3`.

    sklearn.tree.DecisionTreeClassifier(
        max_depth      = 3,
        min_samples_leaf = 7286,   # 2 % of the 2021 rows
        random_state   = 0)

Fitted once on the 2021 partition. Depth 3, 7
leaves. No ensemble, no boosting, no forest, no automated search.

Target (PREREG A6): `y = 1` iff the hypothetical LONG 1R/1R bracket opened at
that decision finishes **gross** points > 0.

### Learned rules

```
|--- dist_pdh_norm <= 0.769
|   |--- atr1m <= -0.777
|   |   |--- dist_open_norm <= 0.813
|   |   |   |--- class: 0
|   |   |--- dist_open_norm >  0.813
|   |   |   |--- class: 0
|   |--- atr1m >  -0.777
|   |   |--- secs_since_low_300 <= -0.753
|   |   |   |--- class: 1
|   |   |--- secs_since_low_300 >  -0.753
|   |   |   |--- class: 0
|--- dist_pdh_norm >  0.769
|   |--- atr1m <= -0.177
|   |   |--- secs_since_high_300 <= 0.616
|   |   |   |--- class: 0
|   |   |--- secs_since_high_300 >  0.616
|   |   |   |--- class: 1
|   |--- atr1m >  -0.177
|   |   |--- class: 1
```

### Feature importances

| feature | importance |
|---|---|
| `atr1m` | 0.3966 |
| `dist_pdh_norm` | 0.2696 |
| `secs_since_low_300` | 0.1216 |
| `secs_since_high_300` | 0.1156 |
| `dist_open_norm` | 0.0965 |

## 7. Score, direction, threshold

    score      = P(y=1 | x) - 0.5
    direction  = +1 if score > 0 else -1
    trade iff  |score| >= tau

**tau = 0.017941**, the 80th percentile of
`|score|` on the **2021** rows inside 09:30–11:30 (nominal top
20 %). Frozen as this number and applied unchanged
everywhere. Ties at tau are kept, so the realised selection rate on 2022 was
74.7%, not 20 % —
a depth-3 tree emits at most 8 distinct scores and the quantile falls inside a
tie group. Disclosed, not adjusted: PREREG A7 fixed the tie rule in advance.

## 8. Risk geometry

    R      = clip(0.50 x ATR14(completed 1-min, floor 2.0 pt), 1.0, 25.0)  points
    stop   = entry - direction x R
    target = entry + direction x R

R is evaluated at the decision timestamp; both levels hang off the **realised
entry price**, never the decision price.

## 9. Execution

    signal      decision timestamp t on the 5-second clock
    entry       first trade print at or after t + 250 ms; abandoned after 60 s
    stop        touch-then-market, filled at the triggering print
    target      resting limit, requires the tape to trade THROUGH by >= 1 tick
    timeout     30 minutes; exits at the last print before the cutoff, P&L counts
    hard exit   16:00 ET (never binding inside the official session)

Resolved on the raw chronological trade sequence by the frozen
`nqr.p3.fastpass`. No OHLC inference, no midpoint fills, no retroactive entry.

## 10. Portfolio rule

**One position at a time.** A candidate arriving while a position is open is
logged `SKIPPED_OVERLAP` and never becomes a second position.

## 11. Friction

Official evaluation at **1.0 NQ point round trip**. Also reported at 0.0, 0.5
and 2.0. Friction is applied to P&L only, never to the label.

## 12. Matched-random control (primary null)

Per executed trade, up to 10 controls: same trading day, same 30-minute
time-of-day bucket, same direction, control R within [0.80, 1.25] x signal R,
drawn without replacement, seed 20260819, identical entry / bracket / horizon /
friction. Controls are independent entries and are deliberately not subject to
the one-position rule. The strategy's own timestamps are not excluded from the
pool.

Also run: C2 opposite direction at the same timestamps; C3 shuffled direction
(1 000 reps, long fraction preserved); C4 day-block-permuted training target
with a full refit (20 reps).

## 13. Inference

Every uncertainty statement is a **day-block bootstrap**: 10 000 resamples of
whole trading days, strategy and controls resampled together so they stay
paired. No statistic anywhere treats overlapping 5-second rows as independent.

## 14. Validation gates (fixed before 2026-Q1 is opened)

Period 2026-Q1, session 09:30–11:30, 1R, friction 1.0 pt.

| gate | requirement | status |
|---|---|---|
| 1 | >= 100 executed trades | hard |
| 2 | net expectancy > 0 R | hard |
| 3 | profit factor > 1.10 | hard |
| 4 | raw WR > 50 % | **preference** (50 % is not the primary null) |
| 5 | E[R] − matched-control E[R], 95 % block-bootstrap CI lower bound > 0 | hard |
| 6 | WR − matched-control WR, 95 % block-bootstrap CI lower bound > 0 | hard |
| 7 | `total_net_R − best_ISO_week_net_R > 0` (PREREG A14) | hard |

Verdict is exactly one of PASS / PROMISING BUT INCONCLUSIVE / FAIL.

## 15. Training / retraining procedure

Fit once on 2021 and never refit. No walk-forward, no periodic retraining, no
online update. Reproducing the model is: build the 2021 state dataset, fit the
preprocessor, fit the tree with the parameters in §6, calibrate tau by §7.

## 16. Search budget actually spent

**TOTAL CONFIGURATIONS EVALUATED: 18**
of a ceiling of 18. Two families x three hyperparameter
settings x three thresholds, each scored against 2022 exactly once. No
configuration outside this set ever had an outcome computed against it.
