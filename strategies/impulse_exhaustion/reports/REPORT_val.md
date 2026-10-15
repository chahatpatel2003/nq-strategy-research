# Impulse Exhaustion — VALIDATION 2024 (frozen impexh-1.0.0.impl2+48c76a0e68b88947)

* spec: `impexh-1.0.0` | entry stage: `FAILED_CONTINUATION` | ablation: `None`
* period **2024-01-01 .. 2024-12-31**, 255 Globex trading days processed
* signals: **45** | accepted: **45** | skipped: **0** | rejected candidates: **67447**
* runtime 142.4s


**Candidate rejections (state machine)**

| reject_reason | len |
|---|---|
| NOT_A_NEW_EXTREME | 47525 |
| NO_VOLUME_DETERIORATION | 15528 |
| NO_EFFICIENCY_DETERIORATION | 4316 |
| ABSORPTION_TOO_LOW | 44 |
| NEW_EXTREME_WHILE_ARMED | 22 |
| ABSORPTION_HISTORY_WARMUP | 12 |

## 1. Headline matrix — window x target x round-trip friction

| window | target | friction | trades | win_rate | expectancy_R | expectancy_pts | PF | total_pts | maxDD_R | p_value |
|---|---|---|---|---|---|---|---|---|---|---|
| 09:30-11:30 ET | 1R | 0.000 | 15 | 0.267 | -0.467 | -2.917 | 0.388 | -43.750 | 7.000 | 0.982 |
| 09:30-11:30 ET | 1R | 0.500 | 15 | 0.267 | -0.567 | -3.417 | 0.334 | -51.250 | 8.506 | 0.982 |
| 09:30-11:30 ET | 1R | 1.000 | 15 | 0.267 | -0.668 | -3.917 | 0.288 | -58.750 | 10.013 | 0.982 |
| 09:30-11:30 ET | 1R | 2.000 | 15 | 0.200 | -0.868 | -4.917 | 0.211 | -73.750 | 13.025 | 0.996 |
| 09:30-11:30 ET | 1.25R | 0.000 | 15 | 0.200 | -0.550 | -2.754 | 0.438 | -41.312 | 8.250 | 0.988 |
| 09:30-11:30 ET | 1.25R | 0.500 | 15 | 0.200 | -0.650 | -3.254 | 0.386 | -48.812 | 9.756 | 0.988 |
| 09:30-11:30 ET | 1.25R | 1.000 | 15 | 0.200 | -0.751 | -3.754 | 0.341 | -56.312 | 11.263 | 0.988 |
| 09:30-11:30 ET | 1.25R | 2.000 | 15 | 0.200 | -0.952 | -4.754 | 0.269 | -71.312 | 14.275 | 0.988 |
| 09:30-11:30 ET | 1.5R | 0.000 | 15 | 0.133 | -0.667 | -3.075 | 0.409 | -46.125 | 10.000 | 0.995 |
| 09:30-11:30 ET | 1.5R | 0.500 | 15 | 0.133 | -0.767 | -3.575 | 0.365 | -53.625 | 11.506 | 0.995 |
| 09:30-11:30 ET | 1.5R | 1.000 | 15 | 0.133 | -0.868 | -4.075 | 0.328 | -61.125 | 13.013 | 0.995 |
| 09:30-11:30 ET | 1.5R | 2.000 | 15 | 0.133 | -1.068 | -5.075 | 0.268 | -76.125 | 16.025 | 0.995 |
| 09:30-11:30 ET | 2R | 0.000 | 15 | 0.133 | -0.600 | -2.367 | 0.545 | -35.500 | 9.000 | 0.981 |
| 09:30-11:30 ET | 2R | 0.500 | 15 | 0.133 | -0.700 | -2.867 | 0.491 | -43.000 | 10.506 | 0.981 |
| 09:30-11:30 ET | 2R | 1.000 | 15 | 0.133 | -0.801 | -3.367 | 0.445 | -50.500 | 12.013 | 0.981 |
| 09:30-11:30 ET | 2R | 2.000 | 15 | 0.133 | -1.002 | -4.367 | 0.370 | -65.500 | 15.025 | 0.981 |
| 09:30-12:00 ET | 1R | 0.000 | 17 | 0.353 | -0.294 | -2.118 | 0.497 | -36.000 | 5.000 | 0.928 |
| 09:30-12:00 ET | 1R | 0.500 | 17 | 0.353 | -0.398 | -2.618 | 0.422 | -44.500 | 6.771 | 0.928 |
| 09:30-12:00 ET | 1R | 1.000 | 17 | 0.353 | -0.503 | -3.118 | 0.358 | -53.000 | 8.543 | 0.928 |
| 09:30-12:00 ET | 1R | 2.000 | 17 | 0.294 | -0.711 | -4.118 | 0.251 | -70.000 | 12.085 | 0.975 |
| 09:30-12:00 ET | 1.25R | 0.000 | 17 | 0.294 | -0.338 | -1.860 | 0.570 | -31.625 | 5.750 | 0.935 |
| 09:30-12:00 ET | 1.25R | 0.500 | 17 | 0.294 | -0.442 | -2.360 | 0.495 | -40.125 | 7.521 | 0.935 |
| 09:30-12:00 ET | 1.25R | 1.000 | 17 | 0.294 | -0.547 | -2.860 | 0.431 | -48.625 | 9.293 | 0.935 |
| 09:30-12:00 ET | 1.25R | 2.000 | 17 | 0.294 | -0.755 | -3.860 | 0.327 | -65.625 | 12.835 | 0.935 |
| 09:30-12:00 ET | 1.5R | 0.000 | 17 | 0.235 | -0.412 | -2.029 | 0.558 | -34.500 | 7.000 | 0.954 |
| 09:30-12:00 ET | 1.5R | 0.500 | 17 | 0.235 | -0.516 | -2.529 | 0.491 | -43.000 | 8.771 | 0.954 |
| 09:30-12:00 ET | 1.5R | 1.000 | 17 | 0.235 | -0.620 | -3.029 | 0.434 | -51.500 | 10.543 | 0.954 |
| 09:30-12:00 ET | 1.5R | 2.000 | 17 | 0.235 | -0.829 | -4.029 | 0.341 | -68.500 | 14.085 | 0.954 |
| 09:30-12:00 ET | 2R | 0.000 | 17 | 0.176 | -0.471 | -1.971 | 0.594 | -33.500 | 8.000 | 0.956 |
| 09:30-12:00 ET | 2R | 0.500 | 17 | 0.176 | -0.575 | -2.471 | 0.531 | -42.000 | 9.771 | 0.956 |
| 09:30-12:00 ET | 2R | 1.000 | 17 | 0.176 | -0.679 | -2.971 | 0.477 | -50.500 | 11.543 | 0.956 |
| 09:30-12:00 ET | 2R | 2.000 | 17 | 0.176 | -0.887 | -3.971 | 0.389 | -67.500 | 15.085 | 0.956 |
| 09:30-16:00 ET | 1R | 0.000 | 45 | 0.467 | -0.067 | -0.778 | 0.745 | -35.000 | 6.000 | 0.724 |
| 09:30-16:00 ET | 1R | 0.500 | 45 | 0.467 | -0.184 | -1.278 | 0.615 | -57.500 | 9.557 | 0.724 |
| 09:30-16:00 ET | 1R | 1.000 | 45 | 0.467 | -0.301 | -1.778 | 0.504 | -80.000 | 14.115 | 0.724 |
| 09:30-16:00 ET | 1R | 2.000 | 45 | 0.444 | -0.536 | -2.778 | 0.325 | -125.000 | 24.103 | 0.814 |
| 09:30-16:00 ET | 1.25R | 0.000 | 45 | 0.400 | -0.100 | -0.910 | 0.729 | -40.938 | 7.500 | 0.772 |
| 09:30-16:00 ET | 1.25R | 0.500 | 45 | 0.400 | -0.217 | -1.410 | 0.615 | -63.438 | 9.812 | 0.772 |
| 09:30-16:00 ET | 1.25R | 1.000 | 45 | 0.400 | -0.334 | -1.910 | 0.518 | -85.938 | 15.051 | 0.772 |
| 09:30-16:00 ET | 1.25R | 2.000 | 45 | 0.400 | -0.569 | -2.910 | 0.362 | -130.938 | 25.603 | 0.772 |
| 09:30-16:00 ET | 1.5R | 0.000 | 45 | 0.356 | -0.111 | -0.878 | 0.752 | -39.500 | 9.500 | 0.775 |
| 09:30-16:00 ET | 1.5R | 0.500 | 45 | 0.356 | -0.228 | -1.378 | 0.644 | -62.000 | 12.530 | 0.775 |
| 09:30-16:00 ET | 1.5R | 1.000 | 45 | 0.356 | -0.346 | -1.878 | 0.552 | -84.500 | 15.561 | 0.775 |
| 09:30-16:00 ET | 1.5R | 2.000 | 45 | 0.356 | -0.580 | -2.878 | 0.405 | -129.500 | 26.103 | 0.775 |
| 09:30-16:00 ET | 2R | 0.000 | 45 | 0.311 | -0.086 | -0.611 | 0.835 | -27.500 | 7.000 | 0.677 |
| 09:30-16:00 ET | 2R | 0.500 | 45 | 0.311 | -0.203 | -1.111 | 0.726 | -50.000 | 11.252 | 0.677 |
| 09:30-16:00 ET | 2R | 1.000 | 45 | 0.311 | -0.321 | -1.611 | 0.634 | -72.500 | 15.625 | 0.677 |
| 09:30-16:00 ET | 2R | 2.000 | 45 | 0.311 | -0.555 | -2.611 | 0.487 | -117.500 | 24.983 | 0.677 |

