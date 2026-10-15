"""Phase-6 reports part 2: per-period development, stability, bootstrap, prop metrics,
entry-quality diagnostics."""
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
REP = SD / "reports"; RES = SD / "results"; DIA = SD / "diagnostics"
P = ["train2021", "select2022", "itest2023", "contam2024", "contam2025h2"]
LAB = dict(zip(P, ["2021", "2022", "2023", "2024", "2025-H2"]))
FR = 1.0
V = json.loads((SD / "models" / "development_verdict.json").read_text())
TAB = pl.read_parquet(SD / "models" / "entry_comparison.parquet")
DG = json.loads((DIA / "diagnostics.json").read_text())
METHODS = list(C6.ENTRY_METHODS) + ["CONTROL_IMMEDIATE", "CONTROL_RANDOM"]
HDR = ("*Context model: the FROZEN Phase-5 `r4p0:A_logit:top2`, τ = 0.179938, "
       "R = 4.0 × ATR14(1-min), 1R/1R, 60-minute hold.*")
REJ = ("> **Phase 6 FAILED before validation.** No entry mechanic passed the\n"
       "> preregistered gates and the causal context does not beat non-context.\n"
       "> 2026-Q1 was never opened.\n")


def load(s, b):
    p = RES / f"run_{s}" / f"book_{b}.parquet"
    return BT.accepted(pl.read_parquet(p)) if p.exists() else pl.DataFrame()


def pooled(b):
    fr = [load(s, b) for s in P]
    return pl.concat([f for f in fr if f.height], how="diagonal")


def m(t, fr=FR, nd=None):
    if t.height == 0:
        return {}
    s = metrics4.summarize(t, fr, n_days_available=nd)
    s["profit_factor_R"] = BT.pf_r(t, fr)
    return s


CTX = {s: pl.read_parquet(RES / f"run_{s}" / "contexts.parquet") for s in P}
DAYS = {s: json.loads((RES / f"run_{s}" / "run_meta.json").read_text())["n_days"] for s in P}

# --------------------------------------------------- development by period
blocks = []
for s in P:
    lines = []
    for b in METHODS:
        t = load(s, b)
        if t.height == 0:
            continue
        st = m(t, FR, DAYS[s]); g0 = m(t, 0.0, DAYS[s])
        lines.append(f"| {b} | {st['n_trades']} | {t.height/CTX[s].height:.2f} | "
                     f"{st['win_rate']:.4f} | {g0['expectancy_R']:+.4f} | "
                     f"{st['expectancy_R']:+.4f} | {st['profit_factor_R']:.3f} | "
                     f"{st['max_drawdown_R']:.2f} | {st['median_hold_min']:.1f} |")
    blocks.append(f"""### {LAB[s]}

{DAYS[s]} trading days, **{CTX[s].height} contexts** ({CTX[s].height/DAYS[s]:.2f}/day of a
possible 4), {int((CTX[s]['direction']>0).sum())} long / {int((CTX[s]['direction']<0).sum())} short.

| book | n | fill/context | WR | gross E[R] | net E[R] | PF(R) | max DD (R) | median hold (min) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(lines)}
""")
(REP / "DEVELOPMENT_BY_PERIOD.md").write_text(f"""# DEVELOPMENT_BY_PERIOD.md — Phase 6

{HDR}

{REJ}
**Every period below is DEVELOPMENT.** The Phase-6 hypothesis came from Phase-5
diagnostics, so 2021–2025-H2 have all already influenced it. None of them is
out-of-sample here, and 2021 is additionally in-sample for the context model
itself. 09:30–11:30 ET, 1.0 pt round-trip friction.

{chr(10).join(blocks)}
## Stability summary — the G2 gate

Net expectancy at 1.0 pt must be positive in ≥ 4 of the 5 periods.

| method | {" | ".join(LAB[s] for s in P)} | periods +ve | verdict |
|---|{"---|" * len(P)}---|---|
{chr(10).join("| " + r["book"] + " | " + " | ".join(f"{r['ER_'+LAB[s]]:+.4f}" for s in P) + f" | **{r['periods_positive']}/5** | {'pass' if r['periods_positive']>=4 else '**FAIL**'} |" for r in TAB.iter_rows(named=True))}
| CONTROL_RANDOM | {" | ".join(f"{m(load(s,'CONTROL_RANDOM'))['expectancy_R']:+.4f}" for s in P)} | {sum(1 for s in P if m(load(s,'CONTROL_RANDOM'))['expectancy_R']>0)}/5 | *(null)* |

**Not one mechanic reaches 4 of 5.** The best are E1, E3 and E5 at 3 of 5. This
gate exists specifically to stop the Phase-5 failure mode of promoting a
candidate carried by a single year, and it does its job here: E5's +0.1727 on
2021 is the largest single-period figure in the table and comes from the context
model's own training year.
""")

