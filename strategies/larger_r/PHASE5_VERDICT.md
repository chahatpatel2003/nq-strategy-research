# PHASE5_VERDICT.md — NQ Larger-R Causal State Strategy

    spec            largerr-1.0.0
    candidate       r4p0:A_logit:top2  (rejected, never frozen)
    budget spent    18 of 18 configurations
    verdict         FAIL  (before fresh validation)
    validation      2026-Q1 NOT OPENED — no Phase-5 code ever read a 2026 row
    phase status    CLOSED

---

## 1. The verdict

# FAIL

Phase 5 tested whether the 55-feature causal state becomes economically tradable
at a materially larger price horizon. **It does not** — not because friction ate
the edge, but because the state's minute-level entry timing never separates from
a random entry placed in the same context.

The failure is decided entirely on development data. The preregistered Gate F
was applied to the 2023 internal out-of-sample test, all four criteria failed,
and per `PHASE5_SEARCH_BUDGET.md` §6 that ends the phase. **2026-Q1 stays
sealed.**

## 2. Gate F, on the 2023 internal out-of-sample test

| requirement | value | result |
|---|---|:---:|
| net expectancy > 0 R | **−0.0379 R** | **FAIL** |
| profit factor > 1.05 | **0.911** in R units (1.256 on points) | **FAIL** |
| advantage over matched random > 0 | **−0.1307 R**, CI [−0.2471, −0.0017] | **FAIL** |
| ≥ 100 executed trades | **93** | **FAIL** |

The advantage interval lies entirely below zero: on the one development year it
had never seen, the candidate is **significantly worse** than random entries
matched on day, half-hour and direction.

## 3. What was run

| stage | period | trades | WR | gross E[R] | net E[R] @1.0 | PF(R) | Δ vs matched (95 % CI) |
|---|---|---:|---:|---:|---:|---:|---|
| fit | 2021 | 105 | 61.90 % | +0.2241 | +0.1875 | 1.569 | −0.0813 [−0.193, +0.027] |
| **selection** | **2022** | 128 | 56.25 % | +0.1173 | +0.0943 | 1.261 | +0.0576 [−0.027, +0.148] |
| **internal OOS** | **2023** | 93 | 49.46 % | −0.0049 | −0.0379 | 0.911 | −0.1307 [−0.247, −0.002] |
| contaminated | 2024 | 83 | 55.42 % | +0.1117 | +0.0826 | 1.241 | +0.0034 [−0.128, +0.137] |
| contaminated | 2025-H2 | 56 | 53.57 % | +0.0558 | +0.0292 | 1.076 | −0.0103 [−0.199, +0.160] |

465 trades over 1,145 trading days. **The advantage CI contains zero in every
period**, and is negative in three of five.

## 4. What Phase 5 got right — the mechanical hypothesis is confirmed

| | Phase 4 | Phase 5 |
|---|---:|---:|
| average R | 7.0 pt | **44 pt** |
| **friction cost per trade** | **0.1435 R** | **0.0296 R** |
| median hold | 0.4 min | **27 min** |
| trades/day | ~140 | **0.40** |
| max drawdown | thousands of R | **4.5–7.9 R** |
| longest losing streak | 14–131 | **3–7** |
| profitable days | 2–7 % | **45–56 %** |
| **gross expectancy** | ≈ 0 or negative everywhere | **positive in 4 of 5 periods** |

Enlarging R cut the friction burden **4.8×**, exactly as designed, and gross
expectancy turned positive. Phase 4's binding constraint is gone.

**So this is not a case of "edge destroyed by cost."** Friction was reduced to
2.4–4.7 % of R and the strategy still failed.

## 5. Why it failed — the decomposition

Three nested populations, net R at 1.0 pt, R = 4.0 × ATR14(1m):

| what is being selected | 2021 | 2022 | 2023 | 2024 | 2025-H2 |
|---|---:|---:|---:|---:|---:|
| nothing — every row, either direction | −0.029 | −0.018 | −0.027 | −0.023 | −0.020 |
| model's **day + half-hour + direction**, random minute | **+0.269** | **+0.037** | **+0.093** | **+0.079** | **+0.040** |
| plus the model's own chosen minute | +0.188 | +0.094 | −0.038 | +0.083 | +0.029 |

The first step up is large and present in **every** period. The second step is
*down* in three of five, significantly so on 2023.

> **The signal identifies favourable (day, half-hour, direction) contexts. Its
> 60-second timing inside them is adverse.**

The unconditional bracket is negative at every R scale (−0.024 to −0.049 R), so
the positive middle row is not a geometry artefact — it is real context
selection that the strategy then gives back at the entry.

This is the single most useful thing Phase 5 produced. It is
`FUTURE_HYPOTHESES.md` H5-1.

## 6. Supporting findings

* **The opposite-direction control is worse in every period** (−0.05 to −0.26 R),
  significantly so on 2021 — consistent with the decomposition, since the matched
  control inherits the model's direction and is also positive. Nothing is flipped:
  an inverse or direction-only strategy is a new hypothesis needing new data.
