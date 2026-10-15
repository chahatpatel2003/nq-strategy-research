# CONTEXT_CAUSALITY_AUDIT.md — Phase 6

**Written before any Phase-6 entry mechanic was evaluated.**

The brief required this audit first, and it was right to. The Phase-5
decomposition that motivated Phase 6 is **not causal**, the leak is large and
measurable, and removing it substantially reverses the Phase-5 headline.

---

## 1. What Phase 5 actually computed

The row Phase 5 published as

> model's day + half-hour + direction, **random minute**

is the output of `nqr.p5.backtest5.matched_controls`. For each **accepted
strategy trade** it:

1. took the trade's `(trading_date, 30-minute bucket)`;
2. pooled **every** usable decision row in that whole bucket;
3. kept those whose R was within [0.80, 1.25] × the trade's R;
4. drew up to 10 at random;
5. **assigned each of them the strategy trade's direction.**

Step 2 does not restrict the draw to minutes at or after the signal. Step 5
hands those earlier minutes a direction that did not exist yet.

## 2. The leak, measured

Every Phase-5 control row stores `matched_to_ts`, the timestamp of the signal it
inherited its direction from. Comparing that against the control's own decision
timestamp:

| period | controls | entered **before** the signal | share | median lead | max lead |
|---|---:|---:|---:|---:|---:|
| 2021 | 846 | 363 | 42.9 % | 8.0 min | 29.0 min |
| 2022 | 1,119 | 453 | 40.5 % | 7.0 min | 29.0 min |
| 2023 | 838 | 382 | 45.6 % | 8.0 min | 29.0 min |
| 2024 | 687 | 335 | 48.8 % | 8.0 min | 29.0 min |
| 2025-H2 | 491 | 222 | 45.2 % | 6.0 min | 29.0 min |
| **total** | **3,981** | **1,755** | **44.1 %** | — | 29.0 min |

**44.1 % of the entries in Phase-5's "context" row were placed before the model
signal that told them which way to trade**, by a median of 6–8 minutes and by as
much as 29.

There are three distinct leaks, and they compound:

1. **Direction leak.** The direction came from a signal that, for 44 % of
   controls, fires *after* the entry. This is straightforward look-ahead.
2. **Bucket-selection leak.** A `(day, bucket)` cell only enters the pool
   because a qualifying signal occurred *somewhere* in it. Cells with no signal
   are never sampled. Knowing "a signal will occur in this half hour" is itself
   future information at any minute before it.
3. **Survivorship.** The pool is built only from buckets where the strategy's
   trade was `ACCEPTED` — i.e. not skipped by the one-position or cooldown
   rules — so the cell set is conditioned on the strategy's full-day sequencing.

## 3. How much the leak was worth

Re-running the identical control with **one** change — the draw is restricted to
decision rows at or after the signal, leaks 2 and 3 untouched:

| period | strategy | published control | **causal control** | leak |
|---|---:|---:|---:|---:|
| 2021 | +0.1875 | +0.2689 (n=846) | **+0.2273** (n=700) | +0.0415 |
| 2022 | +0.0943 | +0.0367 (n=1,119) | **+0.0480** (n=953) | −0.0113 |
| 2023 | −0.0379 | +0.0928 (n=838) | **+0.0480** (n=667) | +0.0449 |
| 2024 | +0.0826 | +0.0791 (n=687) | **+0.0190** (n=544) | +0.0602 |
| 2025-H2 | +0.0292 | +0.0395 (n=491) | **−0.0819** (n=400) | +0.1215 |
| **mean** | **+0.0712** | **+0.1034** | **+0.0521** | **+0.0513** |

Removing only the timing leak halves the apparent context return, and 2025-H2
flips from +0.0395 to −0.0819.

## 4. The consequence for the Phase-5 conclusion

Phase 5 concluded:

> The signal identifies favourable (day, half-hour, direction) contexts. Its
> 60-second timing inside them is adverse.

Counting how often the strategy beat its control:

| comparison | strategy better in |
|---|---|
| vs the **published** (leaky) control | 2 of 5 periods |
| vs the **causal** control | **3 of 5 periods** |

and on the mean, the strategy (+0.0712) is **above** the causal control
(+0.0521), where it was below the leaky one (+0.1034).

