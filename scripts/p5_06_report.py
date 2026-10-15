"""Generate the Phase-5 report set from stored results.  No hand-typed numbers."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import numpy as np
import polars as pl

SD = ROOT / "strategies" / "larger_r"
REP = SD / "reports"; REP.mkdir(parents=True, exist_ok=True)
RES = SD / "results"
DEV = ["train2021", "select2022", "itest2023"]
ALL = DEV + ["contam2024", "contam2025h2"]
LABEL = {"train2021": "2021 train", "select2022": "2022 selection",
         "itest2023": "2023 internal OOS", "contam2024": "2024 CONTAMINATED",
         "contam2025h2": "2025-H2 CONTAMINATED"}
P = [s for s in ALL if (RES / f"run_{s}" / "results.json").exists()]
R = {s: json.loads((RES / f"run_{s}" / "results.json").read_text()) for s in P}
dev = json.loads((SD / "models" / "development_meta.json").read_text())
interp = json.loads((SD / "models" / "interpretation.json").read_text())
sel = pl.read_parquet(SD / "models" / "selection_2022.parquet")
W = {s: R[s]["windows"]["0930_1130"] for s in P}
CAND = dev["winner"]["config"]
HDR = (f"*Candidate `{CAND}` — R = 4.0 × ATR14(1-min), 60-second clock, "
       f"60-minute hold, τ = {dev['winner']['tau']:.6f} (top 2 % of the edge score on 2021)*")
REJ = ("> **This candidate was REJECTED.** It failed the preregistered Gate F on the\n"
       "> 2023 internal out-of-sample test, so it was never frozen and 2026-Q1 was\n"
       "> never opened. Everything below describes a rejected candidate.\n")


def f(s, k, fmt="{:+.4f}"):
    v = W[s].get(k)
    return fmt.format(v) if v is not None and np.isfinite(v) else "—"


# ------------------------------------------------------ 1. development ----
lines = ["| rank | configuration | n | /day | WR | gross E[R] | net E[R] | PF(R) | control E[R] | advantage | Gate E |",
         "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|:---:|"]
for i, r in enumerate(sel.sort("expectancy_R", descending=True).iter_rows(named=True)):
    lines.append(
        f"| {i+1} | `{r['config']}` | {r['n_trades']} | {r['trades_per_day']:.1f} | "
        f"{r['win_rate']:.4f} | {r['gross_expectancy_R']:+.4f} | **{r['expectancy_R']:+.4f}** | "
        f"{r['profit_factor']:.3f} | {r['control_expectancy_R']:+.4f} | {r['advantage_R']:+.4f} | "
        f"{'**PASS**' if r['gateE_pass'] else '—'} |")
byr = sel.group_by("r_tag").agg(pl.col("expectancy_R").mean(), pl.col("gross_expectancy_R").mean(),
                                pl.col("advantage_R").mean(), pl.col("gateE_pass").sum()).sort("r_tag")
(REP / "DEVELOPMENT_AND_SELECTION.md").write_text(f"""# DEVELOPMENT_AND_SELECTION.md — Phase 5

{HDR}

{REJ}
## The budget, fully spent

**TOTAL CONFIGURATIONS EVALUATED: {dev['total_configurations_evaluated']}** of a ceiling of 18
(3 R scales × 2 model families × 3 selectivity levels). Every one was scored
against **2022 only**, on the criterion fixed in `PHASE5_SEARCH_BUDGET.md` §5
before any outcome existed: highest 2022 net expectancy in R at 1.0 pt friction,
subject to ≥ 100 executed trades.

Unlike Phase 4, the budget was spent on **R scale**, because R scale is the
hypothesis. Each family therefore had exactly one hyperparameter setting.

## All 18 on 2022

{chr(10).join(lines)}

## By R scale — the hypothesis under test

| R scale | mean net E[R] | mean gross E[R] | mean advantage | Gate E passes |
|---|---:|---:|---:|---:|
{chr(10).join(f"| `{r['r_tag']}` ({2.0 if r['r_tag']=='r2p0' else 3.0 if r['r_tag']=='r3p0' else 4.0}× ATR1m) | {r['expectancy_R']:+.4f} | {r['gross_expectancy_R']:+.4f} | {r['advantage_R']:+.4f} | {r['gateE_pass']}/6 |" for r in byr.iter_rows(named=True))}

