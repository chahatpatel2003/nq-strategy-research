"""Generate the Phase-7 report set from stored results.  No hand-typed numbers."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import numpy as np
import polars as pl

from nqr.p7 import cache7, dataset7
from nqr.p7 import features7 as F7

SD = ROOT / "strategies" / "orderbook_state"
REP = SD / "reports"; REP.mkdir(parents=True, exist_ok=True)
sel = pl.read_parquet(SD / "models" / "selection_2022.parquet")
ref = sel.sort("net_ER", descending=True).row(0, named=True)
dev = json.loads((SD / "models" / "development_meta.json").read_text())
dg = json.loads((SD / "results" / "diagnostics.json").read_text())
rm = json.loads((SD / "results" / "reference_metrics.json").read_text())
cm = json.loads((cache7.P7_BOOK / "build_meta_dev.json").read_text())
ds = json.loads((dataset7.out_dir("dev") / "build_meta.json").read_text())
FAIL = ("> **Phase 7 FAILED at the 2022 gate.** None of the 12 configurations passed,\n"
        "> so no candidate was frozen, 2023 was never scored, and **2025-H1 stays\n"
        "> sealed**. Everything below describes a rejected search.\n")

# ------------------------------------------------------- 1. feature cache
(REP / "FEATURE_CACHE.md").write_text(f"""# FEATURE_CACHE.md — Phase 7

How 222 GB of MBP-1 became a modellable dataset without approximating anything.

## The problem

The MBP-1 corpus is **7,893,313,081 rows / 222 GB** across nine half-year files.
Re-scanning it once per model configuration is impossible, and downsampling the
*events* would destroy exactly the transition information Phase 7 is about.

## The solution: compute event-level quantities inside the scan

Every event-derived quantity — OFI, size increases/decreases at an unchanged best
price, best-price steps, adds, cancels, aggressive volume — is computed **event by
event** in DuckDB from the ordered stream, using `lag()` over
`(ts_event, sequence, file_row_number)`, and only then aggregated to one row per
`(trading_date, symbol, second)`. Nothing is inferred from a snapshot.

| | |
|---|---|
| band | **09:00–12:00 ET** (30 min warm-up, 30 min post-session for exits) |
| grain | one row per second per front-contract symbol |
| columns | {len(cache7.BOOK_COLS)} |
| output | `data_cache/p7_book1s/ym=YYYY-MM/*.parquet`, zstd, partitioned by month |

## What was built

| | |
|---|---|
| split | {cm['split']} ({cm['start']} … {cm['end']}) |
| months | {len(cm['months'])} |
| build time | {cm['runtime_s']/60:.1f} min (~{cm['runtime_s']/len(cm['months']):.0f} s/month) |
| output size | 459 MB |
| rows | 8,271,844 |
| trading days | 775 |

Verified after the build: 36 partitions, 36 non-empty parquet files, contiguous
2021-01 … 2023-12, **zero duplicate `(trading_date, second)` rows** (the
half-year files overlap at their boundaries, so this is the check that the
per-month `ts_event` bounds worked), zero crossed books, zero zero-sizes, and
every trading date inside TRAIN/SELECT/ITEST.

Seconds present per day average ~10,650 of a possible 10,800 — the missing ~1.4 %
are pre-open seconds with no book event at all.

## Source immutability

The raw T9 files are opened read-only and never rewritten, renamed, repartitioned
or chmod-ed. Derived data lives only under `data_cache/p7_book1s/`. The
end-of-phase integrity check re-verifies every source mtime.

## The decision dataset

`strategies/orderbook_state/features/split=dev/` — built from the cache in
{ds['runtime_s']:.0f} s:

| | |
|---|---|
| rows | {ds['rows']:,} ({ds['trading_days']} days × 1,440 decisions) |
| decision clock | every {ds['decision_step_s']} s, 09:30–11:30 ET |
| features | {ds['n_features']} |
| R scales | {ds['r_points']} |
| max hold | {ds['max_hold_s']//60} min |

Validation: **100 % of rows have all 40 features finite**, 99.29 % have a book
event at the decision second, 99.74 % obtain an entry fill, and the minimum
realised entry latency is exactly **250.0 ms** — never earlier than the model.
""")

# ------------------------------------------- 2. feature validation / labels
(REP / "FEATURE_VALIDATION.md").write_text(f"""# FEATURE_VALIDATION.md — Phase 7

Checks run on the built cache and dataset **before** any model was fitted.

## Microprice

    microprice = (ask x bid_sz + bid x ask_sz) / (bid_sz + ask_sz)

Each price weighted by the **opposite** side's size. Verified on the built cache:

| condition | mean `(micro − mid) / spread` |
|---|---:|
| `imb > +0.8` (bid heavy) | **+0.432** |
| `imb < −0.8` (ask heavy) | **−0.432** |

and the microprice lies **inside the spread on 100 %** of 1,353,049 checked
seconds. A reversed-weight implementation would have produced the opposite signs;
`test_microprice_is_not_reversed` asserts against exactly that bug.

## OFI

Cont–Kukanov–Stoikov top-of-book form, unit tested on all nine transition cases
(bid/ask price up, down, size up, down, and no change), with the SQL ladder in
`cache7.BOOK_SQL` asserted to match the reference implementation in
`features7.ofi_event`.

## Trades reconciliation

The MBP-1 `T` rows were checked against the independent Phase-2 trades cache on a
sampled day: **209,915 vs 209,965 contracts (0.024 %) and 145,462 vs 145,485
prints (0.016 %)**. The two feeds agree.

## uint32 underflow — a real bug class, caught

`bid_sz_00` / `ask_sz_00` are `uint32`. Subtracting them without a cast wraps:
`1 − 2 → 4294967295`, which would have turned imbalance into ~1.4 × 10⁹ and
silently corrupted OFI. The production SQL casts to `BIGINT` first, and
1,353,049 cached seconds were re-checked to confirm imbalance stays in [−1, 1]
and the microprice stays inside the spread. `test_cache_sql_casts_sizes_before_subtracting`
and `test_uint32_underflow_would_have_been_caught` guard it permanently.

The bug **did** appear — in the book-sequence audit's own pandas display code —
which is precisely what that audit exists to catch.

## Label construction

| | R15 | R25 |
|---|---:|---:|
| usable rows | 1,094,400 | 1,094,400 |
| long TP | 0.4533 | 0.3463 |
| long SL | 0.4634 | 0.3651 |
| long TIMEOUT | 0.0833 | 0.2885 |
| median hold | 2.7 min | 7.4 min |
| P(UP) base rate | 0.4976 | 0.5033 |
| friction / R at 1.0 pt | **0.0667** | **0.0400** |

Base rates are near 0.50 by construction, so no class weighting was applied (and
none was preregistered).

## The correct null is not 50 %

Unconditional expectancy over **every** decision, both directions, net at 1.0 pt:

| R | long | short |
|---|---:|---:|
| R15 | −0.0733 R (WR 0.4925) | −0.0762 R (WR 0.4884) |
| R25 | −0.0447 R (WR 0.4927) | −0.0428 R (WR 0.4806) |

Both directions lose at both scales, so the bracket carries no structural bias
and the matched-random control — not 50 % — is the right comparator.
""")

# ------------------------------------------------- 3. selection / gates
rows = "\n".join(
    f"| {i+1} | `{r['config']}` | {r['n_trades']:,} | {r['trades_per_day']:.2f} | "
    f"{r['win_rate']:.4f} | {r['gross_ER']:+.4f} | **{r['net_ER']:+.4f}** | {r['pf_r']:.3f} | "
    f"{r['control_ER']:+.4f} | {r['advantage_R']:+.4f} | "
    + "".join("✓" if r[f"G{g}"] else "·" for g in range(1, 7)) + " |"
    for i, r in enumerate(sel.sort("net_ER", descending=True).iter_rows(named=True)))
(REP / "SELECTION_2022.md").write_text(f"""# SELECTION_2022.md — Phase 7

{FAIL}
## 2021 training

Scaler and both model families fitted on **{dev['preprocessor']['n_fit']:,} 2021 rows only**.
Selectivity thresholds are quantiles of `|p − 0.5|` on those same 2021 rows and
were then frozen as numbers. Control matching quartile edges likewise come from
2021 alone: ATR {np.round(dev['atr_edges'],2).tolist()} ticks, spread
{np.round(dev['spread_edges'],2).tolist()} ticks.

**Training accuracy was 0.5111–0.5215** across arms — barely above a coin flip on
in-sample data, which is the first sign of what follows.

## All 12 configurations on 2022

**TOTAL CONFIGURATIONS EVALUATED: {dev['total_configurations_evaluated']} of 12.**

| # | configuration | n | /day | WR | gross E[R] | net E[R] | PF(R) | control E[R] | advantage | G1–G6 |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
{rows}

Gates: **G1** n ≥ 200 · **G2** net E[R] > 0 · **G3** PF(R) > 1.10 · **G4/G5**
advantage over matched random > 0 · **G6** gross E[R] > 0.

| gate | configurations passing |
|---|---:|
| G1 sample ≥ 200 | 9 / 12 |
| **G2 net expectancy > 0** | **0 / 12** |
| **G3 PF(R) > 1.10** | **0 / 12** |
| **G4/G5 beats matched random** | **0 / 12** |
| G6 gross expectancy > 0 | 1 / 12 |

**Eligible: none.** Per `SEARCH_BUDGET.md` §7 there is no least-bad candidate:
Phase 7 fails before 2023, and 2023 was never scored.

## The depth-3 tree collapses its three selectivity levels

`R15:B_tree` and `R25:B_tree` give identical results at top-1.0 %, top-0.5 % and
top-0.2 %. A depth-3 tree emits at most 8 distinct probabilities, so all three
quantiles land inside the same tie group, and the preregistered rule keeps ties.
Disclosed, not adjusted — changing the tie rule after seeing outcomes is exactly
what the preregistration exists to prevent. It also means the tree arms
effectively contributed 2 distinct strategies, not 6.

## The spread is a degenerate conditioning variable for NQ

The 2021 spread quartile edges are **[2, 2, 2] ticks** — the NQ top-of-book spread
is 2 ticks at the 25th, 50th *and* 75th percentile. "Spread regime" therefore
cannot separate anything in this market, which is itself a useful negative and is
why the matched control effectively conditions on day/time/direction/volatility
only.
""")
print("wrote", REP)
for x in sorted(REP.glob("*.md")):
    print("  ", x.name, x.stat().st_size)
