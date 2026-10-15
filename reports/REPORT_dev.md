# Fast-Slow NQ — DEVELOPMENT 2021-2023

* spec version: `fastslow-1.0.0`
* period: **2021-01-01 .. 2023-12-31** (775 Globex trading days with data)
* A-B-C instances examined: **27,238** (rejected by the pattern gates: 25,408)
* A-B-C patterns passing every gate: **1,830** (of which 1,364 produced no valid reversal trigger)
* reversal-trigger hits before per-pattern dedup: **500**
* days considered: 775, skipped: `{"ROLL_DAY": 13, "NO_LEVELS": 19, "NO_ATR": 0, "TOO_FEW_BARS": 0}`
* runtime: 5.3s

## 1. Headline matrix - variant x target x round-trip friction

Friction is applied as a flat round-trip cost in NQ points on every trade (entry already pays the modelled first-print slippage on top of this).

| variant | target | friction_pts | trades | win_rate | expectancy_R | expectancy_pts | total_pts | profit_factor | max_dd_R | p_value |
|---|---|---|---|---|---|---|---|---|---|---|
| ANY | 1R | 0.000 | 449 | 0.492 | -0.014 | 0.008 | 3.500 | 1.001 | 20.837 | 0.647 |
| ANY | 1R | 0.500 | 449 | 0.492 | -0.063 | -0.492 | -221.000 | 0.934 | 39.073 | 0.647 |
| ANY | 1R | 1.000 | 449 | 0.492 | -0.113 | -0.992 | -445.500 | 0.872 | 57.785 | 0.647 |
| ANY | 1R | 2.000 | 449 | 0.492 | -0.211 | -1.992 | -894.500 | 0.758 | 100.720 | 0.647 |
| ANY | 2R | 0.000 | 449 | 0.330 | -0.016 | -0.145 | -65.000 | 0.985 | 24.053 | 0.584 |
| ANY | 2R | 0.500 | 449 | 0.330 | -0.065 | -0.645 | -289.500 | 0.935 | 39.259 | 0.584 |
| ANY | 2R | 1.000 | 449 | 0.330 | -0.114 | -1.145 | -514.000 | 0.889 | 60.003 | 0.584 |
| ANY | 2R | 2.000 | 449 | 0.330 | -0.213 | -2.145 | -963.000 | 0.805 | 102.655 | 0.584 |
| ENGULFING | 1R | 0.000 | 194 | 0.567 | 0.136 | 2.250 | 436.500 | 1.274 | 5.010 | 0.036 |
| ENGULFING | 1R | 0.500 | 194 | 0.567 | 0.099 | 1.750 | 339.500 | 1.208 | 5.311 | 0.036 |
| ENGULFING | 1R | 1.000 | 194 | 0.567 | 0.062 | 1.250 | 242.500 | 1.145 | 6.420 | 0.036 |
| ENGULFING | 1R | 2.000 | 194 | 0.567 | -0.011 | 0.250 | 48.500 | 1.028 | 10.546 | 0.036 |
| ENGULFING | 2R | 0.000 | 194 | 0.366 | 0.087 | 1.927 | 373.750 | 1.164 | 13.010 | 0.187 |
| ENGULFING | 2R | 0.500 | 194 | 0.366 | 0.050 | 1.427 | 276.750 | 1.119 | 14.093 | 0.187 |
| ENGULFING | 2R | 1.000 | 194 | 0.366 | 0.013 | 0.927 | 179.750 | 1.075 | 15.175 | 0.187 |
| ENGULFING | 2R | 2.000 | 194 | 0.366 | -0.061 | -0.073 | -14.250 | 0.994 | 17.341 | 0.187 |
| PIN | 1R | 0.000 | 272 | 0.430 | -0.139 | -1.961 | -533.500 | 0.712 | 45.791 | 0.991 |
| PIN | 1R | 0.500 | 272 | 0.430 | -0.196 | -2.461 | -669.500 | 0.653 | 58.955 | 0.991 |
| PIN | 1R | 1.000 | 272 | 0.430 | -0.254 | -2.961 | -805.500 | 0.598 | 74.120 | 0.991 |
| PIN | 1R | 2.000 | 272 | 0.430 | -0.369 | -3.961 | -1,078 | 0.501 | 104.449 | 0.991 |
| PIN | 2R | 0.000 | 272 | 0.287 | -0.139 | -2.515 | -684.000 | 0.708 | 48.851 | 0.956 |
| PIN | 2R | 0.500 | 272 | 0.287 | -0.197 | -3.015 | -820.000 | 0.663 | 60.893 | 0.956 |
| PIN | 2R | 1.000 | 272 | 0.287 | -0.254 | -3.515 | -956.000 | 0.623 | 75.559 | 0.956 |
| PIN | 2R | 2.000 | 272 | 0.287 | -0.369 | -4.515 | -1,228 | 0.550 | 106.223 | 0.956 |
| STAR | 1R | 0.000 | 16 | 0.500 | 0.000 | 1.500 | 24.000 | 1.157 | 5.000 | 0.598 |
| STAR | 1R | 0.500 | 16 | 0.500 | -0.034 | 1.000 | 16.000 | 1.102 | 5.247 | 0.598 |
| STAR | 1R | 1.000 | 16 | 0.500 | -0.069 | 0.500 | 8.000 | 1.050 | 5.494 | 0.598 |
| STAR | 1R | 2.000 | 16 | 0.500 | -0.137 | -0.500 | -8.000 | 0.953 | 5.988 | 0.598 |
| STAR | 2R | 0.000 | 16 | 0.375 | 0.123 | 3.672 | 58.750 | 1.293 | 4.000 | 0.453 |
| STAR | 2R | 0.500 | 16 | 0.375 | 0.089 | 3.172 | 50.750 | 1.247 | 4.247 | 0.453 |
| STAR | 2R | 1.000 | 16 | 0.375 | 0.055 | 2.672 | 42.750 | 1.203 | 4.494 | 0.453 |
| STAR | 2R | 2.000 | 16 | 0.375 | -0.014 | 1.672 | 26.750 | 1.121 | 4.988 | 0.453 |


## 2.1 Variant `ANY`

* signals generated: **466** | accepted: **449** | skipped: **17**

Skip reasons:

| skip_reason | len |
|---|---|
| CONCURRENT_POSITION | 11 |
| R_TOO_LARGE | 5 |
| R_TOO_SMALL | 1 |

* 09:30-11:30 ET trades: **102** (0.132 / trading day)

### ANY - target 1R (primary) - GROSS (0.0 pts friction)

| metric | value |
|---|---|
| executed trades | 449 |
| trades / trading day | 0.579 |
| long | 213 |
| short | 236 |
| wins | 221 |
| losses | 228 |
| breakevens | 0 |
| win rate | 0.492 |
| win rate 95% CI low | 0.446 |
| win rate 95% CI high | 0.538 |
| break-even win rate | 0.500 |
| p(win rate > break-even), one-sided | 0.647 |
| expectancy (R) | -0.014 |
| expectancy (NQ points) | 0.008 |
| average R | -0.014 |
| total points | 3.500 |
| total R | -6.335 |
| profit factor | 1.001 |
| average winner (pts) | 14.681 |
| average loser (pts) | -14.215 |
| median winner (pts) | 12.750 |
| median loser (pts) | -11.000 |
| max drawdown (R) | 20.837 |
| max drawdown (pts) | 208.250 |
| longest winning streak | 6 |
| longest losing streak | 9 |
| average MAE (pts) | 10.091 |
| median MAE (pts) | 8.000 |
| average MFE (pts) | 10.444 |
| median MFE (pts) | 8.250 |
| average hold (min) | 7.966 |
| median hold (min) | 4.068 |
| average R distance (pts) | 14.514 |
| TP exits | 221 |
| SL exits | 226 |
| timeout exits | 2 |
| t-stat of mean R | -0.299 |

<small>friction 0.5 pts -> expectancy -0.0634 R / -0.492 pts, PF 0.934, total -221.0 pts</small>


<small>friction 1.0 pts -> expectancy -0.1128 R / -0.992 pts, PF 0.872, total -445.5 pts</small>


