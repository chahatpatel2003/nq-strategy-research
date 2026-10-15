# nq_strategy_research

Reproducible research framework for CME **NQ** futures strategies.
**Phase 1 = the published Fast-Slow Nasdaq-100 pattern, and nothing else.**

Verdict for Phase 1 is in `PHASE1_VERDICT.md`. Short version: **FAIL** on 2024
validation, with the infrastructure intact and the 2025+ holdout untouched.

---

## Layout

```
nq_strategy_research/
├── DATA_AUDIT.md              Phase 0 — what is in the T9 parquet files
├── FAST_SLOW_SPEC.md          the mechanical rule set (written BEFORE any P&L)
├── FAST_SLOW_SPEC_FROZEN.md   frozen identifier + file hash manifest
├── PHASE1_VERDICT.md          pre-registered verdict, applied
├── config/fast_slow_baseline.yaml    every frozen parameter
├── src/nqr/
│   ├── holdout.py             the 2025+ guard (raises HoldoutViolation)
│   ├── paths.py               T9 discovery, read-only
│   ├── sessions/calendar.py   Globex day, ASIA/EU/US/POST, DST via zoneinfo
│   ├── data/                  audit, contract/roll selection, tick cache
│   ├── bars/ levels/ signals/ backtest/ execution/ metrics/ viz/
├── strategies/fast_slow/runner.py    A-B-C + trigger assembly
├── scripts/                   00…06, the whole pipeline
├── tests/                     80 tests
├── data_cache/                derived (ticks ~2.1 GB, bars ~34 MB) — regenerable
├── results/                   trade logs, front map, verdict.json
└── reports/                   markdown reports + diagnostic charts
```

The original T9 parquet files are opened read-only and are **never** written to.
Everything derived lands under `data_cache/`, `results/`, `reports/`, `logs/`.

---

## Reproducing everything from scratch

Requires the Samsung T9 mounted at `/Volumes/T9`. Total wall time ≈ 12 min,
almost all of it the two full passes over ~400 M trade prints on USB.

```bash
cd nq_strategy_research

# 0. environment (Python 3.12; versions pinned in requirements-lock.txt)
uv venv --python 3.12 .venv
uv pip install polars pyarrow duckdb numpy pandas matplotlib scipy pyyaml pytest tzdata

# 1. Phase 0 — audit the raw data           (~7 min; writes results/data_audit.json
#    + results/contract_daily_volume.parquet)
.venv/bin/python scripts/00_audit.py

# 2. front-contract map, tick cache, 2-minute bars   (~3 min)
.venv/bin/python scripts/01_build_cache.py

# 3. test suite (must be green before any backtest is believed)
.venv/bin/python -m pytest tests/ -q

# 4. Stage A — development 2021-2023        (~5 s)
.venv/bin/python scripts/02_run_fast_slow.py --split dev
.venv/bin/python scripts/03_report.py --tag dev --title "Fast-Slow NQ — DEVELOPMENT 2021-2023"
.venv/bin/python scripts/04_charts.py --tag dev --variant ANY

# 5. Stage B — freeze  (prints the frozen identifier; must be
#    fastslow-1.0.0+5980044a44eebf7b for the results in this repo)
.venv/bin/python scripts/05_freeze.py

# 6. Stage C — validation 2024              (~2 s)
.venv/bin/python scripts/02_run_fast_slow.py --split val
.venv/bin/python scripts/03_report.py --tag val --title "Fast-Slow NQ — VALIDATION 2024"
.venv/bin/python scripts/04_charts.py --tag val --variant ANY

# 7. pre-registered verdict
.venv/bin/python scripts/06_verdict.py

# 8. end-of-phase integrity check (holdout untouched, T9 files unmodified,
#    frozen manifest still matches disk)
.venv/bin/python scripts/07_integrity_check.py
```

`scripts/01_build_cache.py` skips the tick cache if `data_cache/ticks` already
exists; delete that directory to force a rebuild.

### Outputs

| what | where |
|---|---|
| development report | `reports/REPORT_dev.md` |
| validation report | `reports/REPORT_val.md` |
| trade logs (parquet + CSV) | `results/fast_slow_{dev,val}/trades_{ANY,ENGULFING,PIN,STAR}.{parquet,csv}` |
| rejected A-B-C patterns | `results/fast_slow_{dev,val}/abc_rejects.parquet` |
| level segments | `results/level_segments_{dev,val}.parquet` |
| front contract / rolls | `results/front_map.parquet`, `results/roll_dates.parquet` |
| diagnostic charts | `reports/charts/{dev,val}_ANY/{winners,losers,skipped,rejected_abc}/` |
| verdict | `results/verdict.json` |