# ---------------------------------------------------------------- bootstrap
rows = []
for r in TAB.iter_rows(named=True):
    rows.append(f"| {r['book']} | {r['n_trades']} | {r['adv_diff']:+.4f} | "
                f"[{r['adv_lo']:+.4f}, {r['adv_hi']:+.4f}] | "
                f"{'excludes 0 (worse)' if r['adv_hi']<0 else ('excludes 0 (better)' if r['adv_lo']>0 else 'contains 0')} | "
                f"{r['wr_diff']:+.4f} | [{r['wr_lo']:+.4f}, {r['wr_hi']:+.4f}] |")
cv = V["context_vs_noncontext"]; cw = V["context_vs_noncontext_wr"]
(REP / "BOOTSTRAP.md").write_text(f"""# BOOTSTRAP.md — Phase 6 uncertainty

{HDR}

{REJ}
Contexts cluster by day and a day can carry up to four of them, so no interval
here treats a trade or a context as independent. Every figure is a **trading-day
block bootstrap**: 10 000 resamples of whole trading days, with the candidate and
its control resampled **together** so the pairing survives.

## Primary gate G4 — each mechanic minus CONTROL_RANDOM

| method | n | Δ expectancy (R) | 95 % CI | verdict | Δ win rate | 95 % CI |
|---|---:|---:|---|---|---:|---|
{chr(10).join(rows)}

Not one interval lies above zero. **E2's lies entirely below it**: a fixed
10-minute delay is significantly *worse* than entering at a random minute.

## Context vs non-context

| statistic | difference | 95 % CI | verdict |
|---|---:|---|---|
| expectancy (R) | {cv['diff']:+.4f} | [{cv['ci95_lo']:+.4f}, {cv['ci95_hi']:+.4f}] | contains 0 |
| win rate | {cw['diff']:+.4f} | [{cw['ci95_lo']:+.4f}, {cw['ci95_hi']:+.4f}] | contains 0 |

Pooled over {cv['n_days']} trading days.

## Why day blocks matter here

The Phase-6 books are small — {TAB['n_trades'].min()}–{TAB['n_trades'].max()} trades per
mechanic across five years — and up to four contexts share a day and therefore
share that day's regime. An i.i.d. interval on {TAB['n_trades'].max()} trades would be
roughly half the width of the day-block interval and would have declared several
of these differences significant. It would have been wrong.
""")