## 2. 09:30-11:30 ET  (PRIMARY)

### 1R target, **1.0 pt** round-trip friction (primary friction)

| metric | value |
|---|---|
| executed trades | 15 |
| trades / trading day | 0.059 |
| long | 7 |
| short | 8 |
| wins | 4 |
| losses | 11 |
| win rate | 0.267 |
| win rate 95% CI low | 0.109 |
| win rate 95% CI high | 0.520 |
| p(WR > 50%), one-sided | 0.982 |
| expectancy (R) | -0.668 |
| median R | -1.129 |
| expectancy (pts) | -3.917 |
| profit factor | 0.288 |
| avg winner (pts) | 5.938 |
| avg loser (pts) | -7.500 |
| max drawdown (R, trade seq) | 10.013 |
| max drawdown (R, daily) | 10.013 |
| longest winning streak | 2 |
| longest losing streak | 5 |
| avg MFE (pts) | 3.967 |
| avg MAE (pts) | 5.167 |
| avg MAE on winners (pts) | 1.375 |
| avg MFE on losers (pts) | 2.773 |
| avg hold (min) | 0.484 |
| median hold (min) | 0.266 |
| TP exits | 4 |
| SL exits | 11 |
| timeout exits | 0 |
| avg R distance (pts) | 6.617 |
| t-stat of mean R | -2.880 |