<small>friction 2.0 pts -> expectancy -0.2114 R / -1.992 pts, PF 0.758, total -894.5 pts</small>


### ANY - target 2R (secondary) - GROSS (0.0 pts friction)

| metric | value |
|---|---|
| executed trades | 449 |
| trades / trading day | 0.579 |
| long | 213 |
| short | 236 |
| wins | 148 |
| losses | 301 |
| breakevens | 0 |
| win rate | 0.330 |
| win rate 95% CI low | 0.288 |
| win rate 95% CI high | 0.374 |
| break-even win rate | 0.333 |
| p(win rate > break-even), one-sided | 0.584 |
| expectancy (R) | -0.016 |
| expectancy (NQ points) | -0.145 |
| average R | -0.016 |
| total points | -65.000 |
| total R | -7.012 |
| profit factor | 0.985 |
| average winner (pts) | 28.811 |
| average loser (pts) | -14.382 |
| median winner (pts) | 24.250 |
| median loser (pts) | -11.750 |
| max drawdown (R) | 24.053 |
| max drawdown (pts) | 331.750 |
| longest winning streak | 6 |
| longest losing streak | 11 |
| average MAE (pts) | 11.796 |
| median MAE (pts) | 9.250 |
| average MFE (pts) | 16.135 |
| median MFE (pts) | 11.250 |
| average hold (min) | 15.612 |
| median hold (min) | 8.219 |
| average R distance (pts) | 14.514 |
| TP exits | 145 |
| SL exits | 299 |
| timeout exits | 5 |
| t-stat of mean R | -0.236 |

<small>friction 0.5 pts -> expectancy -0.0649 R / -0.645 pts, PF 0.935, total -289.5 pts</small>


<small>friction 1.0 pts -> expectancy -0.1143 R / -1.145 pts, PF 0.889, total -514.0 pts</small>


<small>friction 2.0 pts -> expectancy -0.2129 R / -2.145 pts, PF 0.805, total -963.0 pts</small>


### ANY - breakdowns (target 1R, gross)


**Year**

| year | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 145 | 71 | 74 | 0.490 | 0.410 | 0.570 | -0.017 | 0.503 | 73.000 | 1.083 | 8.862 | 9.090 | 4.975 |
| 2022 | 149 | 74 | 75 | 0.497 | 0.417 | 0.576 | -0.005 | -0.320 | -47.750 | 0.965 | 12.760 | 12.975 | 4.068 |
| 2023 | 155 | 76 | 79 | 0.490 | 0.413 | 0.568 | -0.019 | -0.140 | -21.750 | 0.978 | 8.676 | 9.279 | 3.704 |

**Month**

| month | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2021-02 | 12 | 4 | 8 | 0.333 | 0.138 | 0.609 | -0.333 | -5.104 | -61.250 | 0.438 | 10.729 | 7.729 | 5.304 |
| 2021-03 | 9 | 6 | 3 | 0.667 | 0.354 | 0.879 | 0.389 | 5.500 | 49.500 | 1.908 | 13.194 | 15.389 | 4.060 |
| 2021-04 | 13 | 6 | 7 | 0.462 | 0.232 | 0.709 | -0.077 | -4.731 | -61.500 | 0.479 | 10.712 | 7.654 | 4.606 |
| 2021-05 | 6 | 5 | 1 | 0.833 | 0.436 | 0.970 | 0.667 | 7.917 | 47.500 | 6.278 | 5.667 | 10.042 | 4.862 |
| 2021-06 | 14 | 7 | 7 | 0.500 | 0.268 | 0.732 | 0.000 | 2.393 | 33.500 | 1.740 | 4.571 | 7.036 | 4.744 |
| 2021-07 | 19 | 7 | 12 | 0.368 | 0.191 | 0.590 | -0.263 | -2.066 | -39.250 | 0.684 | 7.855 | 7.526 | 2.985 |
| 2021-08 | 16 | 11 | 5 | 0.688 | 0.444 | 0.858 | 0.375 | 3.562 | 57.000 | 2.226 | 5.891 | 7.312 | 4.060 |
| 2021-09 | 18 | 6 | 12 | 0.333 | 0.163 | 0.563 | -0.333 | -3.889 | -70.000 | 0.555 | 11.708 | 8.139 | 4.635 |
| 2021-10 | 14 | 8 | 6 | 0.571 | 0.326 | 0.786 | 0.143 | 6.679 | 93.500 | 3.022 | 6.929 | 11.000 | 6.013 |
| 2021-11 | 20 | 10 | 10 | 0.500 | 0.299 | 0.701 | 0.000 | 2.950 | 59.000 | 1.593 | 8.713 | 10.900 | 8.437 |
| 2021-12 | 4 | 1 | 3 | 0.250 | 0.046 | 0.699 | -0.507 | -8.750 | -35.000 | 0.489 | 18.688 | 12.500 | 2.461 |
| 2022-01 | 17 | 5 | 12 | 0.294 | 0.133 | 0.531 | -0.415 | -8.603 | -146.250 | 0.396 | 17.044 | 11.353 | 3.831 |
| 2022-02 | 15 | 10 | 5 | 0.667 | 0.417 | 0.848 | 0.333 | 7.033 | 105.500 | 2.047 | 9.550 | 16.350 | 2.171 |
| 2022-03 | 9 | 5 | 4 | 0.556 | 0.267 | 0.811 | 0.111 | 4.750 | 42.750 | 1.631 | 12.639 | 15.722 | 3.438 |
| 2022-04 | 11 | 7 | 4 | 0.636 | 0.354 | 0.848 | 0.273 | 3.727 | 41.000 | 1.896 | 7.500 | 10.727 | 4.154 |
| 2022-05 | 14 | 6 | 8 | 0.429 | 0.214 | 0.674 | -0.143 | -7.357 | -103.000 | 0.561 | 20.911 | 20.000 | 4.288 |
| 2022-06 | 12 | 5 | 7 | 0.417 | 0.193 | 0.680 | -0.170 | -4.646 | -55.750 | 0.535 | 11.521 | 8.396 | 2.171 |
| 2022-07 | 12 | 7 | 5 | 0.583 | 0.320 | 0.807 | 0.167 | 2.250 | 27.000 | 1.411 | 10.229 | 10.688 | 4.517 |
| 2022-08 | 16 | 7 | 9 | 0.438 | 0.231 | 0.668 | -0.106 | -1.781 | -28.500 | 0.782 | 12.016 | 10.719 | 7.800 |
| 2022-09 | 15 | 10 | 5 | 0.667 | 0.417 | 0.848 | 0.333 | 5.033 | 75.500 | 1.586 | 11.650 | 16.867 | 4.210 |
| 2022-10 | 11 | 7 | 4 | 0.636 | 0.354 | 0.848 | 0.273 | 1.205 | 13.250 | 1.133 | 15.636 | 14.477 | 8.898 |
| 2022-11 | 8 | 3 | 5 | 0.375 | 0.137 | 0.694 | -0.250 | -0.438 | -3.500 | 0.938 | 9.750 | 8.219 | 2.090 |
| 2022-12 | 9 | 2 | 7 | 0.222 | 0.063 | 0.547 | -0.556 | -1.750 | -15.750 | 0.786 | 11.250 | 8.556 | 3.776 |
| 2023-01 | 11 | 4 | 7 | 0.364 | 0.152 | 0.646 | -0.273 | -4.864 | -53.500 | 0.429 | 9.841 | 6.682 | 2.358 |
| 2023-02 | 6 | 4 | 2 | 0.667 | 0.300 | 0.903 | 0.333 | 9.375 | 56.250 | 3.557 | 8.958 | 15.833 | 2.444 |
| 2023-03 | 11 | 6 | 5 | 0.545 | 0.280 | 0.787 | 0.091 | 5.023 | 55.250 | 1.917 | 8.727 | 14.136 | 3.905 |
| 2023-04 | 10 | 5 | 5 | 0.500 | 0.237 | 0.763 | 0.000 | 1.775 | 17.750 | 1.480 | 5.725 | 6.825 | 4.523 |
| 2023-05 | 24 | 12 | 12 | 0.500 | 0.314 | 0.686 | 0.000 | -0.167 | -4.000 | 0.970 | 7.906 | 8.042 | 4.994 |
| 2023-06 | 18 | 7 | 11 | 0.389 | 0.203 | 0.614 | -0.222 | -1.333 | -24.000 | 0.828 | 10.028 | 9.347 | 3.685 |
| 2023-07 | 14 | 8 | 6 | 0.571 | 0.326 | 0.786 | 0.143 | 2.536 | 35.500 | 1.478 | 7.179 | 10.179 | 2.981 |
| 2023-08 | 19 | 8 | 11 | 0.421 | 0.231 | 0.637 | -0.158 | -4.329 | -82.250 | 0.478 | 9.789 | 8.329 | 2.940 |
| 2023-09 | 13 | 6 | 7 | 0.462 | 0.232 | 0.709 | -0.077 | -2.538 | -33.000 | 0.636 | 9.577 | 8.327 | 4.256 |
| 2023-10 | 10 | 5 | 5 | 0.500 | 0.237 | 0.763 | 0.000 | -2.825 | -28.250 | 0.718 | 12.900 | 11.175 | 3.943 |
| 2023-11 | 9 | 2 | 7 | 0.222 | 0.063 | 0.547 | -0.556 | -5.083 | -45.750 | 0.402 | 9.528 | 6.889 | 3.771 |
| 2023-12 | 10 | 9 | 1 | 0.900 | 0.596 | 0.982 | 0.800 | 8.425 | 84.250 | 9.868 | 3.350 | 10.200 | 3.553 |

