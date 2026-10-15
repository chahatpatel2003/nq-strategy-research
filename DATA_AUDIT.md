# DATA_AUDIT.md — Databento NQ trade & MBP-1 inventory (Phase 0)

Everything below was produced by `python scripts/00_audit.py`
(module `src/nqr/data/audit.py`), which reads the T9 parquet files **read-only**
and refuses, via `src/nqr/holdout.py`, to touch any half-year file dated 2025 or
later. Nothing in this document derives from sealed data.

---

## 1. Where the data is

Located by walking `/Volumes/T9` looking for directories named `trades` / `mbp1`
that contain `YYYY_H[12].parquet` — the path was discovered, not assumed:

| dataset | path |
|---|---|
| trades | `/Volumes/T9/nq data/raw/trades` |
| MBP-1 | `/Volumes/T9/nq data/raw/mbp1` |

### Files present

| dataset | halves on disk | used in Phase 1 |
|---|---|---|
| trades | 2021_H1 … 2024_H2, **2025_H1, 2025_H2, 2026_H1** | 2021_H1 … 2024_H2 only |
| MBP-1 | 2021_H1 … 2024_H2, **2025_H1** | **none** (not needed for Fast-Slow) |

A second copy of `2025_H2.parquet` and `2026_H1.parquet` also exists under
`/Volumes/T9/NQ_HOLDOUT/`. **No 2025 or 2026 file was opened.** Their existence
is recorded here only so the inventory is complete.

MBP-1 is 18–35 GB *per half-year* (≈ 434 GB total). Phase 1 never opens it; it
is reserved for the later order-flow work, for which the 2025-H1 sealed holdout
conveniently exists in both schemas.

---

## 2. Schema

Both schemas are standard Databento DBN, written by `parquet-cpp-arrow 24.0.0`,
with `ts_recv` as the pandas index column.

**trades** (14 columns)

| column | arrow type | meaning / finding |
|---|---|---|
| `ts_event` | `timestamp[ns, tz=UTC]` | exchange matching-engine time — **the canonical clock for this project** |
| `ts_recv` | `timestamp[ns, tz=UTC]` | Databento capture time |
| `rtype` | `uint8` | constant `0` (MBP-0 / trade) |
| `publisher_id` | `uint16` | constant `1` (GLBX.MDP3) |
| `instrument_id` | `uint32` | numeric id, 1:1 with `symbol` |
| `action` | `large_string` | constant `'T'` |
| `side` | `large_string` | aggressor: `A` sell-aggressor, `B` buy-aggressor, `N` none. Split is ≈50/50 with a few hundred `N` per half-year |
| `depth` | `uint8` | constant `0` |
| `price` | `double` | **already in index points** (not 1e-9 fixed point). 100 % tick-aligned for outrights |
| `size` | `uint32` | contracts; always ≥ 1, never null |
| `flags` | `uint8` | almost always `0`; see §4 |
| `ts_in_delta` | `int32` | venue-side send delta |
| `sequence` | `uint32` | venue sequence; **not unique** — one aggressor sweeping several resting orders emits several records sharing it |
| `symbol` | `large_string` | e.g. `NQH1`, and calendar spreads `NQH1-NQM1` |

**MBP-1** (20 columns) — the same fields plus `bid_px_00`, `ask_px_00`,
`bid_sz_00`, `ask_sz_00`, `bid_ct_00`, `ask_ct_00`. Schema recorded for later
phases; **not read**.

Timestamps are already tz-aware UTC in the files. Session logic converts to
`America/New_York` with `zoneinfo`, so DST is handled by the tz database rather
than by any fixed offset (unit-tested at both 2024 transitions).

---

## 3. Inventory and coverage (2021–2024 only)