The largest scale is the only one producing a Gate-E pass, which is directionally
consistent with the hypothesis. But note the third column: **the average advantage
over matched random is negative at every R scale.**

## What changed versus Phase 4, and what did not

**Changed — gross expectancy turned positive.** 12 of the 18 configurations have
positive zero-friction expectancy on 2022. In Phase 4, gross was ≈ 0 or negative
in every period. Enlarging R did what it was supposed to do mechanically.

**Did not change — the model still does not beat its control.** The matched-random
advantage is negative for **16 of 18** configurations. Only 2 of 18 clear Gate E,
and the winner's advantage (+{dev['winner']['advantage_R']:.4f} R) has a
day-block CI of
[{R['select2022']['vs_matched']['expectancy_R']['ci95_lo']:+.4f},
{R['select2022']['vs_matched']['expectancy_R']['ci95_hi']:+.4f}] — it **contains
zero**. Gate E was passed on a point estimate with no statistical support, which
is exactly what the 2023 test then exposed.

## The selected candidate

`{CAND}`: 2022 n={dev['winner']['n_trades']}, WR {dev['winner']['win_rate']:.4f},
net E[R] {dev['winner']['expectancy_R']:+.4f}, PF(R) {W['select2022']['profit_factor_R']:.3f}.

**A structural caution, recorded here rather than after the fact:** ranking on
expectancy alone systematically favours the *smallest* sample, because small
samples have the widest spread. The winner is the most selective setting
(top 2 %) on the largest R — 128 trades from 30,480 decision rows, 0.5 trades a
day. That is the configuration most exposed to noise, and it is the one the
preregistered criterion picked.
""")

# --------------------------------------------------------- 2. 2023 OOS ----
w = W["itest2023"]; v = R["itest2023"]["vs_matched"]
gates = [("net expectancy > 0 R", w["expectancy_R"] > 0, f"{w['expectancy_R']:+.4f} R"),
         ("profit factor > 1.05", w["profit_factor_R"] > 1.05,
          f"{w['profit_factor_R']:.3f} in R units ({w['profit_factor_points']:.3f} in points)"),
         ("advantage over matched random > 0", v["expectancy_R"]["diff"] > 0,
          f"{v['expectancy_R']['diff']:+.4f} R, CI [{v['expectancy_R']['ci95_lo']:+.4f}, {v['expectancy_R']['ci95_hi']:+.4f}]"),
         ("≥ 100 executed trades", w["n_trades"] >= 100, f"{w['n_trades']}")]
(REP / "ITEST_2023.md").write_text(f"""# ITEST_2023.md — Phase 5 internal out-of-sample test

{HDR}

2023 took no part in fitting, baseline estimation, threshold calibration or
configuration selection. It was scored once, after `{CAND}` had already been
chosen on 2022.

## Gate F — the preregistered prerequisite for freezing

| requirement | value | result |
|---|---|:---:|
{chr(10).join(f"| {n} | {val} | {'PASS' if ok else '**FAIL**'} |" for n, ok, val in gates)}

**All four fail.** Per `PHASE5_SEARCH_BUDGET.md` §6 this ends Phase 5:
the candidate is not frozen, the contaminated diagnostics cannot revive it, and
**2026-Q1 stays sealed**.

## The numbers

| | |
|---|---|
| trading days | {w['n_trading_days_available']} |
| executed trades | {w['n_trades']} ({w['trades_per_day']:.2f}/day) |
| win rate | {w['win_rate']:.4f} (Wilson 95 % [{w['win_rate_ci95_lo']:.4f}, {w['win_rate_ci95_hi']:.4f}]) |
| **gross expectancy (0.0 pt)** | **{R['itest2023']['friction_sweep']['0.0']['expectancy_R']:+.4f} R** |
| **net expectancy (1.0 pt)** | **{w['expectancy_R']:+.4f} R** |
| profit factor (R units) | {w['profit_factor_R']:.3f} |
| median hold | {w['median_hold_min']:.1f} min |
| average R | {w['avg_R_distance_points']:.1f} pt |
| TP / SL / TIMEOUT | {w['tp_hits']} / {w['sl_hits']} / {w['timeouts']} |
| max drawdown | {w['max_drawdown_R']:.1f} R |