**Level family**

| family | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ASIA_H | 77 | 37 | 40 | 0.481 | 0.373 | 0.590 | -0.039 | 0.182 | 14.000 | 1.029 | 8.899 | 9.253 | 4.154 |
| ASIA_L | 81 | 35 | 46 | 0.432 | 0.330 | 0.541 | -0.136 | -1.827 | -148.000 | 0.797 | 11.932 | 11.216 | 4.384 |
| EU_H | 60 | 27 | 33 | 0.450 | 0.331 | 0.575 | -0.087 | -0.250 | -15.000 | 0.969 | 10.979 | 11.692 | 5.056 |
| EU_L | 57 | 26 | 31 | 0.456 | 0.334 | 0.584 | -0.088 | -0.978 | -55.750 | 0.869 | 10.254 | 8.798 | 3.038 |
| PDH | 57 | 28 | 29 | 0.491 | 0.366 | 0.617 | -0.018 | -1.421 | -81.000 | 0.808 | 10.158 | 9.904 | 4.815 |
| PDL | 76 | 44 | 32 | 0.579 | 0.467 | 0.684 | 0.158 | 2.118 | 161.000 | 1.347 | 9.145 | 11.197 | 3.315 |
| US_H | 21 | 13 | 8 | 0.619 | 0.409 | 0.792 | 0.238 | 2.714 | 57.000 | 1.702 | 6.357 | 7.798 | 3.895 |
| US_L | 20 | 11 | 9 | 0.550 | 0.342 | 0.742 | 0.100 | 3.562 | 71.250 | 1.466 | 11.425 | 14.312 | 4.845 |

**Trigger type**

| trigger_type | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ENGULFING | 172 | 102 | 70 | 0.593 | 0.518 | 0.664 | 0.189 | 3.426 | 589.250 | 1.449 | 11.863 | 14.549 | 6.263 |
| PIN | 269 | 116 | 153 | 0.431 | 0.373 | 0.491 | -0.137 | -1.986 | -534.250 | 0.708 | 8.784 | 7.770 | 2.912 |
| STAR | 8 | 3 | 5 | 0.375 | 0.137 | 0.694 | -0.250 | -6.438 | -51.500 | 0.476 | 15.938 | 12.094 | 7.229 |

**Direction**

| side | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | 213 | 110 | 103 | 0.516 | 0.450 | 0.583 | 0.035 | 0.346 | 73.750 | 1.047 | 10.097 | 11.042 | 3.974 |
| SHORT | 236 | 111 | 125 | 0.470 | 0.408 | 0.534 | -0.058 | -0.298 | -70.250 | 0.958 | 10.086 | 9.905 | 4.119 |

**Session**

| session | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ASIA | 41 | 23 | 18 | 0.561 | 0.410 | 0.701 | 0.120 | 0.720 | 29.500 | 1.191 | 5.421 | 5.848 | 4.256 |
| EU | 111 | 56 | 55 | 0.505 | 0.413 | 0.596 | 0.009 | 0.523 | 58.000 | 1.101 | 7.716 | 7.709 | 4.368 |
| POST | 5 | 0 | 5 | 0.000 | 0.000 | 0.434 | -1.000 | -8.950 | -44.750 | 0.000 | 9.150 | 3.300 | 7.789 |
| US | 292 | 142 | 150 | 0.486 | 0.430 | 0.543 | -0.025 | -0.134 | -39.250 | 0.984 | 11.666 | 12.252 | 3.791 |

**Fast-Slow time-ratio bucket**

| tr_bucket | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2.0-2.5 | 128 | 57 | 71 | 0.445 | 0.362 | 0.532 | -0.103 | -1.215 | -155.500 | 0.856 | 10.918 | 11.172 | 4.710 |
| 2.5-3.0 | 86 | 48 | 38 | 0.558 | 0.453 | 0.658 | 0.116 | 2.390 | 205.500 | 1.418 | 8.910 | 10.378 | 3.805 |
| >=3.0 | 235 | 116 | 119 | 0.494 | 0.430 | 0.557 | -0.013 | -0.198 | -46.500 | 0.972 | 10.073 | 10.072 | 3.974 |

**09:30-11:30 ET subset**

| metric | value |
|---|---|
| executed trades | 102 |
| trades / trading day | 0.132 |
| long | 46 |
| short | 56 |
| wins | 48 |
| losses | 54 |
| breakevens | 0 |
| win rate | 0.471 |
| win rate 95% CI low | 0.377 |
| win rate 95% CI high | 0.567 |
| break-even win rate | 0.500 |
| p(win rate > break-even), one-sided | 0.756 |
| expectancy (R) | -0.059 |
| expectancy (NQ points) | -1.042 |

## 2.2 Variant `ENGULFING`

* signals generated: **206** | accepted: **194** | skipped: **12**

Skip reasons:

| skip_reason | len |
|---|---|
| CONCURRENT_POSITION | 9 |
| R_TOO_LARGE | 3 |

* 09:30-11:30 ET trades: **44** (0.057 / trading day)

### ENGULFING - target 1R (primary) - GROSS (0.0 pts friction)

| metric | value |
|---|---|
| executed trades | 194 |
| trades / trading day | 0.250 |
| long | 94 |
| short | 100 |
| wins | 110 |
| losses | 84 |
| breakevens | 0 |
| win rate | 0.567 |
| win rate 95% CI low | 0.497 |
| win rate 95% CI high | 0.635 |
| break-even win rate | 0.500 |
| p(win rate > break-even), one-sided | 0.036 |
| expectancy (R) | 0.136 |
| expectancy (NQ points) | 2.250 |
| average R | 0.136 |
| total points | 436.500 |
| total R | 26.449 |
| profit factor | 1.274 |
| average winner (pts) | 18.448 |
| average loser (pts) | -18.961 |
| median winner (pts) | 16.750 |
| median loser (pts) | -16.625 |
| max drawdown (R) | 5.010 |
| max drawdown (pts) | 155.750 |
| longest winning streak | 5 |
| longest losing streak | 4 |
| average MAE (pts) | 12.238 |
| median MAE (pts) | 9.250 |
| average MFE (pts) | 14.120 |
| median MFE (pts) | 11.875 |
| average hold (min) | 12.799 |
| median hold (min) | 6.388 |
| average R distance (pts) | 18.793 |
| TP exits | 110 |
| SL exits | 83 |
| timeout exits | 1 |
| t-stat of mean R | 1.915 |

<small>friction 0.5 pts -> expectancy 0.0994 R / 1.750 pts, PF 1.208, total 339.5 pts</small>


<small>friction 1.0 pts -> expectancy 0.0624 R / 1.250 pts, PF 1.145, total 242.5 pts</small>


<small>friction 2.0 pts -> expectancy -0.0115 R / 0.250 pts, PF 1.028, total 48.5 pts</small>


