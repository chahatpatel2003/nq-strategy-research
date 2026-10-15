# LABELS.md — Phase-5 larger-R label construction

How every Phase-5 outcome was produced, and how it differs from Phase 4.

---

## 1. The decision row

One row per **60-second** decision timestamp inside 09:30:00–11:30:00 ET —
120 rows per trading day, first at 09:30:00, last at 11:29:00. Roll days are
excluded.

Each row carries the 55 frozen Phase-4 causal features observed at that instant
(grid convention: the decision stamped `T0+i+1` reads `grid[i]`, so every input
second has closed), plus **six** resolved outcomes: LONG and SHORT for each of
the three R scales.

## 2. R

    R = clip(mult × ATR14(completed 1-minute bars, floor 2.0 pt), 5.0, 200.0)

with `mult ∈ {2.0, 3.0, 4.0}` — the `r2p0` / `r3p0` / `r4p0` scales. The ATR is
the frozen `nqr.p2.features.causal_atr_minutes`, the same unit Phases 2–4 used,
evaluated at the decision timestamp. The rails are absurdity rails: measured on
the 2021 training sample the floor binds on 0.139 % of the smallest scale and the
cap on 0.000 %.

Realised R across development: median **21–42 points** on the 2021 sample,
**31–62 points** in higher-volatility months, averaging **36–54 points** on the
executed trades — against Phase 4's 7 points.

## 3. Entry

Market order at the decision timestamp, latency **250 ms**, filled at the first
trade print at or after `t + 250 ms`, abandoned if no print arrives inside 60 s.
Identical to Phases 1–4 and identical for strategy and controls.

Verified over all 137,400 decision rows: minimum realised latency is exactly
**250.0 ms** (never earlier), median 295–304 ms, maximum 29.6 s (inside the 60 s
cap).

## 4. Bracket

    stop   = entry − direction × R      (stop-market: triggers on a print at or
                                         beyond the stop, fills at that print)
    target = entry + direction × R      (resting limit: the tape must trade
                                         THROUGH by ≥ 1 tick; a touch is not a fill)

Both hang off the **realised entry price**, never the decision price. Resolved on
the raw chronological trade sequence — no OHLC approximation, no candle-order
guessing.

## 5. Maximum hold and the timeout rule

**60 minutes**, plus a hard 16:00 ET rail that never binds (the last entry is
~11:30, so the horizon ends by ~12:30).

This is the one place Phase 5 deliberately departs from Phase 4:

| | Phase 4 | Phase 5 |
|---|---|---|
| timeout exit | last print **before** the cutoff | **first print at or after** the cutoff |

Phase 4's rule is not executable — at the moment of that print the cutoff had not
yet arrived, so no real timeout order could have filled there. Phase 5 takes the
first print at or after the cutoff, which is what a timeout order actually gets,
and is strictly the more conservative of the two. If the tape goes quiet for more
than 60 s past the cutoff, it falls back to the last print before it.

`resolve_p5` is asserted **identical to the frozen `nqr.p3.fastpass.resolve_fast`
on every TP and SL outcome** over randomised tapes
(`tests/test_p5_labels.py::test_tp_and_sl_branches_match_the_frozen_engine_exactly`);
it differs only on the TIMEOUT branch.

Consequence, and it is intentional: realised holds reach **60.5–60.7 minutes**,
slightly past the nominal hour, because the exit waits for the next print.

**Timeouts are never discarded.** Their realised P&L, R, MFE, MAE and hold are
all recorded and counted at every friction level. At `r4p0` roughly 30–40 % of
trades time out, and they carry real, usually small, P&L.

## 6. Resolution rates, measured before the horizon was fixed

On 24 sampled 2021 training days, reporting **resolution only** — no win rate, no
expectancy — which is what justified choosing 60 minutes over 90:

| scale | @30 min | **@60 min** | @90 min | @120 min | median hold @60 |
|---|---:|---:|---:|---:|---:|
| `r2p0` | 90.7 % | **98.0 %** | 99.4 % | 99.8 % | 12.2 min |
| `r3p0` | 62.5 % | **82.2 %** | 89.2 % | 92.9 % | 26.9 min |
| `r4p0` | 39.5 % | **59.9 %** | 72.6 % | 79.7 % | 38.8 min |

## 7. The modelling target

    y = 1  iff the hypothetical LONG bracket finishes with GROSS points > 0

A property of the tape alone, so one model serves both directions. The SHORT
bracket is resolved and stored for every row and is the basis of the
opposite-direction control. **Friction is applied to P&L, never to the label.**

## 8. Friction

Every outcome is stored gross; `net_{0p0,0p5,1p0,2p0}` and the corresponding
`netR_*` are derived. The official evaluation is 1.0 NQ point round trip, which
at these R scales is **2.4–4.7 % of R** against Phase 4's 14.4 %.

## 9. No label crosses a trading day

Verified over all 137,400 rows across dev, 2024 and 2025-H2: **zero** labels
resolve on a later trading date. Whole-year splits therefore need no purge or
embargo.

## 10. Dataset

Partitioned parquet under `strategies/larger_r/features/split=<split>/ym=<month>/`.
Per split: dev 91,440 rows / 762 days, 2024 30,600 / 255, 2025-H2 15,360 / 128.
Columns: 9 meta, 42 label (3 scales × [R + 2 directions × 6 fields + y]),
55 features.
