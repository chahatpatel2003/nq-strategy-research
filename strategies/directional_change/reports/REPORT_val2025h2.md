# Directional Change — FRESH VALIDATION 2025-H2 (frozen dcevent-1.0.0.impl3+d33e5d5d116f1adb)

> # FRESH VALIDATION — 2025-H2
>
> Run once, after the freeze, on data never previously touched by this project. This is the split the pre-registered verdict is based on.

* spec `dcevent-1.0.0` | theta = `0.5 x VU`
* period **2025-07-01 .. 2025-12-31**, 128 trading days
* runtime 12.4s

## 1. Headline — family x window x round-trip friction (target 1R)

The no-edge baseline for a symmetric +-1R bracket is 50 %. `p_value` is the one-sided binomial test against it.

| family | window | friction | trades | win_rate | ci_lo | ci_hi | expectancy_R | expectancy_pts | PF | p_value |
|---|---|---|---|---|---|---|---|---|---|---|
| DC_A | 09:30-11:30 ET | 0.000 | 15583 | 0.482 | 0.474 | 0.490 | -0.040 | -0.286 | 0.927 | 1.000 |
| DC_A | 09:30-11:30 ET | 0.500 | 15583 | 0.482 | 0.474 | 0.490 | -0.127 | -0.786 | 0.811 | 1.000 |
| DC_A | 09:30-11:30 ET | 1.000 | 15583 | 0.482 | 0.474 | 0.490 | -0.214 | -1.286 | 0.709 | 1.000 |
| DC_A | 09:30-11:30 ET | 2.000 | 15583 | 0.474 | 0.467 | 0.482 | -0.389 | -2.286 | 0.537 | 1.000 |
| DC_A | 09:30-10:30 ET | 0.000 | 9511 | 0.480 | 0.470 | 0.490 | -0.046 | -0.285 | 0.928 | 1.000 |
| DC_A | 09:30-10:30 ET | 0.500 | 9511 | 0.480 | 0.470 | 0.490 | -0.133 | -0.785 | 0.814 | 1.000 |
| DC_A | 09:30-10:30 ET | 1.000 | 9511 | 0.480 | 0.470 | 0.490 | -0.221 | -1.285 | 0.713 | 1.000 |
| DC_A | 09:30-10:30 ET | 2.000 | 9511 | 0.473 | 0.463 | 0.483 | -0.395 | -2.285 | 0.543 | 1.000 |
| DC_A | 10:30-11:30 ET | 0.000 | 6072 | 0.486 | 0.473 | 0.498 | -0.031 | -0.289 | 0.924 | 0.987 |
| DC_A | 10:30-11:30 ET | 0.500 | 6072 | 0.486 | 0.473 | 0.498 | -0.118 | -0.789 | 0.806 | 0.987 |
| DC_A | 10:30-11:30 ET | 1.000 | 6072 | 0.486 | 0.473 | 0.498 | -0.205 | -1.289 | 0.702 | 0.988 |
| DC_A | 10:30-11:30 ET | 2.000 | 6072 | 0.477 | 0.464 | 0.489 | -0.378 | -2.289 | 0.527 | 1.000 |
| DC_A | 09:30-12:00 ET | 0.000 | 18638 | 0.481 | 0.474 | 0.489 | -0.041 | -0.274 | 0.928 | 1.000 |
| DC_A | 09:30-12:00 ET | 0.500 | 18638 | 0.481 | 0.474 | 0.489 | -0.131 | -0.774 | 0.810 | 1.000 |
| DC_A | 09:30-12:00 ET | 1.000 | 18638 | 0.481 | 0.474 | 0.489 | -0.221 | -1.274 | 0.705 | 1.000 |
| DC_A | 09:30-12:00 ET | 2.000 | 18638 | 0.474 | 0.467 | 0.481 | -0.400 | -2.274 | 0.530 | 1.000 |
| DC_A | 09:30-16:00 ET | 0.000 | 44793 | 0.483 | 0.479 | 0.488 | -0.038 | -0.189 | 0.939 | 1.000 |
| DC_A | 09:30-16:00 ET | 0.500 | 44793 | 0.483 | 0.479 | 0.488 | -0.151 | -0.689 | 0.794 | 1.000 |
| DC_A | 09:30-16:00 ET | 1.000 | 44793 | 0.483 | 0.478 | 0.487 | -0.264 | -1.189 | 0.669 | 1.000 |
| DC_A | 09:30-16:00 ET | 2.000 | 44793 | 0.471 | 0.467 | 0.476 | -0.491 | -2.189 | 0.468 | 1.000 |
| DC_B | 09:30-11:30 ET | 0.000 | 14603 | 0.483 | 0.475 | 0.491 | -0.041 | -0.265 | 0.932 | 1.000 |
| DC_B | 09:30-11:30 ET | 0.500 | 14603 | 0.483 | 0.475 | 0.491 | -0.128 | -0.765 | 0.816 | 1.000 |
| DC_B | 09:30-11:30 ET | 1.000 | 14603 | 0.483 | 0.475 | 0.491 | -0.215 | -1.265 | 0.713 | 1.000 |
| DC_B | 09:30-11:30 ET | 2.000 | 14603 | 0.476 | 0.467 | 0.484 | -0.390 | -2.265 | 0.540 | 1.000 |
| DC_B | 09:30-10:30 ET | 0.000 | 9016 | 0.482 | 0.472 | 0.492 | -0.043 | -0.290 | 0.927 | 1.000 |
| DC_B | 09:30-10:30 ET | 0.500 | 9016 | 0.482 | 0.472 | 0.492 | -0.131 | -0.790 | 0.813 | 1.000 |
| DC_B | 09:30-10:30 ET | 1.000 | 9016 | 0.482 | 0.472 | 0.492 | -0.218 | -1.290 | 0.712 | 1.000 |
| DC_B | 09:30-10:30 ET | 2.000 | 9016 | 0.476 | 0.466 | 0.486 | -0.394 | -2.290 | 0.541 | 1.000 |
| DC_B | 10:30-11:30 ET | 0.000 | 5587 | 0.484 | 0.471 | 0.497 | -0.037 | -0.225 | 0.941 | 0.993 |
| DC_B | 10:30-11:30 ET | 0.500 | 5587 | 0.484 | 0.471 | 0.497 | -0.124 | -0.725 | 0.821 | 0.993 |
| DC_B | 10:30-11:30 ET | 1.000 | 5587 | 0.484 | 0.471 | 0.497 | -0.210 | -1.225 | 0.715 | 0.993 |
| DC_B | 10:30-11:30 ET | 2.000 | 5587 | 0.475 | 0.462 | 0.488 | -0.384 | -2.225 | 0.539 | 1.000 |
| DC_B | 09:30-12:00 ET | 0.000 | 17456 | 0.482 | 0.475 | 0.490 | -0.041 | -0.257 | 0.932 | 1.000 |
| DC_B | 09:30-12:00 ET | 0.500 | 17456 | 0.482 | 0.475 | 0.490 | -0.131 | -0.757 | 0.814 | 1.000 |
| DC_B | 09:30-12:00 ET | 1.000 | 17456 | 0.482 | 0.475 | 0.489 | -0.221 | -1.257 | 0.709 | 1.000 |
| DC_B | 09:30-12:00 ET | 2.000 | 17456 | 0.475 | 0.468 | 0.482 | -0.400 | -2.257 | 0.534 | 1.000 |
| DC_B | 09:30-16:00 ET | 0.000 | 41596 | 0.484 | 0.479 | 0.489 | -0.038 | -0.177 | 0.943 | 1.000 |
| DC_B | 09:30-16:00 ET | 0.500 | 41596 | 0.484 | 0.479 | 0.489 | -0.151 | -0.677 | 0.797 | 1.000 |
| DC_B | 09:30-16:00 ET | 1.000 | 41596 | 0.484 | 0.479 | 0.488 | -0.264 | -1.177 | 0.673 | 1.000 |
| DC_B | 09:30-16:00 ET | 2.000 | 41596 | 0.473 | 0.468 | 0.478 | -0.491 | -2.177 | 0.472 | 1.000 |
| DC_C | 09:30-11:30 ET | 0.000 | 4182 | 0.470 | 0.455 | 0.485 | -0.065 | -0.453 | 0.885 | 1.000 |
| DC_C | 09:30-11:30 ET | 0.500 | 4182 | 0.470 | 0.455 | 0.485 | -0.155 | -0.953 | 0.773 | 1.000 |
| DC_C | 09:30-11:30 ET | 1.000 | 4182 | 0.470 | 0.455 | 0.485 | -0.245 | -1.453 | 0.674 | 1.000 |
| DC_C | 09:30-11:30 ET | 2.000 | 4182 | 0.460 | 0.445 | 0.475 | -0.425 | -2.453 | 0.508 | 1.000 |
| DC_C | 09:30-10:30 ET | 0.000 | 2568 | 0.467 | 0.448 | 0.486 | -0.072 | -0.471 | 0.882 | 1.000 |
| DC_C | 09:30-10:30 ET | 0.500 | 2568 | 0.467 | 0.448 | 0.486 | -0.163 | -0.971 | 0.772 | 1.000 |
| DC_C | 09:30-10:30 ET | 1.000 | 2568 | 0.467 | 0.448 | 0.486 | -0.254 | -1.471 | 0.675 | 1.000 |
| DC_C | 09:30-10:30 ET | 2.000 | 2568 | 0.458 | 0.439 | 0.477 | -0.436 | -2.471 | 0.511 | 1.000 |
| DC_C | 10:30-11:30 ET | 0.000 | 1614 | 0.475 | 0.450 | 0.499 | -0.054 | -0.423 | 0.889 | 0.981 |
| DC_C | 10:30-11:30 ET | 0.500 | 1614 | 0.475 | 0.450 | 0.499 | -0.142 | -0.923 | 0.774 | 0.981 |
| DC_C | 10:30-11:30 ET | 1.000 | 1614 | 0.475 | 0.450 | 0.499 | -0.231 | -1.423 | 0.673 | 0.981 |
| DC_C | 10:30-11:30 ET | 2.000 | 1614 | 0.464 | 0.440 | 0.488 | -0.407 | -2.423 | 0.503 | 0.998 |
| DC_C | 09:30-12:00 ET | 0.000 | 4991 | 0.469 | 0.455 | 0.483 | -0.066 | -0.452 | 0.883 | 1.000 |
| DC_C | 09:30-12:00 ET | 0.500 | 4991 | 0.469 | 0.455 | 0.483 | -0.158 | -0.952 | 0.769 | 1.000 |
| DC_C | 09:30-12:00 ET | 1.000 | 4991 | 0.469 | 0.455 | 0.483 | -0.249 | -1.452 | 0.669 | 1.000 |
| DC_C | 09:30-12:00 ET | 2.000 | 4991 | 0.460 | 0.446 | 0.474 | -0.433 | -2.452 | 0.502 | 1.000 |
| DC_C | 09:30-16:00 ET | 0.000 | 12052 | 0.478 | 0.469 | 0.487 | -0.047 | -0.276 | 0.911 | 1.000 |
| DC_C | 09:30-16:00 ET | 0.500 | 12052 | 0.478 | 0.469 | 0.487 | -0.161 | -0.776 | 0.770 | 1.000 |
| DC_C | 09:30-16:00 ET | 1.000 | 12052 | 0.478 | 0.469 | 0.486 | -0.275 | -1.276 | 0.649 | 1.000 |
| DC_C | 09:30-16:00 ET | 2.000 | 12052 | 0.465 | 0.456 | 0.474 | -0.503 | -2.276 | 0.453 | 1.000 |