### ENGULFING - target 2R (secondary) - GROSS (0.0 pts friction)

| metric | value |
|---|---|
| executed trades | 194 |
| trades / trading day | 0.250 |
| long | 94 |
| short | 100 |
| wins | 71 |
| losses | 123 |
| breakevens | 0 |
| win rate | 0.366 |
| win rate 95% CI low | 0.301 |
| win rate 95% CI high | 0.436 |
| break-even win rate | 0.333 |
| p(win rate > break-even), one-sided | 0.187 |
| expectancy (R) | 0.087 |
| expectancy (NQ points) | 1.927 |
| average R | 0.087 |
| total points | 373.750 |
| total R | 16.898 |
| profit factor | 1.164 |
| average winner (pts) | 37.275 |
| average loser (pts) | -18.478 |
| median winner (pts) | 33.000 |
| median loser (pts) | -17.000 |
| max drawdown (R) | 13.010 |
| max drawdown (pts) | 208.500 |
| longest winning streak | 3 |
| longest losing streak | 7 |
| average MAE (pts) | 14.582 |
| median MAE (pts) | 12.000 |
| average MFE (pts) | 22.354 |
| median MFE (pts) | 17.000 |
| average hold (min) | 24.495 |
| median hold (min) | 14.619 |
| average R distance (pts) | 18.793 |
| TP exits | 68 |
| SL exits | 122 |
| timeout exits | 4 |
| t-stat of mean R | 0.846 |

<small>friction 0.5 pts -> expectancy 0.0501 R / 1.427 pts, PF 1.119, total 276.8 pts</small>


<small>friction 1.0 pts -> expectancy 0.0132 R / 0.927 pts, PF 1.075, total 179.8 pts</small>


<small>friction 2.0 pts -> expectancy -0.0607 R / -0.073 pts, PF 0.994, total -14.2 pts</small>


### ENGULFING - breakdowns (target 1R, gross)


**Year**

| year | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 67 | 39 | 28 | 0.582 | 0.463 | 0.693 | 0.172 | 4.198 | 281.250 | 1.680 | 10.638 | 13.056 | 8.234 |
| 2022 | 65 | 38 | 27 | 0.585 | 0.463 | 0.696 | 0.169 | 1.231 | 80.000 | 1.109 | 16.385 | 17.115 | 6.206 |
| 2023 | 62 | 33 | 29 | 0.532 | 0.410 | 0.651 | 0.064 | 1.214 | 75.250 | 1.169 | 9.621 | 12.129 | 5.795 |

**Month**

| month | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2021-02 | 5 | 3 | 2 | 0.600 | 0.231 | 0.882 | 0.200 | 3.450 | 17.250 | 1.585 | 9.850 | 10.100 | 8.705 |
| 2021-03 | 6 | 4 | 2 | 0.667 | 0.300 | 0.903 | 0.417 | 6.417 | 38.500 | 1.865 | 16.833 | 17.792 | 8.717 |
| 2021-04 | 6 | 3 | 3 | 0.500 | 0.188 | 0.812 | 0.000 | -4.500 | -27.000 | 0.528 | 10.458 | 11.458 | 5.176 |
| 2021-05 | 3 | 2 | 1 | 0.667 | 0.208 | 0.939 | 0.333 | 12.250 | 36.750 | 5.083 | 11.917 | 16.000 | 14.708 |
| 2021-06 | 7 | 4 | 3 | 0.571 | 0.250 | 0.842 | 0.143 | 6.000 | 42.000 | 2.846 | 4.250 | 10.179 | 4.736 |
| 2021-07 | 6 | 3 | 3 | 0.500 | 0.188 | 0.812 | 0.000 | 0.208 | 1.250 | 1.031 | 7.958 | 12.583 | 5.949 |
| 2021-08 | 6 | 4 | 2 | 0.667 | 0.300 | 0.903 | 0.333 | 5.250 | 31.500 | 2.189 | 9.000 | 9.958 | 7.826 |
| 2021-09 | 7 | 3 | 4 | 0.429 | 0.158 | 0.750 | -0.143 | -1.214 | -8.500 | 0.879 | 16.179 | 11.893 | 9.180 |
| 2021-10 | 9 | 6 | 3 | 0.667 | 0.354 | 0.879 | 0.333 | 8.750 | 78.750 | 3.561 | 7.556 | 13.333 | 16.010 |
| 2021-11 | 9 | 6 | 3 | 0.667 | 0.354 | 0.879 | 0.333 | 10.667 | 96.000 | 5.085 | 9.583 | 15.750 | 9.127 |
| 2021-12 | 3 | 1 | 2 | 0.333 | 0.061 | 0.792 | -0.333 | -8.417 | -25.250 | 0.570 | 21.667 | 16.417 | 2.783 |
| 2022-01 | 6 | 3 | 3 | 0.500 | 0.188 | 0.812 | -0.004 | -7.292 | -43.750 | 0.625 | 26.875 | 18.667 | 5.867 |
| 2022-02 | 5 | 3 | 2 | 0.600 | 0.231 | 0.882 | 0.199 | 7.650 | 38.250 | 1.560 | 15.000 | 23.200 | 4.601 |
| 2022-03 | 4 | 3 | 1 | 0.750 | 0.301 | 0.954 | 0.500 | 12.125 | 48.500 | 2.338 | 17.438 | 27.438 | 11.562 |
| 2022-04 | 2 | 2 | 0 | 1.000 | 0.342 | 1.000 | 1.000 | 12.750 | 25.500 | inf | 1.375 | 13.000 | 5.551 |
| 2022-05 | 5 | 2 | 3 | 0.400 | 0.118 | 0.769 | -0.202 | -11.100 | -55.500 | 0.483 | 28.000 | 23.750 | 8.034 |
| 2022-06 | 6 | 3 | 3 | 0.500 | 0.188 | 0.812 | 0.000 | -5.500 | -33.000 | 0.581 | 14.625 | 9.667 | 2.749 |
| 2022-07 | 6 | 5 | 1 | 0.833 | 0.436 | 0.970 | 0.667 | 10.750 | 64.500 | 8.371 | 9.500 | 13.250 | 7.361 |
| 2022-08 | 10 | 4 | 6 | 0.400 | 0.168 | 0.687 | -0.200 | -2.700 | -27.000 | 0.738 | 14.700 | 12.150 | 13.111 |
| 2022-09 | 8 | 5 | 3 | 0.625 | 0.306 | 0.863 | 0.249 | -0.094 | -0.750 | 0.993 | 16.281 | 18.812 | 5.398 |
| 2022-10 | 8 | 4 | 4 | 0.500 | 0.215 | 0.785 | 0.000 | -3.875 | -31.000 | 0.690 | 18.000 | 14.250 | 7.457 |
| 2022-11 | 2 | 2 | 0 | 1.000 | 0.342 | 1.000 | 1.000 | 23.250 | 46.500 | inf | 7.250 | 23.500 | 9.982 |
| 2022-12 | 3 | 2 | 1 | 0.667 | 0.208 | 0.939 | 0.333 | 15.917 | 47.750 | 5.775 | 11.917 | 19.833 | 11.013 |
| 2023-01 | 4 | 2 | 2 | 0.500 | 0.150 | 0.850 | 0.000 | -2.688 | -10.750 | 0.632 | 8.625 | 9.375 | 11.525 |
| 2023-02 | 2 | 1 | 1 | 0.500 | 0.095 | 0.905 | 0.000 | 19.875 | 39.750 | 3.741 | 15.250 | 33.250 | 2.623 |
| 2023-03 | 3 | 3 | 0 | 1.000 | 0.439 | 1.000 | 1.000 | 21.000 | 63.000 | inf | 5.750 | 21.417 | 4.512 |
| 2023-04 | 3 | 1 | 2 | 0.333 | 0.061 | 0.792 | -0.333 | -1.500 | -4.500 | 0.743 | 6.333 | 7.167 | 6.041 |
| 2023-05 | 10 | 5 | 5 | 0.500 | 0.237 | 0.763 | 0.000 | -3.550 | -35.500 | 0.660 | 13.050 | 11.475 | 10.188 |
| 2023-06 | 10 | 5 | 5 | 0.500 | 0.237 | 0.763 | 0.000 | 1.525 | 15.250 | 1.223 | 8.350 | 11.050 | 3.776 |
| 2023-07 | 6 | 4 | 2 | 0.667 | 0.300 | 0.903 | 0.333 | 7.375 | 44.250 | 2.718 | 8.000 | 13.958 | 10.973 |
| 2023-08 | 11 | 4 | 7 | 0.364 | 0.152 | 0.646 | -0.274 | -5.114 | -56.250 | 0.440 | 10.523 | 9.136 | 10.059 |
| 2023-09 | 3 | 3 | 0 | 1.000 | 0.439 | 1.000 | 1.000 | 9.083 | 27.250 | inf | 4.750 | 9.500 | 4.330 |
| 2023-10 | 5 | 2 | 3 | 0.400 | 0.118 | 0.769 | -0.200 | -3.700 | -18.500 | 0.656 | 13.150 | 13.600 | 5.828 |
| 2023-11 | 3 | 1 | 2 | 0.333 | 0.061 | 0.792 | -0.333 | -3.583 | -10.750 | 0.645 | 10.667 | 11.083 | 3.704 |
| 2023-12 | 2 | 2 | 0 | 1.000 | 0.342 | 1.000 | 1.000 | 11.000 | 22.000 | inf | 2.750 | 11.500 | 24.221 |

