# FEATURE_REGISTRY.md — Phase 7 causal top-of-book state

**Written and frozen BEFORE any label or outcome was computed.**

**40 base features** — the hard cap, exactly reached, not exceeded. Every one is
derived from the actual MBP-1 schema audited in `MBP1_SCHEMA_AUDIT.md`. Nothing
here assumes depth beyond level 0, order IDs, queue position or hidden
liquidity, because none of those exist in this data.

## Conventions

* `t` — decision timestamp, every 5 s during 09:30:00–11:30:00 ET.
* The per-second book cache is expanded onto a dense 1-second grid over
  09:00–12:00 ET. Grid index `i` is the second `[T0+i, T0+i+1)`; a decision
  stamped `T0+i+1` reads `grid[i]`, so **every input second has closed**.
* Seconds with no book event carry the **last known** quote forward (causal);
  their event counters are zero.
* Windows are **1 s, 5 s, 15 s**, all trailing and closed at `i`. No centred
  window, no forward fill from a later second, no nearest-neighbour join.
* `b`, `a` = best bid/ask price; `B`, `A` = `bid_sz_00`, `ask_sz_00`.
* `scale` = trailing 15 s mean of `(B + A)`, the liquidity unit used to make
  contract-denominated quantities regime-free.
* Event-level quantities (OFI, size increases/decreases, price steps, adds,
  cancels) are computed **event by event** from the ordered stream
  `(ts_event, sequence, file_row_number)` and only then summed into a second.

---

## Family 1 — current BBO state (7)

| # | name | formula |
|---|---|---|
| 1 | `spread_ticks` | `(a − b) / 0.25` |
| 2 | `bid_sz` | `B` |
| 3 | `ask_sz` | `A` |
| 4 | `bbo_sz_total` | `B + A` |
| 5 | `imb` | `(B − A) / (B + A)` |
| 6 | `micro_off_ticks` | `(microprice − mid) / 0.25` |
| 7 | `avg_ord_sz_bbo` | `(B + A) / (bid_ct + ask_ct)` |

**Microprice** — the one formula most easily got backwards, so it is stated
explicitly and unit tested:

    microprice = (a·B + b·A) / (B + A)

Each price is weighted by the **opposite** side's size. A heavy bid therefore
pushes the microprice **up toward the ask**. Verified empirically on the built
cache: with `imb > +0.8` the mean `(micro − mid) / spread` is **+0.432**; with
`imb < −0.8` it is **−0.432**; and the microprice lies inside the spread on
100 % of rows.

`avg_ord_sz_bbo` uses `bid_ct_00`/`ask_ct_00`, which MBP-1 does provide — the
count of resting orders at the touch. It does **not** imply queue position.

## Family 2 — BBO imbalance persistence (4)

| # | name | window | formula |
|---|---|---|---|
| 8 | `imb_mean_5` | 5 s | event-weighted mean of per-event imbalance |
| 9 | `imb_mean_15` | 15 s | same over 15 s |
| 10 | `imb_frac_pos_15` | 15 s | `n(imb>0) / (n(imb>0) + n(imb<0))`, event counts |
| 11 | `imb_dev_1_15` | 15 s | `imb − imb_mean_15` (latest minus trailing mean) |

Event-weighted, not second-weighted: a second with 900 events carries more
weight than one with 3, which is what "persistent imbalance" should mean.

## Family 3 — microprice pressure (4)

| # | name | window | formula |
|---|---|---|---|
| 12 | `micro_off_mean_5` | 5 s | event-weighted mean `(micro − mid)`, in ticks |
| 13 | `micro_off_mean_15` | 15 s | same over 15 s |
| 14 | `micro_press_persist_15` | 15 s | `Σ sign(micro − mid) / n(seconds with events)`, in [−1, 1] |
| 15 | `micro_off_change_5` | 5 s | `micro_off_ticks − micro_off_mean_5` |