## 2. Family `DC_A`

* signals **110,253** | accepted **44,793** | skipped **65,460**

| skip_reason | len |
|---|---|
| SKIPPED_OVERLAP | 43421 |
| OUTSIDE_RTH | 22038 |
| NO_ENTRY_PRINT | 1 |

### DC_A — PRIMARY 09:30-11:30 ET, 1R, 1.0 pt friction

| metric | value |
|---|---|
| executed trades | 15583 |
| trades / day (mean) | 121.742 |
| trades / day (median) | 121.000 |
| long | 7845 |
| short | 7738 |
| wins | 7512 |
| losses | 8070 |
| win rate | 0.482 |
| win rate 95% CI low | 0.474 |
| win rate 95% CI high | 0.490 |
| break-even WR at this friction | 0.567 |
| p(WR > 50%), one-sided | 1.000 |
| expectancy (R) | -0.214 |
| median R | -1.063 |
| expectancy (pts) | -1.286 |
| profit factor | 0.709 |
| avg winner (pts) | 6.494 |
| avg loser (pts) | -8.529 |
| avg R distance (pts) | 7.486 |
| max drawdown (R, trade seq) | 3,343 |
| max drawdown (R, daily) | 3,341 |
| longest winning streak | 12 |
| longest losing streak | 15 |
| avg MFE (pts) | 5.309 |
| avg MAE (pts) | 5.367 |
| avg MAE on winners (pts) | 2.826 |
| avg MFE on losers (pts) | 2.797 |
| avg hold (min) | 0.529 |
| median hold (min) | 0.325 |
| TP exits | 7513 |
| SL exits | 8070 |
| timeout exits | 0 |
| t-stat of mean R | -26.513 |

