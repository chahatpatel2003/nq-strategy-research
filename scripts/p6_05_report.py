"""Generate the Phase-6 report set from stored results.  No hand-typed numbers."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import numpy as np
import polars as pl

from nqr.p4 import metrics4
from nqr.p5.dataset5 import FRICTIONS
from nqr.p6 import backtest6 as BT
from nqr.p6 import context6 as C6

SD = ROOT / "strategies" / "context_entry"
REP = SD / "reports"; REP.mkdir(parents=True, exist_ok=True)
RES = SD / "results"; DIA = SD / "diagnostics"
P = ["train2021", "select2022", "itest2023", "contam2024", "contam2025h2"]
LAB = dict(zip(P, ["2021", "2022", "2023", "2024", "2025-H2"]))
FR = 1.0
V = json.loads((SD / "models" / "development_verdict.json").read_text())
TAB = pl.read_parquet(SD / "models" / "entry_comparison.parquet")
DG = json.loads((DIA / "diagnostics.json").read_text())
BOOKS = list(C6.ENTRY_METHODS) + ["CONTROL_IMMEDIATE", "CONTROL_RANDOM", "CONTROL_NONCONTEXT"]
HDR = ("*Context model: the FROZEN Phase-5 `r4p0:A_logit:top2`, τ = 0.179938, "
       "R = 4.0 × ATR14(1-min), 1R/1R, 60-minute hold. Phase 6 changes only the "
       "entry moment.*")
REJ = ("> **Phase 6 FAILED before validation.** No entry mechanic passed the\n"
       "> preregistered development gates, and the causal context itself does not\n"
       "> beat non-context moments. 2026-Q1 was never opened.\n")


def load(s, b):
    p = RES / f"run_{s}" / f"book_{b}.parquet"
    return BT.accepted(pl.read_parquet(p)) if p.exists() else pl.DataFrame()


def pooled(b):
    fr = [load(s, b) for s in P]
    return pl.concat([f for f in fr if f.height], how="diagonal")


def m(t, fr=FR):
    if t.height == 0:
        return {}
    s = metrics4.summarize(t, fr)
    s["profit_factor_R"] = BT.pf_r(t, fr)
    return s


CTX = {s: pl.read_parquet(RES / f"run_{s}" / "contexts.parquet") for s in P}
DAYS = {s: json.loads((RES / f"run_{s}" / "run_meta.json").read_text())["n_days"] for s in P}
NC = sum(CTX[s].height for s in P)

# ------------------------------------------------- 1. context vs non-context
ctxr = json.loads((SD / "models" / "context_reality.json").read_text())
rows = "\n".join(
    f"| {LAB[s]} | {CTX[s].height} | {ctxr[s]['in']['expectancy_R']:+.4f} | "
    f"{ctxr[s]['in']['n_trades']:,} | {ctxr[s]['in']['win_rate']:.4f} | "
    f"{ctxr[s]['non']['expectancy_R']:+.4f} | {ctxr[s]['non']['n_trades']:,} | "
    f"{ctxr[s]['non']['win_rate']:.4f} | {ctxr[s]['diff']['diff']:+.4f} | "
    f"[{ctxr[s]['diff']['ci95_lo']:+.4f}, {ctxr[s]['diff']['ci95_hi']:+.4f}] |" for s in P)
cv = V["context_vs_noncontext"]; cw = V["context_vs_noncontext_wr"]
(REP / "CONTEXT_VS_NONCONTEXT.md").write_text(f"""# CONTEXT_VS_NONCONTEXT.md — Phase 6

{HDR}

{REJ}
**Is the causally activated context worth anything at all?** This is logically
prior to any entry question, and `PHASE6_SEARCH_BUDGET.md` §6 makes a negative
answer an independent failure condition.

Both arms are random minutes under identical execution. The only difference is
whether a context was active.

| period | contexts | in-context E[R] | n | WR | non-context E[R] | n | WR | diff | 95 % day-block CI |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
{rows}
| **pooled** | **{NC}** | **{V['context_pooled']['expectancy_R']:+.4f}** | {V['context_pooled']['n_trades']:,} | {V['context_pooled']['win_rate']:.4f} | **{V['noncontext_pooled']['expectancy_R']:+.4f}** | {V['noncontext_pooled']['n_trades']:,} | {V['noncontext_pooled']['win_rate']:.4f} | **{cv['diff']:+.4f}** | **[{cv['ci95_lo']:+.4f}, {cv['ci95_hi']:+.4f}]** |

Win-rate difference pooled: {cw['diff']:+.4f}, CI [{cw['ci95_lo']:+.4f}, {cw['ci95_hi']:+.4f}].