---

## Holdout policy

| period | status |
|---|---|
| 2021-01-01 → 2023-12-31 | development |
| 2024-01-01 → 2024-12-31 | validation (run once, after the freeze) |
| 2025-01-01 → 2025-06-30 | **SEALED** — trades *and* MBP-1 |
| 2025-07-01 → | **SEALED** — trades only |

`src/nqr/holdout.py` raises `HoldoutViolation` on any attempt to read a date, a
date range, or a filename in the sealed region, and every SQL query carries a
`trading_date < 2025-01-01` predicate. The guard is expressed on the **Globex
trading date**, not the UTC calendar date, so the 23:00–24:00 UTC tail of
2024-12-31 — which belongs to Globex day 2025-01-02 — is excluded as well.

Unlocking needs `--unlock-holdout`, which additionally requires the literal
confirmation string `I_AM_DELIBERATELY_UNSEALING_THE_HOLDOUT`. **Phase 1 never
passes it.** Verify at any time with:

```bash
.venv/bin/python -m pytest tests/test_holdout.py -q
.venv/bin/python -c "import polars as pl; b=pl.read_parquet('data_cache/bars/bars_2m.parquet'); print('max trading date:', b['trading_date'].max())"
```

---

## Design notes that matter

* **`ts_event` is the clock.** Prices are stored as `int32` ticks, so every
  level / stop / target comparison is exact.
* **Bars are half-open `[t, t+2min)` on the UTC epoch grid**, which coincides
  with even ET minutes in both EST and EDT. A bar is knowable only at its end.
* **All durations are wall-clock**, never bar counts, so untraded gaps cannot
  make a slow leg look fast.
* **One contract per Globex day**, chosen by the *previous* day's volume; all
  levels for that day come from the same contract. No back-adjustment, no
  splicing, roll days excluded.
* **Outcomes come from the raw tape, never from OHLC.** A resting limit needs
  the tape to trade *through* it by a tick — a touch is not a fill. A stop fills
  at the print that triggered it.
* **Entry is the first print ≥ trigger-bar close + 250 ms**, never the close.
* **Costs are never assumed away**: every table is reported at 0.0 / 0.5 / 1.0 /
  2.0 points of round-trip friction, always all four.

---

# Phase 2 — Candidate #2: impulse exhaustion / absorption reversal

Verdict in `strategies/impulse_exhaustion/PHASE2_VERDICT.md`.

```
strategies/impulse_exhaustion/
├── IMPULSE_EXHAUSTION_SPEC.md          mechanical rule set (written BEFORE any P&L)
├── IMPULSE_EXHAUSTION_SPEC_FROZEN.md   frozen id + file hash manifest
├── PHASE2_VERDICT.md                   pre-registered verdict, applied
├── config/baseline.yaml                every frozen parameter
├── runner.py                           day runner: features -> state machine -> trades
├── results/run_*/                      trade logs (parquet + CSV), rejects, controls
├── reports/                            reports, leakage audit, FUTURE_HYPOTHESES.md
└── diagnostics/charts_*/               random-sample charts
src/nqr/p2/                             cache2, signing, features, absorption,
                                        statemachine, controls, metrics2, charts
```

Phase 1 files are untouched; `scripts/p2_09_integrity.py` re-runs the Phase-1
integrity check and verifies the Phase-1 frozen id is unchanged.

## Reproducing Phase 2

```bash
# 1. caches: signed front-contract ticks (~3 min) and 1-second MBP-1 BBO (~75 min)
.venv/bin/python scripts/p2_01_build_cache.py --what ticks
.venv/bin/python scripts/p2_01_build_cache.py --what bbo

# 2. STEP 1 - verify the native aggressor field against a causal quote rule
.venv/bin/python scripts/p2_02_verify_signing.py --days 12

# 3. freeze BEFORE any P&L  (records the signing check and the count calibration)
.venv/bin/python scripts/p2_06_freeze.py     --count-check results/p2_count_calibration.json

# 4. tests
.venv/bin/python -m pytest tests/ -q

# 5. development 2021-2023, then validation 2024 (run once)
.venv/bin/python scripts/p2_03_run.py --split dev
.venv/bin/python scripts/p2_04_report.py --tag dev --title "Impulse Exhaustion — DEVELOPMENT 2021-2023"
.venv/bin/python scripts/p2_03_run.py --split val
.venv/bin/python scripts/p2_04_report.py --tag val --title "Impulse Exhaustion — VALIDATION 2024"

# 6. diagnostics
.venv/bin/python scripts/p2_05_charts.py  --tag dev
.venv/bin/python scripts/p2_07_controls.py --tag dev
.venv/bin/python scripts/p2_07_controls.py --tag val
.venv/bin/python scripts/p2_10_ablation.py dev
.venv/bin/python scripts/p2_11_leakage_audit.py

# 7. verdict + integrity
.venv/bin/python scripts/p2_08_verdict.py
.venv/bin/python scripts/p2_09_integrity.py
```