**Frequency / prop-firm profile**

| metric | value |
|---|---|
| % days with 0 trades | 0.000 |
| % days with 1 | 0.000 |
| % days with 2 | 0.000 |
| % days with 3-4 | 0.000 |
| % days with 5+ | 1.000 |
| trades/day 09:30-10:30 | 74.305 |
| trades/day 10:30-11:30 | 47.438 |
| median minutes between trades | 0.755 |
| % profitable days | 0.016 |
| daily R mean | -26.103 |
| daily R 5th pct | -50.165 |
| max daily loss (R) | -92.486 |
| longest stretch below peak (days) | 128 |

**Other windows (1R, primary friction)**

| window | trades | win_rate | ci_lo | ci_hi | expectancy_R | PF | trades_per_day |
|---|---|---|---|---|---|---|---|
| 09:30-11:30 ET | 15583 | 0.482 | 0.474 | 0.490 | -0.214 | 0.709 | 121.742 |
| 09:30-10:30 ET | 9511 | 0.480 | 0.470 | 0.490 | -0.221 | 0.713 | 74.305 |
| 10:30-11:30 ET | 6072 | 0.486 | 0.473 | 0.498 | -0.205 | 0.702 | 47.438 |
| 09:30-12:00 ET | 18638 | 0.481 | 0.474 | 0.489 | -0.221 | 0.705 | 145.609 |
| 09:30-16:00 ET | 44793 | 0.483 | 0.478 | 0.487 | -0.264 | 0.669 | 349.945 |

**Target sensitivity on the SAME entries (primary window, primary friction)**

_1R is the pre-registered primary. Each target is shown against its own no-edge break-even, so a high hit rate at a small target is not mistaken for an edge._

| target | trades | win_rate | no_edge_breakeven | excess_vs_breakeven | expectancy_R | PF |
|---|---|---|---|---|---|---|
| 0.75R | 15583 | 0.550 | 0.571 | -0.021 | -0.214 | 0.666 |
| 1R | 15583 | 0.482 | 0.500 | -0.018 | -0.214 | 0.709 |
| 1.25R | 15583 | 0.427 | 0.444 | -0.017 | -0.217 | 0.731 |
| 1.5R | 15583 | 0.382 | 0.400 | -0.018 | -0.223 | 0.742 |
| 2R | 15583 | 0.321 | 0.333 | -0.012 | -0.216 | 0.779 |