| file | GB | rows | of which spreads | first `ts_event` (local) | last `ts_event` (local) |
|---|---|---|---|---|---|
| `2021_H1.parquet` | 1.11 | 43,112,586 | 188,505 | 2021-01-03 15:00 | 2021-06-30 16:59 |
| `2021_H2.parquet` | 1.10 | 42,552,097 | 190,620 | 2021-06-30 17:00 | 2021-12-31 13:59 |
| `2022_H1.parquet` | 1.51 | 60,018,704 | 249,465 | 2022-01-02 15:00 | 2022-06-30 16:59 |
| `2022_H2.parquet` | 1.43 | 55,802,672 | 201,167 | 2022-06-30 17:00 | 2022-12-30 13:59 |
| `2023_H1.parquet` | 1.31 | 50,285,745 | 246,292 | 2023-01-02 15:00 | 2023-06-30 13:59 |
| `2023_H2.parquet` | 1.30 | 50,488,364 | 205,406 | 2023-07-02 15:00 | 2023-12-29 13:59 |
| `2024_H1.parquet` | 1.30 | 51,075,993 | 223,069 | 2024-01-01 15:00 | 2024-06-30 16:59 |
| `2024_H2.parquet` | 1.23 | 48,648,606 | 273,132 | 2024-06-30 17:00 | 2024-12-31 13:59 |

* **1 034 Globex trading days** with data, 2021-01-04 → 2024-12-31
  (259 / 258 / 258 / 259 per year).
* The only weekdays with **no** data are 2021-12-24, 2022-04-15, 2022-12-26,
  2023-01-02, 2023-12-25, 2024-01-01, 2024-03-29, 2024-12-25 — all CME full
  holidays. **There are no unexplained gaps.**
* Lowest-volume days are exactly the expected half-sessions (Good Friday,
  July 4th, Thanksgiving, Memorial/Labor Day).
* Median day contains **690** two-minute bars = 23 h × 30, i.e. every single
  2-minute interval of a normal Globex day trades.
* The half-year files are cut at **00:00 UTC**, not at an ET session boundary,
  so the 2021_H1/H2 and 2022_H2/2023_H1 joins fall *inside* a Globex day. All
  processing reads the halves together and groups by Globex trading date, so
  this is invisible downstream.

## 4. Quality checks

| file | off-tick prints | nulls | size ≤ 0 | p50 lat ms | p99 lat ms | max lat ms | `ts_recv` desc | `ts_event` desc | `ts_event > ts_recv` |
|---|---|---|---|---|---|---|---|---|---|
| `2021_H1.parquet` | 150,551 | 0 | 0 | 0.268 | 4.61 | 297 | 0 | 4,180 | 0 |
| `2021_H2.parquet` | 151,116 | 0 | 0 | 0.235 | 3.35 | 405 | 0 | 15,646 | 5 |
| `2022_H1.parquet` | 195,393 | 0 | 0 | 0.251 | 5.42 | 233 | 0 | 27,268 | 0 |
| `2022_H2.parquet` | 157,264 | 0 | 0 | 0.241 | 5.53 | 287 | 0 | 18,132 | 0 |
| `2023_H1.parquet` | 193,574 | 0 | 0 | 0.238 | 18.00 | 286 | 0 | 19,729 | 414,156 |
| `2023_H2.parquet` | 163,388 | 0 | 0 | 0.239 | 4.72 | 256 | 0 | 9,846 | 1,932 |
| `2024_H1.parquet` | 172,886 | 0 | 0 | 0.246 | 4.89 | 98 | 0 | 8,723 | 64 |
| `2024_H2.parquet` | 212,640 | 0 | 0 | 0.262 | 5.77 | 110 | 0 | 6,992 | 17 |

**Findings**

1. **Price scaling / tick alignment.** Every off-tick print in the entire
   dataset is a *calendar spread* (verified per file: off-tick count ≤ spread
   count, and grouping off-tick rows by `symbol LIKE '%-%'` yields 100 % spreads).
   **Outright NQ prices are 100 % aligned to 0.25.** Prices are therefore stored
   internally as `int32` ticks, making every level/stop/target comparison exact.