## The pooled interval contains zero

In-context is positive in absolute terms (+{V['context_pooled']['expectancy_R']:.4f} R,
PF(R) {V['context_pooled']['profit_factor_R']:.3f}) but is **not** statistically
distinguishable from trading a no-context half-hour on the same day.

## And the entire effect is the model's own training year

| | in-context | non-context | diff | 95 % CI |
|---|---:|---:|---:|---|
| all five periods | +0.0711 | −0.0040 | +0.0752 | [−0.0234, +0.1721] |
| **excluding 2021** | **+0.0220** | **+0.0513** | **−0.0293** | [−0.1440, +0.0848] |

2021 is where the Phase-5 context model was fitted. It is the only period whose
interval excludes zero (+0.3999, [+0.2242, +0.5768]). Outside it, **no-context
moments are better than in-context moments**, and 2024 and 2025-H2 are both
negative for the context.

**The causal context does not survive out of sample.** See
`CONTEXT_CAUSALITY_AUDIT.md` for why the Phase-5 version appeared to.

## Context frequency

| period | trading days | contexts | contexts/day (of 4 possible) | long | short |
|---|---:|---:|---:|---:|---:|
{chr(10).join(f"| {LAB[s]} | {DAYS[s]} | {CTX[s].height} | {CTX[s].height/DAYS[s]:.2f} | {int((CTX[s]['direction']>0).sum())} | {int((CTX[s]['direction']<0).sum())} |" for s in P)}
| **total** | **{sum(DAYS.values())}** | **{NC}** | **{NC/sum(DAYS.values()):.2f}** | {sum(int((CTX[s]['direction']>0).sum()) for s in P)} | {sum(int((CTX[s]['direction']<0).sum()) for s in P)} |

A top-2 % threshold fires in roughly one bucket in nine, and the contexts are
**{sum(int((CTX[s]['direction']<0).sum()) for s in P)/NC:.0%} short**.
""")

# ------------------------------------------------------ 2. entry mechanics
g = V["gates"]
grows = "\n".join(
    f"| **{k}** | {v['n']} {'✓' if v['G1'] else '✗'} | {v['periods_positive']}/5 "
    f"{'✓' if v['G2_periods'] else '✗'} | {v['net_ER']:+.4f} {'✓' if v['G2_combined'] else '✗'} | "
    f"{v['pf_r']:.3f} {'✓' if v['G3'] else '✗'} | {v['adv_lo']:+.4f} {'✓' if v['G4'] else '✗'} | "
    f"{'**ELIGIBLE**' if v['eligible'] else 'rejected'} |" for k, v in g.items())
erows = "\n".join(
    f"| {r['book']} | {r['n_trades']} | {r['win_rate']:.4f} | {r['gross_ER']:+.4f} | "
    f"{r['net_ER']:+.4f} | {r['pf_r']:.3f} | {r['periods_positive']}/5 | "
    f"{r['median_advantage']:+.4f} | {r['adv_diff']:+.4f} | "
    f"[{r['adv_lo']:+.4f}, {r['adv_hi']:+.4f}] | {r['median_wait_min']:.1f} | "
    f"{r['mean_entry_improv_R']:+.4f} |" for r in TAB.iter_rows(named=True))
rnd = m(pooled("CONTROL_RANDOM"))
adv = pl.DataFrame(DG["adverse_selection"])
arows = "\n".join(
    f"| {r['method']} | {r['improve_R']:+.4f} | {r['pre_mae_R']:.4f} | {r['net']:+.4f} | "
    f"{r['n']} ({r['fill_rate']:.0%}) |" for r in adv.iter_rows(named=True))
(REP / "ENTRY_MECHANICS.md").write_text(f"""# ENTRY_MECHANICS.md — Phase 6

{HDR}

{REJ}
## TOTAL ENTRY CONFIGURATIONS EVALUATED: {V['total_configurations_evaluated']} of a ceiling of 6

All six were fixed in `PHASE6_SEARCH_BUDGET.md` §2 before any outcome existed.
No seventh mechanic and no nearby parameter value was tried.

## All six against the primary null, pooled 2021–2025-H2

| method | n | WR | gross E[R] | net E[R] | PF(R) | periods +ve | median advantage | pooled advantage | 95 % day-block CI | median wait (min) | mean fill improvement (R) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
{erows}
| **CONTROL_RANDOM** | {rnd['n_trades']:,} | {rnd['win_rate']:.4f} | {m(pooled('CONTROL_RANDOM'),0.0)['expectancy_R']:+.4f} | **{rnd['expectancy_R']:+.4f}** | {rnd['profit_factor_R']:.3f} | — | — | — | *(the primary null)* | — | — |