## Phase 2 design notes

* **Event-time causality.** Everything is ordered by `ts_event`. For a trade at
  `t` the BBO used is the last MBP-1 state with `ts_event < t` — strictly before,
  so quote lookahead is structurally impossible.
* **Aggressor side is verified, not assumed** against that causal quote rule on
  development days; inside-spread trades stay UNKNOWN (no tick-rule guessing).
* **VU** = ATR14 of *completed* 1-minute bars; the in-progress minute cannot
  leak its own range into the threshold that detects an event inside it.
* **Extremes are directional-change events**, published only when the θ
  retracement completes, and never at their own second.
* **Absorption is a proxy**, defined once: aggressive volume per tick of
  best-price advance, ranked against a bounded rolling window of strictly
  earlier same-direction legs. No global or full-day percentile.
* **Execution is Phase 1's engine verbatim** — trade-through limits, touch-fill
  stops, raw-tape first passage.

---

# Phase 3 — Candidate #3: directional-change / event-time

Verdict in `strategies/directional_change/PHASE3_VERDICT.md`. Short version:
**FAIL** on fresh 2025-H2 validation, decisively (15,583 trades, win-rate CI
±0.8 pp, excludes 50 %).

```
strategies/directional_change/
├── DIRECTIONAL_CHANGE_SPEC.md          rule set (written BEFORE any P&L)
├── DIRECTIONAL_CHANGE_SPEC_FROZEN.md   frozen id + file hash manifest
├── EVENT_ENGINE.md                     Phase-3A event-engine documentation
├── PHASE3_VERDICT.md                   pre-registered verdict, applied
├── config/baseline.yaml                every frozen parameter
├── runner.py                           ticks -> DC events -> signals -> trades
├── results/                            event logs, trade logs, controls, sensitivity
├── reports/                            reports, integrity audit, FUTURE_HYPOTHESES.md
└── diagnostics/                        random DC-sequence and per-trade charts
src/nqr/p3/                             holdout3, cache3, dc_engine, strategies,
                                        fastpass, metrics3, charts3
```

## Phase-3 period policy

| period | status |
|---|---|
| 2021-01-01 … 2023-12-31 | development |
| 2024-01-01 … 2024-12-31 | **CONTAMINATED DIAGNOSTIC** — consumed as validation by Phases 1–2; never counts toward a Phase-3 PASS |
| 2025-01-01 … 2025-06-30 | **SEALED** — no unlock path exists in Phase 3; the last period with both Trades and MBP-1 |
| 2025-07-01 … 2025-12-31 | fresh validation — narrow explicit unlock, run once |
| 2026-01-01 … | **SEALED** — no unlock path exists in Phase 3 |

`src/nqr/p3/holdout3.py` enforces this. The unlock opens 2025-H2 **and nothing
else**: 2025-H1 and 2026 are refused by the date guard, the file guard and the
month loader even while it is active.

## Reproducing Phase 3

```bash
# 1. PHASE 3A - event engine only (no strategy, no P&L)
.venv/bin/python scripts/p3_01_events.py --split dev --tag engine_audit
.venv/bin/python scripts/p3_02_event_charts.py --split dev --n 20

# 2. freeze BEFORE any P&L
.venv/bin/python scripts/p3_03_freeze.py --impl-version 3     --engine-audit results/p3_engine_audit.json

# 3. tests (Phase 1 + 2 + 3)
.venv/bin/python -m pytest tests/ -q

# 4. development, then the 2024 contaminated diagnostic
.venv/bin/python scripts/p3_04_run.py --split dev
.venv/bin/python scripts/p3_05_report.py --tag dev --title "Directional Change — DEVELOPMENT 2021-2023"
.venv/bin/python scripts/p3_04_run.py --split diag2024
.venv/bin/python scripts/p3_05_report.py --tag diag2024 --title "Directional Change — 2024 CONTAMINATED DIAGNOSTIC (NOT VALIDATION)"

# 5. controls, sensitivity, charts
.venv/bin/python scripts/p3_06_controls.py --tag dev --split dev
.venv/bin/python scripts/p3_07_sensitivity.py --stride 3
.venv/bin/python scripts/p3_08_charts.py --tag dev

# 6. FRESH VALIDATION - only after the freeze, run once
.venv/bin/python scripts/p3_09_build_validation_cache.py     --confirm "I_AM_UNLOCKING_ONLY_2025_H2_FOR_PHASE3_VALIDATION"
.venv/bin/python scripts/p3_04_run.py --split val2025h2 --unlock-validation
.venv/bin/python scripts/p3_05_report.py --tag val2025h2 --title "Directional Change — FRESH VALIDATION 2025-H2"
.venv/bin/python scripts/p3_06_controls.py --tag val2025h2 --split val2025h2 --unlock-validation
.venv/bin/python scripts/p3_08_charts.py --tag val2025h2 --unlock-validation

# 7. verdict + integrity
.venv/bin/python scripts/p3_10_verdict.py
.venv/bin/python scripts/p3_11_integrity.py
```