# ------------------------------------------------------------ prop metrics
K = [("n_trades", "total trades", "{:,.0f}"), ("trades_per_day", "trades / day", "{:.3f}"),
     ("median_trades_per_day", "median trades / day", "{:.0f}"),
     ("pct_zero_trade_days", "% 0-trade days", "{:.1%}"),
     ("pct_1_trade_days", "% 1-trade days", "{:.1%}"),
     ("pct_2_trade_days", "% 2-trade days", "{:.1%}"),
     ("pct_3plus_trade_days", "% 3+-trade days", "{:.1%}"),
     ("win_rate", "win rate", "{:.4f}"),
     ("win_rate_ci95_lo", "WR 95 % CI low", "{:.4f}"),
     ("win_rate_ci95_hi", "WR 95 % CI high", "{:.4f}"),
     ("expectancy_R", "net expectancy (R)", "{:+.4f}"),
     ("profit_factor_R", "**PF(R)**", "{:.3f}"),
     ("profit_factor", "PF (points)", "{:.3f}"),
     ("R_per_day", "R / day", "{:+.4f}"), ("median_R_per_day", "median R / day", "{:+.2f}"),
     ("pct_profitable_days", "profitable-day %", "{:.1%}"),
     ("max_daily_loss_R", "max daily loss (R)", "{:+.2f}"),
     ("p95_daily_loss_R", "95th pct daily loss (R)", "{:+.2f}"),
     ("max_drawdown_R", "max drawdown (R)", "{:.2f}"),
     ("longest_loss_streak", "longest losing streak", "{:.0f}"),
     ("longest_win_streak", "longest winning streak", "{:.0f}"),
     ("drawdown_recovery_days", "drawdown recovery (days)", "{:.0f}"),
     ("avg_hold_min", "average hold (min)", "{:.1f}"),
     ("median_hold_min", "median hold (min)", "{:.1f}"),
     ("avg_MAE_points", "avg adverse excursion (pt)", "{:.1f}"),
     ("avg_MFE_points", "avg favourable excursion (pt)", "{:.1f}"),
     ("avg_R_distance_points", "average R (pt)", "{:.1f}"),
     ("tp_hits", "TP", "{:.0f}"), ("sl_hits", "SL", "{:.0f}"),
     ("timeouts", "TIMEOUT", "{:.0f}")]
ND = sum(DAYS.values()); NC = sum(CTX[s].height for s in P)
stats = {b: m(pooled(b), FR, ND) for b in METHODS}


def cell(b, k, f):
    v = stats[b].get(k)
    if v is None:
        return "—"
    if isinstance(v, float) and not np.isfinite(v):
        return "∞" if v == float("inf") else "—"
    return f.format(v)


body = "\n".join("| " + lab + " | " + " | ".join(cell(b, k, f) for b in METHODS) + " |"
                 for k, lab, f in K)
fills = " | ".join(f"{pooled(b).height/NC:.2f}" for b in METHODS)
(REP / "PROP_FIRM_METRICS.md").write_text(f"""# PROP_FIRM_METRICS.md — Phase 6

{HDR}

{REJ}
Pooled 2021–2025-H2: **{ND} trading days, {NC} contexts** ({NC/ND:.2f}/day of a
possible 4). 09:30–11:30 ET, 1R/1R, 1.0 NQ point round-trip friction. No dollar
sizing. Profit factor is reported in **R units** — `PF(R)` — per the Phase-5
correction; the points figure is shown alongside and never used for a gate.

| metric | {" | ".join(METHODS)} |
|---|{"---|" * len(METHODS)}
| contexts/day | {" | ".join(f"{NC/ND:.2f}" for _ in METHODS)} |
| entry fill rate per context | {fills} |
{body}

## Reading it

`CONTROL_RANDOM` is not a strategy — it is up to 10 independent entries per
context and is not subject to the one-position rule, so its trade count and
per-day figures are not comparable to the mechanics. Its **expectancy, win rate
and PF(R)** are, and those are the numbers the gates use.

Every mechanic is far below any usable frequency:
**{stats['E1']['trades_per_day']:.2f}–{max(stats[b]['trades_per_day'] for b in C6.ENTRY_METHODS):.2f}
trades per day** with **{min(stats[b]['pct_zero_trade_days'] for b in C6.ENTRY_METHODS):.0%}+
zero-trade days**, because a top-2 % context fires in about one bucket in nine and
the mechanics then decline 26–56 % of those.

Holds are {stats['E3']['median_hold_min']:.0f}–{stats['E2']['median_hold_min']:.0f} minutes
and average R is {stats['E3']['avg_R_distance_points']:.0f} points, both inherited
unchanged from the frozen Phase-5 geometry.
""")

