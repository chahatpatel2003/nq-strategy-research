# Fast-Slow NQ — VALIDATION 2024 (frozen fastslow-1.0.0+5980044a44eebf7b)

* spec version: `fastslow-1.0.0`
* period: **2024-01-01 .. 2024-12-31** (259 Globex trading days with data)
* A-B-C instances examined: **9,336** (rejected by the pattern gates: 8,685)
* A-B-C patterns passing every gate: **651** (of which 485 produced no valid reversal trigger)
* reversal-trigger hits before per-pattern dedup: **176**
* days considered: 259, skipped: `{"ROLL_DAY": 4, "NO_LEVELS": 0, "NO_ATR": 0, "TOO_FEW_BARS": 0}`
* runtime: 2.0s

## 1. Headline matrix - variant x target x round-trip friction

Friction is applied as a flat round-trip cost in NQ points on every trade (entry already pays the modelled first-print slippage on top of this).

| variant | target | friction_pts | trades | win_rate | expectancy_R | expectancy_pts | total_pts | profit_factor | max_dd_R | p_value |
|---|---|---|---|---|---|---|---|---|---|---|
| ANY | 1R | 0.000 | 159 | 0.453 | -0.096 | -0.456 | -72.500 | 0.941 | 18.339 | 0.898 |
| ANY | 1R | 0.500 | 159 | 0.453 | -0.140 | -0.956 | -152.000 | 0.881 | 25.182 | 0.898 |
| ANY | 1R | 1.000 | 159 | 0.453 | -0.184 | -1.456 | -231.500 | 0.824 | 32.026 | 0.898 |
| ANY | 1R | 2.000 | 159 | 0.453 | -0.272 | -2.456 | -390.500 | 0.722 | 45.714 | 0.898 |
| ANY | 2R | 0.000 | 159 | 0.258 | -0.268 | -1.583 | -251.750 | 0.845 | 44.561 | 0.984 |
| ANY | 2R | 0.500 | 159 | 0.258 | -0.312 | -2.083 | -331.250 | 0.803 | 51.526 | 0.984 |
| ANY | 2R | 1.000 | 159 | 0.258 | -0.356 | -2.583 | -410.750 | 0.764 | 58.492 | 0.984 |
| ANY | 2R | 2.000 | 159 | 0.258 | -0.443 | -3.583 | -569.750 | 0.694 | 72.423 | 0.984 |
| ENGULFING | 1R | 0.000 | 60 | 0.450 | -0.100 | 0.271 | 16.250 | 1.030 | 10.014 | 0.817 |
| ENGULFING | 1R | 0.500 | 60 | 0.450 | -0.135 | -0.229 | -13.750 | 0.975 | 11.420 | 0.817 |
| ENGULFING | 1R | 1.000 | 60 | 0.450 | -0.171 | -0.729 | -43.750 | 0.923 | 13.089 | 0.817 |
| ENGULFING | 1R | 2.000 | 60 | 0.450 | -0.241 | -1.729 | -103.750 | 0.827 | 17.164 | 0.817 |
| ENGULFING | 2R | 0.000 | 60 | 0.300 | -0.153 | -2.304 | -138.250 | 0.811 | 13.178 | 0.750 |
| ENGULFING | 2R | 0.500 | 60 | 0.300 | -0.188 | -2.804 | -168.250 | 0.777 | 14.949 | 0.750 |
| ENGULFING | 2R | 1.000 | 60 | 0.300 | -0.223 | -3.304 | -198.250 | 0.744 | 16.720 | 0.750 |
| ENGULFING | 2R | 2.000 | 60 | 0.300 | -0.294 | -4.304 | -258.250 | 0.684 | 20.263 | 0.750 |
| PIN | 1R | 0.000 | 105 | 0.467 | -0.070 | -0.114 | -12.000 | 0.983 | 11.246 | 0.782 |
| PIN | 1R | 0.500 | 105 | 0.467 | -0.118 | -0.614 | -64.500 | 0.913 | 13.831 | 0.782 |
| PIN | 1R | 1.000 | 105 | 0.467 | -0.167 | -1.114 | -117.000 | 0.848 | 18.387 | 0.782 |
| PIN | 1R | 2.000 | 105 | 0.467 | -0.264 | -2.114 | -222.000 | 0.731 | 28.450 | 0.782 |
| PIN | 2R | 0.000 | 105 | 0.238 | -0.318 | -1.126 | -118.250 | 0.877 | 35.383 | 0.987 |
| PIN | 2R | 0.500 | 105 | 0.238 | -0.366 | -1.626 | -170.750 | 0.830 | 40.312 | 0.987 |
| PIN | 2R | 1.000 | 105 | 0.238 | -0.415 | -2.126 | -223.250 | 0.786 | 45.242 | 0.987 |
| PIN | 2R | 2.000 | 105 | 0.238 | -0.512 | -3.126 | -328.250 | 0.708 | 55.101 | 0.987 |
| STAR | 1R | 0.000 | 4 | 0.500 | 0.000 | -5.000 | -20.000 | 0.604 | 2.000 | 0.688 |
| STAR | 1R | 0.500 | 4 | 0.500 | -0.030 | -5.500 | -22.000 | 0.573 | 2.047 | 0.688 |
| STAR | 1R | 1.000 | 4 | 0.500 | -0.061 | -6.000 | -24.000 | 0.543 | 2.094 | 0.688 |
| STAR | 1R | 2.000 | 4 | 0.500 | -0.121 | -7.000 | -28.000 | 0.486 | 2.188 | 0.688 |
| STAR | 2R | 0.000 | 4 | 0.500 | 0.500 | 2.625 | 10.500 | 1.208 | 2.000 | 0.407 |
| STAR | 2R | 0.500 | 4 | 0.500 | 0.470 | 2.125 | 8.500 | 1.165 | 2.047 | 0.407 |
| STAR | 2R | 1.000 | 4 | 0.500 | 0.439 | 1.625 | 6.500 | 1.124 | 2.094 | 0.407 |
| STAR | 2R | 2.000 | 4 | 0.500 | 0.379 | 0.625 | 2.500 | 1.046 | 2.188 | 0.407 |


