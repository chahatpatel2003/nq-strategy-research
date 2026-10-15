# PHASE6_VERDICT.md — NQ Context + Entry-Timing Research

    spec            ctxentry-1.0.0
    entry budget    6 of 6 configurations evaluated
    eligible        NONE
    verdict         FAIL  (before fresh validation)
    validation      2026-Q1 NOT OPENED — no Phase-6 code read a 2026 row
    phase status    CLOSED

---

## 1. The verdict

# FAIL

Phase 6 fails twice over, and either failure alone would be sufficient.

**Its premise did not survive contact with a causal implementation.** The
Phase-5 decomposition that motivated this phase used future information; under a
strictly causal context rule the "good context" is statistically
indistinguishable from no context, and outside the model's own training year it
is *worse* than no context.

**And no entry mechanic beat random timing.** All six have a negative advantage
against a random entry inside the same context. So does entering immediately.
Not one passed the preregistered gates.

## 2. The audit came first, and it changed everything

The brief required auditing the Phase-5 context decomposition before building
anything. It was not causal.

`nqr.p5.backtest5.matched_controls` drew control entries from the **whole**
30-minute bucket and handed each one the direction of a signal that, for 44.1 %
of them, had **not yet fired** — a median of 6–8 minutes early, up to 29.

| period | controls | entered before their own signal | share |
|---|---:|---:|---:|
| 2021 | 846 | 363 | 42.9 % |
| 2022 | 1,119 | 453 | 40.5 % |
| 2023 | 838 | 382 | 45.6 % |
| 2024 | 687 | 335 | 48.8 % |
| 2025-H2 | 491 | 222 | 45.2 % |
| **total** | **3,981** | **1,755** | **44.1 %** |

Restricting the draw to minutes at or after the signal — changing nothing else —
halves the apparent context return and reverses the headline:

| | mean E[R] | periods where the Phase-5 strategy beat it |
|---|---:|---:|
| Phase-5 published control | +0.1034 | 2 of 5 |
| the same control, made causal | **+0.0521** | **3 of 5** |
| the Phase-5 strategy itself | +0.0712 | — |

> **Phase 5's finding that the model's entry timing was adverse was largely an
> artefact of its own control being allowed to see the future.**

Phase 5's *verdict* is untouched — its candidate still failed Gate F on 2023 on
four independent criteria. But the mechanism recorded in `PHASE5_VERDICT.md` §5
and `FUTURE_HYPOTHESES.md` H5-1 is now known to be unsound. Phase 5 is immutable,
so the correction lives in `CONTEXT_CAUSALITY_AUDIT.md`, here, and in
`reports/PHASE6_LEAKAGE_AUDIT.md` item 17.

## 3. The causal context does not survive

Random minutes inside an activated context vs random minutes in a no-context
bucket on the same day, same direction distribution, same R:

| period | contexts | in-context E[R] | non-context E[R] | diff | 95 % day-block CI |
|---|---:|---:|---:|---:|---|
| 2021 | 121 | **+0.2230** | −0.1769 | +0.3999 | **[+0.2242, +0.5768]** |
| 2022 | 139 | +0.0510 | +0.0783 | −0.0273 | [−0.2094, +0.1561] |
| 2023 | 93 | +0.0675 | −0.0272 | +0.0947 | [−0.1486, +0.3303] |
| 2024 | 89 | +0.0230 | +0.1871 | −0.1642 | [−0.3945, +0.0857] |
| 2025-H2 | 60 | −0.1210 | −0.0711 | −0.0499 | [−0.3112, +0.2281] |
| **pooled** | **502** | **+0.0711** | −0.0040 | +0.0752 | **[−0.0234, +0.1721]** |

The pooled interval contains zero. And the effect is one year:

| | in-context | non-context | diff |
|---|---:|---:|---:|
| all five periods | +0.0711 | −0.0040 | +0.0752 |
| **excluding 2021** | **+0.0220** | **+0.0513** | **−0.0293** |

**2021 is the year the context model was fitted.** It is the only period whose
interval excludes zero. Outside it, no-context moments are better.

`PHASE6_SEARCH_BUDGET.md` §6 makes this an independent failure condition, and it
is met.

