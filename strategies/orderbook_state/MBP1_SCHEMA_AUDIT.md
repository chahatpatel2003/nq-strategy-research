# MBP1_SCHEMA_AUDIT.md — Phase 7

**Written before any Phase-7 feature was designed and before any outcome was
computed.** Everything below is established from the files themselves — parquet
footers for inventory and coverage, and a small number of **2021 development**
rows for semantics. **No 2025-H1 market row was decoded.**

---

## 1. Inventory (parquet footer metadata only)

| file | GB | rows | row groups | first `ts_event` (UTC) | last `ts_event` (UTC) |
|---|---:|---:|---:|---|---|
| `2021_H1.parquet` | 18.6 | 657,942,643 | 10,040 | 2020-12-27 20:00:24 | 2021-06-30 23:59:59 |
| `2021_H2.parquet` | 19.8 | 705,575,236 | 10,767 | 2021-06-30 16:50:56 | 2021-12-31 22:00:00 |
| `2022_H1.parquet` | 27.1 | 964,817,016 | 14,722 | 2022-01-02 20:00:06 | 2022-06-30 23:59:59 |
| `2022_H2.parquet` | 23.6 | 841,208,433 | 12,836 | 2022-06-26 19:00:10 | 2022-12-30 22:00:00 |
| `2023_H1.parquet` | 21.9 | 778,472,503 | 11,879 | 2023-01-01 20:00:04 | 2023-06-30 21:00:00 |
| `2023_H2.parquet` | 24.3 | 874,549,719 | 13,345 | 2023-07-02 12:00:03 | 2023-12-31 13:00:04 |
| `2024_H1.parquet` | 24.4 | 875,658,962 | 13,362 | 2023-12-31 13:00:04 | 2024-06-30 23:59:59 |
| `2024_H2.parquet` | 27.1 | 958,974,497 | 14,633 | 2024-06-30 12:00:04 | 2024-12-31 22:00:00 |
| **`2025_H1.parquet`** | **35.3** | **1,236,114,072** | **18,862** | **2024-12-29 13:00:05** | **2025-06-30 23:59:59** |
| **total** | **222** | **7,893,313,081** | | | |

**MBP-1 coverage runs 2021-H1 through 2025-H1 and stops there.** There is no
2025-H2 and no 2026 MBP-1 file — the later halves exist for Trades only. That
makes 2025-H1 not merely the last *untouched* MBP window but the last MBP window
that exists at all.

**2025-H1 coverage, established from the footer without decoding a row:**
1,236,114,072 rows across 18,862 row groups, spanning 2024-12-29 13:00 UTC to
2025-06-30 23:59 UTC. It is fully populated and its first timestamps fall in
**December 2024** — so any read of it must carry the Globex trading-date
predicate, not a naive file-level assumption.

**Half-year files overlap at their boundaries.** `2023_H2` ends and `2024_H1`
begins at the identical timestamp `2023-12-31 13:00:04.375472715`. Phase 7
therefore bounds every scan by explicit per-month `ts_event` limits as well as by
the trading-date guard, so no trading date can be read from two files.

## 2. Schema — identical across all nine files

| # | column | type |
|---:|---|---|
| 0 | `ts_event` | `timestamp[ns, tz=UTC]` |
| 1 | `rtype` | `uint8` |
| 2 | `publisher_id` | `uint16` |
| 3 | `instrument_id` | `uint32` |
| 4 | `action` | `large_string` |
| 5 | `side` | `large_string` |
| 6 | `depth` | `uint8` |
| 7 | `price` | `double` |
| 8 | `size` | `uint32` |
| 9 | `flags` | `uint8` |
| 10 | `ts_in_delta` | `int32` |
| 11 | `sequence` | `uint32` |
| 12 | `bid_px_00` | `double` |
| 13 | `ask_px_00` | `double` |
| 14 | `bid_sz_00` | `uint32` |
| 15 | `ask_sz_00` | `uint32` |
| 16 | `bid_ct_00` | `uint32` |
| 17 | `ask_ct_00` | `uint32` |
| 18 | `symbol` | `large_string` |
| 19 | `ts_recv` | `timestamp[ns, tz=UTC]` |

Verified field-by-field identical (names **and** types) across all nine files.

# 3. WHAT THIS DATA IS — AND IS NOT

## It IS: one book level, with event actions

* **exactly one level of depth.** The only book columns are `_00`. There is no
  `bid_px_01`, no `_02`, no `_09`. `depth` is **0 on every row** of the sampled
  RTH window. **This is standard MBP-1 and Phase 7 uses only the top of book.**
* **`action` is populated and meaningful.** Observed values over a 30-minute RTH
  sample (all symbols): `A` add (373,121), `C` cancel (341,164), `M` modify
  (122,930), `T` trade (55,871). This is stronger than a pure quote feed — Phase 7
  **can** legitimately count adds and cancels at the top of book rather than
  inferring them from size changes, and it does both.
* **`side`** ∈ {`B`, `A`, `N`}. On a `T` row it is the **aggressor** side: a trade
  printing at the ask carries `side='B'`, a trade at the bid carries `side='A'`.
  Verified directly against the book columns on the raw stream, and consistent
  with the Trades-file convention Phase 2 verified at 99.998 % over 3.88 M trades.
