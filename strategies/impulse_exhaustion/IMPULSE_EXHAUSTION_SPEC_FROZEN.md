# IMPULSE_EXHAUSTION_SPEC_FROZEN.md

**Frozen baseline identifier**

    impexh-1.0.0.impl2+48c76a0e68b88947

`spec_version` = `impexh-1.0.0` · implementation version `2`
combined SHA-256 = `48c76a0e68b88947ed9f700f15976514b66f2ae86e0b5deccdcfc5d0a2a06d90`
frozen at = `2026-08-19T23:54:24.389920+00:00`

Reproduce with `python scripts/p2_06_freeze.py`. The identifier is a SHA-256 over
the ordered `(path, file-sha256)` pairs below. If any of these files changes the
identifier changes, and the result is a **different hypothesis** that must be
named `ImpulseExhaustion_v2` and may **not** inherit 2024 as an untouched
validation set.

## Frozen file manifest

| file | sha256 |
|---|---|
| `strategies/impulse_exhaustion/config/baseline.yaml` | `a8e7e5d66b232a4db4b4e5cf4288c04e28f845ec9c374a177536be13a43001c5` |
| `strategies/impulse_exhaustion/IMPULSE_EXHAUSTION_SPEC.md` | `7225fbf5b70531ecf6ebba3c3a572c1dddd1715440309947ef7b5443db37d298` |
| `strategies/impulse_exhaustion/runner.py` | `42cd3f3316c04bcde25c2b092b5cad16762ad9761057820b5693e09159d0e020` |
| `src/nqr/p2/cache2.py` | `b8265df55959eef836b411a4d9bba39e8314a914715a7516826c3881bab757bc` |
| `src/nqr/p2/signing.py` | `3d594b48565d8c9bf1e1adfbcd3f775a6ca12654d37e5e73fd4f20e40592d453` |
| `src/nqr/p2/features.py` | `3a13d59f980dc90fa4ab67cc91bd593ddd36fd1af339461ea054c7c14df6757c` |
| `src/nqr/p2/absorption.py` | `ad3b9322ef8b1e29b4be1ccb082e55241157ec0bc3549e24721423e25032be8c` |
| `src/nqr/p2/statemachine.py` | `124b41ce9353ea2aef3c5de3f99a9769d388676cb9e1604bdc25fd089993ba62` |
| `src/nqr/p2/controls.py` | `9ba2a8c97444466032c0e94a9453993e11ed84e0ba2942f7aaa50590555ffcaf` |
| `src/nqr/holdout.py` | `c5afa82417538cbea78370f707a95fc065676ddb3b20f15e35a19003d15188c6` |
| `src/nqr/sessions/calendar.py` | `cad87a736641eaddff692a4b1acf49c39555d9d98c0f0e640ec694e121d21e48` |
| `src/nqr/data/contracts.py` | `b8d8adf70cc3afc06cf0c24327f665b545c33cb2c2b426eea544762851529224` |
| `src/nqr/backtest/engine.py` | `20b639972c944d708e10acb6e441f719f59e1c9fb122729cc9dbad77e938d555` |
| `scripts/p2_01_build_cache.py` | `f7e1c509aae413069d2bbcf5409fc64e0a97652fb80f33a68ca80ac397d53e57` |
| `scripts/p2_03_run.py` | `64d124c9bd86c2cc27504d9f0c64bd40ec33d6b04fd69bc6f09d09a1ecd19529` |

## Trade-signing verification (STEP 1), development days only

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

## Pre-freeze signal-count check

The specification was checked once on development for **signal count only**, to
confirm it is neither degenerate nor absurd. **No win rate, expectancy or P&L
was computed before the freeze.**