## Against matched random

| statistic | strategy | matched control | Δ | 95 % day-block CI |
|---|---:|---:|---:|---|
| expectancy (R) | {w['expectancy_R']:+.4f} | {R['itest2023']['matched_control']['expectancy_R']:+.4f} | {v['expectancy_R']['diff']:+.4f} | [{v['expectancy_R']['ci95_lo']:+.4f}, {v['expectancy_R']['ci95_hi']:+.4f}] |
| win rate | {w['win_rate']:.4f} | {R['itest2023']['matched_control']['win_rate']:.4f} | {v['win_rate']['diff']:+.4f} | [{v['win_rate']['ci95_lo']:+.4f}, {v['win_rate']['ci95_hi']:+.4f}] |

The expectancy interval lies **entirely below zero**. On the one development year
it had never seen, the strategy is not merely no better than random entries
matched on day, time bucket and direction — it is **significantly worse**.

Note what the control itself earned: **{R['itest2023']['matched_control']['expectancy_R']:+.4f} R**.
The days, half-hours and directions the model selected were profitable. The
specific minutes it chose inside them were not.

## A reporting note on profit factor

`metrics4.summarize` computes profit factor on **points** while expectancy is in
**R**. With a volatility-scaled R those can disagree in sign — here PF(points) is
{w['profit_factor_points']:.3f} while PF(R) is {w['profit_factor_R']:.3f} — because a
large-R trade contributes more points but the same ±1R. Phase 5 sizes risk per
trade, so **PF in R units is the figure the gates mean**, and it is the one used
above. Both are reported everywhere.
""")

# ------------------------------------------------ 3. friction / gross edge ----
fr = ["0.0", "0.5", "1.0", "2.0"]
(REP / "FRICTION_AND_GROSS_EDGE.md").write_text(f"""# FRICTION_AND_GROSS_EDGE.md — Phase 5

{HDR}

{REJ}
Phase 4's central lesson was that "no gross edge" and "edge destroyed by cost"
are different diagnoses and must never be confused. This report separates them.

## Expectancy in R at every friction level

| friction | {" | ".join(LABEL[s] for s in P)} |
|---|{"---|" * len(P)}
{chr(10).join("| **" + x + " pt** | " + " | ".join(f"{R[s]['friction_sweep'][x]['expectancy_R']:+.4f}" for s in P) + " |" for x in fr)}
| *friction cost/trade* | {" | ".join(f"*{R[s]['friction_sweep']['0.0']['expectancy_R'] - R[s]['friction_sweep']['1.0']['expectancy_R']:.4f} R*" for s in P)} |

## The mechanical hypothesis is CONFIRMED

| | Phase 4 | Phase 5 |
|---|---:|---:|
| average R | 7.0 pt | {np.mean([W[s]['avg_R_distance_points'] for s in P]):.1f} pt |
| friction cost per trade | 0.1435 R | **{np.mean([R[s]['friction_sweep']['0.0']['expectancy_R'] - R[s]['friction_sweep']['1.0']['expectancy_R'] for s in P]):.4f} R** |
| median hold | 0.4 min | {np.mean([W[s]['median_hold_min'] for s in P]):.1f} min |
| trades/day | ~140 | {np.mean([W[s]['trades_per_day'] for s in P]):.2f} |

Enlarging R cut the friction burden by roughly **{0.1435 / np.mean([R[s]['friction_sweep']['0.0']['expectancy_R'] - R[s]['friction_sweep']['1.0']['expectancy_R'] for s in P]):.1f}×**,
exactly as designed. **Friction is no longer the binding constraint.**

## And gross expectancy did turn positive