## 2.1 Variant `ANY`

* signals generated: **166** | accepted: **159** | skipped: **7**

Skip reasons:

| skip_reason | len |
|---|---|
| CONCURRENT_POSITION | 7 |

* 09:30-11:30 ET trades: **34** (0.131 / trading day)

### ANY - target 1R (primary) - GROSS (0.0 pts friction)

| metric | value |
|---|---|
| executed trades | 159 |
| trades / trading day | 0.614 |
| long | 62 |
| short | 97 |
| wins | 72 |
| losses | 87 |
| breakevens | 0 |
| win rate | 0.453 |
| win rate 95% CI low | 0.377 |
| win rate 95% CI high | 0.530 |
| break-even win rate | 0.500 |
| p(win rate > break-even), one-sided | 0.898 |
| expectancy (R) | -0.096 |
| expectancy (NQ points) | -0.456 |
| average R | -0.096 |
| total points | -72.500 |
| total R | -15.339 |
| profit factor | 0.941 |
| average winner (pts) | 16.104 |
| average loser (pts) | -14.161 |
| median winner (pts) | 13.375 |
| median loser (pts) | -13.500 |
| max drawdown (R) | 18.339 |
| max drawdown (pts) | 186.500 |
| longest winning streak | 6 |
| longest losing streak | 8 |
| average MAE (pts) | 10.821 |
| median MAE (pts) | 9.250 |
| average MFE (pts) | 10.527 |
| median MFE (pts) | 8.000 |
| average hold (min) | 8.279 |
| median hold (min) | 4.564 |
| average R distance (pts) | 15.053 |
| TP exits | 71 |
| SL exits | 87 |
| timeout exits | 1 |
| t-stat of mean R | -1.219 |

<small>friction 0.5 pts -> expectancy -0.1404 R / -0.956 pts, PF 0.881, total -152.0 pts</small>


<small>friction 1.0 pts -> expectancy -0.1844 R / -1.456 pts, PF 0.824, total -231.5 pts</small>


<small>friction 2.0 pts -> expectancy -0.2723 R / -2.456 pts, PF 0.722, total -390.5 pts</small>


### ANY - target 2R (secondary) - GROSS (0.0 pts friction)

| metric | value |
|---|---|
| executed trades | 159 |
| trades / trading day | 0.614 |
| long | 62 |
| short | 97 |
| wins | 41 |
| losses | 118 |
| breakevens | 0 |
| win rate | 0.258 |
| win rate 95% CI low | 0.196 |
| win rate 95% CI high | 0.331 |
| break-even win rate | 0.333 |
| p(win rate > break-even), one-sided | 0.984 |
| expectancy (R) | -0.268 |
| expectancy (NQ points) | -1.583 |
| average R | -0.268 |
| total points | -251.750 |
| total R | -42.561 |
| profit factor | 0.845 |
| average winner (pts) | 33.476 |
| average loser (pts) | -13.765 |
| median winner (pts) | 30.000 |
| median loser (pts) | -12.000 |
| max drawdown (R) | 44.561 |
| max drawdown (pts) | 442.750 |
| longest winning streak | 4 |
| longest losing streak | 10 |
| average MAE (pts) | 12.736 |
| median MAE (pts) | 11.000 |
| average MFE (pts) | 16.020 |
| median MFE (pts) | 9.500 |
| average hold (min) | 18.101 |
| median hold (min) | 7.186 |
| average R distance (pts) | 15.053 |
| TP exits | 36 |
| SL exits | 118 |
| timeout exits | 5 |
| t-stat of mean R | -2.663 |

<small>friction 0.5 pts -> expectancy -0.3116 R / -2.083 pts, PF 0.803, total -331.2 pts</small>


<small>friction 1.0 pts -> expectancy -0.3556 R / -2.583 pts, PF 0.764, total -410.8 pts</small>


<small>friction 2.0 pts -> expectancy -0.4435 R / -3.583 pts, PF 0.694, total -569.8 pts</small>


### ANY - breakdowns (target 1R, gross)


**Year**

| year | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024 | 159 | 72 | 87 | 0.453 | 0.377 | 0.530 | -0.096 | -0.456 | -72.500 | 0.941 | 10.821 | 10.527 | 4.564 |

**Month**

| month | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024-01 | 16 | 8 | 8 | 0.500 | 0.280 | 0.720 | 0.000 | 1.531 | 24.500 | 1.202 | 11.953 | 13.656 | 6.112 |
| 2024-02 | 19 | 8 | 11 | 0.421 | 0.231 | 0.637 | -0.158 | -0.987 | -18.750 | 0.816 | 6.632 | 6.434 | 2.352 |
| 2024-03 | 11 | 4 | 7 | 0.364 | 0.152 | 0.646 | -0.273 | -0.977 | -10.750 | 0.866 | 10.455 | 9.455 | 4.610 |
| 2024-04 | 9 | 4 | 5 | 0.444 | 0.189 | 0.733 | -0.111 | -2.750 | -24.750 | 0.693 | 11.500 | 10.833 | 4.426 |
| 2024-05 | 8 | 4 | 4 | 0.500 | 0.215 | 0.785 | -0.031 | -0.938 | -7.500 | 0.878 | 10.281 | 10.969 | 5.614 |
| 2024-06 | 27 | 11 | 16 | 0.407 | 0.245 | 0.593 | -0.185 | -0.954 | -25.750 | 0.877 | 11.148 | 10.157 | 4.564 |
| 2024-07 | 9 | 4 | 5 | 0.444 | 0.189 | 0.733 | -0.111 | 0.222 | 2.000 | 1.029 | 10.889 | 10.111 | 5.209 |
| 2024-08 | 12 | 7 | 5 | 0.583 | 0.320 | 0.807 | 0.162 | 4.042 | 48.500 | 1.624 | 11.125 | 13.104 | 6.607 |
| 2024-09 | 14 | 8 | 6 | 0.571 | 0.326 | 0.786 | 0.143 | 2.679 | 37.500 | 1.386 | 11.054 | 11.339 | 3.743 |
| 2024-10 | 20 | 9 | 11 | 0.450 | 0.258 | 0.658 | -0.102 | -1.038 | -20.750 | 0.876 | 10.287 | 11.325 | 3.370 |
| 2024-11 | 10 | 3 | 7 | 0.300 | 0.108 | 0.603 | -0.400 | -6.600 | -66.000 | 0.499 | 17.050 | 9.150 | 3.756 |
| 2024-12 | 4 | 2 | 2 | 0.500 | 0.150 | 0.850 | 0.000 | -2.688 | -10.750 | 0.674 | 9.750 | 11.125 | 4.277 |