# ------------------------------------------------- entry quality diagnostics
tw = pl.DataFrame(DG["time_within_context"])
bd = pl.DataFrame(DG["bucket_direction"])
eq = pl.DataFrame(DG["entry_quality"])
(REP / "ENTRY_QUALITY_DIAGNOSTICS.md").write_text(f"""# ENTRY_QUALITY_DIAGNOSTICS.md — Phase 6

# DIAGNOSTIC ONLY — POST-HOC — REQUIRES NEW UNTOUCHED DATA

{HDR}

The candidate set was already rejected by the preregistered gates before any of
this was computed. Nothing here modified Phase 6. Cell counts are given so the
reader can discount for multiplicity.

## 1. Time within context ({tw.height} cells)

Measured on `CONTROL_RANDOM`, so it is not confounded by any mechanic's own
selection.

| wait after activation | n | WR | gross E[R] | net E[R] | PF(R) | avg MAE (pt) |
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(f"| {r['bin']} | {r['n_trades']:,} | {r['win_rate']:.4f} | {r['gross_ER']:+.4f} | {r['expectancy_R']:+.4f} | {r['profit_factor_R']:.3f} | {r['avg_MAE_points']:.2f} |" for r in tw.iter_rows(named=True))}

**Essentially flat, with a mild decline.** The first five minutes are the best
cell (+{tw['expectancy_R'][0]:.4f} R) and 15–20 minutes the worst
(+{tw['expectancy_R'].min():.4f} R). Whatever the context is worth, it is worth
slightly *more* early — which is why every delay mechanic loses to random and to
immediate entry.

## 2. Half-hour bucket × direction ({bd.height} cells)

| bucket | side | n | WR | gross E[R] | net E[R] | PF(R) |
|---|---|---:|---:|---:|---:|---:|
{chr(10).join(f"| {r['bucket']} | {r['side']} | {r['n_trades']:,} | {r['win_rate']:.4f} | {r['gross_ER']:+.4f} | {r['expectancy_R']:+.4f} | {r['profit_factor_R']:.3f} |" for r in bd.iter_rows(named=True))}

The spread across 8 cells is very wide — **11:00–11:30 LONG at
+{bd.filter((pl.col('bucket')=='11:00-11:30')&(pl.col('side')=='LONG'))['expectancy_R'][0]:.4f} R
and PF(R) {bd.filter((pl.col('bucket')=='11:00-11:30')&(pl.col('side')=='LONG'))['profit_factor_R'][0]:.2f}
against 11:00–11:30 SHORT at
{bd.filter((pl.col('bucket')=='11:00-11:30')&(pl.col('side')=='SHORT'))['expectancy_R'][0]:+.4f} R** —
and the short side supplies most of the volume. This is exactly the kind of
subgroup the brief forbids promoting, and it is not promoted. See
`FUTURE_HYPOTHESES.md` H6-3.

## 3. Entry quality — what each mechanic buys

| method | n | fill/context | median wait | fill improvement (R) | pre-entry MAE (R) | pre-entry MFE (R) | median bucket left (min) | trade MFE (pt) | trade MAE (pt) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(f"| {r['method']} | {r['n']} | {r['fill_rate']:.2f} | {r['median_wait_min']:.1f}m | {r['mean_improve_R']:+.4f} | {r['mean_pre_mae_R']:.4f} | {r['mean_pre_mfe_R']:.4f} | {r['median_remaining_min']:.1f} | {r['avg_MFE_points']:.2f} | {r['avg_MAE_points']:.2f} |" for r in eq.iter_rows(named=True))}

The `pre-entry MAE` column is the whole story: waiting costs more adverse
excursion than the price improvement it buys, at every depth. Full decomposition
in `ENTRY_MECHANICS.md`.
""")
print("wrote part 2")
for x in sorted(REP.glob("*.md")):
    print("  ", x.name, x.stat().st_size)