* **The larger horizon selected better features than Phase 4 did.** The
  elastic-net leans on session location and clock position —
  `dist_or30_lo_norm` (−0.345), `secs_since_open` (+0.333), `dist_open_norm`
  (+0.292) — and prefers the *stationary* `atr_pct_rank` (+0.117) over the raw
  `atr1m`, which does not reach the top 15. Phase 4's tree had put 39.7 % of its
  weight on raw `atr1m` and did not generalise.
* **Trade side / delta is uninformative for the second time**, now at a second
  horizon: mean |coefficient| 0.048 against 0.056 overall, `delta_accel`
  eliminated by L1, and unconditional delta quartiles flat within 0.007 R. Two
  independent horizons, same answer. This says nothing about MBP-1.
* **Frequency never reached the target.** 0.33–0.50 trades/day against a goal of
  2–7, with 70 % zero-trade days, because top-2 % selectivity, 60-minute holds and
  one position at a time cannot coexist in a 120-minute session. Hence 56–128
  trades per period — too few to resolve the effect being sought.
* **The selection rule has a defect worth naming.** Ranking 18 configurations on
  expectancy alone favours the smallest sample; the winner had the fewest trades
  of any eligible `r4p0` setting, and its Gate-E advantage (+0.058 R) had a CI of
  [−0.027, +0.148] — it passed on a point estimate with no statistical support.
  The gate as written did not require the CI to exclude zero. That is a flaw in
  the preregistration, and the fix belongs to the next phase's gates, not to this
  phase's results.

## 7. 2026-Q1 was never opened

**No Phase-5 code read a single 2026 row.** `scripts/p5_09_integrity.py` confirms
there is no 2026 month in any tick cache, no `split=val2026q1` feature directory,
no `run_val2026q1` result directory, and no `front_map_p5val.parquet` — the front
map a validation build would have had to create first.

The only contact any phase has ever had with `2026_H1.parquet` remains the
Phase-4 parquet-footer read. No row has ever been decoded.

This was not a judgement call at the end. It is what the preregistration
required: Gate F failed, so the candidate was never frozen, and an unfrozen
candidate has no route to validation.

## 8. What this does and does not mean

**It does not mean there is no profitable NQ edge**, and it does not retire the
larger-R idea. The correct statement is narrow:

> A single logistic model over the 55 Phase-4 causal features, thresholded on
> edge-over-a-training-baseline at the top 2 %, entering at market on a 60-second
> clock with R = 4 × ATR14(1-min) and a 60-minute hold, failed to beat matched
> random entries on 2023 and was rejected before validation.

Three things it deliberately did not test, in order of promise:

1. **The same signal with different entry mechanics** (H5-1) — the decomposition
   says the context selection works and the timing is what loses. This is the
   strongest thread either phase has produced.
2. **MBP-1 order flow** — trades-derived delta has now failed at two horizons;
   real book data has never been looked at. 2025-H1 was sealed for exactly this.
3. **A longer signal window or more instruments** (H5-3) — the sample sizes here
   were never adequate.

## 9. Reproduction

```bash
python -m pytest tests -q                                   # 335 tests

python scripts/p5_01_build_dataset.py --split dev --workers 5
python scripts/p5_02_develop.py                              # 2021 fit, 2022 select + Gate E
python scripts/p5_03_run_split.py --split itest2023           # Gate F -> REJECTED
python scripts/p5_03_run_split.py --split train2021
python scripts/p5_03_run_split.py --split select2022

python scripts/p5_01_build_dataset.py --split contam2024 --workers 5
python scripts/p5_01_build_dataset.py --split contam2025h2 --workers 5
python scripts/p5_03_run_split.py --split contam2024
python scripts/p5_03_run_split.py --split contam2025h2

python scripts/p5_04_diagnostics.py
python scripts/p5_05_charts.py
python scripts/p5_06_report.py && python scripts/p5_06b_report.py
python scripts/p5_09_integrity.py

# NEVER RUN — the candidate was rejected at Gate F, so there is no route here:
# python scripts/p5_01_build_dataset.py --split val2026q1 --unlock-validation
# python scripts/p5_03_run_split.py --split val2026q1 \
#     --confirm I_AM_UNLOCKING_ONLY_2026_Q1_FOR_PHASE5_VALIDATION
```

## 10. Seals at the close of Phase 5

| window | status |
|---|---|
| 2025-01-01 … 2025-06-30 (Trades **+ MBP-1**) | **SEALED — never opened by any phase** |
| 2026-01-01 … 2026-03-31 | **UNOPENED — footer metadata only; not spent by Phase 4 or Phase 5** |
| 2026-04-01 onward | **SEALED — never opened by any phase** |

MBP-1 was not opened in Phase 5 at all; the guard now refuses any path containing
`mbp1` and any raw `.dbn` archive outright.

Phases 1–4 remain byte-identical:
`fastslow-1.0.0+5980044a44eebf7b`,
`impexh-1.0.0.impl2+48c76a0e68b88947`,
`dcevent-1.0.0.impl3+d33e5d5d116f1adb`,
`statedisc-1.0.0+c147134184dfb32d`.