**Level family**

| family | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ASIA_H | 26 | 8 | 18 | 0.308 | 0.165 | 0.500 | -0.394 | -3.192 | -83.000 | 0.631 | 12.077 | 8.827 | 4.617 |
| ASIA_L | 26 | 12 | 14 | 0.462 | 0.288 | 0.645 | -0.077 | -1.087 | -28.250 | 0.861 | 10.942 | 9.288 | 4.360 |
| EU_H | 19 | 10 | 9 | 0.526 | 0.317 | 0.727 | 0.052 | 1.882 | 35.750 | 1.249 | 11.671 | 13.066 | 6.005 |
| EU_L | 29 | 13 | 16 | 0.448 | 0.284 | 0.625 | -0.103 | 1.603 | 46.500 | 1.208 | 11.388 | 13.121 | 2.889 |
| PDH | 23 | 9 | 14 | 0.391 | 0.222 | 0.592 | -0.219 | -3.467 | -79.750 | 0.525 | 8.022 | 7.033 | 3.885 |
| PDL | 15 | 8 | 7 | 0.533 | 0.301 | 0.752 | 0.067 | -0.367 | -5.500 | 0.956 | 11.567 | 11.467 | 5.173 |
| US_H | 18 | 12 | 6 | 0.667 | 0.437 | 0.837 | 0.331 | 5.000 | 90.000 | 1.928 | 9.097 | 12.917 | 4.299 |
| US_L | 3 | 0 | 3 | 0.000 | 0.000 | 0.561 | -1.000 | -16.083 | -48.250 | 0.000 | 16.083 | 2.583 | 2.298 |

**Trigger type**

| trigger_type | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ENGULFING | 52 | 23 | 29 | 0.442 | 0.316 | 0.577 | -0.116 | -0.192 | -10.000 | 0.979 | 13.178 | 12.543 | 5.843 |
| PIN | 105 | 49 | 56 | 0.467 | 0.374 | 0.562 | -0.070 | -0.114 | -12.000 | 0.983 | 9.367 | 9.379 | 3.012 |
| STAR | 2 | 0 | 2 | 0.000 | 0.000 | 0.658 | -1.000 | -25.250 | -50.500 | 0.000 | 25.875 | 18.375 | 14.858 |

**Direction**

| side | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | 62 | 27 | 35 | 0.435 | 0.319 | 0.559 | -0.130 | -0.149 | -9.250 | 0.983 | 12.964 | 12.512 | 5.000 |
| SHORT | 97 | 45 | 52 | 0.464 | 0.368 | 0.563 | -0.075 | -0.652 | -63.250 | 0.906 | 9.451 | 9.258 | 3.719 |

**Session**

| session | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ASIA | 14 | 7 | 7 | 0.500 | 0.268 | 0.732 | -0.005 | -0.589 | -8.250 | 0.906 | 8.232 | 7.625 | 8.360 |
| EU | 26 | 10 | 16 | 0.385 | 0.224 | 0.575 | -0.232 | -2.510 | -65.250 | 0.620 | 7.923 | 6.144 | 4.979 |
| POST | 5 | 1 | 4 | 0.200 | 0.036 | 0.624 | -0.649 | -6.050 | -30.250 | 0.262 | 9.200 | 3.700 | 3.013 |
| US | 114 | 54 | 60 | 0.474 | 0.384 | 0.565 | -0.053 | 0.274 | 31.250 | 1.034 | 11.871 | 12.182 | 4.176 |

**Fast-Slow time-ratio bucket**

| tr_bucket | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2.0-2.5 | 45 | 15 | 30 | 0.333 | 0.214 | 0.479 | -0.340 | -4.556 | -205.000 | 0.545 | 12.294 | 9.561 | 4.623 |
| 2.5-3.0 | 27 | 14 | 13 | 0.519 | 0.340 | 0.693 | 0.036 | 1.861 | 50.250 | 1.266 | 10.352 | 12.796 | 4.239 |
| >=3.0 | 87 | 43 | 44 | 0.494 | 0.392 | 0.597 | -0.012 | 0.945 | 82.250 | 1.139 | 10.204 | 10.322 | 4.105 |

**09:30-11:30 ET subset**

| metric | value |
|---|---|
| executed trades | 34 |
| trades / trading day | 0.131 |
| long | 10 |
| short | 24 |
| wins | 20 |
| losses | 14 |
| breakevens | 0 |
| win rate | 0.588 |
| win rate 95% CI low | 0.422 |
| win rate 95% CI high | 0.736 |
| break-even win rate | 0.500 |
| p(win rate > break-even), one-sided | 0.196 |
| expectancy (R) | 0.176 |
| expectancy (NQ points) | 2.735 |

## 2.2 Variant `ENGULFING`

* signals generated: **61** | accepted: **60** | skipped: **1**

Skip reasons:

| skip_reason | len |
|---|---|
| CONCURRENT_POSITION | 1 |

* 09:30-11:30 ET trades: **12** (0.046 / trading day)