**Prop-firm daily profile**

| metric | value |
|---|---|
| % days with zero trades | 0.941 |
| % days with 1 trade | 0.059 |
| % days with 2 trades | 0.000 |
| % days with 3+ trades | 0.000 |
| median trades / active day | 1.000 |
| % profitable days | 0.267 |
| daily R mean | -0.668 |
| daily R median | -1.129 |
| daily R 5th pct | -1.300 |
| daily R 95th pct | 0.859 |
| max daily loss (R) | -1.333 |
| best day (R) | 0.935 |
| longest drawdown (days below peak) | 15 |

**Friction sensitivity (1R)**

| friction | win_rate | expectancy_R | expectancy_points | profit_factor | total_points |
|---|---|---|---|---|---|
| 0.000 | 0.267 | -0.467 | -2.917 | 0.388 | -43.750 |
| 0.500 | 0.267 | -0.567 | -3.417 | 0.334 | -51.250 |
| 1.000 | 0.267 | -0.668 | -3.917 | 0.288 | -58.750 |
| 2.000 | 0.200 | -0.868 | -4.917 | 0.211 | -73.750 |

**Hour-of-day (1R, primary friction)**

| et_hour | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 9 | 8 | 3 | 5 | 0.375 | 0.137 | 0.694 | -0.408 | -2.812 | -22.500 | 0.503 | 5.625 | 5.719 | 0.217 |
| 10 | 3 | 0 | 3 | 0.000 | 0.000 | 0.561 | -1.171 | -7.250 | -21.750 | 0.000 | 6.333 | 1.583 | 0.272 |
| 11 | 4 | 1 | 3 | 0.250 | 0.046 | 0.699 | -0.808 | -3.625 | -14.500 | 0.065 | 3.375 | 2.250 | 0.320 |