**Level family**

| family | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ASIA_H | 30 | 17 | 13 | 0.567 | 0.392 | 0.726 | 0.133 | 1.150 | 34.500 | 1.142 | 11.975 | 13.108 | 6.201 |
| ASIA_L | 39 | 20 | 19 | 0.513 | 0.362 | 0.661 | 0.025 | 1.365 | 53.250 | 1.158 | 13.269 | 14.058 | 6.180 |
| EU_H | 36 | 17 | 19 | 0.472 | 0.320 | 0.630 | -0.042 | 0.625 | 22.500 | 1.063 | 13.729 | 14.889 | 12.106 |
| EU_L | 22 | 12 | 10 | 0.545 | 0.347 | 0.731 | 0.090 | 0.602 | 13.250 | 1.068 | 12.705 | 11.534 | 4.888 |
| PDH | 26 | 17 | 9 | 0.654 | 0.462 | 0.806 | 0.308 | 1.192 | 31.000 | 1.148 | 12.471 | 13.702 | 9.400 |
| PDL | 23 | 17 | 6 | 0.739 | 0.535 | 0.875 | 0.478 | 10.043 | 231.000 | 3.532 | 8.250 | 16.370 | 5.125 |
| US_H | 10 | 4 | 6 | 0.400 | 0.168 | 0.687 | -0.201 | -7.725 | -77.250 | 0.366 | 12.800 | 8.675 | 6.676 |
| US_L | 8 | 6 | 2 | 0.750 | 0.409 | 0.929 | 0.499 | 16.031 | 128.250 | 4.206 | 10.219 | 23.562 | 8.546 |

**Trigger type**

| trigger_type | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ENGULFING | 194 | 110 | 84 | 0.567 | 0.497 | 0.635 | 0.136 | 2.250 | 436.500 | 1.274 | 12.238 | 14.120 | 6.388 |

**Direction**

| side | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | 94 | 55 | 39 | 0.585 | 0.484 | 0.679 | 0.175 | 3.069 | 288.500 | 1.373 | 12.516 | 14.949 | 9.072 |
| SHORT | 100 | 55 | 45 | 0.550 | 0.452 | 0.644 | 0.100 | 1.480 | 148.000 | 1.180 | 11.977 | 13.340 | 5.755 |

**Session**

| session | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ASIA | 17 | 12 | 5 | 0.706 | 0.469 | 0.867 | 0.410 | 2.735 | 46.500 | 1.912 | 5.294 | 7.162 | 9.547 |
| EU | 43 | 26 | 17 | 0.605 | 0.456 | 0.736 | 0.209 | 3.233 | 139.000 | 1.612 | 8.738 | 11.157 | 9.127 |
| POST | 2 | 0 | 2 | 0.000 | 0.000 | 0.658 | -1.000 | -7.250 | -14.500 | 0.000 | 7.625 | 0.375 | 3.057 |
| US | 132 | 72 | 60 | 0.545 | 0.460 | 0.628 | 0.094 | 2.011 | 265.500 | 1.204 | 14.343 | 16.189 | 5.923 |

**Fast-Slow time-ratio bucket**

| tr_bucket | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2.0-2.5 | 58 | 31 | 27 | 0.534 | 0.408 | 0.657 | 0.077 | 2.280 | 132.250 | 1.262 | 12.547 | 15.125 | 7.598 |
| 2.5-3.0 | 31 | 21 | 10 | 0.677 | 0.501 | 0.814 | 0.355 | 7.984 | 247.500 | 2.972 | 8.242 | 13.815 | 4.641 |
| >=3.0 | 105 | 58 | 47 | 0.552 | 0.457 | 0.644 | 0.104 | 0.540 | 56.750 | 1.059 | 13.248 | 13.655 | 8.234 |

**09:30-11:30 ET subset**

| metric | value |
|---|---|
| executed trades | 44 |
| trades / trading day | 0.057 |
| long | 17 |
| short | 27 |
| wins | 25 |
| losses | 19 |
| breakevens | 0 |
| win rate | 0.568 |
| win rate 95% CI low | 0.422 |
| win rate 95% CI high | 0.703 |
| break-even win rate | 0.500 |
| p(win rate > break-even), one-sided | 0.226 |
| expectancy (R) | 0.136 |
| expectancy (NQ points) | 2.330 |

## 2.3 Variant `PIN`

* signals generated: **277** | accepted: **272** | skipped: **5**

Skip reasons:

| skip_reason | len |
|---|---|
| CONCURRENT_POSITION | 3 |
| R_TOO_LARGE | 1 |
| R_TOO_SMALL | 1 |

* 09:30-11:30 ET trades: **62** (0.080 / trading day)

### PIN - target 1R (primary) - GROSS (0.0 pts friction)

| metric | value |
|---|---|
| executed trades | 272 |
| trades / trading day | 0.351 |
| long | 129 |
| short | 143 |
| wins | 117 |
| losses | 155 |
| breakevens | 0 |
| win rate | 0.430 |
| win rate 95% CI low | 0.373 |
| win rate 95% CI high | 0.490 |
| break-even win rate | 0.500 |
| p(win rate > break-even), one-sided | 0.991 |
| expectancy (R) | -0.139 |
| expectancy (NQ points) | -1.961 |
| average R | -0.139 |
| total points | -533.500 |
| total R | -37.791 |
| profit factor | 0.712 |
| average winner (pts) | 11.250 |
| average loser (pts) | -11.934 |
| median winner (pts) | 9.250 |
| median loser (pts) | -9.750 |
| max drawdown (R) | 45.791 |
| max drawdown (pts) | 595.750 |
| longest winning streak | 6 |
| longest losing streak | 10 |
| average MAE (pts) | 8.770 |
| median MAE (pts) | 7.000 |
| average MFE (pts) | 7.777 |
| median MFE (pts) | 6.250 |
| average hold (min) | 5.629 |
| median hold (min) | 2.898 |
| average R distance (pts) | 11.666 |
| TP exits | 117 |
| SL exits | 154 |
| timeout exits | 1 |
| t-stat of mean R | -2.311 |

<small>friction 0.5 pts -> expectancy -0.1963 R / -2.461 pts, PF 0.653, total -669.5 pts</small>


<small>friction 1.0 pts -> expectancy -0.2537 R / -2.961 pts, PF 0.598, total -805.5 pts</small>


<small>friction 2.0 pts -> expectancy -0.3685 R / -3.961 pts, PF 0.501, total -1077.5 pts</small>


### PIN - target 2R (secondary) - GROSS (0.0 pts friction)

