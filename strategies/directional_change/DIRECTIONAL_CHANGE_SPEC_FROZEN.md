# DIRECTIONAL_CHANGE_SPEC_FROZEN.md

**Frozen baseline identifier**

    dcevent-1.0.0.impl3+d33e5d5d116f1adb

`spec_version` = `dcevent-1.0.0` · implementation version `3`
combined SHA-256 = `d33e5d5d116f1adb070c1abb9a52206d3d07809e6a3dbc65f36ea485883e53f9`
frozen at = `2026-08-20T00:56:54.897013+00:00`

Reproduce with `python scripts/p3_03_freeze.py`. The identifier is a SHA-256 over
the ordered `(path, file-sha256)` pairs below. If any of these files changes the
identifier changes and the result is a **different hypothesis**, which may not
inherit 2025-H2 as fresh validation.

## Frozen parameters

| parameter | value |
|---|---|
| `theta` | `0.5 x VU`, floor `1.0` pt |
| VU | ATR14 of completed 1-minute bars, floor `2.0` pt |
| `theta` sampling | at run start (previous confirmation), held for the run |
| DC-B `beta` | `0.5` x theta extension |
| DC-C `gamma` | `2.0` x theta prior overshoot |
| R | `= theta`, symmetric +-1R primary |
| entry latency | `250` ms |
| primary window | `09:30-11:30` ET |
| primary friction | `1.0` pt round trip |

## Frozen file manifest

| file | sha256 |
|---|---|
| `strategies/directional_change/config/baseline.yaml` | `1dfbdd1708656af544f219c3be94795b7dd8f44380f751f34db3d7e57d22e8a6` |
| `strategies/directional_change/DIRECTIONAL_CHANGE_SPEC.md` | `4ad6ea780e8759787c2243f14e6f0834190df956d2098397ef8c5dab80676e1f` |
| `strategies/directional_change/runner.py` | `6a50f4c2d296d33374959f68fe338d40b38e23497fe3772687654bf48fe2fe74` |
| `src/nqr/p3/holdout3.py` | `49174e467d8624cb2b860a61d7664716d038e60984907c8b72e8a0b1cb1ac21f` |
| `src/nqr/p3/cache3.py` | `8f1c06d171cf0ec5b05c0e94eaf16979876300389fcee55b10e611233329e63b` |
| `src/nqr/p3/dc_engine.py` | `eb3db748417b25495a4ebeaf6ef232782519dcb820514f30e899a32163733cec` |
| `src/nqr/p3/strategies.py` | `7456da60b25db89ea4bbc2500586d9712a32e10d7fd143939f1683470b823158` |
| `src/nqr/p3/fastpass.py` | `230056188e7604f4e7eca1440af9e7a1af381b9425e356c41e65926637ea2c5e` |
| `src/nqr/p2/features.py` | `3a13d59f980dc90fa4ab67cc91bd593ddd36fd1af339461ea054c7c14df6757c` |
| `src/nqr/backtest/engine.py` | `20b639972c944d708e10acb6e441f719f59e1c9fb122729cc9dbad77e938d555` |
| `src/nqr/sessions/calendar.py` | `cad87a736641eaddff692a4b1acf49c39555d9d98c0f0e640ec694e121d21e48` |
| `src/nqr/data/contracts.py` | `b8d8adf70cc3afc06cf0c24327f665b545c33cb2c2b426eea544762851529224` |
| `scripts/p3_01_events.py` | `6f9a005ce5ffb26d286e05c9606845001b6f43b54f19748bd4c5055a3335bf9a` |
| `scripts/p3_04_run.py` | `2f47114532180b10c787176953804e1bea80ec1b60b11017bcc4548f4ec4b1ae` |

## Pre-freeze engine audit (Phase 3A — event geometry only, NO P&L)

```
{
  "note": "PHASE 3A ENGINE AUDIT - event geometry only. No win rate, expectancy or P&L of any kind was computed before the freeze.",
  "split": "dev 2021-2023",
  "trading_days": 762,
  "n_events": 643758,
  "events_per_day_total": 844.8,
  "events_per_day_rth": 670.7,
  "events_per_day_primary_window": 234.5,
  "theta_points": {
    "p25": 2.83,
    "median": 4.06,
    "p75": 5.88
  },
  "theta_points_primary_window": {
    "p25": 3.94,
    "median": 5.6,
    "p75": 7.71
  },
  "implied_breakeven_wr_at_1pt_friction_primary": 0.5893,
  "direction_balance": {
    "1": 321863,
    "-1": 321895
  },
  "prev_overshoot_ratio": {
    "median": 0.676,
    "p75": 1.405,
    "p90": 2.356,
    "frac_ge_gamma_2.0": 0.1414
  },
  "dc_magnitude_over_theta": {
    "median": 1.032
  },
  "event_seconds": {
    "median": 22.8,
    "p90": 76.5
  },
  "causality_check": {
    "all_conf_idx_gt_ext_idx": true,
    "all_conf_ts_ge_ext_ts": true,
    "events_with_conf_ts_equal_ext_ts": 134,
    "events_with_conf_ts_equal_ext_ts_fraction": 0.000208,
    "explanation_of_equal_timestamps": "0.02% of events confirm within the SAME nanosecond as their extreme: one aggressive sweep produced several prints sharing a ts_event and crossed theta inside it. Ordering is by (ts_event, source row number), so conf_idx > ext_idx still holds strictly - the confirming print genuinely follows the extreme in exchange sequence order. No future information is used, and the 250 ms entry latency is applied from the confirmation timestamp regardless.",
    "all_dc_magnitude_ge_theta": true,
    "ext_to_conf_seconds": {
      "p1": 0.003,
      "median": 9.341,
      "p99": 59.6
    },
    "last_overshoot_per_day_left_unfinished": true
  }
}
```

## Freeze protocol

1. `DIRECTIONAL_CHANGE_SPEC.md` and `config/baseline.yaml` were completed before
   any strategy P&L existed.
2. Phase 3A validated the **event engine only**: event counts, theta scale and
   randomly sampled DC-sequence charts. No win rate, expectancy or P&L of any
   kind was computed before this freeze.
3. `theta` was left at the brief's named `0.50 x VU`. The cost arithmetic it
   implies (a ~60 % gross win rate needed at 1.0 pt friction, given a median
   primary-window theta near 4.8 pt) was measured from event geometry alone and
   is disclosed in the spec **before** validation rather than used to move the
   design or the gate.
4. No parameter grid was searched. The theta sensitivity grid is a
   post-baseline diagnostic and cannot change the baseline.
5. 2024 is a contaminated diagnostic and can never satisfy a PASS criterion.
6. Fresh validation (2025-H2) is unlocked only after this freeze and run once.
7. Only a genuine implementation **bug** may be fixed: document, regression-test,
   bump `impl_version`, rerun everything.

## Pre-registered PASS gate (restated, unchanged)

Fresh validation 2025-07-01 .. 2025-12-31 · 09:30-11:30 ET · 1R · 1.0 pt
round-trip friction · **each family separately**. All six required: trades >= 100;
win rate > 50 %; 95 % CI lower bound > 50 %; net expectancy > 0 R; profit factor
> 1.10; one-sided binomial p < 0.05. **If no family passes, PHASE 3 = FAIL.**
Failing families are never combined into a composite.