* **09:30-10:30**: n=10 WR=0.300 [0.108, 0.603] expR=-0.5581 PF=0.373 (0.039 trades/day)

* **10:30-11:30**: n=5 WR=0.200 [0.036, 0.624] expR=-0.8863 PF=0.047 (0.020 trades/day)

## 3. 09:30-12:00 ET  (diagnostic)

### 1R target, **1.0 pt** round-trip friction (primary friction)

| metric | value |
|---|---|
| executed trades | 17 |
| trades / trading day | 0.067 |
| long | 8 |
| short | 9 |
| wins | 6 |
| losses | 11 |
| win rate | 0.353 |
| win rate 95% CI low | 0.173 |
| win rate 95% CI high | 0.587 |
| p(WR > 50%), one-sided | 0.928 |
| expectancy (R) | -0.503 |
| median R | -1.114 |
| expectancy (pts) | -3.118 |
| profit factor | 0.358 |
| avg winner (pts) | 4.917 |
| avg loser (pts) | -7.500 |
| max drawdown (R, trade seq) | 8.543 |
| max drawdown (R, daily) | 8.543 |
| longest winning streak | 2 |
| longest losing streak | 4 |
| avg MFE (pts) | 3.985 |
| avg MAE (pts) | 4.559 |
| avg MAE on winners (pts) | 0.917 |
| avg MFE on losers (pts) | 2.773 |
| avg hold (min) | 0.441 |
| median hold (min) | 0.215 |
| TP exits | 6 |
| SL exits | 11 |
| timeout exits | 0 |
| avg R distance (pts) | 6.294 |
| t-stat of mean R | -2.158 |

**Prop-firm daily profile**

| metric | value |
|---|---|
| % days with zero trades | 0.941 |
| % days with 1 trade | 0.055 |
| % days with 2 trades | 0.000 |
| % days with 3+ trades | 0.004 |
| median trades / active day | 1.000 |
| % profitable days | 0.333 |
| daily R mean | -0.570 |
| daily R median | -1.129 |
| daily R 5th pct | -1.300 |
| daily R 95th pct | 0.859 |
| max daily loss (R) | -1.333 |
| best day (R) | 0.935 |
| longest drawdown (days below peak) | 15 |

**Friction sensitivity (1R)**

| friction | win_rate | expectancy_R | expectancy_points | profit_factor | total_points |
|---|---|---|---|---|---|
| 0.000 | 0.353 | -0.294 | -2.118 | 0.497 | -36.000 |
| 0.500 | 0.353 | -0.398 | -2.618 | 0.422 | -44.500 |
| 1.000 | 0.353 | -0.503 | -3.118 | 0.358 | -53.000 |
| 2.000 | 0.294 | -0.711 | -4.118 | 0.251 | -70.000 |

**Hour-of-day (1R, primary friction)**

| et_hour | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 9 | 8 | 3 | 5 | 0.375 | 0.137 | 0.694 | -0.408 | -2.812 | -22.500 | 0.503 | 5.625 | 5.719 | 0.217 |
| 10 | 3 | 0 | 3 | 0.000 | 0.000 | 0.561 | -1.171 | -7.250 | -21.750 | 0.000 | 6.333 | 1.583 | 0.272 |
| 11 | 6 | 3 | 3 | 0.500 | 0.188 | 0.812 | -0.294 | -1.458 | -8.750 | 0.435 | 2.250 | 2.875 | 0.138 |