## Family 4 — quote update intensity (4)

| # | name | window | formula |
|---|---|---|---|
| 16 | `quote_upd_per_s_5` | 5 s | `(bid updates + ask updates) / 5` |
| 17 | `upd_asym_5` | 5 s | `(bid upd − ask upd) / (bid upd + ask upd)` |
| 18 | `bid_px_chg_per_s_15` | 15 s | best-bid price changes per second |
| 19 | `ask_px_chg_per_s_15` | 15 s | best-ask price changes per second |

An "update" is an event where that side's price **or** size changed from the
previous event.

## Family 5 — top-of-book order-flow imbalance (3)

| # | name | window |
|---|---|---|
| 20 | `ofi_1` | 1 s |
| 21 | `ofi_5` | 5 s |
| 22 | `ofi_15` | 15 s |

Per-event OFI is the **Cont–Kukanov–Stoikov** top-of-book formulation, computed
between consecutive events of the ordered stream:

    bid term:   P^b_n > P^b_{n−1}  ->  +q^b_n
                P^b_n = P^b_{n−1}  ->  q^b_n − q^b_{n−1}
                P^b_n < P^b_{n−1}  ->  −q^b_{n−1}

    ask term:   P^a_n < P^a_{n−1}  ->  −q^a_n
                P^a_n = P^a_{n−1}  ->  −(q^a_n − q^a_{n−1})
                P^a_n > P^a_{n−1}  ->  +q^a_{n−1}

    e_n = bid term + ask term          (positive = buying pressure)

Summed over the window and divided by `scale`. Because a `T` row carries the
book state *before* its fill is applied (see `MBP1_SCHEMA_AUDIT.md` §5), the
depletion caused by a trade enters OFI through the `C`/`M` row that follows it —
so trades are captured **once**, not twice. All six transition cases are unit
tested, and the SQL in `cache7.BOOK_SQL` and the reference implementation in
`features7.ofi_event` are tested against each other.

## Family 6 — displayed size decrease / increase (4)

MBP-1 does expose `action` (`A`/`C`/`M`/`T`), so adds and cancels are observable
rather than inferred. These features nonetheless measure the **objective size
change at an unchanged best price**, which is the quantity that matters for the
touch and does not require attributing a change to a particular order.

| # | name | window | formula |
|---|---|---|---|
| 23 | `bid_net_size_flow_5` | 5 s | `(Σ bid size increases − Σ bid size decreases) / scale` |
| 24 | `ask_net_size_flow_5` | 5 s | `(Σ ask size increases − Σ ask size decreases) / scale` |
| 25 | `repl_ratio_bid_15` | 15 s | `Σ bid increases / Σ bid decreases` |
| 26 | `repl_ratio_ask_15` | 15 s | `Σ ask increases / Σ ask decreases` |

"Increase" and "decrease" mean exactly that — a size change at the same best
price. They are **not** called cancellations or additions, because a single
order's identity is not observable.

## Family 7 — price-level step asymmetry (2)

| # | name | window | formula |
|---|---|---|---|
| 27 | `bid_step_asym_15` | 15 s | `(n bid-up − n bid-down) / (n bid-up + n bid-down)` |
| 28 | `ask_step_asym_15` | 15 s | `(n ask-up − n ask-down) / (n ask-up + n ask-down)` |

Objective counts of best-price steps. No inference about hidden orders.

## Family 8 — trade aggression (4)

Uses the MBP-1 `T` rows directly, which are natively aligned to the book state.
Their `side` is the **aggressor** side, verified against the book on the raw
stream and consistent with the Trades-file convention Phase 2 validated at
99.998 % over 3.88 M trades. The MBP-1 `T` rows reconcile with the Trades cache
to within **0.02 %** on volume and count over a sampled day.