## Phase-3 design notes

* **Causality is the whole point.** An extreme is not known to be an extreme
  until price retraces θ from it, so every signal is stamped at the
  *confirmation*, never at the extreme. Enforced structurally
  (`conf_idx > ext_idx`) and tested by truncating the price path at each
  confirmation and by overwriting all later prices.
* **Trades only.** MBP-1 is untouched, preserving 2025-H1 for order-flow work.
* **θ = 0.50 × VU**, sampled once at each run start and held for that run.
* **R = θ**, a pure distance from the entry — never a historical extreme.
* **`src/nqr/p3/fastpass.py`** is a chunked first-passage resolver asserted
  equal to the frozen Phase-1 engine on 40 randomised tapes.
* **Corrected no-edge baseline** (finding `H3-02`): with realistic fills — an
  adverse entry slippage and a limit that must trade *through* by a tick — a
  symmetric ±1R bracket has an empirical no-edge win rate near **48 %**, not
  50 %. Use the matched-random control as the comparator, not the theoretical
  50 %.

# Phase 4 — Candidate #4: causal state / sequence discovery

**Verdict: FAIL** (at the development stage) · frozen id
`statedisc-1.0.0+c147134184dfb32d` ·
`strategies/state_discovery/PHASE4_VERDICT.md`

The first *discovery* phase rather than a hand-invented pattern: a bounded,
preregistered search over 55 causal features of the NQ trade tape, asking
whether any recurring market state beats matched-random entries after realistic
costs. It does not.

* **55 registered causal features** across 9 families (cap 60), all trailing and
  closed at the decision timestamp. Registry written before any label existed.
* **5-second decision clock**, 09:30–11:30 ET, 1440 decisions/day.
* **R = 0.50 × ATR14(completed 1-min)**, clipped to [1, 25] pt; ±1R bracket;
  30-minute maximum hold; one position at a time.
* **18 configurations, hard-capped** — 2 model families × 3 hyperparameters × 3
  thresholds — selected on 2022 alone by a criterion fixed in advance.
* **Trades only.** MBP-1 was never opened; family 6 uses the native Databento
  aggressor field on the strength of the archived Phase-2 verification.

## Result

| period | trades | WR | E[R] @1.0 pt | PF | Δ vs matched random |
|---|---:|---:|---:|---:|---|
| 2021 train | 34,653 | 49.08 % | −0.2428 | 0.689 | CI contains 0 |
| 2022 selection | 37,667 | 50.23 % | −0.1395 | 0.798 | **CI excludes 0** |
| 2023 internal OOS | 36,145 | 48.26 % | −0.2449 | 0.671 | CI contains 0 |
| 2024 *contaminated* | 36,092 | 49.00 % | −0.1986 | 0.729 | CI contains 0 |
| 2025-H2 *contaminated* | 18,000 | 49.33 % | −0.1745 | 0.762 | CI contains 0 |

162,557 trades, 1,145 trading days. All 18 configurations were negative on 2022;
the winner is the least-negative of a uniformly losing set.

**2026-Q1 fresh validation was deliberately NOT spent, and Phase 4 is CLOSED on
the development result.** Development fails four of the seven hard gates by a
wide margin and the gross result is also ≤ 0, so a validation run could only
confirm an arithmetically determined FAIL. The quarter stays pristine and is
reserved for the larger-R hypothesis (H4-1). See `PHASE4_VERDICT.md` §6.

## Phase-4 findings worth carrying forward

* **There is no gross edge.** At *zero* friction the strategy is −0.013 to
  −0.030 R in four of five periods (+0.0025 R on the selection year). Friction
  did not destroy an edge; there was none to destroy.
