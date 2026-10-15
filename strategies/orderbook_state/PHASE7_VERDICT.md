# PHASE7_VERDICT.md — NQ MBP-1 Order-Book State Discovery

    spec            obstate-1.0.0
    budget spent    12 of 12 configurations
    eligible        NONE
    verdict         FAIL  (before 2023, before 2024, before the holdout)
    holdout         2025-H1 NOT OPENED — no Phase-7 code decoded a single row
    phase status    CLOSED

---

## 1. The verdict

# FAIL

The bounded MBP-1 top-of-book experiment specified in `FEATURE_REGISTRY.md`,
`SEARCH_BUDGET.md` and `PHASE7_SPEC.md` did **not** identify a robust, executable
edge. None of the 12 configurations passed the 2022 gates, so no candidate was
frozen, 2023 was never scored, 2024 was never opened, and **2025-H1 — the last
untouched MBP-1 window in existence — stays sealed.**

## 2. The 2022 gate

| gate | requirement | configurations passing |
|---|---|---:|
| G1 | ≥ 200 executed trades | 9 / 12 |
| **G2** | **net expectancy > 0 R** | **0 / 12** |
| **G3** | **PF(R) > 1.10** | **0 / 12** |
| **G4/G5** | **beats matched random** | **0 / 12** |
| G6 | gross expectancy > 0 | 1 / 12 |

The least-bad configuration, `R25:A_logit:top1p0`, returned **−0.0389 R** net,
PF(R) 0.924, with an advantage over matched random of **−0.0032 R**. Per
`SEARCH_BUDGET.md` §8 there is no least-bad candidate, and the phase ends here.

## 3. Three independent lines of evidence, all negative

### There is no gross edge

At **zero** friction the reference configuration returns **+0.0011 R**, against an
unconditional baseline (every decision, both directions) of **−0.0448 R**. So the
model lands +0.006 R from doing nothing. Friction at R = 25 pt is only 0.040 R —
the second-smallest of any phase — so this is emphatically **not** "edge destroyed
by cost". There was no edge.

### It does not beat matched random, on either causal control

| control | control E[R] | Δ E[R] | 95 % day-block CI |
|---|---:|---:|---|
| cross-day, same 5-min bucket (primary) | −0.0357 | **−0.0032** | [−0.0448, +0.0396] |
| same-day, forward-only (secondary) | −0.0461 | +0.0072 | [−0.0257, +0.0399] |

Two independently-constructed controls — one matching time-of-day exactly and
giving up the day, one matching the day and giving up exact time-of-day — both
contain zero. Control causality is **asserted at runtime**, not assumed; that is
the direct fix for the defect Phase 6 found in Phase 5.

### The nulls say there was never a relationship

| null | result |
|---|---|
| **N1 label permutation** (50 refits, permuted within training days) | null E[R] **−0.0266 ± 0.0114** vs observed **−0.0389**. The real model is **1.1 σ on the wrong side**; **p(null ≥ observed) = 0.84** |
| **N2 temporal shift** (+7 trading days) | shifted E[R] **−0.0390** vs observed **−0.0389** — a difference of **0.0001 R** |

A model trained on **scrambled labels does better** than the real one, 84 % of the
time. And destroying the causal feature→outcome link entirely changes the result
by one ten-thousandth of an R.

This is the sharpest negative in the project. Phase 4's equivalent test gave
p = 0.00 and beat its null by 5 σ — a real, if untradably small, signal. Phase 7
has no such signal to find.

## 4. The central research question, answered carefully

> **Does causal MBP-1 top-of-book information add anything beyond price and
> trades?**

The mandatory ablation, each arm with its own 2021 scaler and its own 2021
threshold, identical dates / R / family / selectivity / execution:

| arm | features | net E[R] | **vs doing nothing (−0.0448)** |
|---|---:|---:|---:|
| A0 full | 40 | −0.0389 | **+0.0059** |
| A1 quote-only | 32 | −0.0611 | −0.0162 |
| A2 trades + context | 8 | −0.1173 | −0.0724 |

`A0 − A2 = +0.0784 R` with a 95 % CI of **[+0.0082, +0.1605]**, excluding zero.

**Reported alone, that looks like a discovery. It is not.** The comparison is
against an arm that is *worse than doing nothing* by 0.072 R. The book features
measurably outperform a trades-and-price model — by returning it to the level of
no model at all.

> **Phase 7 did not establish incremental tradable information from MBP-1.**