### DC_A — stability breakdowns (primary window, 1R, primary friction)

_Diagnostics only. No subgroup is promoted to the strategy._


**Year**

| year | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2025 | 15583 | 7512 | 8070 | 0.482 | 0.474 | 0.490 | -0.214 | -1.286 | -20,044 | 0.709 | 5.367 | 5.309 | 0.325 |

**Month**

| month | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2025-07 | 2676 | 1283 | 1393 | 0.479 | 0.461 | 0.498 | -0.254 | -1.218 | -3,258 | 0.638 | 3.947 | 3.938 | 0.325 |
| 2025-08 | 2646 | 1317 | 1329 | 0.498 | 0.479 | 0.517 | -0.188 | -1.026 | -2,715 | 0.745 | 4.931 | 5.076 | 0.281 |
| 2025-09 | 2615 | 1259 | 1356 | 0.481 | 0.462 | 0.501 | -0.251 | -1.179 | -3,082 | 0.678 | 4.316 | 4.402 | 0.319 |
| 2025-10 | 2824 | 1357 | 1467 | 0.481 | 0.462 | 0.499 | -0.204 | -1.389 | -3,922 | 0.693 | 5.497 | 5.324 | 0.324 |
| 2025-11 | 2311 | 1097 | 1213 | 0.475 | 0.454 | 0.495 | -0.180 | -1.599 | -3,696 | 0.752 | 8.019 | 7.789 | 0.360 |
| 2025-12 | 2511 | 1199 | 1312 | 0.477 | 0.458 | 0.497 | -0.206 | -1.343 | -3,371 | 0.718 | 5.846 | 5.659 | 0.329 |

**Direction**

| side | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | 7845 | 3740 | 4105 | 0.477 | 0.466 | 0.488 | -0.226 | -1.321 | -10,365 | 0.701 | 5.343 | 5.254 | 0.304 |
| SHORT | 7738 | 3772 | 3965 | 0.487 | 0.476 | 0.499 | -0.203 | -1.251 | -9,679 | 0.716 | 5.391 | 5.364 | 0.349 |

**Hour of day**

| et_hour | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 9 | 6575 | 3158 | 3417 | 0.480 | 0.468 | 0.492 | -0.239 | -1.251 | -8,228 | 0.695 | 4.910 | 4.907 | 0.116 |
| 10 | 5935 | 2870 | 3065 | 0.484 | 0.471 | 0.496 | -0.184 | -1.321 | -7,842 | 0.729 | 6.051 | 5.944 | 0.502 |
| 11 | 3073 | 1484 | 1588 | 0.483 | 0.465 | 0.501 | -0.220 | -1.293 | -3,974 | 0.691 | 5.024 | 4.942 | 0.490 |

**Volatility (VU) quartile-ish**

| vol_bucket | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10.0-16.0 | 5483 | 2663 | 2820 | 0.486 | 0.472 | 0.499 | -0.191 | -1.214 | -6,659 | 0.683 | 4.543 | 4.560 | 0.341 |
| 6.0-10.0 | 3589 | 1730 | 1859 | 0.482 | 0.466 | 0.498 | -0.295 | -1.169 | -4,196 | 0.557 | 2.889 | 2.956 | 0.125 |
| <6.0 | 977 | 455 | 521 | 0.466 | 0.435 | 0.497 | -0.520 | -1.187 | -1,159 | 0.354 | 1.731 | 1.797 | 0.037 |
| >=16.0 | 5534 | 2664 | 2870 | 0.481 | 0.468 | 0.495 | -0.131 | -1.451 | -8,030 | 0.781 | 8.431 | 8.197 | 0.483 |

**Theta bucket (pts)**

| theta_bucket | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3.0-5.0 | 3589 | 1730 | 1859 | 0.482 | 0.466 | 0.498 | -0.295 | -1.169 | -4,196 | 0.557 | 2.889 | 2.956 | 0.125 |
| 5.0-8.0 | 5483 | 2663 | 2820 | 0.486 | 0.472 | 0.499 | -0.191 | -1.214 | -6,659 | 0.683 | 4.543 | 4.560 | 0.341 |
| <3.0 | 977 | 455 | 521 | 0.466 | 0.435 | 0.497 | -0.520 | -1.187 | -1,159 | 0.354 | 1.731 | 1.797 | 0.037 |
| >=8.0 | 5534 | 2664 | 2870 | 0.481 | 0.468 | 0.495 | -0.131 | -1.451 | -8,030 | 0.781 | 8.431 | 8.197 | 0.483 |

**Event size (DC magnitude / theta)**

| event_size_bucket | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1.05-1.2 | 2876 | 1378 | 1498 | 0.479 | 0.461 | 0.497 | -0.290 | -1.239 | -3,563 | 0.623 | 3.749 | 3.806 | 0.130 |
| 1.2-1.5 | 207 | 101 | 106 | 0.488 | 0.421 | 0.556 | -0.387 | -1.219 | -252.339 | 0.556 | 3.115 | 3.152 | 0.041 |
| <1.05 | 12458 | 6007 | 6450 | 0.482 | 0.473 | 0.491 | -0.195 | -1.301 | -16,211 | 0.724 | 5.781 | 5.691 | 0.378 |
| >=1.5 | 42 | 26 | 16 | 0.619 | 0.468 | 0.750 | -0.010 | -0.412 | -17.295 | 0.864 | 4.327 | 5.310 | 0.032 |