* **`bid_ct_00` / `ask_ct_00`** give the **number of resting orders** at the best
  price, which permits an average-order-size-at-BBO measure.
* **`sequence`** is present and is monotone in `ts_event`.

## It is NOT: depth, and it is NOT MBO

Phase 7 therefore **cannot** and **does not** measure any of the following, and
no feature pretends otherwise:

| not available | why |
|---|---|
| level-2…10 depth, book shape, depth-weighted imbalance | only `_00` exists |
| **queue position** | no order IDs; a cancel cannot be ranked within its level |
| individual order lifetime, order-level aggressiveness | no order IDs |
| hidden / iceberg liquidity | not represented in MBP-1 |
| refresh of a *specific* order vs a *new* order at the same price | `A` tells us an add occurred, not whose |
| depth beyond the touch consumed by a sweep | the sweep's deeper fills appear as `T` rows but the resulting deeper book does not |

**A Phase-7 failure would therefore not be evidence against order-flow research
generally.** It would be evidence about the **top of book only**.

## 4. Event ordering — the critical audit

Phase 6 closed on a control-causality defect, so ordering was audited before any
feature was written.

Measured on NQH1 over 09:30–10:00 ET, 2021-03-10 (656,093 rows):

| quantity | value |
|---|---:|
| rows | 656,093 |
| distinct `ts_event` | 592,404 |
| rows sharing a `ts_event` with another row | 119,514 (18.2 %) |
| maximum rows at one `ts_event` | 45 |
| `ts_event` values where `sequence` **cannot** break the tie | **12,283** |
| times `sequence` decreases when ordered by `(ts_event, sequence)` | **0** |

So:

* **`sequence` is a valid ordering key** — monotone in `ts_event`, never
  decreasing.
* **`sequence` is not unique.** Multi-message exchange packets share both
  `ts_event` and `sequence`. The clearest case is a single aggressive order
  sweeping two price levels, which emits two `T` rows with identical `ts_event`
  and identical `sequence` at two different prices.

**Frozen ordering rule:**

    ORDER BY ts_event, sequence, file_row_number

File row order is the exchange's own within-packet message order and is the only
defensible final tie-break. It is fully deterministic. Asserted by
`tests/test_p7_causality.py`.

Because Phase 7's decision clock is 5 seconds and its features aggregate to whole
seconds, rows sharing a `ts_event` always fall in the same second — the ordering
matters for computing **transitions** correctly, not for assigning events to
decision times.

## 5. Book-state semantics — what a row's `bid_*`/`ask_*` mean

Established by reading the raw ordered stream. Excerpt (NQH1, 2021-03-10
06:35:00 ET, ordered by the rule above):

```
 seq        action side price      size  bid_px    bid_sz  ask_px    ask_sz
 233746922  A      A    12921.75   1     12921.00  2       12921.75  1
 233746983  T      B    12921.75   1     12921.00  2       12921.75  1   <- packet
 233746983  T      B    12922.25   1     12921.00  2       12921.75  1   <- same seq
 233746984  C      A    12922.25   1     12921.00  2       12922.25  2
```

A `T` row still shows the **resting liquidity being consumed**; the removal
appears on the `C`/`M` row that follows in the same packet. Consequently:

* order-flow imbalance computed on **book-state transitions between consecutive
  rows** captures trade-driven depletion via the following message and **does not
  double count** the trade;
* the two `T` rows above are one sweep, and file order preserves which level was
  taken first.

## 6. Data quality — full RTH day, NQH1, 2021-03-10 (5,245,685 rows)

| check | result |
|---|---:|
| null `bid_px_00` or `ask_px_00` | **0** |
| null `bid_sz_00` or `ask_sz_00` | **0** |
| crossed or locked (`ask ≤ bid`) | **0** |
| zero size at either side of the touch | **0** |
| zero order count at either side | **0** |
| minimum spread | 0.25 (1 tick) |
| median spread | 0.75 (3 ticks) |
| maximum spread | 9.00 |

The feed is clean. Phase 7's ingest nonetheless filters defensively on
non-null prices, positive sizes and `ask > bid`, and the count of rows dropped is
reported in the feature-validation report.

## 7. `flags`

Two values observed in the sample: `130` and `0`. `T` rows carry `0`; the final
message of a packet carries `130`, whose high bit (128) is Databento's
`F_LAST`. Phase 7 does **not** rely on flag semantics for any feature — the
ordering rule in §4 already reconstructs packet order — and the observed values
are recorded here only so the reader can see that no flag was silently assumed.

## 8. What Phase 7 reads, and what it never reads

| period | MBP-1 access |
|---|---|
| 2021, 2022, 2023 | development — read to build the per-second cache |
| 2024 | contaminated diagnostic — read **only after** the candidate is frozen |
| **2025-H1** | **fresh validation — metadata only until earned; the guard has one narrow unlock** |
| 2025-H2, 2026 | **no MBP-1 exists, and `holdout7` refuses the paths regardless** |

`src/nqr/p7/holdout7.py` blocks `2025_H2`, `2026_H1`, `2026_H2` and any raw
`.dbn` unconditionally, and blocks `2025_H1` until the explicit Phase-7 phrase is
given. 2026 has **no unlock path at all** in Phase 7.