| metric | value |
|---|---|
| executed trades | 272 |
| trades / trading day | 0.351 |
| long | 129 |
| short | 143 |
| wins | 78 |
| losses | 194 |
| breakevens | 0 |
| win rate | 0.287 |
| win rate 95% CI low | 0.236 |
| win rate 95% CI high | 0.343 |
| break-even win rate | 0.333 |
| p(win rate > break-even), one-sided | 0.956 |
| expectancy (R) | -0.139 |
| expectancy (NQ points) | -2.515 |
| average R | -0.139 |
| total points | -684.000 |
| total R | -37.896 |
| profit factor | 0.708 |
| average winner (pts) | 21.224 |
| average loser (pts) | -12.059 |
| median winner (pts) | 18.250 |
| median loser (pts) | -9.750 |
| max drawdown (R) | 48.851 |
| max drawdown (pts) | 779.750 |
| longest winning streak | 5 |
| longest losing streak | 11 |
| average MAE (pts) | 10.119 |
| median MAE (pts) | 8.500 |
| average MFE (pts) | 11.528 |
| median MFE (pts) | 8.500 |
| average hold (min) | 11.285 |
| median hold (min) | 5.893 |
| average R distance (pts) | 11.666 |
| TP exits | 78 |
| SL exits | 193 |
| timeout exits | 1 |
| t-stat of mean R | -1.691 |

<small>friction 0.5 pts -> expectancy -0.1967 R / -3.015 pts, PF 0.663, total -820.0 pts</small>


<small>friction 1.0 pts -> expectancy -0.2541 R / -3.515 pts, PF 0.623, total -956.0 pts</small>


<small>friction 2.0 pts -> expectancy -0.3689 R / -4.515 pts, PF 0.550, total -1228.0 pts</small>


### PIN - breakdowns (target 1R, gross)


**Year**

| year | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 89 | 39 | 50 | 0.438 | 0.340 | 0.542 | -0.124 | -1.323 | -117.750 | 0.765 | 7.360 | 6.545 | 3.695 |
| 2022 | 86 | 34 | 52 | 0.395 | 0.299 | 0.501 | -0.207 | -3.017 | -259.500 | 0.644 | 10.677 | 9.302 | 2.342 |
| 2023 | 97 | 44 | 53 | 0.454 | 0.358 | 0.553 | -0.093 | -1.611 | -156.250 | 0.748 | 8.374 | 7.554 | 3.099 |

**Month**

| month | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2021-02 | 9 | 2 | 7 | 0.222 | 0.063 | 0.547 | -0.556 | -5.222 | -47.000 | 0.414 | 10.417 | 8.194 | 5.311 |
| 2021-03 | 3 | 2 | 1 | 0.667 | 0.208 | 0.939 | 0.333 | 3.667 | 11.000 | 2.100 | 5.917 | 10.583 | 3.038 |
| 2021-04 | 8 | 3 | 5 | 0.375 | 0.137 | 0.694 | -0.250 | -5.844 | -46.750 | 0.360 | 11.125 | 5.219 | 5.325 |
| 2021-05 | 4 | 4 | 0 | 1.000 | 0.510 | 1.000 | 1.000 | 6.938 | 27.750 | inf | 2.688 | 7.375 | 2.814 |
| 2021-06 | 8 | 4 | 4 | 0.500 | 0.215 | 0.785 | 0.000 | -0.375 | -3.000 | 0.880 | 4.625 | 4.375 | 5.157 |
| 2021-07 | 15 | 5 | 10 | 0.333 | 0.152 | 0.583 | -0.333 | -2.200 | -33.000 | 0.655 | 7.817 | 6.650 | 2.985 |
| 2021-08 | 11 | 7 | 4 | 0.636 | 0.354 | 0.848 | 0.273 | 1.409 | 15.500 | 1.517 | 4.568 | 5.205 | 2.348 |
| 2021-09 | 11 | 3 | 8 | 0.273 | 0.097 | 0.566 | -0.455 | -5.545 | -61.000 | 0.293 | 8.841 | 4.636 | 1.747 |
| 2021-10 | 6 | 3 | 3 | 0.500 | 0.188 | 0.812 | 0.000 | 6.083 | 36.500 | 3.355 | 5.375 | 9.333 | 1.742 |
| 2021-11 | 13 | 6 | 7 | 0.462 | 0.232 | 0.709 | -0.077 | -0.615 | -8.000 | 0.895 | 7.692 | 8.154 | 8.187 |
| 2021-12 | 1 | 0 | 1 | 0.000 | 0.000 | 0.793 | -1.026 | -9.750 | -9.750 | 0.000 | 9.750 | 0.750 | 2.140 |
| 2022-01 | 10 | 2 | 8 | 0.200 | 0.057 | 0.510 | -0.603 | -7.975 | -79.750 | 0.222 | 10.575 | 5.950 | 2.170 |
| 2022-02 | 11 | 7 | 4 | 0.636 | 0.354 | 0.848 | 0.273 | 2.568 | 28.250 | 1.395 | 9.886 | 11.886 | 2.171 |
| 2022-03 | 6 | 2 | 4 | 0.333 | 0.097 | 0.700 | -0.333 | -7.000 | -42.000 | 0.380 | 13.458 | 9.167 | 2.721 |
| 2022-04 | 9 | 5 | 4 | 0.556 | 0.267 | 0.811 | 0.111 | 1.722 | 15.500 | 1.339 | 8.861 | 10.222 | 4.154 |
| 2022-05 | 8 | 3 | 5 | 0.375 | 0.137 | 0.694 | -0.250 | -8.000 | -64.000 | 0.498 | 17.312 | 18.031 | 2.832 |
| 2022-06 | 6 | 2 | 4 | 0.333 | 0.097 | 0.700 | -0.341 | -3.792 | -22.750 | 0.448 | 8.417 | 7.125 | 1.713 |
| 2022-07 | 6 | 2 | 4 | 0.333 | 0.097 | 0.700 | -0.333 | -6.250 | -37.500 | 0.342 | 10.958 | 8.125 | 1.659 |
| 2022-08 | 9 | 3 | 6 | 0.333 | 0.121 | 0.646 | -0.299 | -6.306 | -56.750 | 0.314 | 11.250 | 7.444 | 4.043 |
| 2022-09 | 6 | 4 | 2 | 0.667 | 0.300 | 0.903 | 0.333 | 9.708 | 58.250 | 3.479 | 6.750 | 14.042 | 1.663 |
| 2022-10 | 3 | 3 | 0 | 1.000 | 0.439 | 1.000 | 1.000 | 14.750 | 44.250 | inf | 9.333 | 15.083 | 8.898 |
| 2022-11 | 6 | 1 | 5 | 0.167 | 0.030 | 0.564 | -0.667 | -8.333 | -50.000 | 0.115 | 10.583 | 3.125 | 1.971 |
| 2022-12 | 6 | 0 | 6 | 0.000 | 0.000 | 0.390 | -1.000 | -8.833 | -53.000 | 0.000 | 9.208 | 1.958 | 1.008 |
| 2023-01 | 7 | 2 | 5 | 0.286 | 0.082 | 0.641 | -0.429 | -6.107 | -42.750 | 0.337 | 10.536 | 5.143 | 2.358 |
| 2023-02 | 3 | 2 | 1 | 0.667 | 0.208 | 0.939 | 0.333 | 1.417 | 4.250 | 1.567 | 4.583 | 5.333 | 2.018 |
| 2023-03 | 8 | 3 | 5 | 0.375 | 0.137 | 0.694 | -0.250 | -0.969 | -7.750 | 0.871 | 9.844 | 11.406 | 3.408 |
| 2023-04 | 7 | 4 | 3 | 0.571 | 0.250 | 0.842 | 0.143 | 3.179 | 22.250 | 2.141 | 5.464 | 6.679 | 3.256 |
| 2023-05 | 15 | 7 | 8 | 0.467 | 0.248 | 0.699 | -0.067 | -0.067 | -1.000 | 0.984 | 6.117 | 6.300 | 3.511 |
| 2023-06 | 9 | 3 | 6 | 0.333 | 0.121 | 0.646 | -0.333 | -2.806 | -25.250 | 0.646 | 11.139 | 8.139 | 3.227 |
| 2023-07 | 8 | 4 | 4 | 0.500 | 0.215 | 0.785 | 0.000 | -1.094 | -8.750 | 0.820 | 6.562 | 7.344 | 1.729 |
| 2023-08 | 9 | 4 | 5 | 0.444 | 0.189 | 0.733 | -0.111 | -4.472 | -40.250 | 0.435 | 9.417 | 6.889 | 2.117 |
| 2023-09 | 11 | 4 | 7 | 0.364 | 0.152 | 0.646 | -0.273 | -4.932 | -54.250 | 0.402 | 10.295 | 7.818 | 4.256 |
| 2023-10 | 6 | 3 | 3 | 0.500 | 0.188 | 0.812 | 0.000 | -5.000 | -30.000 | 0.551 | 13.917 | 10.083 | 3.168 |
| 2023-11 | 6 | 1 | 5 | 0.167 | 0.030 | 0.564 | -0.667 | -5.833 | -35.000 | 0.243 | 8.958 | 4.792 | 6.980 |
| 2023-12 | 8 | 7 | 1 | 0.875 | 0.529 | 0.978 | 0.750 | 7.781 | 62.250 | 7.553 | 3.500 | 9.875 | 2.790 |