### ENGULFING - target 1R (primary) - GROSS (0.0 pts friction)

| metric | value |
|---|---|
| executed trades | 60 |
| trades / trading day | 0.232 |
| long | 21 |
| short | 39 |
| wins | 27 |
| losses | 33 |
| breakevens | 0 |
| win rate | 0.450 |
| win rate 95% CI low | 0.331 |
| win rate 95% CI high | 0.575 |
| break-even win rate | 0.500 |
| p(win rate > break-even), one-sided | 0.817 |
| expectancy (R) | -0.100 |
| expectancy (NQ points) | 0.271 |
| average R | -0.100 |
| total points | 16.250 |
| total R | -6.014 |
| profit factor | 1.030 |
| average winner (pts) | 20.343 |
| average loser (pts) | -16.152 |
| median winner (pts) | 17.750 |
| median loser (pts) | -15.250 |
| max drawdown (R) | 10.014 |
| max drawdown (pts) | 91.250 |
| longest winning streak | 3 |
| longest losing streak | 4 |
| average MAE (pts) | 13.025 |
| median MAE (pts) | 11.500 |
| average MFE (pts) | 12.758 |
| median MFE (pts) | 10.125 |
| average hold (min) | 11.516 |
| median hold (min) | 7.253 |
| average R distance (pts) | 18.033 |
| TP exits | 27 |
| SL exits | 33 |
| timeout exits | 0 |
| t-stat of mean R | -0.774 |

<small>friction 0.5 pts -> expectancy -0.1354 R / -0.229 pts, PF 0.975, total -13.8 pts</small>


<small>friction 1.0 pts -> expectancy -0.1705 R / -0.729 pts, PF 0.923, total -43.8 pts</small>


<small>friction 2.0 pts -> expectancy -0.2409 R / -1.729 pts, PF 0.827, total -103.8 pts</small>


### ENGULFING - target 2R (secondary) - GROSS (0.0 pts friction)

| metric | value |
|---|---|
| executed trades | 60 |
| trades / trading day | 0.232 |
| long | 21 |
| short | 39 |
| wins | 18 |
| losses | 42 |
| breakevens | 0 |
| win rate | 0.300 |
| win rate 95% CI low | 0.199 |
| win rate 95% CI high | 0.425 |
| break-even win rate | 0.333 |
| p(win rate > break-even), one-sided | 0.750 |
| expectancy (R) | -0.153 |
| expectancy (NQ points) | -2.304 |
| average R | -0.153 |
| total points | -138.250 |
| total R | -9.178 |
| profit factor | 0.811 |
| average winner (pts) | 33.028 |
| average loser (pts) | -17.446 |
| median winner (pts) | 35.250 |
| median loser (pts) | -15.500 |
| max drawdown (R) | 13.178 |
| max drawdown (pts) | 201.750 |
| longest winning streak | 2 |
| longest losing streak | 7 |
| average MAE (pts) | 15.196 |
| median MAE (pts) | 13.000 |
| average MFE (pts) | 20.483 |
| median MFE (pts) | 10.875 |
| average hold (min) | 27.894 |
| median hold (min) | 13.838 |
| average R distance (pts) | 18.033 |
| TP exits | 16 |
| SL exits | 42 |
| timeout exits | 2 |
| t-stat of mean R | -0.888 |

<small>friction 0.5 pts -> expectancy -0.1881 R / -2.804 pts, PF 0.777, total -168.2 pts</small>


<small>friction 1.0 pts -> expectancy -0.2233 R / -3.304 pts, PF 0.744, total -198.2 pts</small>


<small>friction 2.0 pts -> expectancy -0.2936 R / -4.304 pts, PF 0.684, total -258.2 pts</small>


### ENGULFING - breakdowns (target 1R, gross)


**Year**

| year | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024 | 60 | 27 | 33 | 0.450 | 0.331 | 0.575 | -0.100 | 0.271 | 16.250 | 1.030 | 13.025 | 12.758 | 7.253 |

**Month**

| month | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024-01 | 9 | 4 | 5 | 0.444 | 0.189 | 0.733 | -0.111 | 2.833 | 25.500 | 1.283 | 16.528 | 19.333 | 11.499 |
| 2024-02 | 9 | 3 | 6 | 0.333 | 0.121 | 0.646 | -0.333 | -3.528 | -31.750 | 0.594 | 9.972 | 7.417 | 3.835 |
| 2024-03 | 3 | 2 | 1 | 0.667 | 0.208 | 0.939 | 0.333 | 15.417 | 46.250 | 6.968 | 10.500 | 20.833 | 7.194 |
| 2024-04 | 4 | 1 | 3 | 0.250 | 0.046 | 0.699 | -0.500 | -7.000 | -28.000 | 0.263 | 12.062 | 5.688 | 5.215 |
| 2024-05 | 3 | 2 | 1 | 0.667 | 0.208 | 0.939 | 0.333 | 5.667 | 17.000 | 2.417 | 7.667 | 12.167 | 3.335 |
| 2024-06 | 7 | 3 | 4 | 0.429 | 0.158 | 0.750 | -0.143 | 0.714 | 5.000 | 1.084 | 14.179 | 14.750 | 15.505 |
| 2024-07 | 4 | 1 | 3 | 0.250 | 0.046 | 0.699 | -0.500 | -5.125 | -20.500 | 0.619 | 15.438 | 12.812 | 5.388 |
| 2024-08 | 5 | 3 | 2 | 0.600 | 0.231 | 0.882 | 0.197 | 5.050 | 25.250 | 1.515 | 18.050 | 18.850 | 15.313 |
| 2024-09 | 5 | 3 | 2 | 0.600 | 0.231 | 0.882 | 0.200 | 3.650 | 18.250 | 1.760 | 7.650 | 9.850 | 10.720 |
| 2024-10 | 5 | 3 | 2 | 0.600 | 0.231 | 0.882 | 0.200 | 0.650 | 3.250 | 1.075 | 11.850 | 12.750 | 4.788 |
| 2024-11 | 5 | 1 | 4 | 0.200 | 0.036 | 0.624 | -0.600 | -11.400 | -57.000 | 0.257 | 17.550 | 5.550 | 2.298 |
| 2024-12 | 1 | 1 | 0 | 1.000 | 0.207 | 1.000 | 1.000 | 13.000 | 13.000 | inf | 3.750 | 13.500 | 4.669 |