2. **Sortedness.** `ts_recv` is non-decreasing in file order in **every** file
   (0 inversions), confirming the files are written in capture order.
   `ts_event` has a handful of inversions per file (4 k–27 k out of 40–60 M,
   ≈ 1 in 3 million). Because the project uses `ts_event` as its clock and the
   backtester binary-searches the tape, **the tick cache is explicitly sorted by
   `(ts_event, source row number)`** — without that, `searchsorted` would be
   subtly wrong on those rows. A regression test covers it.

3. **`ts_event > ts_recv`.** Impossible in principle, observed on a minority of
   2023 rows (0.8 % of 2023_H1, max 125 ms, spread over many days) and a
   negligible number elsewhere. This is capture-gateway clock skew. At a
   2-minute bar horizon with a 250 ms modelled execution latency it is
   immaterial; it is recorded rather than corrected.

4. **Feed latency.** `ts_recv − ts_event` median 0.24–0.27 ms, p99 < 6 ms,
   worst case ≈ 0.4 s. The choice of clock cannot move a 2-minute bar boundary.

5. **`flags`.** Zero everywhere except 29 600 rows on 4 days in 2022_H1 which
   carry `flags = 4` (Databento `F_MAYBE_BAD_BOOK`). That flag concerns book
   consistency, not trade-price validity, and the trades schema does not depend
   on book state. Note that `F_LAST` (128) is never set in this export, so
   "last message of an event" cannot be recovered from the flags.

6. **Duplicate-event behaviour.** 283 803 groups / 363 651 extra rows in
   2021_H1 are byte-identical on `(ts_event, ts_recv, instrument_id, sequence,
   price, size, side)`. These are **not** feed duplicates: Databento's GLBX
   trades schema emits **one record per fill**, so a single aggressor matching
   several equal-sized resting orders produces several identical records.
   Cross-check: summing `size` gives ≈ 430 k contracts/day for the 2021 front
   month, which matches NQ's published ADV. **No de-duplication is applied** —
   removing them would understate volume. They are harmless for OHLC (identical
   price) and for TP/SL sequencing (identical price and time).

7. **No corruption found.** Zero nulls, zero non-positive sizes, single-valued
   `action` / `rtype` / `publisher_id` / `depth`, and NQ price ranges
   (10 484.75 – 22 387.75 over 2021-2024 front-month bars) match the index's
   actual history.

---

## 5. Multiple expiries and contract rolls

**Several NQ expiries coexist in every file, plus calendar spreads.** Example
(2021_H1): `NQM1` 32.5 M contracts, `NQH1` 28.1 M, `NQU1` 5.8 M, `NQZ1` 5 448,
alongside `NQH1-NQM1` (374 801), `NQM1-NQU1` (327 003) and six other spreads.
Blindly concatenating on `symbol` would splice two price series together.

Handling (see `src/nqr/data/contracts.py`):

* Spreads are excluded by `symbol NOT LIKE '%-%'` **and** the positive filter
  `^NQ[FGHJKMNQUVXZ][0-9]{1,2}$`.
* **Front contract for trading day D = the outright with the highest volume on
  the previous trading day D−1.** Strictly causal.
* Exactly **one** contract is used for the whole of day D, and every level for
  day D is computed from that same contract's own bars — so **no synthetic
  series and no simultaneous-expiry contamination is possible**.
* **No back-adjustment.** The strategy trades real levels; levels must be real
  prices. Since a day never mixes contracts, there is no jump to adjust away.
* **The roll day itself is excluded from signal generation** (13 days in
  development, 4 in validation), because on that day the newly-front contract's
  immediately preceding sessions were thin. From D+1 onward the previous day is
  already fully liquid in the new contract, so no further exclusion is needed.
* `ATR20` uses the plain **day range**, not true range, specifically so that a
  roll cannot inflate it.

### Outright volume, 2021–2024