**Level family**

| family | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ASIA_H | 49 | 21 | 28 | 0.429 | 0.300 | 0.567 | -0.143 | -0.306 | -15.000 | 0.940 | 7.077 | 7.260 | 2.358 |
| ASIA_L | 44 | 15 | 29 | 0.341 | 0.219 | 0.489 | -0.319 | -4.938 | -217.250 | 0.466 | 10.580 | 8.239 | 4.000 |
| EU_H | 29 | 11 | 18 | 0.379 | 0.227 | 0.560 | -0.231 | -2.871 | -83.250 | 0.606 | 9.129 | 7.457 | 3.197 |
| EU_L | 35 | 14 | 21 | 0.400 | 0.256 | 0.564 | -0.200 | -2.429 | -85.000 | 0.639 | 8.550 | 6.721 | 1.984 |
| PDH | 33 | 12 | 21 | 0.364 | 0.222 | 0.534 | -0.274 | -3.432 | -113.250 | 0.509 | 8.303 | 7.311 | 3.204 |
| PDL | 55 | 29 | 26 | 0.527 | 0.398 | 0.653 | 0.054 | -0.282 | -15.500 | 0.956 | 8.927 | 8.936 | 2.298 |
| US_H | 13 | 9 | 4 | 0.692 | 0.424 | 0.873 | 0.385 | 4.538 | 59.000 | 2.698 | 6.365 | 7.827 | 2.004 |
| US_L | 14 | 6 | 8 | 0.429 | 0.214 | 0.674 | -0.143 | -4.518 | -63.250 | 0.502 | 11.536 | 7.929 | 4.368 |

**Trigger type**

| trigger_type | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PIN | 272 | 117 | 155 | 0.430 | 0.373 | 0.490 | -0.139 | -1.961 | -533.500 | 0.712 | 8.770 | 7.777 | 2.898 |

**Direction**

| side | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | 129 | 60 | 69 | 0.465 | 0.381 | 0.551 | -0.070 | -2.072 | -267.250 | 0.709 | 8.919 | 8.215 | 2.912 |
| SHORT | 143 | 57 | 86 | 0.399 | 0.322 | 0.480 | -0.201 | -1.862 | -266.250 | 0.714 | 8.636 | 7.381 | 2.885 |

**Session**

| session | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ASIA | 25 | 12 | 13 | 0.480 | 0.300 | 0.665 | -0.042 | -0.440 | -11.000 | 0.894 | 5.410 | 4.970 | 2.140 |
| EU | 73 | 30 | 43 | 0.411 | 0.305 | 0.526 | -0.178 | -1.757 | -128.250 | 0.688 | 7.531 | 5.716 | 3.181 |
| POST | 3 | 0 | 3 | 0.000 | 0.000 | 0.561 | -1.000 | -10.083 | -30.250 | 0.000 | 10.167 | 5.250 | 11.758 |
| US | 171 | 75 | 96 | 0.439 | 0.366 | 0.514 | -0.121 | -2.129 | -364.000 | 0.721 | 9.766 | 9.111 | 2.858 |

**Fast-Slow time-ratio bucket**

| tr_bucket | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2.0-2.5 | 72 | 29 | 43 | 0.403 | 0.297 | 0.518 | -0.191 | -2.851 | -205.250 | 0.636 | 9.514 | 8.639 | 2.935 |
| 2.5-3.0 | 59 | 28 | 31 | 0.475 | 0.353 | 0.600 | -0.051 | -1.419 | -83.750 | 0.798 | 9.534 | 8.242 | 3.256 |
| >=3.0 | 141 | 60 | 81 | 0.426 | 0.347 | 0.508 | -0.149 | -1.734 | -244.500 | 0.720 | 8.071 | 7.142 | 2.381 |

**09:30-11:30 ET subset**

| metric | value |
|---|---|
| executed trades | 62 |
| trades / trading day | 0.080 |
| long | 32 |
| short | 30 |
| wins | 25 |
| losses | 37 |
| breakevens | 0 |
| win rate | 0.403 |
| win rate 95% CI low | 0.290 |
| win rate 95% CI high | 0.527 |
| break-even win rate | 0.500 |
| p(win rate > break-even), one-sided | 0.951 |
| expectancy (R) | -0.194 |
| expectancy (NQ points) | -3.782 |

## 2.4 Variant `STAR`

* signals generated: **17** | accepted: **16** | skipped: **1**

Skip reasons:

| skip_reason | len |
|---|---|
| R_TOO_LARGE | 1 |

* 09:30-11:30 ET trades: **2** (0.003 / trading day)

### STAR - target 1R (primary) - GROSS (0.0 pts friction)

| metric | value |
|---|---|
| executed trades | 16 |
| trades / trading day | 0.021 |
| long | 9 |
| short | 7 |
| wins | 8 |
| losses | 8 |
| breakevens | 0 |
| win rate | 0.500 |
| win rate 95% CI low | 0.280 |
| win rate 95% CI high | 0.720 |
| break-even win rate | 0.500 |
| p(win rate > break-even), one-sided | 0.598 |
| expectancy (R) | 0.000 |
| expectancy (NQ points) | 1.500 |
| average R | 0.000 |
| total points | 24.000 |
| total R | 0.000 |
| profit factor | 1.157 |
| average winner (pts) | 22.125 |
| average loser (pts) | -19.125 |
| median winner (pts) | 17.250 |
| median loser (pts) | -18.625 |
| max drawdown (R) | 5.000 |
| max drawdown (pts) | 95.500 |
| longest winning streak | 3 |
| longest losing streak | 4 |
| average MAE (pts) | 15.094 |
| median MAE (pts) | 14.750 |
| average MFE (pts) | 16.312 |
| median MFE (pts) | 12.875 |
| average hold (min) | 12.579 |
| median hold (min) | 9.998 |
| average R distance (pts) | 20.625 |
| TP exits | 8 |
| SL exits | 8 |
| timeout exits | 0 |
| t-stat of mean R | 0.000 |

<small>friction 0.5 pts -> expectancy -0.0343 R / 1.000 pts, PF 1.102, total 16.0 pts</small>


<small>friction 1.0 pts -> expectancy -0.0686 R / 0.500 pts, PF 1.050, total 8.0 pts</small>


<small>friction 2.0 pts -> expectancy -0.1372 R / -0.500 pts, PF 0.953, total -8.0 pts</small>


### STAR - target 2R (secondary) - GROSS (0.0 pts friction)

| metric | value |
|---|---|
| executed trades | 16 |
| trades / trading day | 0.021 |
| long | 9 |
| short | 7 |
| wins | 6 |
| losses | 10 |
| breakevens | 0 |
| win rate | 0.375 |
| win rate 95% CI low | 0.185 |
| win rate 95% CI high | 0.614 |
| break-even win rate | 0.333 |
| p(win rate > break-even), one-sided | 0.453 |
| expectancy (R) | 0.123 |
| expectancy (NQ points) | 3.672 |
| average R | 0.123 |
| total points | 58.750 |
| total R | 1.972 |
| profit factor | 1.293 |
| average winner (pts) | 43.250 |
| average loser (pts) | -20.075 |
| median winner (pts) | 34.500 |
| median loser (pts) | -18.625 |
| max drawdown (R) | 4.000 |
| max drawdown (pts) | 72.500 |
| longest winning streak | 2 |
| longest losing streak | 4 |
| average MAE (pts) | 17.266 |
| median MAE (pts) | 16.500 |
| average MFE (pts) | 25.531 |
| median MFE (pts) | 18.125 |
| average hold (min) | 20.449 |
| median hold (min) | 20.201 |
| average R distance (pts) | 20.625 |
| TP exits | 6 |
| SL exits | 10 |
| timeout exits | 0 |
| t-stat of mean R | 0.328 |