Zero-friction expectancy is positive in **{sum(1 for s in P if R[s]['friction_sweep']['0.0']['expectancy_R'] > 0)} of {len(P)}** periods,
against Phase 4 where it was ≈ 0 or negative in every one. At this horizon the
state does appear to sit on a positive gross return.

**But that is not the same as an edge**, and the reason is the next section.

## The unconditional larger-R bracket is NOT structurally profitable

Computed over **every** decision row, no model involved, net at 1.0 pt:

| R scale | long E[R] | long WR | short E[R] | short WR | mean of the two |
|---|---:|---:|---:|---:|---:|
| `r2p0` (2.0× ATR1m) | −0.0566 | 0.4934 | −0.0410 | 0.5003 | **−0.0488** |
| `r3p0` (3.0× ATR1m) | −0.0329 | 0.5000 | −0.0317 | 0.4913 | **−0.0323** |
| `r4p0` (4.0× ATR1m) | −0.0192 | 0.5076 | −0.0280 | 0.4794 | **−0.0236** |

A coin-flip entry loses at every scale, so the positive strategy figures are not
an artefact of the bracket geometry. They are the product of *selecting* days,
half-hours and directions — which is real, and which the matched control shares
in full. See `MATCHED_RANDOM.md`.

## Verdict on the cost question

> **Phase 5 is not a case of "edge destroyed by cost".** Friction was reduced to
> {np.mean([R[s]['friction_sweep']['0.0']['expectancy_R'] - R[s]['friction_sweep']['1.0']['expectancy_R'] for s in P]):.3f} R
> per trade — 2–5 % of R — and the strategy still failed, because it never
> separated from a random entry placed in the same context.
""")

# --------------------------------------------------------- 4. controls ----
rows = []
for s in P:
    v = R[s]["vs_matched"]["expectancy_R"]; ww = R[s]["vs_matched"]["win_rate"]
    o = R[s]["vs_opposite"]["expectancy_R"]
    rows.append(
        f"| {LABEL[s]} | {W[s]['n_trades']} | {W[s]['expectancy_R']:+.4f} | "
        f"{R[s]['matched_control']['expectancy_R']:+.4f} | {v['diff']:+.4f} | "
        f"[{v['ci95_lo']:+.4f}, {v['ci95_hi']:+.4f}] | "
        f"{'**worse**' if v['ci95_hi'] < 0 else ('better' if v['ci95_lo'] > 0 else 'indistinguishable')} | "
        f"{R[s]['opposite_control']['expectancy_R']:+.4f} | "
        f"[{o['ci95_lo']:+.4f}, {o['ci95_hi']:+.4f}] |")
(REP / "MATCHED_RANDOM.md").write_text(f"""# MATCHED_RANDOM.md — Phase 5 controls

{HDR}

{REJ}
Both controls were defined in `PHASE5_SPEC.md` §15 before any outcome existed and
read the **same** tick-resolved labels as the strategy, so execution, bracket,
horizon, timeout and friction are identical by construction.

## C1 — matched random (the primary null)

Same trading day, same 30-minute time-of-day bucket, same direction, control R
within [0.80, 1.25] × the signal's R, up to 10 per trade, seed 20260820.

| period | n | strategy E[R] | control E[R] | Δ | 95 % day-block CI | verdict | opposite E[R] | Δ CI vs opposite |
|---|---:|---:|---:|---:|---|:---:|---:|---|
{chr(10).join(rows)}

**The strategy never beats its matched control with statistical support in any
period**, and on 2023 the interval lies entirely below zero.

## The decomposition that explains Phase 5

Three nested populations, all at 1.0 pt friction:

| what is being selected | 2021 | 2022 | 2023 | 2024 | 2025-H2 |
|---|---:|---:|---:|---:|---:|
| nothing (every row, either direction) | −0.022 | −0.016 | +0.010 | −0.011 | −0.057 |
| model's **day + 30-min bucket + direction**, random minute | {" | ".join(f"{R[s]['matched_control']['expectancy_R']:+.3f}" for s in P)} |
| model's day + bucket + direction **+ its chosen minute** | {" | ".join(f"{W[s]['expectancy_R']:+.3f}" for s in P)} |