* **A real state signal exists and is ~7× too small.** Control C4 (permute the
  training target within trading days, refit, rescore 2022) puts the null at
  −0.1592 ± 0.0043 R against an observed −0.1395 R — 0 of 20 permutations reach
  it. The learned signal is worth ~0.02 R/trade; friction at
  R ≈ 7 pt costs ~0.14 R/trade.
* **R is the binding constraint, not the features.** Median hold ~30 s and ~140
  trades/day. Break-even on the measured signal would need R ≈ 50 pt.
* **Confidence is not monotone in outcome.** The most confident *short* bucket
  is the worst in all five periods and underperforms its own matched control.
* **Trade-side/delta contributed exactly zero** at this horizon — a clean
  negative on trades-derived order flow, and not a statement about MBP-1.

## Reproducing Phase 4

```bash
python -m pytest tests -q                                   # 284 tests

python scripts/p4_01_build_dataset.py --split dev --workers 5   # ~35 s
python scripts/p4_02_develop.py                             # 2021 fit, 2022 select
python scripts/p4_03_run_split.py --split itest2023          # 2023, once
python scripts/p4_04_freeze.py                              # -> frozen id

python scripts/p4_00_build_caches.py --split contam2025h2
python scripts/p4_01_build_dataset.py --split contam2024 --workers 5
python scripts/p4_01_build_dataset.py --split contam2025h2 --workers 5
python scripts/p4_03_run_split.py --split contam2024
python scripts/p4_03_run_split.py --split contam2025h2

python scripts/p4_05_null_c4.py
python scripts/p4_06_calibration.py
python scripts/p4_07_charts.py
python scripts/p4_08_report.py && python scripts/p4_08b_report.py
python scripts/p4_09_integrity.py
```

## Phase-4 period policy

    2021        DISCOVERY_TRAIN   fit, scaler, threshold calibration
    2022        SELECTION         the 18 configurations, once
    2023        INTERNAL_TEST     scored once, after the choice
    2024        CONTAM_2024       diagnostic only
    2025-H1     SEALED            no unlock path exists (Trades + MBP-1)
    2025-H2     CONTAM_2025H2     diagnostic only
    2026-Q1     FRESH_VAL         narrow one-shot unlock — NOT SPENT
    2026-04-01+ SEALED_FINAL      no unlock path exists

`src/nqr/p4/holdout4.py` has exactly one unlock function, scoped to 2026-Q1;
2025-H1 and 2026-04-01+ stay blocked even while it is active. Note that
`2026_H1.parquet` physically extends to 2026-06-17, so every read of it carries
a trading-date predicate that refuses any range reaching 2026-04-01.

# Phase 5 — Candidate #5: larger-R causal state

**Verdict: FAIL** (before fresh validation) ·
`strategies/larger_r/PHASE5_VERDICT.md`

A post-Phase-4 hypothesis: Phase 4 measured a real but tiny state signal
(~0.02 R/trade) against friction costing 0.14 R/trade at R ≈ 7 points, so
**H5** asked whether the *same* state becomes tradable at a materially larger R
where friction is 2–5 % of R instead of 14 %.

* **Same 55 causal features**, imported read-only from the frozen
  `nqr.p4.features4`. None added, none removed.
* **Volatility-normalised R** at 2.0 / 3.0 / 4.0 × ATR14(completed 1-min) —
  chosen over fixed points because the dev-year session-median ATR spans 1.59×
  while price spans only 1.19×.
* **60-second clock** (120 decisions/day), **60-minute hold**, executable
  timeout, one position at a time plus a one-interval cooldown.
* **18 configurations, hard-capped** — 3 R scales × 2 families × 3 selectivity
  levels — selected on 2022 alone.
* **Signal = edge over a training-only control baseline**, per half-hour bucket
  and direction, never against theoretical 50 %.

## Result

| period | trades | WR | gross E[R] | net E[R] @1.0 | PF(R) | Δ vs matched random |
|---|---:|---:|---:|---:|---:|---|
| 2021 train | 105 | 61.90 % | +0.2241 | +0.1875 | 1.569 | −0.081 [−0.193, +0.027] |
| 2022 selection | 128 | 56.25 % | +0.1173 | +0.0943 | 1.261 | +0.058 [−0.027, +0.148] |
| **2023 internal OOS** | 93 | 49.46 % | −0.0049 | **−0.0379** | 0.911 | **−0.131 [−0.247, −0.002]** |
| 2024 *contaminated* | 83 | 55.42 % | +0.1117 | +0.0826 | 1.241 | +0.003 [−0.128, +0.137] |
| 2025-H2 *contaminated* | 56 | 53.57 % | +0.0558 | +0.0292 | 1.076 | −0.010 [−0.199, +0.160] |