## 4. No entry mechanic beat random timing

Pooled 2021–2025-H2, 09:30–11:30, 1R/1R, 1.0 pt friction:

| method | n | WR | gross E[R] | net E[R] | PF(R) | periods +ve | advantage vs random | 95 % day-block CI |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| E1 — 5 min delay | 369 | 0.5149 | +0.0567 | +0.0270 | 1.067 | 3/5 | −0.0442 | [−0.1064, +0.0173] |
| E2 — 10 min delay | 328 | 0.5091 | +0.0344 | +0.0043 | 1.010 | 2/5 | **−0.0669** | **[−0.1350, −0.0006]** |
| E3 — 0.25 R pullback | 323 | 0.5387 | +0.0945 | +0.0641 | 1.161 | 3/5 | −0.0070 | [−0.0846, +0.0712] |
| E4 — 0.50 R pullback | 227 | 0.4890 | +0.0123 | −0.0197 | 0.957 | 2/5 | −0.0909 | [−0.1960, +0.0110] |
| E5 — 0.25 R + resume | 321 | 0.5358 | +0.0772 | +0.0464 | 1.115 | 3/5 | −0.0247 | [−0.1002, +0.0511] |
| E6 — 0.50 R + resume | 221 | 0.4887 | +0.0103 | −0.0219 | 0.952 | 1/5 | −0.0931 | [−0.1982, +0.0099] |
| `CONTROL_IMMEDIATE` | 409 | 0.5550 | +0.0977 | +0.0680 | 1.181 | 4/5 | −0.0032 | [−0.0728, +0.0671] |
| **`CONTROL_RANDOM`** | **4,484** | **0.5511** | **+0.1005** | **+0.0711** | **1.194** | — | *(the null)* | — |

**Every mechanic is worse than random.** E2's interval excludes zero **on the
wrong side**: a fixed 10-minute delay is significantly worse than a coin toss on
the minute.

### Gates

| method | G1 n ≥ 300 | G2 ≥ 4/5 +ve | G2 combined > 0 | G3 PF(R) > 1.10 | G4 advantage CI > 0 | eligible |
|---|---|---|---|---|---|---|
| E1 | 369 ✓ | 3/5 ✗ | ✓ | 1.07 ✗ | ✗ | no |
| E2 | 328 ✓ | 2/5 ✗ | ✓ | 1.01 ✗ | ✗ | no |
| E3 | 323 ✓ | 3/5 ✗ | ✓ | 1.16 ✓ | ✗ | no |
| E4 | 227 ✗ | 2/5 ✗ | ✗ | 0.96 ✗ | ✗ | no |
| E5 | 321 ✓ | 3/5 ✗ | ✓ | 1.11 ✓ | ✗ | no |
| E6 | 221 ✗ | 1/5 ✗ | ✗ | 0.95 ✗ | ✗ | no |

**ELIGIBLE: NONE.** No mechanic reaches 4 of 5 positive periods and none has a
positive advantage lower bound. Per §6 of the budget there is no least-bad
candidate: **2026-Q1 stays sealed.**

## 5. Why — adverse selection offsets the price improvement almost exactly

The clearest result in Phase 6:

| method | price improvement vs immediate (R) | adverse excursion before entry (R) | net |
|---|---:|---:|---:|
| E1 | +0.0372 | 0.4901 | −0.4529 |
| E2 | +0.0733 | 0.6965 | −0.6232 |
| **E3** | **+0.2573** | **0.2786** | **−0.0213** |
| **E4** | **+0.5036** | **0.5296** | **−0.0260** |
| E5 | +0.2542 | 0.3837 | −0.1295 |
| E6 | +0.5084 | 0.6346 | −0.1261 |

A mechanic only gets a better price when the market has **already moved against
the context**, and at both pullback depths the discount it buys is within
**0.03 R** of the adverse excursion it must sit through. That is not a near-miss
to be optimised around — it is what an efficient market looks like at this
timescale, and it predicts that no pullback depth would work. Which is exactly
why the budget forbade testing more of them.