**Prior overshoot / theta**

| overshoot_bucket | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5-1.0 | 2917 | 1367 | 1550 | 0.469 | 0.451 | 0.487 | -0.239 | -1.515 | -4,420 | 0.668 | 5.472 | 5.233 | 0.343 |
| 1.0-2.0 | 6550 | 3241 | 3309 | 0.495 | 0.483 | 0.507 | -0.185 | -1.140 | -7,470 | 0.739 | 5.357 | 5.407 | 0.351 |
| <0.5 | 1951 | 947 | 1003 | 0.485 | 0.463 | 0.508 | -0.211 | -1.084 | -2,115 | 0.746 | 5.213 | 5.383 | 0.315 |
| >=2.0 | 4165 | 1957 | 2208 | 0.470 | 0.455 | 0.485 | -0.244 | -1.450 | -6,040 | 0.675 | 5.380 | 5.171 | 0.277 |

## 3. Family `DC_B`

* signals **64,800** | accepted **41,596** | skipped **23,204**

| skip_reason | len |
|---|---|
| OUTSIDE_RTH | 12528 |
| SKIPPED_OVERLAP | 10676 |

### DC_B — PRIMARY 09:30-11:30 ET, 1R, 1.0 pt friction

| metric | value |
|---|---|
| executed trades | 14603 |
| trades / day (mean) | 114.086 |
| trades / day (median) | 113.000 |
| long | 7259 |
| short | 7344 |
| wins | 7048 |
| losses | 7554 |
| win rate | 0.483 |
| win rate 95% CI low | 0.475 |
| win rate 95% CI high | 0.491 |
| break-even WR at this friction | 0.567 |
| p(WR > 50%), one-sided | 1.000 |
| expectancy (R) | -0.215 |
| median R | -1.063 |
| expectancy (pts) | -1.265 |
| profit factor | 0.713 |
| avg winner (pts) | 6.517 |
| avg loser (pts) | -8.526 |
| avg R distance (pts) | 7.485 |
| max drawdown (R, trade seq) | 3,146 |
| max drawdown (R, daily) | 3,143 |
| longest winning streak | 13 |
| longest losing streak | 11 |
| avg MFE (pts) | 5.362 |
| avg MAE (pts) | 5.321 |
| avg MAE on winners (pts) | 2.794 |
| avg MFE on losers (pts) | 2.804 |
| avg hold (min) | 0.517 |
| median hold (min) | 0.304 |
| TP exits | 7049 |
| SL exits | 7554 |
| timeout exits | 0 |
| t-stat of mean R | -25.702 |

**Frequency / prop-firm profile**

| metric | value |
|---|---|
| % days with 0 trades | 0.000 |
| % days with 1 | 0.000 |
| % days with 2 | 0.000 |
| % days with 3-4 | 0.000 |
| % days with 5+ | 1.000 |
| trades/day 09:30-10:30 | 70.438 |
| trades/day 10:30-11:30 | 43.648 |
| median minutes between trades | 0.733 |
| % profitable days | 0.039 |
| daily R mean | -24.556 |
| daily R 5th pct | -53.869 |
| max daily loss (R) | -82.643 |
| longest stretch below peak (days) | 128 |

**Other windows (1R, primary friction)**

| window | trades | win_rate | ci_lo | ci_hi | expectancy_R | PF | trades_per_day |
|---|---|---|---|---|---|---|---|
| 09:30-11:30 ET | 14603 | 0.483 | 0.475 | 0.491 | -0.215 | 0.713 | 114.086 |
| 09:30-10:30 ET | 9016 | 0.482 | 0.472 | 0.492 | -0.218 | 0.712 | 70.438 |
| 10:30-11:30 ET | 5587 | 0.484 | 0.471 | 0.497 | -0.210 | 0.715 | 43.648 |
| 09:30-12:00 ET | 17456 | 0.482 | 0.475 | 0.489 | -0.221 | 0.709 | 136.375 |
| 09:30-16:00 ET | 41596 | 0.484 | 0.479 | 0.488 | -0.264 | 0.673 | 324.969 |

**Target sensitivity on the SAME entries (primary window, primary friction)**

_1R is the pre-registered primary. Each target is shown against its own no-edge break-even, so a high hit rate at a small target is not mistaken for an edge._

| target | trades | win_rate | no_edge_breakeven | excess_vs_breakeven | expectancy_R | PF |
|---|---|---|---|---|---|---|
| 0.75R | 14603 | 0.554 | 0.571 | -0.018 | -0.210 | 0.669 |
| 1R | 14603 | 0.483 | 0.500 | -0.017 | -0.215 | 0.713 |
| 1.25R | 14603 | 0.432 | 0.444 | -0.013 | -0.210 | 0.749 |
| 1.5R | 14603 | 0.393 | 0.400 | -0.007 | -0.198 | 0.780 |
| 2R | 14603 | 0.330 | 0.333 | -0.003 | -0.191 | 0.814 |

### DC_B — stability breakdowns (primary window, 1R, primary friction)

_Diagnostics only. No subgroup is promoted to the strategy._


**Year**

| year | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2025 | 14603 | 7048 | 7554 | 0.483 | 0.475 | 0.491 | -0.215 | -1.265 | -18,477 | 0.713 | 5.321 | 5.362 | 0.304 |