**Level family**

| family | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ASIA_H | 8 | 0 | 8 | 0.000 | 0.000 | 0.324 | -1.000 | -14.594 | -116.750 | 0.000 | 15.094 | 4.938 | 6.403 |
| ASIA_L | 7 | 4 | 3 | 0.571 | 0.250 | 0.842 | 0.143 | 1.179 | 8.250 | 1.136 | 12.036 | 13.464 | 5.209 |
| EU_H | 11 | 7 | 4 | 0.636 | 0.354 | 0.848 | 0.273 | 3.818 | 42.000 | 1.618 | 9.773 | 13.864 | 6.005 |
| EU_L | 12 | 7 | 5 | 0.583 | 0.320 | 0.807 | 0.167 | 11.812 | 141.750 | 3.476 | 12.000 | 18.250 | 5.370 |
| PDH | 9 | 2 | 7 | 0.222 | 0.063 | 0.547 | -0.556 | -9.167 | -82.500 | 0.311 | 16.056 | 10.944 | 14.529 |
| PDL | 6 | 5 | 1 | 0.833 | 0.436 | 0.970 | 0.667 | 11.500 | 69.000 | 4.680 | 10.250 | 16.042 | 14.049 |
| US_H | 6 | 2 | 4 | 0.333 | 0.097 | 0.700 | -0.336 | -2.542 | -15.250 | 0.752 | 14.792 | 10.833 | 6.050 |
| US_L | 1 | 0 | 1 | 0.000 | 0.000 | 0.793 | -1.000 | -30.250 | -30.250 | 0.000 | 30.250 | 0.500 | 2.298 |

**Trigger type**

| trigger_type | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ENGULFING | 60 | 27 | 33 | 0.450 | 0.331 | 0.575 | -0.100 | 0.271 | 16.250 | 1.030 | 13.025 | 12.758 | 7.253 |

**Direction**

| side | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | 21 | 11 | 10 | 0.524 | 0.324 | 0.717 | 0.047 | 3.929 | 82.500 | 1.474 | 13.643 | 15.238 | 7.674 |
| SHORT | 39 | 16 | 23 | 0.410 | 0.271 | 0.566 | -0.179 | -1.699 | -66.250 | 0.815 | 12.692 | 11.423 | 7.194 |

**Session**

| session | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ASIA | 5 | 3 | 2 | 0.600 | 0.231 | 0.882 | 0.200 | 1.950 | 9.750 | 1.406 | 7.750 | 7.350 | 10.720 |
| EU | 11 | 5 | 6 | 0.455 | 0.213 | 0.720 | -0.092 | -0.114 | -1.250 | 0.983 | 8.523 | 9.977 | 8.184 |
| POST | 3 | 0 | 3 | 0.000 | 0.000 | 0.561 | -1.000 | -11.167 | -33.500 | 0.000 | 11.250 | 2.333 | 3.013 |
| US | 41 | 19 | 22 | 0.463 | 0.321 | 0.613 | -0.073 | 1.006 | 41.250 | 1.103 | 15.006 | 14.927 | 5.568 |

**Fast-Slow time-ratio bucket**

| tr_bucket | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2.0-2.5 | 15 | 3 | 12 | 0.200 | 0.070 | 0.452 | -0.600 | -9.250 | -138.750 | 0.303 | 14.983 | 8.083 | 5.058 |
| 2.5-3.0 | 13 | 8 | 5 | 0.615 | 0.355 | 0.823 | 0.231 | 7.327 | 95.250 | 2.165 | 11.000 | 16.654 | 8.184 |
| >=3.0 | 32 | 16 | 16 | 0.500 | 0.336 | 0.664 | -0.000 | 1.867 | 59.750 | 1.237 | 12.930 | 13.367 | 8.168 |

**09:30-11:30 ET subset**

| metric | value |
|---|---|
| executed trades | 12 |
| trades / trading day | 0.046 |
| long | 3 |
| short | 9 |
| wins | 7 |
| losses | 5 |
| breakevens | 0 |
| win rate | 0.583 |
| win rate 95% CI low | 0.320 |
| win rate 95% CI high | 0.807 |
| break-even win rate | 0.500 |
| p(win rate > break-even), one-sided | 0.387 |
| expectancy (R) | 0.167 |
| expectancy (NQ points) | 4.521 |

## 2.3 Variant `PIN`

* signals generated: **111** | accepted: **105** | skipped: **6**

Skip reasons:

| skip_reason | len |
|---|---|
| CONCURRENT_POSITION | 6 |

* 09:30-11:30 ET trades: **20** (0.077 / trading day)

### PIN - target 1R (primary) - GROSS (0.0 pts friction)

| metric | value |
|---|---|
| executed trades | 105 |
| trades / trading day | 0.405 |
| long | 43 |
| short | 62 |
| wins | 49 |
| losses | 56 |
| breakevens | 0 |
| win rate | 0.467 |
| win rate 95% CI low | 0.374 |
| win rate 95% CI high | 0.562 |
| break-even win rate | 0.500 |
| p(win rate > break-even), one-sided | 0.782 |
| expectancy (R) | -0.070 |
| expectancy (NQ points) | -0.114 |
| average R | -0.070 |
| total points | -12.000 |
| total R | -7.325 |
| profit factor | 0.983 |
| average winner (pts) | 14.311 |
| average loser (pts) | -12.737 |
| median winner (pts) | 11.000 |
| median loser (pts) | -11.250 |
| max drawdown (R) | 11.246 |
| max drawdown (pts) | 135.750 |
| longest winning streak | 4 |
| longest losing streak | 6 |
| average MAE (pts) | 9.367 |
| median MAE (pts) | 7.750 |
| average MFE (pts) | 9.379 |
| median MFE (pts) | 7.250 |
| average hold (min) | 7.193 |
| median hold (min) | 3.012 |
| average R distance (pts) | 13.493 |
| TP exits | 48 |
| SL exits | 56 |
| timeout exits | 1 |
| t-stat of mean R | -0.714 |