> **The Phase-5 finding that the model's entry timing is adverse was largely an
> artefact of its own control being allowed to see the future.** A benchmark
> given look-ahead beat a strategy that was not. That is not evidence about
> timing.

This does not rescue Phase 5 — its candidate still failed Gate F on 2023 on four
independent criteria, and that verdict stands untouched. But the *reason*
recorded in `PHASE5_VERDICT.md` §5 and `FUTURE_HYPOTHESES.md` H5-1 is now known
to be unsound, and the correction is recorded here rather than by editing Phase 5,
which is immutable.

## 5. What Phase 6 does instead

Because the Phase-5 context is **not** proven causal, this audit takes the
branch the brief specified: build the context activation rule from scratch,
fully causally, and re-measure.

**Phase-6 Context Activation Rule (frozen, implemented in `nqr.p6.context6`):**

* the session 09:30–11:30 ET is divided into four fixed 30-minute buckets;
* inside each bucket, the **first** decision timestamp whose frozen Phase-5 edge
  score clears the frozen `tau = 0.179938` activates the context;
* its predicted direction is **locked** for the remainder of that bucket — later
  flips, and later higher scores, are ignored;
* R is locked at activation from the frozen `r4p0` rule;
* the reference price is the first executable print after activation;
* at most **one** context per bucket; if nothing qualifies, there is **no**
  context;
* every entry mechanic and every control may only trigger in
  `[activation, bucket_end)`.

Nothing about a context depends on anything after its activation timestamp.
This is asserted by
`tests/test_p6_context.py::test_context_uses_no_information_after_its_activation_timestamp`,
which deletes the entire future and requires the context to be identical, and by
`test_context_activates_on_the_FIRST_qualifying_signal_in_a_bucket`, which plants
a *higher* score later in the bucket and requires it to be ignored.

## 6. Does the causal context survive?

**Largely, no.** Random minutes inside an activated context, against random
minutes in a no-context bucket on the same day with the same direction
distribution and the same R scale:

| period | contexts | in-context E[R] | n | non-context E[R] | n | diff | 95 % day-block CI |
|---|---:|---:|---:|---:|---:|---:|---|
| 2021 | 121 | **+0.2230** | 1,096 | −0.1769 | 1,130 | +0.3999 | [+0.2242, +0.5768] |
| 2022 | 139 | +0.0510 | 1,276 | +0.0783 | 1,150 | −0.0273 | [−0.2094, +0.1561] |
| 2023 | 93 | +0.0675 | 803 | −0.0272 | 930 | +0.0947 | [−0.1486, +0.3303] |
| 2024 | 89 | +0.0230 | 790 | +0.1871 | 850 | −0.1642 | [−0.3945, +0.0857] |
| 2025-H2 | 60 | −0.1210 | 519 | −0.0711 | 600 | −0.0499 | [−0.3112, +0.2281] |
| **pooled** | **502** | **+0.0711** | 4,484 | −0.0040 | 4,660 | +0.0752 | **[−0.0234, +0.1721]** |

The pooled interval **contains zero**. And the whole effect is one year:

| | in-context | non-context | diff | 95 % CI |
|---|---:|---:|---:|---|
| all five periods | +0.0711 | −0.0040 | +0.0752 | [−0.0234, +0.1721] |
| **excluding 2021** | **+0.0220** | **+0.0513** | **−0.0293** | [−0.1440, +0.0848] |

**2021 is the year the context model was fitted on.** Outside it, no-context
moments are *better* than in-context moments. The only period whose CI excludes
zero is the in-sample one.

## 7. Verdict of the audit

1. The Phase-5 decomposition **used future information** — 44.1 % of its control
   entries preceded the signal that gave them direction. It is not a tradable
   context and must not be described as one.
2. Under a strictly causal activation rule, the context is **positive in
   absolute terms but statistically indistinguishable from no context**, and the
   entire advantage is confined to the model's own training year.
3. Phase 6 proceeds anyway, because the entry question is still well posed —
   *given* an activated context, does a deterministic entry mechanic beat random
   timing inside it? — and because the answer is worth knowing regardless of
   whether the context itself is real.
4. Per `PHASE6_SEARCH_BUDGET.md` §6, a context that does not beat non-context is
   an **additional failure condition** for Phase 6, reported prominently
   whatever the six mechanics show.

This document was written before any of E1–E6 had an outcome computed against it.
