# PHASE2_LEAKAGE_AUDIT.md

Generated 2026-08-20T00:09:33.360716+00:00 by `scripts/p2_11_leakage_audit.py`.

Automated test result: **`50 passed in 0.52s`**

## The ten required verifications

| # | claim | status | evidence |
|---|---|---|---|
| 1 | Every rolling feature is trailing-only | ✅ | `rolling_min`/`rolling_max` use polars trailing windows; unit-tested that mutating future samples cannot change a past value (`test_rolling_min_is_trailing_only`, `test_rolling_max_is_trailing_only`). |
| 2 | Every percentile uses past data only | ✅ | `TrailingPercentile` is a bounded deque of the last 2000 same-direction legs; a leg's rank is taken BEFORE it is pushed (`test_leg_never_ranks_against_itself`), and the window is capped so it can never become a whole-sample statistic (`test_absorption_history_is_not_a_full_day_or_global_statistic`). |
| 3 | No full-day statistic is used intraday | ✅ | The only cross-observation statistic in the strategy is the absorption percentile, which is a rolling deque that is never reset or recomputed per day. VU is a 14-minute trailing ATR. No daily high/low, daily VWAP or session aggregate enters any gate. |
| 4 | No future BBO is used to classify trades | ✅ | For a trade at ts_event = t the quote used is the last MBP-1 state with ts_event < t, STRICTLY before (`test_quote_used_is_strictly_before_the_trade`, `test_future_quotes_cannot_change_a_past_classification`). Inside-spread trades stay UNKNOWN - there is no tick-rule fallback. |
| 5 | Extremes become available only when causally confirmed | ✅ | Directional-change extremes are published at the second the theta retracement completes, and confirmation additionally requires conf_idx > ext_idx so that a single second which both sets and appears to retrace an extreme does not confirm (`test_dc_extremes_are_never_published_at_their_own_index`, `test_same_bar_extreme_and_retrace_does_not_confirm`). |
| 6 | Entry occurs strictly after confirmation | ✅ | Entry is the first print with ts_event >= signal bar close + 250 ms; asserted on every accepted trade in the trade-log audit below. |
| 7 | TP/SL uses raw event sequencing | ✅ | Phase-1 `nqr.backtest.engine.resolve` walks the tick tape; limits need a trade-through of one tick, stops fill at the triggering print. No OHLC inference anywhere (Phase-1 tests `test_p2`/`test_execution`). |
| 8 | Contract selection is causal | ✅ | Front contract for day D is the volume leader of day D-1 (`test_front_contract_choice_is_causal`); roll days are excluded. |
| 9 | Validation did not influence the frozen design | ✅ | The spec and config were completed and hashed before any P&L. The pre-freeze check computed SIGNAL COUNTS ONLY (results/p2_count_calibration.json) and left the configuration unchanged. Validation was run once. |
| 10 | 2025+ remains sealed | ✅ | p2 tick cache max month = 2024-12; p2 BBO cache max month = 2024-12; every SQL query carries a Globex-trading-date guard (`test_sql_guard_still_active_and_on_trading_date`). |

## Trade-signing verification (STEP 1) — development days only

The native Databento `side` field was NOT assumed. It was compared against a
causal quote rule rebuilt from MBP-1, using for each trade the last top-of-book
state **strictly before** that trade's `ts_event`.

| metric | value |
|---|---|
| days_sampled | 12 |
| total_trades | 3882888 |
| total_unambiguous | 3882344 |
| total_agree | 3882282 |
| total_disagree | 62 |
| overall_agreement_rate | 0.9999840302662515 |
| mean_inside_spread_frac | 0.00013300190548794832 |
| native_unknown_frac | 0.0 |
| native_buy_frac | 0.5016740749512959 |

## Trade-log causality audit

Asserted on every accepted trade of every completed run:

| check | dev | val |
|---|---|---|
| accepted | 161 | 45 |
| entry_after_signal_plus_latency | ✅ | ✅ |
| exit_at_or_after_entry | ✅ | ✅ |
| signal_after_arm | ✅ | ✅ |
| arm_after_impulse_end | ✅ | ✅ |
| extreme_at_or_before_arm | ✅ | ✅ |
| leg_confirms_before_arm | ✅ | ✅ |
| stop_is_4_ticks_beyond_extreme | ✅ | ✅ |
| R_equals_entry_minus_stop | ✅ | ✅ |
| max_trading_date | 2023-12-27 | 2024-12-27 |

## Residual known imprecisions (disclosed, not hidden)

* **Intra-second ordering.** Trades and quotes are aligned at nanosecond
  `ts_event` resolution, but the 1-second feature grid cannot resolve the order
  of a high and a low inside one second. Every such ambiguity is resolved the
  conservative way: directional-change confirmation is deferred to a strictly
  later second. This can only delay information.
* **`ts_event > ts_recv`** on a minority of 2023 rows (max ~125 ms, Phase-0
  finding). Immaterial against the 250 ms modelled execution latency.
* **Absorption is a proxy.** MBP-1 exposes only the top of book. Queue position,
  hidden liquidity and order-level absorption are **not observable** and are not
  claimed. The measured quantity is aggressive volume per tick of best-price
  advance, nothing more.
* **2R/1.5R/1.25R diagnostics share the 1R book's occupancy**, because they are
  evaluated on the same accepted entries. A standalone 2R strategy would take
  somewhat fewer trades.