```
{
  "note": "PRE-FREEZE COUNT CALIBRATION. Signal COUNTS only - no win rate, expectancy, P&L or outcome of any kind was computed for any of these trials.",
  "conclusion": "Signal frequency is insensitive to the impulse threshold across the brief's entire suggested region (60-65 signals in 2021). The binding constraints are Stage B (three strictly increasing confirmed peaks) and Stage C (double deterioration), both mandated by the hypothesis and therefore NOT relaxed. The originally reasoned configuration was kept UNCHANGED. theta=0.50 was probed and rejected: it produced FEWER signals and began breaching the 600s extension budget (329 vs 2 EXTENSION_TOO_SLOW), confirming the original theta=0.25 reasoning.",
  "implication": "~26 signals/year in the 09:30-11:30 primary window means the pre-registered 100-trade PASS gate cannot be met in a single validation year. This is disclosed BEFORE validation is run; the gate is NOT changed.",
  "trials": [
    {
      "tag": "smoke",
      "description": "BASELINE as specified: impulse 1.00xVU/90s, theta 0.25xVU",
      "year": "2021 only",
      "signals_total": 61,
      "signals_0930_1130": 25,
      "signals_0930_1600": 57,
      "rejected_candidates": 61320,
      "top_reject": [
        "NOT_A_NEW_EXTREME",
        43445
      ]
    },
    {
      "tag": "cnt_0.50",
      "description": "theta 0.50xVU (scale probe)",
      "year": "2021 only",
      "signals_total": 39,
      "signals_0930_1130": 17,
      "signals_0930_1600": 39,
      "rejected_candidates": 42734,
      "top_reject": [
        "NOT_A_NEW_EXTREME",
        29960
      ]
    },
    {
      "tag": "i075_120",
      "description": "impulse 0.75xVU/120s (permissive corner of the brief's region)",
      "year": "2021 only",
      "signals_total": 65,
      "signals_0930_1130": 26,
      "signals_0930_1600": 61,
      "rejected_candidates": 75675,
      "top_reject": [
        "NOT_A_NEW_EXTREME",
        53690
      ]
    },
    {
      "tag": "i075_090",
      "description": "impulse 0.75xVU/90s",
      "year": "2021 only",
      "signals_total": 65,
      "signals_0930_1130": 25,
      "signals_0930_1600": 61,
      "rejected_candidates": 72654,
      "top_reject": [
        "NOT_A_NEW_EXTREME",
        51592
      ]
    },
    {
      "tag": "i100_120",
      "description": "impulse 1.00xVU/120s",
      "year": "2021 only",
      "signals_total": 60,
      "signals_0930_1130": 26,
      "signals_0930_1600": 56,
      "rejected_candidates": 65268,
      "top_reject": [
        "NOT_A_NEW_EXTREME",
        46246
      ]
    },
    {
      "tag": "cnt2",
      "description": "FINAL spec: absorption reference distribution session-matched to RTH, window 2000/min 500",
      "year": "2021 only",
      "signals_total": 50,
      "signals_0930_1130": 20,
      "signals_0930_1600": 50,
      "rejected_candidates": 61348,
      "top_reject": [
        "NOT_A_NEW_EXTREME",
        43457
      ]
    }
  ],
  "defect_found_and_corrected_pre_freeze": {
    "defect": "The absorption reference distribution was contaminated by pre-open legs. A 500-leg window spans only ~3 hours, so at 09:35 the reference was dominated by 08:00-09:30 legs, which carry far less volume per tick than RTH legs. Almost every RTH leg therefore ranked near the top and the 70th-percentile gate stopped discriminating (20 rejections out of 61,320).",
    "evidence": "COUNT diagnostic only - reject-reason tallies. No win rate, expectancy or P&L was computed.",
    "correction": "Reference distribution restricted to RTH legs (session-matched); window lengthened to 2000 legs (~2 RTH days) with a 500-observation warm-up. The absorption FORMULA was not changed.",
    "residual_finding": "Even after the correction the absorption gate rejects only 26 of 61,348 candidates. This is structural, not a bug: Stage C's efficiency-deterioration test (progress per aggressive contract falling) and Stage D's absorption proxy (aggressive volume per tick of best-price advance) are near-reciprocal measures, so Stage D is largely implied by Stage C. This is REPORTED, not engineered away - the pre-registered ablation (variant B vs C) is exactly the instrument for it."
  },
  "final_expected_sample": {
    "per_year_0930_1130": 20,
    "per_year_0930_1600": 50,
    "dev_3y_0930_1130_estimate": 60,
    "dev_3y_0930_1600_estimate": 150,
    "note": "The pre-registered 100-trade PASS gate is unreachable in a single validation year. Disclosed before validation; the gate is NOT changed."
  }
}
```

## Freeze protocol

1. `IMPULSE_EXHAUSTION_SPEC.md` and `config/baseline.yaml` were completed before
   any P&L existed. Every threshold comes from a-priori reasoning about NQ tick
   size, NQ 1-minute range and the timescale of the hypothesis.
2. Exactly **one** absorption formula was written. No alternatives were coded,
   run or compared.
3. No parameter grid was swept. The brief's suggested regions
   (0.75-1.25 VU, 30-120 s) were collapsed to a single canonical value by
   reasoning, not by search.
4. Development (2021-2023) is for implementation verification and diagnostics.
   A weak year does not license a rule change.
5. Validation (2024) is run **exactly once** against this manifest.
6. Only a genuine implementation **bug** may be fixed; it must be documented,
   regression-tested, bump `impl_version`, and force a full rerun.

## Pre-registered PASS / FAIL gate (restated, unchanged)

2024 validation · 09:30-11:30 ET · 1R · 1.0 pt round-trip friction. **PASS**
requires all six: trades >= 100; net expectancy > 0 R; profit factor > 1.10;
win rate > 50 %; 95 % binomial CI lower bound > 50 %; one-sided binomial
p < 0.05. **PROMISING BUT INCONCLUSIVE** if expectancy is positive but a
significance or sample gate fails. **FAIL** otherwise.
