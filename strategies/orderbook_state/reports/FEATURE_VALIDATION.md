# FEATURE_VALIDATION.md — Phase 7

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