**Month**

| month | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2025-07 | 2534 | 1213 | 1321 | 0.479 | 0.459 | 0.498 | -0.256 | -1.276 | -3,232 | 0.627 | 3.951 | 4.005 | 0.288 |
| 2025-08 | 2460 | 1181 | 1279 | 0.480 | 0.460 | 0.500 | -0.226 | -1.283 | -3,157 | 0.692 | 4.961 | 5.022 | 0.275 |
| 2025-09 | 2458 | 1152 | 1306 | 0.469 | 0.449 | 0.488 | -0.281 | -1.399 | -3,438 | 0.628 | 4.367 | 4.307 | 0.297 |
| 2025-10 | 2621 | 1289 | 1332 | 0.492 | 0.473 | 0.511 | -0.183 | -1.075 | -2,819 | 0.751 | 5.321 | 5.477 | 0.317 |
| 2025-11 | 2170 | 1081 | 1088 | 0.498 | 0.477 | 0.519 | -0.133 | -1.148 | -2,491 | 0.816 | 7.857 | 7.977 | 0.340 |
| 2025-12 | 2360 | 1132 | 1228 | 0.480 | 0.460 | 0.500 | -0.203 | -1.415 | -3,339 | 0.707 | 5.830 | 5.739 | 0.312 |

**Direction**

| side | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | 7259 | 3477 | 3782 | 0.479 | 0.468 | 0.490 | -0.223 | -1.307 | -9,484 | 0.705 | 5.347 | 5.344 | 0.322 |
| SHORT | 7344 | 3571 | 3772 | 0.486 | 0.475 | 0.498 | -0.207 | -1.225 | -8,993 | 0.721 | 5.295 | 5.379 | 0.286 |

**Hour of day**

| et_hour | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 9 | 6235 | 3066 | 3169 | 0.492 | 0.479 | 0.504 | -0.219 | -1.084 | -6,760 | 0.729 | 4.815 | 4.994 | 0.112 |
| 10 | 5556 | 2612 | 2944 | 0.470 | 0.457 | 0.483 | -0.212 | -1.562 | -8,678 | 0.690 | 6.102 | 5.924 | 0.474 |
| 11 | 2812 | 1370 | 1441 | 0.487 | 0.469 | 0.506 | -0.213 | -1.081 | -3,039 | 0.735 | 4.899 | 5.065 | 0.449 |

**Volatility (VU) quartile-ish**

| vol_bucket | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10.0-16.0 | 5131 | 2500 | 2631 | 0.487 | 0.474 | 0.501 | -0.190 | -1.197 | -6,144 | 0.687 | 4.528 | 4.646 | 0.325 |
| 6.0-10.0 | 3343 | 1573 | 1770 | 0.471 | 0.454 | 0.487 | -0.321 | -1.275 | -4,264 | 0.528 | 2.927 | 2.958 | 0.120 |
| <6.0 | 946 | 444 | 501 | 0.469 | 0.438 | 0.501 | -0.513 | -1.171 | -1,108 | 0.361 | 1.704 | 1.796 | 0.032 |
| >=16.0 | 5183 | 2531 | 2652 | 0.488 | 0.475 | 0.502 | -0.118 | -1.343 | -6,962 | 0.795 | 8.311 | 8.272 | 0.448 |

**Theta bucket (pts)**

| theta_bucket | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3.0-5.0 | 3343 | 1573 | 1770 | 0.471 | 0.454 | 0.487 | -0.321 | -1.275 | -4,264 | 0.528 | 2.927 | 2.958 | 0.120 |
| 5.0-8.0 | 5131 | 2500 | 2631 | 0.487 | 0.474 | 0.501 | -0.190 | -1.197 | -6,144 | 0.687 | 4.528 | 4.646 | 0.325 |
| <3.0 | 946 | 444 | 501 | 0.469 | 0.438 | 0.501 | -0.513 | -1.171 | -1,108 | 0.361 | 1.704 | 1.796 | 0.032 |
| >=8.0 | 5183 | 2531 | 2652 | 0.488 | 0.475 | 0.502 | -0.118 | -1.343 | -6,962 | 0.795 | 8.311 | 8.272 | 0.448 |

**Event size (DC magnitude / theta)**

| event_size_bucket | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1.05-1.2 | 2689 | 1292 | 1397 | 0.480 | 0.462 | 0.499 | -0.292 | -1.132 | -3,044 | 0.646 | 3.645 | 3.785 | 0.125 |
| 1.2-1.5 | 172 | 82 | 90 | 0.477 | 0.403 | 0.551 | -0.422 | -1.123 | -193.223 | 0.545 | 2.791 | 2.849 | 0.044 |
| <1.05 | 11728 | 5669 | 6058 | 0.483 | 0.474 | 0.492 | -0.194 | -1.296 | -15,201 | 0.725 | 5.743 | 5.762 | 0.346 |
| >=1.5 | 14 | 5 | 9 | 0.357 | 0.163 | 0.612 | -0.553 | -2.807 | -39.295 | 0.358 | 4.732 | 3.518 | 0.017 |

**Prior overshoot / theta**