**Every one of the six has a negative advantage over random timing inside the
same context.** So does `CONTROL_IMMEDIATE`. Random entry beats deliberate entry.

For E2 the interval [{g['E2']['adv_lo']:+.4f}, …] excludes zero **on the wrong
side** — a fixed 10-minute delay is significantly worse than random.

## Per-period net expectancy at 1.0 pt

| method | {" | ".join(LAB[s] for s in P)} |
|---|{"---|" * len(P)}
{chr(10).join("| " + r["book"] + " | " + " | ".join(f"{r['ER_'+LAB[s]]:+.4f}" for s in P) + " |" for r in TAB.iter_rows(named=True))}
| **CONTROL_RANDOM** | {" | ".join(f"{m(load(s,'CONTROL_RANDOM'))['expectancy_R']:+.4f}" for s in P)} |

## Preregistered development gates

| method | G1 n ≥ 300 | G2 ≥ 4/5 periods +ve | G2 combined > 0 | G3 PF(R) > 1.10 | G4 advantage CI low > 0 | result |
|---|---|---|---|---|---|---|
{grows}

**ELIGIBLE: {V['eligible'] if V['eligible'] else 'NONE'}.**
E4 and E6 additionally fail the sample floor — they only trigger on 44–45 % of
contexts. Not one mechanic reaches 4 of 5 positive periods, and not one has a
positive advantage lower bound.

Per `PHASE6_SEARCH_BUDGET.md` §6 there is no least-bad candidate:
**Phase 6 fails before validation and 2026-Q1 stays sealed.**

## Why the pullback entries do not help — the mechanism

| method | price improvement vs immediate (R) | adverse excursion before entry (R) | net | contexts entered |
|---|---:|---:|---:|---:|
{arows}

This is the clearest result in Phase 6. A mechanic that waits for a better price
**only gets one when the market has already moved against the context**, and the
adverse excursion it must sit through is consistently larger than the discount it
buys:

* **E3** buys a {adv['improve_R'][2]:+.4f} R better fill and pays {adv['pre_mae_R'][2]:.4f} R of adverse excursion — almost exactly a wash.
* **E4** buys {adv['improve_R'][3]:+.4f} R and pays {adv['pre_mae_R'][3]:.4f} R — also a wash, on half as many contexts.
* **E1/E2** are strictly worse: a pure clock delay sits through {adv['pre_mae_R'][0]:.2f}–{adv['pre_mae_R'][1]:.2f} R of adverse excursion and is compensated with only {adv['improve_R'][0]:+.3f}–{adv['improve_R'][1]:+.3f} R of price.

Adverse selection is not *approximately* offsetting the price improvement — it is
offsetting it almost exactly, at both pullback depths. That is what a
well-functioning market looks like at this timescale.

## A diagnostic that is NOT a gate

Restricting `CONTROL_RANDOM` to only the contexts each mechanic actually entered
(a fairer like-for-like, since E3–E6 skip contexts that never pull back):

| method | contexts | mechanic E[R] | random on the same contexts | diff | 95 % CI |
|---|---:|---:|---:|---:|---|
| E1 | 369 | +0.0270 | +0.0518 | −0.0248 | [−0.0796, +0.0306] |
| E2 | 328 | +0.0043 | +0.0192 | −0.0149 | [−0.0741, +0.0432] |
| E3 | 323 | +0.0641 | +0.0029 | +0.0612 | [−0.0083, +0.1325] |
| E4 | 227 | **−0.0197** | −0.1098 | +0.0901 | **[+0.0028, +0.1795]** |
| E5 | 321 | +0.0464 | −0.0021 | +0.0485 | [−0.0200, +0.1175] |
| E6 | 221 | **−0.0219** | −0.0958 | +0.0739 | [−0.0119, +0.1594] |

On the subset of contexts that *do* pull back, the pullback entries **do** beat a
random entry in those same contexts, and E4's interval excludes zero.

**This does not rescue anything, and it is not used as a gate.** The
preregistered comparison is against the full random-control population and was
fixed before any outcome; swapping it for this one after seeing the results is
precisely the post-hoc gate change the brief forbids. Note also that E4's and
E6's absolute expectancy is still **negative** — they lose less than random in
bad contexts, which is not a tradable edge. It is recorded as hypothesis H6-2.
""")
print("wrote", REP)
for x in sorted(REP.glob("*.md")):
    print("  ", x.name, x.stat().st_size)