<small>friction 0.5 pts -> expectancy -0.1183 R / -0.614 pts, PF 0.913, total -64.5 pts</small>


<small>friction 1.0 pts -> expectancy -0.1669 R / -1.114 pts, PF 0.848, total -117.0 pts</small>


<small>friction 2.0 pts -> expectancy -0.2640 R / -2.114 pts, PF 0.731, total -222.0 pts</small>


### PIN - target 2R (secondary) - GROSS (0.0 pts friction)

| metric | value |
|---|---|
| executed trades | 105 |
| trades / trading day | 0.405 |
| long | 43 |
| short | 62 |
| wins | 25 |
| losses | 80 |
| breakevens | 0 |
| win rate | 0.238 |
| win rate 95% CI low | 0.167 |
| win rate 95% CI high | 0.328 |
| break-even win rate | 0.333 |
| p(win rate > break-even), one-sided | 0.987 |
| expectancy (R) | -0.318 |
| expectancy (NQ points) | -1.126 |
| average R | -0.318 |
| total points | -118.250 |
| total R | -33.383 |
| profit factor | 0.877 |
| average winner (pts) | 33.800 |
| average loser (pts) | -12.041 |
| median winner (pts) | 27.500 |
| median loser (pts) | -10.250 |
| max drawdown (R) | 35.383 |
| max drawdown (pts) | 365.250 |
| longest winning streak | 3 |
| longest losing streak | 10 |
| average MAE (pts) | 11.319 |
| median MAE (pts) | 9.750 |
| average MFE (pts) | 14.017 |
| median MFE (pts) | 8.500 |
| average hold (min) | 14.232 |
| median hold (min) | 5.618 |
| average R distance (pts) | 13.493 |
| TP exits | 22 |
| SL exits | 80 |
| timeout exits | 3 |
| t-stat of mean R | -2.626 |

<small>friction 0.5 pts -> expectancy -0.3665 R / -1.626 pts, PF 0.830, total -170.8 pts</small>


<small>friction 1.0 pts -> expectancy -0.4150 R / -2.126 pts, PF 0.786, total -223.2 pts</small>


<small>friction 2.0 pts -> expectancy -0.5121 R / -3.126 pts, PF 0.708, total -328.2 pts</small>


### PIN - breakdowns (target 1R, gross)


**Year**

| year | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024 | 105 | 49 | 56 | 0.467 | 0.374 | 0.562 | -0.070 | -0.114 | -12.000 | 0.983 | 9.367 | 9.379 | 3.012 |

**Month**

| month | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024-01 | 7 | 4 | 3 | 0.571 | 0.250 | 0.842 | 0.143 | -0.143 | -1.000 | 0.968 | 6.071 | 6.357 | 0.946 |
| 2024-02 | 12 | 6 | 6 | 0.500 | 0.254 | 0.746 | 0.000 | 0.875 | 10.500 | 1.249 | 4.667 | 6.042 | 1.689 |
| 2024-03 | 9 | 2 | 7 | 0.222 | 0.063 | 0.547 | -0.556 | -7.194 | -64.750 | 0.196 | 10.139 | 5.444 | 3.249 |
| 2024-04 | 5 | 3 | 2 | 0.600 | 0.231 | 0.882 | 0.200 | 0.650 | 3.250 | 1.076 | 11.050 | 14.950 | 1.715 |
| 2024-05 | 5 | 2 | 3 | 0.400 | 0.118 | 0.769 | -0.249 | -4.900 | -24.500 | 0.505 | 11.850 | 10.250 | 7.186 |
| 2024-06 | 22 | 10 | 12 | 0.455 | 0.269 | 0.653 | -0.091 | 0.830 | 18.250 | 1.128 | 9.739 | 9.489 | 3.949 |
| 2024-07 | 5 | 3 | 2 | 0.600 | 0.231 | 0.882 | 0.200 | 4.500 | 22.500 | 2.500 | 7.250 | 7.950 | 2.377 |
| 2024-08 | 9 | 5 | 4 | 0.556 | 0.267 | 0.811 | 0.107 | 2.889 | 26.000 | 1.439 | 9.361 | 11.944 | 6.091 |
| 2024-09 | 9 | 5 | 4 | 0.556 | 0.267 | 0.811 | 0.111 | 2.139 | 19.250 | 1.263 | 12.944 | 12.167 | 1.507 |
| 2024-10 | 14 | 6 | 8 | 0.429 | 0.214 | 0.674 | -0.146 | 0.804 | 11.250 | 1.126 | 7.857 | 9.464 | 2.481 |
| 2024-11 | 5 | 2 | 3 | 0.400 | 0.118 | 0.769 | -0.200 | -1.800 | -9.000 | 0.836 | 16.550 | 12.750 | 5.576 |
| 2024-12 | 3 | 1 | 2 | 0.333 | 0.061 | 0.792 | -0.333 | -7.917 | -23.750 | 0.280 | 11.750 | 10.333 | 3.885 |

**Level family**