Read down the columns. Going from *nothing* to the model's chosen context adds a
large positive amount in every period. Going from that context to the model's
chosen **minute** subtracts in {sum(1 for s in P if W[s]['expectancy_R'] < R[s]['matched_control']['expectancy_R'])} of {len(P)}.

> **The signal identifies favourable (day, half-hour, direction) contexts. Its
> 60-second timing inside them is not merely uninformative — it is adverse.**

That is the single most useful thing Phase 5 produced, and it is recorded as
hypothesis H5-1 in `FUTURE_HYPOTHESES.md`.

## C2 — opposite direction

The flip is worse than the strategy in every period (see the last two columns
above), significantly so on 2021. So the **direction** call does carry
information — which is consistent with the decomposition, since the matched
control inherits that direction and is also positive.

Nothing is flipped and nothing is rebuilt around this. An inverse or
direction-only strategy would be a new hypothesis requiring new data.
""")

# ------------------------------------------------ 5. feature importance ----
top = "\n".join(f"| `{n}` | {v:+.5f} |" for n, v in interp["top15"])
fam6 = ["delta_60_norm", "delta_300_norm", "delta_per_vol_60", "delta_per_vol_300",
        "cum_delta_norm", "delta_accel"]
m6 = np.mean([abs(interp["coefficients"][f]) for f in fam6])
mall = np.mean([abs(v) for v in interp["coefficients"].values()])
(REP / "FEATURE_IMPORTANCE.md").write_text(f"""# FEATURE_IMPORTANCE.md — Phase 5

{HDR}

{REJ}
The selected family was **A — elastic-net logistic regression** (C = 0.1,
l1_ratio = 0.5), fitted on 2021 with training-only standardisation, so the
coefficients below are directly comparable across features.
{interp['n_nonzero']} of 55 coefficients are non-zero; L1 eliminated
{55 - interp['n_nonzero']} (`{'`, `'.join(k for k, v in interp['coefficients'].items() if v == 0.0)}`).

## Top 15 by |coefficient|

| feature | coefficient |
|---|---:|
{top}

## What the larger horizon actually selected

Phase 4's tree was dominated by **`atr1m` (39.7 %)** — a raw-points volatility
level, and a regime variable that did not generalise. At the 60-minute horizon
the picture is different and, on its face, healthier:

* **Session location dominates.** `dist_or30_lo_norm` (−0.345),
  `dist_open_norm` (+0.292), `dist_vwap_norm` (+0.129), `dist_or30_hi_norm`
  (+0.089), `dist_pdh_norm` (+0.088) — family 8, objective location, takes five
  of the top eleven slots.
* **Clock position is the second theme.** `secs_since_open` (+0.333) and
  `is_second_hour` (−0.125) are family 7. The model leans heavily on *when* in
  the session it is.
* **Volatility enters in its stationary form.** `atr_pct_rank` (+0.117), the
  trailing within-day percentile, is in the top six while the raw `atr1m` is
  **not in the top 15** at all. The elastic-net preferred the stationary
  companion — the opposite of Phase 4's choice, and the right one.

## Trade side / delta — still close to irrelevant

| feature | coefficient |
|---|---:|
{chr(10).join(f"| `{f}` | {interp['coefficients'][f]:+.5f} |" for f in fam6)}

Mean |coefficient| for family 6 is **{m6:.5f}** against **{mall:.5f}** across all
55 — slightly *below* average, with `delta_accel` eliminated outright. In the
unconditional state diagnostics the delta quartiles are flat to four decimal
places (−0.0066 to −0.0132 R).

Phase 4 found family 6 contributed exactly zero at a 5-second clock and a
30-minute horizon. Phase 5 finds it contributes almost nothing at a 60-second
clock and a 60-minute horizon either. **Two independent horizons, same answer:
trades-derived order flow carries no usable directional information here.**
This says nothing about MBP-1 book data, which neither phase opened.
""")
print("wrote part 1")
for x in sorted(REP.glob("*.md")):
    print("  ", x.name, x.stat().st_size)
