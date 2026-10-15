# FEATURE_CACHE.md — Phase 7

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
| columns | 42 |
| output | `data_cache/p7_book1s/ym=YYYY-MM/*.parquet`, zstd, partitioned by month |

## What was built

| | |
|---|---|
| split | dev (2021-01-01 … 2023-12-31) |
| months | 36 |
| build time | 60.4 min (~101 s/month) |
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
26 s:

| | |
|---|---|
| rows | 1,097,280 (762 days × 1,440 decisions) |
| decision clock | every 5 s, 09:30–11:30 ET |
| features | 40 |
| R scales | {'R15': 15.0, 'R25': 25.0} |
| max hold | 15 min |

Validation: **100 % of rows have all 40 features finite**, 99.29 % have a book
event at the decision second, 99.74 % obtain an entry fill, and the minimum
realised entry latency is exactly **250.0 ms** — never earlier than the model.
