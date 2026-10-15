# SEARCH_BUDGET_COMPLETION.md — Phase 7

Completion record required by `SEARCH_BUDGET.md` §13. That file is hashed into the
pre-registration set and is never edited to carry the count.

# TOTAL CONFIGURATIONS EVALUATED: 12 of a ceiling of 12

| dimension | permitted | used |
|---|---:|---:|
| base features | ≤ 40 | **40** |
| feature windows | 3 | 3 (1 s, 5 s, 15 s) |
| decision clocks | 1 | 1 (5 s) |
| sessions | 1 | 1 (09:30–11:30 ET) |
| R scales | 2 | 2 (15 pt, 25 pt) |
| RR | 1 | 1 (1R/1R) |
| maximum holds | 1 | 1 (15 min) |
| execution models | 1 | 1 |
| model families | 2 | 2 |
| hyperparameter settings per family | 1 | 1 |
| selectivity levels | 3 | 3 (1.0 % / 0.5 % / 0.2 %) |
| **configurations scored against an outcome** | **≤ 12** | **12** |
| production candidates frozen | ≤ 1 | **0** |
| fresh-validation runs | ≤ 1 | **0 — not spent** |

## Every configuration, and what happened to it

| id | n (2022) | net E[R] | PF(R) | eligible |
|---|---:|---:|---:|---|
| `R25:A_logit:top1p0` | 2,229 | −0.0389 | 0.924 | no |
| `R25:A_logit:top0p5` | 1,572 | −0.0626 | 0.880 | no |
| `R25:A_logit:top0p2` | 1,055 | −0.0639 | 0.878 | no |
| `R15:A_logit:top1p0` | 2,816 | −0.0760 | 0.858 | no |
| `R25:B_tree:top1p0` | 1,021 | −0.0857 | 0.839 | no |
| `R25:B_tree:top0p5` | 1,021 | −0.0857 | 0.839 | no |
| `R25:B_tree:top0p2` | 1,021 | −0.0857 | 0.839 | no |
| `R15:A_logit:top0p5` | 1,608 | −0.0962 | 0.822 | no |
| `R15:A_logit:top0p2` | 758 | −0.1046 | 0.806 | no |
| `R15:B_tree:top1p0` | 49 | −0.2289 | 0.523 | no |
| `R15:B_tree:top0p5` | 49 | −0.2289 | 0.523 | no |
| `R15:B_tree:top0p2` | 49 | −0.2289 | 0.523 | no |

**Failures and errors: none.** All 12 ran to completion.

## A disclosure about effective breadth

The six `B_tree` rows are **four duplicates**: a depth-3 tree emits at most 8
distinct probabilities, so the 99.0 / 99.5 / 99.8 percentiles of `|p − 0.5|` all
land inside the same tie group, and the preregistered rule keeps ties. The budget
therefore bought **8 distinct strategies, not 12**. This is disclosed rather than
corrected — changing the tie rule after seeing outcomes is precisely the failure
the preregistration exists to prevent.

## The budget was not reopened

No 13th configuration, no third R scale, no nearby parameter value, no additional
model family, no extra threshold, and no feature beyond the 40 registered — before
or after the gates failed. Post-hoc observations went to `FUTURE_HYPOTHESES.md`
marked **POST-HOC — REQUIRES NEW UNTOUCHED DATA**.

The three ablation arms (A0/A1/A2) and the two null tests (N1/N2) are
**diagnostics**, not configurations: they re-use the reference configuration's
family, R and selectivity and were run only after the phase had already failed.
They could not, and did not, promote anything.