That the trades-only arm is actively harmful is itself consistent: Phases 4, 5 and
7 have now each found trades-derived flow uninformative, at three different
horizons.

## 5. What the model weighted, and what it ignored

Pure order-book families carry **75.9 %** of the coefficient mass, so the model did
lean on the book. What it chose is telling:

* **`bid_px_chg_per_s_15` is the largest single coefficient (−0.106)** — best-bid
  churn rate, a quote-instability measure, not a directional one.
* **BBO state 25.2 %**, quote-update intensity 19.9 %, imbalance persistence 12.3 %.
* **OFI carries 1.2 %.** An L1-regularised model with all three OFI horizons
  available very nearly discarded the canonical top-of-book predictor.
* Trade aggression 1.3 %, failure-to-advance 0.2 %.

## 6. What did work

The **trade-frequency profile is the best any phase has produced**: 8.78
trades/day, median 4, 66 % of days with 3+ trades, holds averaging 2.8 minutes
against a 15-minute cap. Squarely in the 2–7/day band the brief called
interesting. It is the only thing here that works, and a well-shaped schedule of
unprofitable trades is not worth anything.

Also worth recording: **93 % of trades are short** (2,083 vs 146) — the same
lopsidedness Phases 5 and 6 flagged in an entirely different model. That is now a
three-phase pattern.

## 7. What this does and does not mean

**It does not mean "order flow doesn't work."** The precise statement:

> This bounded MBP-1 **top-of-book** experiment — 40 preregistered causal features
> over 1/5/15-second windows, a 5-second decision clock in 09:30–11:30 ET, fixed
> 15- and 25-point R with a 15-minute horizon, 12 configurations across two model
> families, trained on 2021 and selected on 2022 — failed to identify a robust,
> executable edge under the specified protocol.

**MBP-1 is not MBO.** This tested nothing about:

* **queue position** — no order IDs exist in this data;
* **individual order lifetime or order-level aggressiveness** — same reason;
* **hidden or iceberg liquidity** — not represented;
* **depth beyond the touch** — only `_00` columns exist;
* **book shape or multi-level imbalance** — same reason.

A negative on the top of book is a real result, but it is a narrow one.

## 8. Why 2025-H1 stays sealed

It is the last untouched Trades + MBP-1 window **and the last MBP-1 window that
exists at all** — coverage stops at 2025-H1; there is no 2025-H2 or 2026 MBP-1
file. A development candidate that fails its first gate, has no gross edge, does
not beat matched random on either control, and is beaten by its own permutation
null does not deserve it.

Only footer metadata was ever read: 1,236,114,072 rows, 18,862 row groups,
2024-12-29 13:00 UTC → 2025-06-30 23:59 UTC. **No row was decoded.**

## 9. Reproduction

```bash
python -m pytest tests -q                                          # 423 tests

python scripts/p7_01_build_book_cache.py --split dev                # ~60 min, 222 GB scanned
python scripts/p7_02_build_dataset.py --split dev --workers 5       # ~26 s
python scripts/p7_03_develop.py                                     # 12 configs -> FAIL
python scripts/p7_05_diagnostics.py                                 # ablation + N1 + N2
python scripts/p7_06_audit_charts.py                                # book-sequence audit + charts
python scripts/p7_07_report.py && python scripts/p7_07b_report.py
python scripts/p7_09_integrity.py

# NEVER RUN — no candidate earned it:
# python scripts/p7_01_build_book_cache.py --split val2025h1 \
#     --confirm I_AM_UNLOCKING_ONLY_2025_H1_FOR_PHASE7_FRESH_VALIDATION
```

## 10. Seals at the close of Phase 7

| window | status |
|---|---|
| **2025-01-01 … 2025-06-30 (Trades + MBP-1)** | **SEALED — never opened by any phase; footer metadata only** |
| 2025-07-01 … 2025-12-31 | spent as Phase-3 validation; no MBP-1 exists; refused by the Phase-7 guard |
| 2026-01-01 … 2026-03-31 | **UNOPENED** — Trades-only reserve; Phase 7 has no code path to it |
| 2026-04-01 onward | **SEALED — final holdout** |

Phases 1–4 remain byte-identical: `fastslow-1.0.0+5980044a44eebf7b`,
`impexh-1.0.0.impl2+48c76a0e68b88947`, `dcevent-1.0.0.impl3+d33e5d5d116f1adb`,
`statedisc-1.0.0+c147134184dfb32d`. Phase-5 artifacts pinned at
`d0783a6638d88aec`, unchanged. Phase 6 froze nothing and is unchanged.
