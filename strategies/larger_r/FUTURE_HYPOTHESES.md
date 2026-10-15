# FUTURE_HYPOTHESES.md — Phase 5

Everything in this file is

# POST-HOC — REQUIRES NEW UNTOUCHED DATA

It was observed after the Phase-5 candidate had already been rejected, on data
that has been used. None of it changed Phase 5, none of it is evidence, and none
of it may become a strategy on 2021–2025.

Untouched data remaining after Phase 5: **2026-Q1** (Trades, still pristine —
Phase 4 declined to spend it and Phase 5 never reached it), **2025-H1** (Trades
**and** MBP-1, sealed for order-flow work) and **2026-04-01 onward** (final
holdout). That is the entire budget for everything below. Spend it on one
well-motivated hypothesis, not on five.

---

## H5-1 — the signal picks the right context and the wrong minute

**The most important thing Phase 5 found, and it is a positive result inside a
negative one.**

Three nested populations, net R at 1.0 pt friction, at R = 4.0 × ATR14(1m):

| what is being selected | 2021 | 2022 | 2023 | 2024 | 2025-H2 |
|---|---:|---:|---:|---:|---:|
| nothing — every row, either direction | −0.029 | −0.018 | −0.027 | −0.023 | −0.020 |
| model's **day + 30-min bucket + direction**, random minute | **+0.269** | **+0.037** | **+0.093** | **+0.079** | **+0.040** |
| the model's own chosen minute as well | +0.188 | +0.094 | −0.038 | +0.083 | +0.029 |

Row 1 to row 2 is a large positive move in **every period, without exception**.
Row 2 to row 3 is negative in three of five, and on 2023 the gap is significant
(−0.131 R, CI [−0.247, −0.002]).

> The state signal identifies favourable *(trading day, half-hour, direction)*
> contexts. Its 60-second timing inside that context is not merely
> uninformative — it is **adverse**.

**Candidate mechanism, untested:** the model fires when something has *just*
happened, and entering at market on the very next print buys the worst point of
a local swing. A random minute in the same half hour gets a better average price.

**Hypothesis for a later phase:** keep the signal, discard the timing. Concretely
one of — (a) enter on a resting limit at a pullback rather than at market;
(b) delay entry by a fixed interval after the trigger; (c) treat the signal as a
*half-hour directional bias* and enter on a separate, simpler timing rule. Each
is a distinct hypothesis; pick one and preregister it.

## H5-2 — the friction/R architecture works and should be kept

Phase 4's binding constraint was friction at 14.35 % of R. Phase 5 cut it to
**2.96 %** by moving R from 7 points to 36–54 points, and the whole profile
changed with it:

| | Phase 4 | Phase 5 |
|---|---:|---:|
| average R | 7.0 pt | 44 pt |
| friction cost per trade | 0.1435 R | **0.0296 R** |
| median hold | 0.4 min | 27 min |
| trades/day | ~140 | 0.40 |
| max drawdown | thousands of R | 4.5–7.9 R |
| longest losing streak | 14–131 | 3–7 |
| profitable days | 2–7 % | 45–56 % |

**Gross expectancy also turned positive** in four of five periods, against ≈ 0 or
negative everywhere in Phase 4. The R architecture is not what failed and should
be carried forward unchanged into any successor phase.

## H5-3 — selectivity and hold are in tension; the frequency target was unreachable

Top-2 % selectivity × 60-minute holds × one position at a time produced **0.33–0.50
trades/day** and **70 % zero-trade days**, against a target of 2–7. A
120-decision session can physically fit about two non-overlapping 30-minute
trades, and the threshold rarely fires twice in a day.

That is why every period has only 56–128 trades — far too few to resolve an
effect of the size Phase 4 measured (~0.02 R).

**Hypothesis:** to get both a large R and a usable sample you need either a
longer signal window (a full RTH session rather than two hours), or several
independent instruments, or a looser threshold with position sizing by
confidence. All three are new designs.

## H5-4 — a training-only baseline imports the training year's drift