The candidate failed **all four** preregistered Gate-F criteria on 2023, so it
was never frozen and **2026-Q1 was never opened** — no Phase-5 code read a single
2026 row.

## What Phase 5 established

* **The friction/R architecture works.** Friction fell from 0.1435 R/trade to
  **0.0296 R** (4.8×), median hold went from 0.4 min to 27 min, max drawdown from
  thousands of R to 4.5–7.9 R, profitable days from 2–7 % to 45–56 %, and **gross
  expectancy turned positive in 4 of 5 periods**. Phase 4's binding constraint is
  gone. This is *not* "edge destroyed by cost".
* **The signal picks the right context and the wrong minute.** Unconditional
  rows return −0.024 R; the model's *day + half-hour + direction* with a **random
  minute** returns +0.037 to +0.269 R in every period; adding the model's own
  chosen minute gives that back in three of five. The timing is adverse, not
  merely uninformative. (`FUTURE_HYPOTHESES.md` H5-1 — the strongest thread
  either phase has produced.)
* **Trade side / delta is uninformative for the second time**, now at a second
  horizon — mean |coef| 0.048 vs 0.056 overall, delta quartiles flat within
  0.007 R. Two independent horizons, same answer. Says nothing about MBP-1.
* **The larger horizon chose better features**: session location and clock
  position dominate, and the elastic-net preferred the *stationary*
  `atr_pct_rank` over the raw `atr1m` that dominated and broke Phase 4.

## Reproducing Phase 5

```bash
python -m pytest tests -q                                    # 335 tests

python scripts/p5_01_build_dataset.py --split dev --workers 5   # ~25 s
python scripts/p5_02_develop.py                              # 2021 fit, 2022 select, Gate E
python scripts/p5_03_run_split.py --split itest2023           # Gate F -> REJECTED
python scripts/p5_03_run_split.py --split train2021
python scripts/p5_03_run_split.py --split select2022

python scripts/p5_01_build_dataset.py --split contam2024 --workers 5
python scripts/p5_01_build_dataset.py --split contam2025h2 --workers 5
python scripts/p5_03_run_split.py --split contam2024
python scripts/p5_03_run_split.py --split contam2025h2

python scripts/p5_04_diagnostics.py                          # time / market-state tables
python scripts/p5_05_charts.py
python scripts/p5_06_report.py && python scripts/p5_06b_report.py
python scripts/p5_09_integrity.py
```

## Phase-5 period policy

    2021        DISCOVERY_TRAIN   models, scaler, control baseline, thresholds
    2022        SELECTION         the 18 configurations, once, + Gate E
    2023        INTERNAL_TEST     scored once -> Gate F failed -> candidate rejected
    2024        CONTAM_2024       diagnostic only
    2025-H1     SEALED            no unlock path exists (Trades + MBP-1)
    2025-H2     CONTAM_2025H2     diagnostic only
    2026-Q1     FRESH_VAL         NEVER OPENED
    2026-04-01+ SEALED_FINAL      no unlock path exists

`src/nqr/p5/holdout5.py` is stricter than Phase 4's: one unlock function scoped
to 2026-Q1, and `assert_path_allowed` additionally refuses any path containing
`mbp1` and any raw `.dbn`/`.dbn.zst` archive. `sql_window_guard` raises *before*
emitting a predicate for any window reaching 2026-04-01, which matters because
`2026_H1.parquet` physically runs to 2026-06-17.

# Phase 6 — Candidate #6: context + entry timing

**Verdict: FAIL** (before fresh validation) ·
`strategies/context_entry/PHASE6_VERDICT.md`

Phase 5 appeared to show the direction model finding good *context* and timing
entries badly. Phase 6 was built to monetise that — and began, as the brief
required, by auditing whether the Phase-5 decomposition was causal.

**It was not.** `nqr.p5.backtest5.matched_controls` drew control entries from the
whole 30-minute bucket and handed each the direction of a signal that, for
**44.1 %** of them, had not yet fired — median 6–8 minutes early, up to 29.
Restricting the draw to minutes at or after the signal halves the apparent
context return (+0.1034 → +0.0521 R) and flips the strategy-vs-control count from
2-of-5 to 3-of-5 periods. See `CONTEXT_CAUSALITY_AUDIT.md`.

Phase 6 therefore rebuilt the context from scratch, causally: inside each of four
30-minute buckets the **first** qualifying signal activates, direction is
**locked**, R is locked, one context per bucket, expiring at bucket end.

## Result — two independent failures

**The causal context does not survive.** Random minutes inside a context vs
random minutes in a no-context bucket on the same day:

| | in-context | non-context | diff | 95 % day-block CI |
|---|---:|---:|---:|---|
| all five periods | +0.0711 | −0.0040 | +0.0752 | [−0.0234, +0.1721] |
| **excluding 2021** | **+0.0220** | **+0.0513** | **−0.0293** | [−0.1440, +0.0848] |

2021 is the year the context model was fitted; it is the only period whose CI
excludes zero.

**And no entry mechanic beat random timing inside the context:**

| method | n | net E[R] | PF(R) | periods +ve | advantage vs random | 95 % CI |
|---|---:|---:|---:|---:|---:|---|
| E1 — 5 min delay | 369 | +0.0270 | 1.067 | 3/5 | −0.0442 | [−0.1064, +0.0173] |
| E2 — 10 min delay | 328 | +0.0043 | 1.010 | 2/5 | **−0.0669** | **[−0.1350, −0.0006]** |
| E3 — 0.25 R pullback | 323 | +0.0641 | 1.161 | 3/5 | −0.0070 | [−0.0846, +0.0712] |
| E4 — 0.50 R pullback | 227 | −0.0197 | 0.957 | 2/5 | −0.0909 | [−0.1960, +0.0110] |
| E5 — 0.25 R + resume | 321 | +0.0464 | 1.115 | 3/5 | −0.0247 | [−0.1002, +0.0511] |
| E6 — 0.50 R + resume | 221 | −0.0219 | 0.952 | 1/5 | −0.0931 | [−0.1982, +0.0099] |
| **CONTROL_RANDOM** | 4,484 | **+0.0711** | 1.194 | — | *(the null)* | — |

502 contexts over 1,145 days. No mechanic reached 4-of-5 positive periods or a
positive advantage lower bound, so **2026-Q1 stays sealed**.

## The mechanism

| method | price improvement (R) | adverse excursion before entry (R) | net |
|---|---:|---:|---:|
| E3 | +0.2573 | 0.2786 | −0.0213 |
| E4 | +0.5036 | 0.5296 | −0.0260 |

A mechanic only gets a better price when the market has already moved against the
context, and at both depths the discount is within **0.03 R** of the adverse
excursion it costs. Clock delays are strictly worse — they absorb 0.49–0.70 R and
are paid 0.04–0.07 R. Inside a context, **earlier is better**.

## Reproducing Phase 6

```bash
python -m pytest tests -q                                    # 369 tests

python scripts/p6_00_fingerprint.py
for s in train2021 select2022 itest2023 contam2024 contam2025h2; do
    python scripts/p6_01_run_split.py --split $s
done
python scripts/p6_02_analyse.py                              # context + gates -> FAIL
python scripts/p6_03_diagnostics.py
python scripts/p6_04_charts.py
python scripts/p6_05_report.py && python scripts/p6_05b_report.py
python scripts/p6_09_integrity.py
```

## Phase-6 period policy

Because the hypothesis is post-hoc, **all five pre-2026 periods are development**
and none is out-of-sample; `holdout6.role_of` says so explicitly. 2021 is
additionally in-sample for the context model. The guard has its own unlock phrase
(a Phase-5 confirmation string is rejected), refuses `mbp1` and raw `.dbn`, and
`p6_09_integrity.py` asserts no Phase-6 module calls `read_parquet` at all.

# Phase 7 — Candidate #7: MBP-1 order-book state discovery

**Verdict: FAIL** (before 2023, before 2024, before the holdout) ·
`strategies/orderbook_state/PHASE7_VERDICT.md`

The first phase whose primary information source is **not** trades and price.
222 GB / 7.89 billion rows of Databento MBP-1 top-of-book, scanned once into a
causal per-second cache.

* **40 registered causal features** (hard cap, exactly reached) over 1/5/15-second
  windows: BBO state, imbalance persistence, microprice pressure, quote-update
  intensity, Cont–Kukanov–Stoikov OFI, size depletion/replenishment, price-level
  steps, trade aggression, replenishment-after-aggression, failure-to-advance,
  minimal context.
* **5-second clock**, 09:30–11:30 ET, fixed **R = 15 pt and 25 pt**, 1R/1R,
  15-minute hold. friction/R = 0.0667 / 0.0400.
* **12 configurations, hard-capped**, trained on 2021, selected on 2022.
* Event ordering `(ts_event, sequence, file_row_number)` — `sequence` is monotone
  but **not unique** (12,283 of 592,404 sampled timestamps have ties it can't
  break, because a sweep emits multiple `T` rows sharing both fields).

## Result — three independent negatives