* **09:30-10:30**: n=10 WR=0.300 [0.108, 0.603] expR=-0.5581 PF=0.373 (0.039 trades/day)

* **10:30-11:30**: n=5 WR=0.200 [0.036, 0.624] expR=-0.8863 PF=0.047 (0.020 trades/day)

## 4. 09:30-16:00 ET  (diagnostic)

### 1R target, **1.0 pt** round-trip friction (primary friction)

| metric | value |
|---|---|
| executed trades | 45 |
| trades / trading day | 0.176 |
| long | 17 |
| short | 28 |
| wins | 21 |
| losses | 24 |
| win rate | 0.467 |
| win rate 95% CI low | 0.329 |
| win rate 95% CI high | 0.609 |
| p(WR > 50%), one-sided | 0.724 |
| expectancy (R) | -0.301 |
| median R | -1.080 |
| expectancy (pts) | -1.778 |
| profit factor | 0.504 |
| avg winner (pts) | 3.869 |
| avg loser (pts) | -6.719 |
| max drawdown (R, trade seq) | 14.115 |
| max drawdown (R, daily) | 14.115 |
| longest winning streak | 4 |
| longest losing streak | 5 |
| avg MFE (pts) | 3.761 |
| avg MAE (pts) | 3.828 |
| avg MAE on winners (pts) | 1.476 |
| avg MFE on losers (pts) | 2.510 |
| avg hold (min) | 0.684 |
| median hold (min) | 0.362 |
| TP exits | 21 |
| SL exits | 24 |
| timeout exits | 0 |
| avg R distance (pts) | 5.322 |
| t-stat of mean R | -2.043 |

**Prop-firm daily profile**

| metric | value |
|---|---|
| % days with zero trades | 0.847 |
| % days with 1 trade | 0.137 |
| % days with 2 trades | 0.008 |
| % days with 3+ trades | 0.008 |
| median trades / active day | 1.000 |
| % profitable days | 0.462 |
| daily R mean | -0.347 |
| daily R median | -1.077 |
| daily R 5th pct | -1.481 |
| daily R 95th pct | 0.846 |
| max daily loss (R) | -2.329 |
| best day (R) | 0.935 |
| longest drawdown (days below peak) | 39 |

**Friction sensitivity (1R)**

| friction | win_rate | expectancy_R | expectancy_points | profit_factor | total_points |
|---|---|---|---|---|---|
| 0.000 | 0.467 | -0.067 | -0.778 | 0.745 | -35.000 |
| 0.500 | 0.467 | -0.184 | -1.278 | 0.615 | -57.500 |
| 1.000 | 0.467 | -0.301 | -1.778 | 0.504 | -80.000 |
| 2.000 | 0.444 | -0.536 | -2.778 | 0.325 | -125.000 |

**Hour-of-day (1R, primary friction)**

| et_hour | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 9 | 8 | 3 | 5 | 0.375 | 0.137 | 0.694 | -0.408 | -2.812 | -22.500 | 0.503 | 5.625 | 5.719 | 0.217 |
| 10 | 3 | 0 | 3 | 0.000 | 0.000 | 0.561 | -1.171 | -7.250 | -21.750 | 0.000 | 6.333 | 1.583 | 0.272 |
| 11 | 6 | 3 | 3 | 0.500 | 0.188 | 0.812 | -0.294 | -1.458 | -8.750 | 0.435 | 2.250 | 2.875 | 0.138 |
| 12 | 9 | 5 | 4 | 0.556 | 0.267 | 0.811 | -0.139 | -0.556 | -5.000 | 0.762 | 2.917 | 3.472 | 0.659 |
| 13 | 3 | 1 | 2 | 0.333 | 0.061 | 0.792 | -0.525 | -2.417 | -7.250 | 0.396 | 5.167 | 3.333 | 0.888 |
| 14 | 7 | 3 | 4 | 0.429 | 0.158 | 0.750 | -0.449 | -2.321 | -16.250 | 0.253 | 2.929 | 1.679 | 0.155 |
| 15 | 9 | 6 | 3 | 0.667 | 0.354 | 0.879 | 0.106 | 0.167 | 1.500 | 1.062 | 3.611 | 5.389 | 1.106 |