Phase 5 correctly refused to use theoretical 50 % as the null and estimated
`b_long`/`b_short` per half-hour bucket from 2021 alone. But 2021 was a strong up
year, so at `r4p0` the fitted long base rate is 0.5161 overall and **0.5404** in
the 11:00–11:30 bucket. Because the trade rule is
`edge = p − b_long` versus `(1 − p) − b_short`, a high `b_long` makes *shorts*
cheap to trigger in that bucket — and indeed on 2023 the candidate produced 581
of its 624 candidates in the second hour.

The baseline is leak-free (training-only, as required) but it hard-codes one
year's drift into where and which way the strategy fires.

**Hypothesis:** estimate the baseline on a *detrended* or drift-neutralised
basis, or over a rolling training window, or symmetrise it so it cannot encode a
directional prior. Any of these is a design change requiring new validation.

## H5-5 — distance from the session open is the strongest raw market effect found

From the unconditional diagnostics (46 cells examined, development years only,
R = 4.0 × ATR1m, net at 1.0 pt):

| `dist_open_norm` quartile | long E[R] | long WR | short E[R] |
|---|---:|---:|---:|
| 1 (furthest **below** the open) | −0.0487 | 0.4883 | +0.0019 |
| 2 | −0.0049 | 0.5097 | −0.0437 |
| 3 | −0.0229 | 0.5031 | −0.0256 |
| 4 (furthest **above** the open) | **+0.0391** | **0.5396** | −0.0951 |

Monotone in the tails and the largest single effect in the whole diagnostic set,
against an unconditional baseline of −0.024 R. It is a trend-day continuation
signature: when price is a long way above where the session opened, buying it
keeps working for another hour.

It is already *inside* the rejected model — `dist_open_norm` is its third-largest
coefficient (+0.292) — which is precisely why it cannot be claimed as a new
finding here. **As a standalone rule it has never been tested.**

## H5-6 — 11:00–11:30 is the only positive time bucket

| bucket | long E[R] | long WR |
|---|---:|---:|
| 09:30–09:45 | −0.0109 | 0.5095 |
| 09:45–10:00 | −0.0051 | 0.5111 |
| 10:00–10:15 | −0.0111 | 0.5076 |
| 10:15–10:30 | −0.0308 | 0.4979 |
| 10:30–10:45 | −0.0385 | 0.4921 |
| 10:45–11:00 | −0.0137 | 0.5098 |
| **11:00–11:15** | **+0.0076** | 0.5228 |
| **11:15–11:30** | **+0.0277** | 0.5304 |

Two of eight cells, modest magnitudes, and the session boundary is arbitrary —
11:30 is where *this project* stops looking, so a positive drift at the edge may
simply be the start of something outside the window. **Do not narrow the session
to it.** If anything it argues for testing a *later* window on new data.

## H5-7 — trade side / delta is now negative twice, at two different horizons

Phase 4: family 6 contributed **exactly zero** importance at a 5-second clock and
30-minute horizon. Phase 5: mean |coefficient| 0.048 against 0.056 across all 55
— below average — with `delta_accel` eliminated by L1, and the unconditional
delta quartiles flat from −0.0066 to −0.0132 R.

**Two independent horizons, same answer.** This is now a reasonably firm negative
on *trades-derived* order flow for NQ direction at these timescales, and it is
worth stating as a result rather than a disappointment.

It says **nothing** about real book data. Quote imbalance, queue dynamics, spread
state and depth live in MBP-1, which neither phase opened. That is exactly what
2025-H1 was sealed for, and after two clean negatives on the trades proxy it is
the better-motivated place to spend it than another trades-only variant.

## H5-8 — the selection rule should require the CI, not the point estimate

Phase 5's Gate E asked for `advantage > 0` as a point estimate. The winner passed
it at +0.058 R with a day-block CI of [−0.027, +0.148] — no statistical support —
and 2023 then rejected it. Ranking 18 configurations on expectancy alone also
systematically favours the smallest sample, which is what happened: the chosen
cell had 128 trades, the fewest of any r4p0 configuration that cleared the
minimum.

**Not a hypothesis about markets — a fix for the next preregistration.** Require
the advantage CI lower bound to exceed zero at the *selection* stage, and add a
minimum-sample floor that scales with the effect size being sought.