| overshoot_bucket | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.5-1.0 | 3430 | 1664 | 1766 | 0.485 | 0.468 | 0.502 | -0.203 | -1.269 | -4,352 | 0.719 | 5.450 | 5.564 | 0.344 |
| 1.0-2.0 | 2788 | 1338 | 1450 | 0.480 | 0.461 | 0.498 | -0.228 | -1.266 | -3,530 | 0.704 | 5.151 | 5.125 | 0.288 |
| <0.5 | 5983 | 2905 | 3077 | 0.486 | 0.473 | 0.498 | -0.208 | -1.225 | -7,331 | 0.722 | 5.318 | 5.426 | 0.297 |
| >=2.0 | 2402 | 1141 | 1261 | 0.475 | 0.455 | 0.495 | -0.235 | -1.359 | -3,265 | 0.693 | 5.340 | 5.186 | 0.283 |

## 4. Family `DC_C`

* signals **15,298** | accepted **12,052** | skipped **3,246**

| skip_reason | len |
|---|---|
| OUTSIDE_RTH | 3183 |
| SKIPPED_OVERLAP | 63 |

### DC_C — PRIMARY 09:30-11:30 ET, 1R, 1.0 pt friction

| metric | value |
|---|---|
| executed trades | 4182 |
| trades / day (mean) | 32.672 |
| trades / day (median) | 32.500 |
| long | 2144 |
| short | 2038 |
| wins | 1965 |
| losses | 2217 |
| win rate | 0.470 |
| win rate 95% CI low | 0.455 |
| win rate 95% CI high | 0.485 |
| break-even WR at this friction | 0.568 |
| p(WR > 50%), one-sided | 1.000 |
| expectancy (R) | -0.245 |
| median R | -1.069 |
| expectancy (pts) | -1.453 |
| profit factor | 0.674 |
| avg winner (pts) | 6.392 |
| avg loser (pts) | -8.406 |
| avg R distance (pts) | 7.374 |
| max drawdown (R, trade seq) | 1,025 |
| max drawdown (R, daily) | 1,024 |
| longest winning streak | 11 |
| longest losing streak | 11 |
| avg MFE (pts) | 5.166 |
| avg MAE (pts) | 5.373 |
| avg MAE on winners (pts) | 2.795 |
| avg MFE on losers (pts) | 2.765 |
| avg hold (min) | 0.480 |
| median hold (min) | 0.276 |
| TP exits | 1965 |
| SL exits | 2217 |
| timeout exits | 0 |
| t-stat of mean R | -15.680 |

**Frequency / prop-firm profile**

| metric | value |
|---|---|
| % days with 0 trades | 0.000 |
| % days with 1 | 0.000 |
| % days with 2 | 0.000 |
| % days with 3-4 | 0.000 |
| % days with 5+ | 1.000 |
| trades/day 09:30-10:30 | 20.062 |
| trades/day 10:30-11:30 | 12.609 |
| median minutes between trades | 2.342 |
| % profitable days | 0.109 |
| daily R mean | -7.997 |
| daily R 5th pct | -16.944 |
| max daily loss (R) | -28.778 |
| longest stretch below peak (days) | 128 |

**Other windows (1R, primary friction)**

| window | trades | win_rate | ci_lo | ci_hi | expectancy_R | PF | trades_per_day |
|---|---|---|---|---|---|---|---|
| 09:30-11:30 ET | 4182 | 0.470 | 0.455 | 0.485 | -0.245 | 0.674 | 32.672 |
| 09:30-10:30 ET | 2568 | 0.467 | 0.448 | 0.486 | -0.254 | 0.675 | 20.062 |
| 10:30-11:30 ET | 1614 | 0.475 | 0.450 | 0.499 | -0.231 | 0.673 | 12.609 |
| 09:30-12:00 ET | 4991 | 0.469 | 0.455 | 0.483 | -0.249 | 0.669 | 38.992 |
| 09:30-16:00 ET | 12052 | 0.478 | 0.469 | 0.486 | -0.275 | 0.649 | 94.156 |

**Target sensitivity on the SAME entries (primary window, primary friction)**

_1R is the pre-registered primary. Each target is shown against its own no-edge break-even, so a high hit rate at a small target is not mistaken for an edge._

| target | trades | win_rate | no_edge_breakeven | excess_vs_breakeven | expectancy_R | PF |
|---|---|---|---|---|---|---|
| 0.75R | 4182 | 0.541 | 0.571 | -0.030 | -0.236 | 0.636 |
| 1R | 4182 | 0.470 | 0.500 | -0.030 | -0.245 | 0.674 |
| 1.25R | 4182 | 0.415 | 0.444 | -0.029 | -0.251 | 0.696 |
| 1.5R | 4182 | 0.375 | 0.400 | -0.025 | -0.248 | 0.721 |
| 2R | 4182 | 0.313 | 0.333 | -0.020 | -0.246 | 0.759 |

### DC_C — stability breakdowns (primary window, 1R, primary friction)

_Diagnostics only. No subgroup is promoted to the strategy._


**Year**

| year | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2025 | 4182 | 1965 | 2217 | 0.470 | 0.455 | 0.485 | -0.245 | -1.453 | -6,075 | 0.674 | 5.373 | 5.166 | 0.276 |

**Month**