* **09:30-10:30**: n=10 WR=0.300 [0.108, 0.603] expR=-0.5581 PF=0.373 (0.039 trades/day)

* **10:30-11:30**: n=5 WR=0.200 [0.036, 0.624] expR=-0.8863 PF=0.047 (0.020 trades/day)

## 5. Diagnostic breakdowns — PRIMARY window, 1R, primary friction

_Diagnostics only. No subgroup is promoted to the strategy._


**Year**

| year | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024 | 15 | 4 | 11 | 0.267 | 0.109 | 0.520 | -0.668 | -3.917 | -58.750 | 0.288 | 5.167 | 3.967 | 0.266 |

**Month**

| month | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024-01 | 2 | 0 | 2 | 0.000 | 0.000 | 0.658 | -1.243 | -5.250 | -10.500 | 0.000 | 4.250 | 1.375 | 0.409 |
| 2024-02 | 2 | 0 | 2 | 0.000 | 0.000 | 0.658 | -1.147 | -8.875 | -17.750 | 0.000 | 8.000 | 4.125 | 0.346 |
| 2024-03 | 2 | 1 | 1 | 0.500 | 0.095 | 0.905 | -0.144 | -2.500 | -5.000 | 0.487 | 4.750 | 4.500 | 0.487 |
| 2024-04 | 2 | 0 | 2 | 0.000 | 0.000 | 0.658 | -1.205 | -6.000 | -12.000 | 0.000 | 5.000 | 0.750 | 0.218 |
| 2024-05 | 1 | 1 | 0 | 1.000 | 0.207 | 1.000 | 0.500 | 1.000 | 1.000 | inf | 1.000 | 2.250 | 0.035 |
| 2024-06 | 2 | 1 | 1 | 0.500 | 0.095 | 0.905 | -0.278 | -0.250 | -0.500 | 0.875 | 2.875 | 2.500 | 0.106 |
| 2024-08 | 1 | 1 | 0 | 1.000 | 0.207 | 1.000 | 0.935 | 14.500 | 14.500 | inf | 1.250 | 16.000 | 0.158 |
| 2024-10 | 2 | 0 | 2 | 0.000 | 0.000 | 0.658 | -1.170 | -7.250 | -14.500 | 0.000 | 6.250 | 4.000 | 1.505 |
| 2024-12 | 1 | 0 | 1 | 0.000 | 0.000 | 0.793 | -1.077 | -14.000 | -14.000 | 0.000 | 13.000 | 6.750 | 0.919 |

**Direction**

| side | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | 7 | 2 | 5 | 0.286 | 0.082 | 0.641 | -0.667 | -4.893 | -34.250 | 0.116 | 5.357 | 2.714 | 0.121 |
| SHORT | 8 | 2 | 6 | 0.250 | 0.071 | 0.591 | -0.668 | -3.062 | -24.500 | 0.440 | 5.000 | 5.062 | 0.375 |

**Impulse magnitude (x VU)**

| imp_size_bucket | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1.25-1.75 | 1 | 0 | 1 | 0.000 | 0.000 | 0.793 | -1.174 | -6.750 | -6.750 | 0.000 | 5.750 | 1.250 | 0.342 |
| 1.75-2.5 | 2 | 1 | 1 | 0.500 | 0.095 | 0.905 | -0.079 | 1.375 | 2.750 | 1.234 | 6.000 | 11.625 | 0.318 |
| <1.25 | 11 | 2 | 9 | 0.182 | 0.051 | 0.477 | -0.860 | -5.295 | -58.250 | 0.090 | 5.205 | 2.750 | 0.266 |
| >=2.5 | 1 | 1 | 0 | 1.000 | 0.207 | 1.000 | 0.778 | 3.500 | 3.500 | inf | 2.500 | 4.750 | 0.121 |