| # | name | window | formula |
|---|---|---|---|
| 29 | `trd_delta_5` | 5 s | `(buy vol − sell vol) / (buy vol + sell vol)` |
| 30 | `trd_delta_15` | 15 s | same over 15 s |
| 31 | `trd_vol_rel_5` | 5 s | `volume/s over 5 s ÷ mean volume/s over 15 s` |
| 32 | `avg_trd_sz_5` | 5 s | `volume / trade count` |

## Family 9 — replenishment after aggression (2)

The genuinely new MBP concept: how much displayed size was **restored** per unit
of aggression, using only replenishment that has **already happened** before the
decision. No "eventually replenished" look-ahead.

| # | name | window | formula |
|---|---|---|---|
| 33 | `ask_repl_per_buy_15` | 15 s | `Σ ask size increases / (aggressive buy volume + 1)` |
| 34 | `bid_repl_per_sell_15` | 15 s | `Σ bid size increases / (aggressive sell volume + 1)` |

## Family 10 — failure to advance (2)

| # | name | window | formula |
|---|---|---|---|
| 35 | `progress_per_signed_vol_15` | 15 s | `Δmid in ticks / (\|buy − sell\| + 1)` |
| 36 | `agg_vol_no_progress_15` | 15 s | `(buy + sell) / (\|Δmid in ticks\| + 1)` |

**No interpretation is encoded.** High aggression with weak progress *might* be
absorption and *might* be noise; the model decides. Phase 2 failed by asserting
the interpretation, and this registry deliberately does not.

## Family 11 — minimal market context (4)

Deliberately small. Phase 7 tests whether the **book** adds information, so the
price/trade context is kept to the minimum needed to avoid confounding by
volatility regime and time of day. This is not a rebuild of the Phase-4
55-feature state.

| # | name | formula |
|---|---|---|
| 37 | `atr1m_ticks` | ATR14 of **completed** 1-minute bars, floor 2.0 pt, in ticks — the frozen `nqr.p2.features.causal_atr_minutes` |
| 38 | `atr_pct_rank` | trailing within-day percentile of `atr1m` over the strictly prior 120 minutes |
| 39 | `secs_since_open` | `t − 09:30:00 ET`, seconds |
| 40 | `ret_15s_norm` | `(mid − mid 15 s ago) / atr1m` |

**Recorded risk:** `secs_since_open` was among the features the Phase-4 tree
leaned on hardest, and that model did not generalise. It is included because the
brief lists it and because time-of-day genuinely conditions book behaviour, but
its importance is reported explicitly in the feature-importance report.

The ATR warm-up uses the trades cache over 08:00–12:00 ET, so ATR14 and its
120-minute trailing percentile are fully warmed by 09:30.

---

## Ablation groups (fixed here, used as diagnostics only)

| group | features | definition |
|---|---:|---|
| **A0 full** | 40 | everything |
| **A1 quote-only** | 32 | drops families 8, 9, 10 — every feature that needs trade volume |
| **A2 trades + context** | 8 | drops families 1–7, 9, 10 — every feature that needs the book |

A2 is families 8 and 11 only. Note `ret_15s_norm` uses mid, a book quantity;
under A2 it is the sole survivor that touches the book at all and is retained
because a price return is not order-book information in any meaningful sense —
this is stated so the reader can discount the A2 arm accordingly rather than
being told it is purely trade-derived.

## Excluded, deliberately

* **Any level beyond `_00`** — it does not exist in MBP-1.
* **Queue position, order lifetime, order-level aggressiveness** — no order IDs.
* **Hidden/iceberg liquidity** — not represented.
* **Depth-weighted or multi-level imbalance** — no depth.
* Any external series (ES, QQQ, VIX, options, news, sentiment, calendar).
* Hand-built interaction terms — the depth-3 tree may find interactions within
  its cap; none are constructed by hand.

## Live computability

Every feature is a trailing aggregate over the last ≤ 15 seconds of top-of-book
events plus one 14-minute ATR, computable incrementally from a live MBP-1 feed
with no lookahead and no vendor-derived inputs.