<small>friction 0.5 pts -> expectancy 0.0890 R / 3.172 pts, PF 1.247, total 50.8 pts</small>


<small>friction 1.0 pts -> expectancy 0.0547 R / 2.672 pts, PF 1.203, total 42.8 pts</small>


<small>friction 2.0 pts -> expectancy -0.0139 R / 1.672 pts, PF 1.121, total 26.8 pts</small>


### STAR - breakdowns (target 1R, gross)


**Year**

| year | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 6 | 1 | 5 | 0.167 | 0.030 | 0.564 | -0.667 | -12.125 | -72.750 | 0.240 | 18.500 | 11.250 | 15.513 |
| 2022 | 7 | 4 | 3 | 0.571 | 0.250 | 0.842 | 0.143 | 9.571 | 67.000 | 2.170 | 15.929 | 23.250 | 7.627 |
| 2023 | 3 | 3 | 0 | 1.000 | 0.439 | 1.000 | 1.000 | 9.917 | 29.750 | inf | 6.333 | 10.250 | 9.918 |

**Month**

| month | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2021-02 | 1 | 0 | 1 | 0.000 | 0.000 | 0.793 | -1.000 | -28.750 | -28.750 | 0.000 | 30.250 | 4.000 | 4.815 |
| 2021-06 | 1 | 0 | 1 | 0.000 | 0.000 | 0.793 | -1.000 | -4.500 | -4.500 | 0.000 | 4.500 | 1.750 | 4.513 |
| 2021-07 | 2 | 0 | 2 | 0.000 | 0.000 | 0.658 | -1.000 | -17.750 | -35.500 | 0.000 | 18.000 | 11.500 | 22.510 |
| 2021-08 | 1 | 1 | 0 | 1.000 | 0.207 | 1.000 | 1.000 | 23.000 | 23.000 | inf | 13.250 | 23.500 | 16.120 |
| 2021-09 | 1 | 0 | 1 | 0.000 | 0.000 | 0.793 | -1.000 | -27.000 | -27.000 | 0.000 | 27.000 | 15.250 | 18.681 |
| 2022-01 | 1 | 0 | 1 | 0.000 | 0.000 | 0.793 | -1.000 | -22.750 | -22.750 | 0.000 | 22.750 | 21.500 | 6.832 |
| 2022-05 | 2 | 2 | 0 | 1.000 | 0.342 | 1.000 | 1.000 | 35.625 | 71.250 | inf | 23.000 | 36.125 | 17.286 |
| 2022-08 | 1 | 0 | 1 | 0.000 | 0.000 | 0.793 | -1.000 | -19.250 | -19.250 | 0.000 | 20.000 | 8.750 | 28.582 |
| 2022-09 | 2 | 2 | 0 | 1.000 | 0.342 | 1.000 | 1.000 | 26.500 | 53.000 | inf | 3.750 | 26.875 | 4.462 |
| 2022-12 | 1 | 0 | 1 | 0.000 | 0.000 | 0.793 | -1.000 | -15.250 | -15.250 | 0.000 | 15.250 | 6.500 | 7.627 |
| 2023-02 | 1 | 1 | 0 | 1.000 | 0.207 | 1.000 | 1.000 | 12.250 | 12.250 | inf | 9.500 | 12.500 | 9.918 |
| 2023-04 | 1 | 1 | 0 | 1.000 | 0.207 | 1.000 | 1.000 | 10.750 | 10.750 | inf | 6.500 | 11.250 | 5.584 |
| 2023-05 | 1 | 1 | 0 | 1.000 | 0.207 | 1.000 | 1.000 | 6.750 | 6.750 | inf | 3.000 | 7.000 | 10.079 |

**Level family**

| family | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ASIA_H | 3 | 1 | 2 | 0.333 | 0.061 | 0.792 | -0.333 | -7.917 | -23.750 | 0.312 | 13.917 | 8.833 | 7.627 |
| EU_H | 3 | 2 | 1 | 0.667 | 0.208 | 0.939 | 0.333 | 18.250 | 54.750 | 4.042 | 18.000 | 28.917 | 14.750 |
| EU_L | 2 | 1 | 1 | 0.500 | 0.095 | 0.905 | 0.000 | 6.000 | 12.000 | 3.667 | 9.375 | 9.375 | 12.167 |
| PDH | 4 | 2 | 2 | 0.500 | 0.150 | 0.850 | 0.000 | -6.812 | -27.250 | 0.411 | 15.125 | 8.312 | 9.998 |
| PDL | 4 | 2 | 2 | 0.500 | 0.150 | 0.850 | 0.000 | 2.062 | 8.250 | 1.166 | 16.625 | 23.938 | 11.476 |

**Trigger type**

| trigger_type | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| STAR | 16 | 8 | 8 | 0.500 | 0.280 | 0.720 | 0.000 | 1.500 | 24.000 | 1.157 | 15.094 | 16.312 | 9.998 |

**Direction**

| side | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | 9 | 4 | 5 | 0.444 | 0.189 | 0.733 | -0.111 | -2.417 | -21.750 | 0.792 | 14.389 | 16.972 | 14.906 |
| SHORT | 7 | 4 | 3 | 0.571 | 0.250 | 0.842 | 0.143 | 6.536 | 45.750 | 1.943 | 16.000 | 15.464 | 7.627 |

**Session**

| session | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ASIA | 1 | 1 | 0 | 1.000 | 0.207 | 1.000 | 1.000 | 6.750 | 6.750 | inf | 3.000 | 7.000 | 10.079 |
| EU | 4 | 3 | 1 | 0.750 | 0.301 | 0.954 | 0.500 | 12.562 | 50.250 | 3.610 | 10.438 | 19.875 | 12.201 |
| US | 11 | 4 | 7 | 0.364 | 0.152 | 0.646 | -0.273 | -3.000 | -33.000 | 0.753 | 17.886 | 15.864 | 9.918 |

**Fast-Slow time-ratio bucket**

| tr_bucket | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2.0-2.5 | 3 | 0 | 3 | 0.000 | 0.000 | 0.561 | -1.000 | -20.083 | -60.250 | 0.000 | 20.583 | 7.000 | 4.815 |
| 2.5-3.0 | 2 | 1 | 1 | 0.500 | 0.095 | 0.905 | 0.000 | 8.500 | 17.000 | 1.944 | 10.875 | 24.375 | 9.625 |
| >=3.0 | 11 | 7 | 4 | 0.636 | 0.354 | 0.848 | 0.273 | 6.114 | 67.250 | 1.900 | 14.364 | 17.386 | 10.079 |

**09:30-11:30 ET subset**

| metric | value |
|---|---|
| executed trades | 2 |
| trades / trading day | 0.003 |
| long | 1 |
| short | 1 |
| wins | 1 |
| losses | 1 |
| breakevens | 0 |
| win rate | 0.500 |
| win rate 95% CI low | 0.095 |
| win rate 95% CI high | 0.905 |
| break-even win rate | 0.500 |
| p(win rate > break-even), one-sided | 0.750 |
| expectancy (R) | 0.000 |
| expectancy (NQ points) | -2.875 |

## 3. A-B-C candidates rejected before any trigger test

| skip_reason | len |
|---|---|
| AB_TOO_FEW_BARS | 11106 |
| AB_MOVE_TOO_SMALL | 6667 |
| TIME_RATIO_TOO_LOW | 6351 |
| NO_TRIGGER | 1105 |
| AB_TOO_MANY_BARS | 781 |
| DIST_RATIO_OUT_OF_RANGE | 499 |
| LEVEL_BROKEN | 259 |
| BC_TOO_MANY_BARS | 4 |