The clock delays are strictly worse: they absorb 0.49–0.70 R of adverse excursion
and are compensated with 0.04–0.07 R of price. And the unconditional data says
why — inside a context, **earlier is better**: random entries return +0.0770 R in
the first five minutes decaying to +0.0637 R at 15–20 minutes.

## 6. One diagnostic that is not a gate, reported anyway

Restricting `CONTROL_RANDOM` to only the contexts each mechanic actually entered
makes the pullbacks look good — E3 +0.0612, **E4 +0.0901 with a CI of
[+0.0028, +0.1795]**, E5 +0.0485, E6 +0.0739 — while both clock delays stay
negative.

**This does not rescue anything.** The preregistered comparison is against the
full control population and was fixed before any outcome; swapping it for a more
favourable one afterwards is the precise failure the budget exists to prevent.
And E4's absolute expectancy is still **−0.0197 R** — it loses *less* than random
in contexts that have already gone against it, which is loss mitigation, not an
edge. Logged as H6-2.

## 7. What Phase 6 established

1. **A leaky control manufactures a discovery.** 44.1 % of Phase-5's control
   entries preceded their own signal, and that single defect produced an entire
   research phase. The fix is a one-line assertion, now a permanent test.
2. **The causal context is not real out of sample.** Positive only in the year
   the model was fitted on; negative relative to no-context everywhere else.
3. **Better entry prices are not free.** At 0.25 R and 0.50 R the adverse
   selection matches the discount to within 0.03 R.
4. **Inside a context, waiting is strictly worse than not waiting** — the mild
   decay in the unconditional data, and the fact that immediate entry beats all
   six mechanics.

## 8. What this does and does not mean

**It does not mean entry timing is irrelevant.** The narrow statement:

> Given a causally activated context from the frozen Phase-5 direction model, in
> 09:30–11:30 ET, with R = 4 × ATR14(1-min) and a 60-minute hold, none of six
> preregistered deterministic entry mechanics — two clock delays, two pullback
> depths and two pullback-plus-resumption variants — beat entering at a random
> minute inside the same context, and the context itself does not beat no context.

Three things it did not test: **faster** mechanics (H6-4 says the edge is
front-loaded, and Phase 6 only tested slower ones); **passive limit entry** filled
by someone else's urgency rather than by an adverse trend (needs MBP-1); and the
**long/short asymmetry** of the direction model, which Phases 5 and 6 have now
flagged independently (H6-6).

## 9. Reproduction

```bash
python -m pytest tests -q                                    # 369 tests

python scripts/p6_00_fingerprint.py                          # pin Phase-5 artifacts
for s in train2021 select2022 itest2023 contam2024 contam2025h2; do
    python scripts/p6_01_run_split.py --split $s
done
python scripts/p6_02_analyse.py                              # context + gates -> FAIL
python scripts/p6_03_diagnostics.py
python scripts/p6_04_charts.py
python scripts/p6_05_report.py && python scripts/p6_05b_report.py
python scripts/p6_09_integrity.py

# NEVER RUN — no candidate qualified, so there is no route here:
# python scripts/p6_01_run_split.py --split val2026q1 \
#     --confirm I_AM_UNLOCKING_ONLY_2026_Q1_FOR_PHASE6_VALIDATION
```

## 10. Seals at the close of Phase 6

| window | status |
|---|---|
| 2025-01-01 … 2025-06-30 (Trades **+ MBP-1**) | **SEALED — never opened by any phase** |
| 2026-01-01 … 2026-03-31 | **UNOPENED — footer metadata only; not spent by Phase 4, 5 or 6** |
| 2026-04-01 onward | **SEALED — never opened by any phase** |

MBP-1 was not opened in Phase 6 at all; the guard refuses it, and no Phase-6
module calls `read_parquet`.

Phases 1–4 remain byte-identical:
`fastslow-1.0.0+5980044a44eebf7b`,
`impexh-1.0.0.impl2+48c76a0e68b88947`,
`dcevent-1.0.0.impl3+d33e5d5d116f1adb`,
`statedisc-1.0.0+c147134184dfb32d`.
Phase-5 artifacts pinned at `d0783a6638d88aec` (11 files) and unchanged.