| gate | passing |
|---|---:|
| G1 sample ≥ 200 | 9 / 12 |
| **G2 net expectancy > 0** | **0 / 12** |
| **G3 PF(R) > 1.10** | **0 / 12** |
| **G4/G5 beats matched random** | **0 / 12** |
| G6 gross expectancy > 0 | 1 / 12 |

**No gross edge**: the least-bad configuration returns **+0.0011 R at zero
friction** against an unconditional baseline of −0.0448 R.

**Does not beat matched random on either causal control**: cross-day
−0.0032 R (CI [−0.0448, +0.0396]); same-day-forward +0.0072 R (CI [−0.0257,
+0.0399]). Control causality is asserted at **runtime** — the direct fix for the
defect Phase 6 found in Phase 5.

**The nulls say there was never a relationship**: a permutation null (50 refits,
permuted within training days) sits at −0.0266 ± 0.0114 against an observed
−0.0389 — the real model is **1.1 σ on the wrong side, p(null ≥ observed) = 0.84**.
And a +7-day temporal shift changes the result by **0.0001 R**.

## The central question, answered carefully

| ablation arm | features | net E[R] | vs doing nothing |
|---|---:|---:|---:|
| A0 full | 40 | −0.0389 | **+0.0059** |
| A1 quote-only | 32 | −0.0611 | −0.0162 |
| A2 trades + context | 8 | −0.1173 | −0.0724 |

`A0 − A2 = +0.0784 R`, CI [+0.0082, +0.1605] — excludes zero. **Reported alone
that looks like a discovery; it isn't.** The comparison is against an arm worse
than doing nothing. The book features outperform a trades-and-price model by
returning it to the level of no model at all.

> **Phase 7 did not establish incremental tradable information from MBP-1.**

## Findings worth carrying forward

* **The negative is about the TOP OF BOOK only.** MBP-1 has one level and no order
  IDs, so queue position, order lifetime, hidden liquidity and book shape were
  never tested. Testing them needs MBP-10 or MBO data this project does not have.
* **OFI carries 1.2 % of coefficient mass** — an L1 model with all three horizons
  available nearly discarded the canonical top-of-book predictor. The largest
  coefficient is `bid_px_chg_per_s_15` (−0.106), quote *churn*, not pressure.
* **The NQ spread is degenerate**: 2021 quartile edges are [2, 2, 2] ticks.
* **Three phases have now found trades-derived flow uninformative** (4, 5, 7); here
  the trades-only arm is 0.072 R *worse* than not trading.
* **93 % of trades are short** — matching Phases 5 (93 %) and 6 (70 %) in entirely
  different models. Now a three-phase pattern, and flagged as a possible artefact
  of the shared 1R/1R label construction (H7-5).

## Reproducing Phase 7

```bash
python -m pytest tests -q                                       # 423 tests

python scripts/p7_01_build_book_cache.py --split dev             # ~60 min, 222 GB
python scripts/p7_02_build_dataset.py --split dev --workers 5    # ~26 s
python scripts/p7_03_develop.py                                  # 12 configs -> FAIL
python scripts/p7_05_diagnostics.py                              # ablation + N1 + N2
python scripts/p7_06_audit_charts.py                             # book-sequence audit
python scripts/p7_07_report.py && python scripts/p7_07b_report.py
python scripts/p7_09_integrity.py
```

## Phase-7 period policy

    2021        TRAIN        scaler, models, selectivity quantiles, control edges
    2022        SELECT       the 12 configurations, once -> all failed
    2023        ITEST        NEVER SCORED (the phase failed before it)
    2024        CONTAM       never opened (post-freeze only; there was no freeze)
    2025-H1     FRESH_VAL    SEALED - the last MBP-1 window that exists
    2025-H2     NOT_PHASE7   refused; no MBP-1 file exists
    2026+       FORBIDDEN    NO PHASE-7 UNLOCK PATH AT ALL

`src/nqr/p7/holdout7.py` has one unlock, scoped to 2025-H1; 2025-H2 and 2026 stay
refused even while it is active. Only parquet-footer metadata was ever read from
2025-H1 — no row was decoded.

## Next phases (NOT built yet)

Fast-Slow was established-strategy candidate #1 and it failed. The framework —
data audit, tick cache, bars, sessions, levels, tick-exact backtester, metrics,
charts, holdout guard — is strategy-agnostic and stays. Later candidates, each
to be treated as its own pre-registered hypothesis: impulse exhaustion /
absorption, failed-continuation reversal, directional-change / event-time,
automated price-sequence discovery, and MBP-1 order-flow (for which the sealed
2025-H1 period exists in both schemas).