| symbol | total contracts | days present |
|---|---|---|
| `NQZ2` | 45,032,598 | 206 |
| `NQH2` | 43,978,241 | 194 |
| `NQZ3` | 43,016,481 | 195 |
| `NQM4` | 42,705,234 | 198 |
| `NQM2` | 41,890,438 | 192 |
| `NQM3` | 40,789,321 | 185 |
| `NQU2` | 40,195,153 | 197 |
| `NQU4` | 39,611,341 | 195 |
| `NQH3` | 39,209,662 | 181 |
| `NQH4` | 39,191,547 | 190 |
| `NQU3` | 39,047,605 | 191 |
| `NQZ1` | 37,218,312 | 200 |
| `NQM1` | 32,537,533 | 120 |
| `NQZ4` | 32,190,145 | 209 |
| `NQU1` | 30,452,037 | 178 |
| `NQH1` | 28,100,902 | 55 |
| `NQH5` | 5,706,534 | 129 |
| `NQM5` | 7,835 | 55 |
| `NQU5` | 8 | 4 |
| `NQZ6` | 2 | 1 |

### Detected rolls

Textbook quarterly cycle, ~8 calendar days before third-Friday expiry
(2021-01-04 is the bootstrap day, which has no previous day to decide from):

| trading day | new front | volume basis day |
|---|---|---|
| 2021-01-04 | `NQH1` | None |
| 2021-03-16 | `NQM1` | 2021-03-15 |
| 2021-06-15 | `NQU1` | 2021-06-14 |
| 2021-09-14 | `NQZ1` | 2021-09-13 |
| 2021-12-13 | `NQH2` | 2021-12-10 |
| 2022-03-15 | `NQM2` | 2022-03-14 |
| 2022-06-14 | `NQU2` | 2022-06-13 |
| 2022-09-13 | `NQZ2` | 2022-09-12 |
| 2022-12-13 | `NQH3` | 2022-12-12 |
| 2023-03-14 | `NQM3` | 2023-03-13 |
| 2023-06-13 | `NQU3` | 2023-06-12 |
| 2023-09-12 | `NQZ3` | 2023-09-11 |
| 2023-12-12 | `NQH4` | 2023-12-11 |
| 2024-03-12 | `NQM4` | 2024-03-11 |
| 2024-06-18 | `NQU4` | 2024-06-17 |
| 2024-09-17 | `NQZ4` | 2024-09-16 |
| 2024-12-18 | `NQH5` | 2024-12-17 |

---

## 6. Decisions taken as a result of this audit

| finding | decision |
|---|---|
| spreads present, non-tick-aligned | excluded by symbol pattern; never eligible as front contract |
| several expiries per file | one volume-selected front contract per Globex day; levels from the same contract |
| `price` already in points and tick-exact | stored as `int32` ticks internally; all comparisons exact |
| `ts_event` has rare inversions | tick cache explicitly sorted by `(ts_event, row)`; regression-tested |
| `ts_event > ts_recv` in some 2023 rows | recorded, not corrected; immaterial at 250 ms modelled latency |
| repeated identical prints are genuine fills | no de-duplication |
| files cut at 00:00 UTC mid-session | all halves read together, grouped by Globex trading date |
| holidays / half sessions | no special-casing; the ≥ 30-bar-per-session rule suppresses stub levels |
| session mapping uncovered 16:00–17:00 ET | labelled `POST`; contributes to PDH/PDL but defines no session level |

---

## 7. Holdout status at the end of Phase 0

| period | status |
|---|---|
| 2021-01-01 → 2023-12-31 | development — used |
| 2024-01-01 → 2024-12-31 | validation — used once, after the freeze |
| 2025-01-01 → 2025-06-30 | **SEALED** (trades + MBP-1) — never opened |
| 2025-07-01 → | **SEALED** (trades only) — never opened |

`data_cache/bars/bars_2m.parquet` max trading date is **2023-12-28 / 2024-12-31**
(dev / full cache) and the cache contains **no row** dated 2025 or later —
asserted programmatically and unit-tested.