| month | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2025-07 | 722 | 343 | 379 | 0.475 | 0.439 | 0.512 | -0.269 | -1.312 | -947.152 | 0.610 | 3.897 | 3.770 | 0.254 |
| 2025-08 | 727 | 348 | 379 | 0.479 | 0.443 | 0.515 | -0.233 | -1.379 | -1,003 | 0.671 | 5.029 | 4.996 | 0.253 |
| 2025-09 | 684 | 320 | 364 | 0.468 | 0.431 | 0.505 | -0.287 | -1.401 | -958.437 | 0.624 | 4.354 | 4.264 | 0.293 |
| 2025-10 | 745 | 356 | 389 | 0.478 | 0.442 | 0.514 | -0.213 | -1.452 | -1,082 | 0.681 | 5.568 | 5.220 | 0.295 |
| 2025-11 | 624 | 289 | 335 | 0.463 | 0.424 | 0.502 | -0.205 | -1.553 | -968.866 | 0.756 | 7.983 | 7.694 | 0.326 |
| 2025-12 | 680 | 309 | 371 | 0.454 | 0.417 | 0.492 | -0.260 | -1.642 | -1,116 | 0.655 | 5.726 | 5.360 | 0.255 |

**Direction**

| side | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | 2144 | 972 | 1172 | 0.453 | 0.432 | 0.474 | -0.277 | -1.630 | -3,494 | 0.644 | 5.469 | 5.113 | 0.248 |
| SHORT | 2038 | 993 | 1045 | 0.487 | 0.466 | 0.509 | -0.211 | -1.267 | -2,581 | 0.708 | 5.272 | 5.222 | 0.321 |

**Hour of day**

| et_hour | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 9 | 1815 | 853 | 962 | 0.470 | 0.447 | 0.493 | -0.270 | -1.325 | -2,406 | 0.673 | 4.823 | 4.734 | 0.089 |
| 10 | 1545 | 734 | 811 | 0.475 | 0.450 | 0.500 | -0.200 | -1.595 | -2,464 | 0.683 | 6.184 | 5.830 | 0.482 |
| 11 | 822 | 378 | 444 | 0.460 | 0.426 | 0.494 | -0.272 | -1.467 | -1,206 | 0.657 | 5.064 | 4.873 | 0.466 |

**Volatility (VU) quartile-ish**

| vol_bucket | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10.0-16.0 | 1418 | 661 | 757 | 0.466 | 0.440 | 0.492 | -0.230 | -1.509 | -2,140 | 0.623 | 4.651 | 4.488 | 0.298 |
| 6.0-10.0 | 997 | 477 | 520 | 0.478 | 0.448 | 0.509 | -0.306 | -1.167 | -1,164 | 0.554 | 2.858 | 2.914 | 0.099 |
| <6.0 | 317 | 140 | 177 | 0.442 | 0.388 | 0.497 | -0.569 | -1.328 | -421.107 | 0.314 | 1.808 | 1.798 | 0.029 |
| >=16.0 | 1450 | 687 | 763 | 0.474 | 0.448 | 0.500 | -0.146 | -1.621 | -2,350 | 0.759 | 8.588 | 8.115 | 0.481 |

**Theta bucket (pts)**

| theta_bucket | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3.0-5.0 | 997 | 477 | 520 | 0.478 | 0.448 | 0.509 | -0.306 | -1.167 | -1,164 | 0.554 | 2.858 | 2.914 | 0.099 |
| 5.0-8.0 | 1418 | 661 | 757 | 0.466 | 0.440 | 0.492 | -0.230 | -1.509 | -2,140 | 0.623 | 4.651 | 4.488 | 0.298 |
| <3.0 | 317 | 140 | 177 | 0.442 | 0.388 | 0.497 | -0.569 | -1.328 | -421.107 | 0.314 | 1.808 | 1.798 | 0.029 |
| >=8.0 | 1450 | 687 | 763 | 0.474 | 0.448 | 0.500 | -0.146 | -1.621 | -2,350 | 0.759 | 8.588 | 8.115 | 0.481 |

**Event size (DC magnitude / theta)**

| event_size_bucket | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1.05-1.2 | 759 | 345 | 414 | 0.455 | 0.419 | 0.490 | -0.355 | -1.571 | -1,193 | 0.530 | 3.738 | 3.498 | 0.089 |
| 1.2-1.5 | 63 | 29 | 34 | 0.460 | 0.343 | 0.582 | -0.407 | -1.133 | -71.393 | 0.597 | 3.040 | 3.262 | 0.055 |
| <1.05 | 3328 | 1571 | 1757 | 0.472 | 0.455 | 0.489 | -0.219 | -1.443 | -4,801 | 0.697 | 5.810 | 5.592 | 0.331 |
| >=1.5 | 32 | 20 | 12 | 0.625 | 0.453 | 0.771 | -0.009 | -0.328 | -10.500 | 0.866 | 3.289 | 4.242 | 0.098 |

**Prior overshoot / theta**

| overshoot_bucket | n_trades | wins | losses | win_rate | win_rate_ci95_lo | win_rate_ci95_hi | expectancy_R | expectancy_points | total_points | profit_factor | avg_MAE_points | avg_MFE_points | median_hold_min |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| >=2.0 | 4182 | 1965 | 2217 | 0.470 | 0.455 | 0.485 | -0.245 | -1.453 | -6,075 | 0.674 | 5.373 | 5.166 | 0.276 |