| family | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ASIA_H | 19 | 8 | 11 | 0.421 | 0.231 | 0.637 | -0.171 | 0.803 | 15.250 | 1.121 | 11.158 | 10.039 | 2.527 |
| ASIA_L | 19 | 8 | 11 | 0.421 | 0.231 | 0.637 | -0.159 | -1.921 | -36.500 | 0.743 | 10.539 | 7.750 | 3.249 |
| EU_H | 8 | 3 | 5 | 0.375 | 0.137 | 0.694 | -0.252 | -0.781 | -6.250 | 0.917 | 14.281 | 11.969 | 6.613 |
| EU_L | 18 | 8 | 10 | 0.444 | 0.246 | 0.663 | -0.111 | -0.597 | -10.750 | 0.918 | 8.889 | 10.056 | 1.201 |
| PDH | 18 | 8 | 10 | 0.444 | 0.246 | 0.663 | -0.113 | -1.069 | -19.250 | 0.796 | 5.917 | 6.000 | 3.234 |
| PDL | 9 | 3 | 6 | 0.333 | 0.121 | 0.646 | -0.333 | -8.278 | -74.500 | 0.292 | 12.444 | 8.417 | 1.395 |
| US_H | 13 | 11 | 2 | 0.846 | 0.578 | 0.957 | 0.690 | 9.442 | 122.750 | 4.458 | 5.827 | 14.269 | 4.173 |
| US_L | 1 | 0 | 1 | 0.000 | 0.000 | 0.793 | -1.000 | -2.750 | -2.750 | 0.000 | 2.750 | 0.750 | 0.172 |

**Trigger type**

| trigger_type | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PIN | 105 | 49 | 56 | 0.467 | 0.374 | 0.562 | -0.070 | -0.114 | -12.000 | 0.983 | 9.367 | 9.379 | 3.012 |

**Direction**

| side | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | 43 | 19 | 24 | 0.442 | 0.304 | 0.589 | -0.117 | 0.238 | 10.250 | 1.029 | 11.436 | 11.471 | 4.179 |
| SHORT | 62 | 30 | 32 | 0.484 | 0.364 | 0.606 | -0.037 | -0.359 | -22.250 | 0.939 | 7.931 | 7.927 | 2.557 |

**Session**

| session | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ASIA | 10 | 4 | 6 | 0.400 | 0.168 | 0.687 | -0.207 | -2.600 | -26.000 | 0.639 | 8.450 | 7.175 | 5.623 |
| EU | 17 | 6 | 11 | 0.353 | 0.173 | 0.587 | -0.295 | -3.191 | -54.250 | 0.483 | 7.103 | 4.441 | 3.249 |
| POST | 2 | 1 | 1 | 0.500 | 0.095 | 0.905 | -0.123 | 1.625 | 3.250 | 1.433 | 6.125 | 5.750 | 19.670 |
| US | 76 | 38 | 38 | 0.500 | 0.390 | 0.610 | 0.000 | 0.855 | 65.000 | 1.123 | 10.079 | 10.868 | 2.442 |

**Fast-Slow time-ratio bucket**

| tr_bucket | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2.0-2.5 | 33 | 13 | 20 | 0.394 | 0.247 | 0.563 | -0.221 | -2.280 | -75.250 | 0.730 | 10.788 | 9.985 | 4.564 |
| 2.5-3.0 | 15 | 8 | 7 | 0.533 | 0.301 | 0.752 | 0.065 | 1.300 | 19.500 | 1.213 | 8.767 | 11.483 | 4.173 |
| >=3.0 | 57 | 28 | 29 | 0.491 | 0.366 | 0.617 | -0.018 | 0.768 | 43.750 | 1.128 | 8.702 | 8.474 | 2.527 |

**09:30-11:30 ET subset**

| metric | value |
|---|---|
| executed trades | 20 |
| trades / trading day | 0.077 |
| long | 6 |
| short | 14 |
| wins | 13 |
| losses | 7 |
| breakevens | 0 |
| win rate | 0.650 |
| win rate 95% CI low | 0.433 |
| win rate 95% CI high | 0.819 |
| break-even win rate | 0.500 |
| p(win rate > break-even), one-sided | 0.132 |
| expectancy (R) | 0.300 |
| expectancy (NQ points) | 4.463 |

## 2.4 Variant `STAR`

* signals generated: **4** | accepted: **4** | skipped: **0**

* 09:30-11:30 ET trades: **3** (0.012 / trading day)

### STAR - target 1R (primary) - GROSS (0.0 pts friction)

| metric | value |
|---|---|
| executed trades | 4 |
| trades / trading day | 0.015 |
| long | 2 |
| short | 2 |
| wins | 2 |
| losses | 2 |
| breakevens | 0 |
| win rate | 0.500 |
| win rate 95% CI low | 0.150 |
| win rate 95% CI high | 0.850 |
| break-even win rate | 0.500 |
| p(win rate > break-even), one-sided | 0.688 |
| expectancy (R) | 0.000 |
| expectancy (NQ points) | -5.000 |
| average R | 0.000 |
| total points | -20.000 |
| total R | 0.000 |
| profit factor | 0.604 |
| average winner (pts) | 15.250 |
| average loser (pts) | -25.250 |
| median winner (pts) | 15.250 |
| median loser (pts) | -25.250 |
| max drawdown (R) | 2.000 |
| max drawdown (pts) | 50.500 |
| longest winning streak | 2 |
| longest losing streak | 2 |
| average MAE (pts) | 15.438 |
| median MAE (pts) | 12.375 |
| average MFE (pts) | 17.000 |
| median MFE (pts) | 15.625 |
| average hold (min) | 9.213 |
| median hold (min) | 3.614 |
| average R distance (pts) | 20.250 |
| TP exits | 2 |
| SL exits | 2 |
| timeout exits | 0 |
| t-stat of mean R | 0.000 |

<small>friction 0.5 pts -> expectancy -0.0303 R / -5.500 pts, PF 0.573, total -22.0 pts</small>


<small>friction 1.0 pts -> expectancy -0.0607 R / -6.000 pts, PF 0.543, total -24.0 pts</small>


<small>friction 2.0 pts -> expectancy -0.1214 R / -7.000 pts, PF 0.486, total -28.0 pts</small>


### STAR - target 2R (secondary) - GROSS (0.0 pts friction)