**Impulse duration (s)**

| imp_dur_bucket | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20-45 | 3 | 0 | 3 | 0.000 | 0.000 | 0.561 | -1.162 | -8.583 | -25.750 | 0.000 | 7.583 | 4.000 | 0.919 |
| 45-70 | 6 | 2 | 4 | 0.333 | 0.097 | 0.700 | -0.581 | -3.417 | -20.500 | 0.219 | 4.000 | 2.458 | 0.304 |
| <20 | 3 | 0 | 3 | 0.000 | 0.000 | 0.561 | -1.185 | -8.167 | -24.500 | 0.000 | 7.250 | 3.667 | 0.168 |
| >=70 | 3 | 2 | 1 | 0.667 | 0.208 | 0.939 | 0.171 | 4.000 | 12.000 | 3.000 | 3.000 | 7.250 | 0.158 |

**Aggression deterioration (leg3/leg1)**

| agg_drop_bucket | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.4-0.6 | 8 | 3 | 5 | 0.375 | 0.137 | 0.694 | -0.467 | -1.906 | -15.250 | 0.570 | 4.219 | 5.000 | 0.163 |
| 0.6-0.7 | 2 | 0 | 2 | 0.000 | 0.000 | 0.658 | -1.125 | -10.375 | -20.750 | 0.000 | 9.375 | 4.000 | 0.631 |
| >=0.7 | 5 | 1 | 4 | 0.200 | 0.036 | 0.624 | -0.804 | -4.550 | -22.750 | 0.133 | 5.000 | 2.300 | 0.272 |

**Absorption percentile**

| absorption_bucket | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.8-0.9 | 6 | 1 | 5 | 0.167 | 0.030 | 0.564 | -0.834 | -6.625 | -39.750 | 0.107 | 6.750 | 4.083 | 0.269 |
| 0.9-0.96 | 5 | 1 | 4 | 0.200 | 0.036 | 0.624 | -0.857 | -5.150 | -25.750 | 0.037 | 4.750 | 2.600 | 0.545 |
| <0.8 | 3 | 1 | 2 | 0.333 | 0.061 | 0.792 | -0.500 | 1.083 | 3.250 | 1.289 | 3.583 | 5.750 | 0.158 |
| >=0.96 | 1 | 1 | 0 | 1.000 | 0.207 | 1.000 | 0.778 | 3.500 | 3.500 | inf | 2.500 | 4.750 | 0.121 |

**Stop distance (R / VU)**

| stop_bucket | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.3-0.5 | 13 | 4 | 9 | 0.308 | 0.127 | 0.576 | -0.593 | -3.173 | -41.250 | 0.365 | 4.769 | 3.673 | 0.215 |
| 0.5-0.75 | 1 | 0 | 1 | 0.000 | 0.000 | 0.793 | -1.211 | -5.750 | -5.750 | 0.000 | 4.750 | 4.500 | 2.843 |
| >=0.75 | 1 | 0 | 1 | 0.000 | 0.000 | 0.793 | -1.093 | -11.750 | -11.750 | 0.000 | 10.750 | 7.250 | 0.478 |

## 6. Target sensitivity on the SAME entries (primary window)

_1R is the pre-registered primary. The others are diagnostics and are not selected on._

| target | n_trades | win_rate | expectancy_R | expectancy_points | profit_factor | avg_hold_min |
|---|---|---|---|---|---|---|
| 1R | 15 | 0.267 | -0.668 | -3.917 | 0.288 | 0.484 |
| 1.25R | 15 | 0.200 | -0.751 | -3.754 | 0.341 | 0.531 |
| 1.5R | 15 | 0.133 | -0.868 | -4.075 | 0.328 | 0.540 |
| 2R | 15 | 0.133 | -0.801 | -3.367 | 0.445 | 0.613 |