| metric | value |
|---|---|
| executed trades | 4 |
| trades / trading day | 0.015 |
| long | 2 |
| short | 2 |
| wins | 2 |
| losses | 2 |
| breakevens | 0 |
| win rate | 0.500 |
| win rate 95% CI low | 0.150 |
| win rate 95% CI high | 0.850 |
| break-even win rate | 0.333 |
| p(win rate > break-even), one-sided | 0.407 |
| expectancy (R) | 0.500 |
| expectancy (NQ points) | 2.625 |
| average R | 0.500 |
| total points | 10.500 |
| total R | 2.000 |
| profit factor | 1.208 |
| average winner (pts) | 30.500 |
| average loser (pts) | -25.250 |
| median winner (pts) | 30.500 |
| median loser (pts) | -25.250 |
| max drawdown (R) | 2.000 |
| max drawdown (pts) | 50.500 |
| longest winning streak | 2 |
| longest losing streak | 2 |
| average MAE (pts) | 15.438 |
| median MAE (pts) | 12.375 |
| average MFE (pts) | 24.812 |
| median MFE (pts) | 25.250 |
| average hold (min) | 15.390 |
| median hold (min) | 15.921 |
| average R distance (pts) | 20.250 |
| TP exits | 2 |
| SL exits | 2 |
| timeout exits | 0 |
| t-stat of mean R | 0.577 |

<small>friction 0.5 pts -> expectancy 0.4697 R / 2.125 pts, PF 1.165, total 8.5 pts</small>


<small>friction 1.0 pts -> expectancy 0.4393 R / 1.625 pts, PF 1.124, total 6.5 pts</small>


<small>friction 2.0 pts -> expectancy 0.3786 R / 0.625 pts, PF 1.046, total 2.5 pts</small>


### STAR - breakdowns (target 1R, gross)


**Year**

| year | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024 | 4 | 2 | 2 | 0.500 | 0.150 | 0.850 | 0.000 | -5.000 | -20.000 | 0.604 | 15.438 | 17.000 | 3.614 |

**Month**

| month | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024-04 | 1 | 1 | 0 | 1.000 | 0.207 | 1.000 | 1.000 | 10.000 | 10.000 | inf | 9.500 | 10.250 | 3.062 |
| 2024-06 | 2 | 1 | 1 | 0.500 | 0.095 | 0.905 | 0.000 | 2.625 | 5.250 | 1.344 | 7.875 | 13.750 | 3.614 |
| 2024-10 | 1 | 0 | 1 | 0.000 | 0.000 | 0.793 | -1.000 | -35.250 | -35.250 | 0.000 | 36.500 | 30.250 | 26.561 |

**Level family**

| family | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ASIA_L | 1 | 1 | 0 | 1.000 | 0.207 | 1.000 | 1.000 | 10.000 | 10.000 | inf | 9.500 | 10.250 | 3.062 |
| EU_L | 1 | 0 | 1 | 0.000 | 0.000 | 0.793 | -1.000 | -35.250 | -35.250 | 0.000 | 36.500 | 30.250 | 26.561 |
| US_H | 1 | 1 | 0 | 1.000 | 0.207 | 1.000 | 1.000 | 20.500 | 20.500 | inf | 0.500 | 21.000 | 4.072 |
| US_L | 1 | 0 | 1 | 0.000 | 0.000 | 0.793 | -1.000 | -15.250 | -15.250 | 0.000 | 15.250 | 6.500 | 3.155 |

**Trigger type**

| trigger_type | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| STAR | 4 | 2 | 2 | 0.500 | 0.150 | 0.850 | 0.000 | -5.000 | -20.000 | 0.604 | 15.438 | 17.000 | 3.614 |

**Direction**

| side | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | 2 | 1 | 1 | 0.500 | 0.095 | 0.905 | 0.000 | -12.625 | -25.250 | 0.284 | 23.000 | 20.250 | 14.812 |
| SHORT | 2 | 1 | 1 | 0.500 | 0.095 | 0.905 | 0.000 | 2.625 | 5.250 | 1.344 | 7.875 | 13.750 | 3.614 |

**Session**

| session | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EU | 1 | 1 | 0 | 1.000 | 0.207 | 1.000 | 1.000 | 10.000 | 10.000 | inf | 9.500 | 10.250 | 3.062 |
| US | 3 | 1 | 2 | 0.333 | 0.061 | 0.792 | -0.333 | -10.000 | -30.000 | 0.406 | 17.417 | 19.250 | 4.072 |

**Fast-Slow time-ratio bucket**

| tr_bucket | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2.5-3.0 | 2 | 1 | 1 | 0.500 | 0.095 | 0.905 | 0.000 | -2.625 | -5.250 | 0.656 | 12.375 | 8.375 | 3.109 |
| >=3.0 | 2 | 1 | 1 | 0.500 | 0.095 | 0.905 | 0.000 | -7.375 | -14.750 | 0.582 | 18.500 | 25.625 | 15.317 |

**09:30-11:30 ET subset**

| metric | value |
|---|---|
| executed trades | 3 |
| trades / trading day | 0.012 |
| long | 1 |
| short | 2 |
| wins | 1 |
| losses | 2 |
| breakevens | 0 |
| win rate | 0.333 |
| win rate 95% CI low | 0.061 |
| win rate 95% CI high | 0.792 |
| break-even win rate | 0.500 |
| p(win rate > break-even), one-sided | 0.875 |
| expectancy (R) | -0.333 |
| expectancy (NQ points) | -10.000 |

## 3. A-B-C candidates rejected before any trigger test

| skip_reason | len |
|---|---|
| AB_TOO_FEW_BARS | 3784 |
| AB_MOVE_TOO_SMALL | 2249 |
| TIME_RATIO_TOO_LOW | 2207 |
| NO_TRIGGER | 389 |
| AB_TOO_MANY_BARS | 261 |
| DIST_RATIO_OUT_OF_RANGE | 181 |
| LEVEL_BROKEN | 96 |
| BC_TOO_MANY_BARS | 3 |