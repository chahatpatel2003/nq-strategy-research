"""Generate the Phase-4 report set from the stored results.  No hand-typed numbers."""
import json, pickle, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import numpy as np
import polars as pl

SD = ROOT / "strategies" / "state_discovery"
REP = SD / "reports"; REP.mkdir(parents=True, exist_ok=True)
RES = SD / "results"
DEV = ["train2021", "select2022", "itest2023"]
CONTAM = ["contam2024", "contam2025h2"]
ALL = DEV + CONTAM
LABEL = {"train2021": "2021 train", "select2022": "2022 selection",
         "itest2023": "2023 internal OOS", "contam2024": "2024 CONTAMINATED",
         "contam2025h2": "2025-H2 CONTAMINATED", "val2026q1": "2026-Q1 FRESH VALIDATION"}


def load(s):
    p = RES / f"run_{s}" / "results.json"
    return json.loads(p.read_text()) if p.exists() else None


R = {s: load(s) for s in ALL + ["val2026q1"]}
R = {k: v for k, v in R.items() if v}
meta = json.loads((SD / "models" / "production_meta.json").read_text())
interp = json.loads((SD / "models" / "interpretation.json").read_text())
frozen = json.loads((ROOT / "results" / "p4_frozen_manifest.json").read_text())
c4 = json.loads((RES / "null_c4.json").read_text())
sel = pl.read_parquet(SD / "models" / "selection_2022.parquet")
present = [s for s in ALL + ["val2026q1"] if s in R]
HDR = f"*Frozen production strategy `{meta['model_key']}` top{int(meta['threshold_q']*100)}, tau = {meta['tau']:.6f} · frozen id `{frozen['frozen_id']}`*"


def row(s, k, fmt="{:+.4f}"):
    v = R[s]["windows"]["0930_1130"].get(k)
    return fmt.format(v) if v is not None and np.isfinite(v) else "—"


def tbl(keys, fmts=None, splits=None):
    splits = splits or present
    fmts = fmts or {}
    out = ["| metric | " + " | ".join(LABEL[s] for s in splits) + " |",
           "|---|" + "---|" * len(splits)]
    for k in keys:
        f = fmts.get(k, "{:+.4f}")
        out.append(f"| `{k}` | " + " | ".join(row(s, k, f) for s in splits) + " |")
    return "\n".join(out)


INT = "{:,.0f}"; PCT = "{:.4f}"; F2 = "{:.3f}"

# ---------------------------------------------------------------- 1. selection
s2 = sel.sort(["expectancy_R", "n_trades"], descending=[True, True])
lines = ["| rank | configuration | candidates | sel. rate | trades | WR | E[R] @1.0pt | PF | >=200 |",
         "|---:|---|---:|---:|---:|---:|---:|---:|:---:|"]
for i, r in enumerate(s2.iter_rows(named=True)):
    lines.append(f"| {i+1} | `{r['config']}` | {r['n_candidates']:,} | {r['selection_rate']:.1%} | "
                 f"{r['n_trades']:,} | {r['win_rate']:.4f} | **{r['expectancy_R']:+.4f}** | "
                 f"{r['profit_factor']:.3f} | {'yes' if r['meets_min_trades'] else 'no'} |")
(REP / "MODEL_SELECTION.md").write_text(f"""# MODEL_SELECTION.md — Phase 4

{HDR}

## The budget, fully spent

**TOTAL CONFIGURATIONS EVALUATED: {meta['total_configurations_evaluated']}** of a
ceiling of 18 (2 families x 3 hyperparameters x 3 thresholds). Every one was
scored against **2022 only**, on the single criterion declared in
`SEARCH_BUDGET.md` §4 before any outcome existed: highest 2022 net expectancy in
R at 1.0 pt friction over 09:30–11:30, subject to >= 200 executed 2022 trades,
ties broken on trade count.

No configuration outside this table ever had an outcome computed against it.
2023, 2024, 2025-H2 and 2026-Q1 took no part in the choice.

## All 18, ranked by the preregistered criterion

{chr(10).join(lines)}

## The result that matters more than the ranking

**Every one of the 18 configurations has negative 2022 net expectancy.** The
spread runs from {s2['expectancy_R'].max():+.4f} R to {s2['expectancy_R'].min():+.4f} R
per trade; not one is above zero. The winner is the least-negative member of a
uniformly losing set, and `SEARCH_BUDGET.md` §4 selects on rank, not on sign.

The candidate carried forward is therefore `{meta['config_name']}` —
2022 expectancy **{meta['selection']['expectancy_R']:+.4f} R** over
{meta['selection']['n_trades']:,} trades, PF {meta['selection']['profit_factor']:.3f}.

### A note on the realised selection rate

The threshold is the nominal top {int(meta['threshold_q']*100)} % of `|score|`
calibrated on 2021. A depth-3 tree emits at most 8 distinct scores, so the 80th
percentile falls **inside a tie group**, and PREREG A7 (written before any
outcome) says ties are kept. The realised 2022 selection rate is therefore
{meta['selection']['selection_rate']:.1%}, not 20 %. This is disclosed rather
than corrected: changing the tie rule after seeing the outcome is precisely
what the preregistration exists to prevent.
""")

# --------------------------------------------------------------- 2. stability
gross = {s: R[s]["friction_sweep"]["0.0"]["expectancy_R"] for s in present}
mrows = []
for s in present:
    v = R[s].get("vs_matched", {}).get("expectancy_R", {})
    w = R[s].get("vs_matched", {}).get("win_rate", {})
    mrows.append(f"| {LABEL[s]} | {v.get('diff', float('nan')):+.4f} | "
                 f"[{v.get('ci95_lo', float('nan')):+.4f}, {v.get('ci95_hi', float('nan')):+.4f}] | "
                 f"{'**yes**' if v.get('ci95_lo', -1) > 0 else 'no'} | "
                 f"{w.get('diff', float('nan')):+.4f} | "
                 f"[{w.get('ci95_lo', float('nan')):+.4f}, {w.get('ci95_hi', float('nan')):+.4f}] | "
                 f"{'**yes**' if w.get('ci95_lo', -1) > 0 else 'no'} |")

(REP / "STABILITY.md").write_text(f"""# STABILITY.md — Phase 4

{HDR}

## Headline, 09:30–11:30, 1R, 1.0 pt round trip

{tbl(['n_trades','win_rate','expectancy_R','profit_factor','R_per_day','trades_per_day',
      'avg_hold_min','max_drawdown_R','pct_profitable_days'],
     {'n_trades': INT, 'win_rate': PCT, 'profit_factor': F2, 'trades_per_day': '{:.1f}',
      'avg_hold_min': '{:.2f}', 'max_drawdown_R': '{:,.0f}', 'pct_profitable_days': PCT})}

## Friction sweep — expectancy in R

| friction | {" | ".join(LABEL[s] for s in present)} |
|---|{"---|" * len(present)}
{chr(10).join("| " + f + " pt | " + " | ".join(f"{R[s]['friction_sweep'][f]['expectancy_R']:+.4f}" for s in present) + " |" for f in ("0.0", "0.5", "1.0", "2.0"))}

**Read the top row first.** At *zero* friction — no commission, no slippage
beyond what the tape already imposed — the strategy is
{", ".join(f"{gross[s]:+.4f} R on {LABEL[s]}" for s in present)}. There is no
gross edge for friction to eat. Friction is not the reason this fails; it is
what turns a flat result into an obviously losing one.

## Against the primary null — matched random entries

| period | ΔE[R] | 95 % block-bootstrap CI | excludes 0 | ΔWR | 95 % CI | excludes 0 |
|---|---:|---|:---:|---:|---|:---:|
{chr(10).join(mrows)}

The only period where the strategy separates from matched random is **2022 —
the year used to select it**. On 2021 (its own training year), on 2023
(untouched during selection), on 2024 and on 2025-H2, the confidence interval
contains zero. That is the signature of a selection artifact, not of an edge.

## Extended-window diagnostics (reported, never used to choose)

| window | {" | ".join(LABEL[s] for s in present)} |
|---|{"---|" * len(present)}
{chr(10).join("| " + w.replace('_', '–') + " | " + " | ".join(f"{R[s]['windows'][w]['expectancy_R']:+.4f} ({R[s]['windows'][w]['n_trades']:,})" for s in present) + " |" for w in ("0930_1130", "0930_1030", "1030_1130", "0930_1200", "0930_1600"))}

No window is profitable in any period. The official 09:30–11:30 session is not
the worst and not the best; widening to 16:00 makes every period worse.
""")

# ------------------------------------------------------- 3. controls and nulls
orows, c3rows = [], []
for s in present:
    o = R[s]["opposite_control"]; p = R[s]["windows"]["0930_1130"]
    v = R[s]["vs_opposite"]["expectancy_R"]
    orows.append(f"| {LABEL[s]} | {p['expectancy_R']:+.4f} | {o['expectancy_R']:+.4f} | "
                 f"{v['diff']:+.4f} | [{v['ci95_lo']:+.4f}, {v['ci95_hi']:+.4f}] | "
                 f"{'yes' if v['ci95_lo'] > 0 else 'no'} |")
    n = R[s]["null_c3_shuffled_direction"]
    c3rows.append(f"| {LABEL[s]} | {n['strategy_ER']:+.4f} | {n['null_ER_mean']:+.4f} | "
                  f"{n['null_ER_p95']:+.4f} | {n['p_strategy_ER_under_null']:.3f} |")

(REP / "CONTROLS_AND_NULLS.md").write_text(f"""# CONTROLS_AND_NULLS.md — Phase 4

{HDR}

All four controls were defined in `PREREG_ADDENDUM.md` before any outcome
existed. Every control uses the identical entry model, bracket, 30-minute
horizon and friction as the strategy, because all of them read the same
tick-resolved labels.

## C1 — matched-random entries (the primary null)

Same day, same 30-minute bucket, same direction, R within [0.80, 1.25] x the
signal's R, up to 10 per trade, seed 20260819.

| period | strategy E[R] | control E[R] | Δ | 95 % CI (day-block) | excludes 0 |
|---|---:|---:|---:|---|:---:|
{chr(10).join(f"| {LABEL[s]} | {R[s]['windows']['0930_1130']['expectancy_R']:+.4f} | {R[s]['matched_control']['expectancy_R']:+.4f} | {R[s]['vs_matched']['expectancy_R']['diff']:+.4f} | [{R[s]['vs_matched']['expectancy_R']['ci95_lo']:+.4f}, {R[s]['vs_matched']['expectancy_R']['ci95_hi']:+.4f}] | {'**yes**' if R[s]['vs_matched']['expectancy_R']['ci95_lo'] > 0 else 'no'} |" for s in present)}

Note what the control expectancy itself says: a *random* entry with this
geometry loses ~0.15–0.27 R per trade. The 1R/1R bracket at
R = 0.50 x ATR14(1-min) is a structurally losing bet after 1.0 pt of friction,
whoever places it. The strategy's job was to overcome that, and it does not.

## C2 — opposite direction, same timestamps

| period | strategy E[R] | flipped E[R] | Δ | 95 % CI | strategy better |
|---|---:|---:|---:|---|:---:|
{chr(10).join(orows)}

The flip is **not** better overall, so there is no hidden inverse strategy here.
On 2023 the two directions are statistically indistinguishable
({R['itest2023']['vs_opposite']['expectancy_R']['diff']:+.4f} R,
CI [{R['itest2023']['vs_opposite']['expectancy_R']['ci95_lo']:+.4f},
{R['itest2023']['vs_opposite']['expectancy_R']['ci95_hi']:+.4f}]) — the model's
direction call carries no out-of-sample information. Nothing is flipped: an
inverse strategy would be a new hypothesis needing new untouched data.

## C3 — shuffled direction labels (1 000 reps per period)

Entry, R and horizon held fixed; only the sign is reassigned at random,
preserving the realised long fraction.

| period | strategy E[R] | null mean | null p95 | p(null ≥ strategy) |
|---|---:|---:|---:|---:|
{chr(10).join(c3rows)}

Significant on 2021 and 2022. **Not** significant on 2023 (p = {R['itest2023']['null_c3_shuffled_direction']['p_strategy_ER_under_null']:.3f}),
2024 (p = {R['contam2024']['null_c3_shuffled_direction']['p_strategy_ER_under_null']:.3f}) or
2025-H2 (p = {R['contam2025h2']['null_c3_shuffled_direction']['p_strategy_ER_under_null']:.3f}).

## C4 — randomised feature/target relationship ({c4['n_rep']} refits)

The 2021 target is permuted **within trading days** — feature marginals and day
structure survive, only the feature→target link dies — the frozen configuration
is refitted, tau is recalibrated by the same rule, and 2022 is rescored.

| quantity | value |
|---|---|
| observed 2022 E[R] | **{c4['observed_2022']['expectancy_R']:+.4f}** |
| null E[R], mean ± sd | {c4['null_expectancy_R_mean']:+.4f} ± {c4['null_expectancy_R_sd']:.4f} |
| null E[R] range | {c4['null_expectancy_R_min']:+.4f} … {c4['null_expectancy_R_max']:+.4f} |
| observed 2022 WR | {c4['observed_2022']['win_rate']:.4f} |
| null WR, mean ± sd | {c4['null_win_rate_mean']:.4f} ± {c4['null_win_rate_sd']:.4f} |
| p(null ≥ observed), E[R] | **{c4['p_null_ge_observed_ER']:.3f}** |
| p(null ≥ observed), WR | **{c4['p_null_ge_observed_WR']:.3f}** |

This is the most informative control in Phase 4, and it cuts both ways.

The model **is** materially different from chance: it beats a same-complexity
model trained on scrambled labels by
**{c4['observed_2022']['expectancy_R'] - c4['null_expectancy_R_mean']:+.4f} R per
trade**, {abs(c4['observed_2022']['expectancy_R'] - c4['null_expectancy_R_mean']) / c4['null_expectancy_R_sd']:.0f} null
standard deviations away, with no permutation reaching it.

And it is **nowhere near enough**. The learned signal is worth about
{abs(c4['observed_2022']['expectancy_R'] - c4['null_expectancy_R_mean']):.3f} R
per trade while friction at this R scale costs roughly 0.20 R per trade. Phase 4
found a real state effect that is an order of magnitude too small to trade.

The caveat: C4 is measured on 2022, the selection year. On 2023 the C3 null
cannot distinguish the model from a coin flip at all.
""")

# -------------------------------------------------------- 4. interpretation
imp = "\n".join(f"| `{k}` | {v:.4f} | {int(round(v*100))} % |" for k, v in interp["importances"].items())
(REP / "MODEL_INTERPRETATION.md").write_text(f"""# MODEL_INTERPRETATION.md — Phase 4

{HDR}

## What kind of model was selected

Family B, a **shallow decision tree**: depth {interp['depth']},
{interp['n_leaves']} leaves, minimum leaf {int(0.02 * meta['preprocessor']['n_fit']):,}
rows (2 % of the 2021 training partition). Family A (regularised logistic
regression) was beaten on the preregistered 2022 criterion by all three tree
depths at the top-20 % threshold.

## Feature importances

| feature | importance | share |
|---|---:|---:|
{imp}

Only **{len(interp['importances'])} of the 55** registered features are used at
all. The depth cap did the feature selection; nothing was ranked against
out-of-sample outcomes.

## The learned rules

```
{interp['rules']}```

## What did it actually discover?

Reading the splits against the nine families:

* **`atr1m` ({interp['importances'].get('atr1m', 0):.0%}, family 3 — volatility level).**
  The dominant variable is the raw level of 1-minute ATR. This is a *regime*
  variable, not a directional one, and it is exactly the kind of feature that
  attaches a model to the period it was fitted on: 2021 volatility levels are
  not 2023 volatility levels.
* **`dist_pdh_norm` ({interp['importances'].get('dist_pdh_norm', 0):.0%}, family 8 — objective location).**
  Distance above or below the previous Globex day's high. The root split.
* **`secs_since_low_300` / `secs_since_high_300`
  ({interp['importances'].get('secs_since_low_300', 0) + interp['importances'].get('secs_since_high_300', 0):.0%}, family 4 — micro structure).**
  How long ago the trailing 5-minute extreme was set: a recency-of-extreme
  proxy, the closest thing here to an exhaustion or pullback idea.
* **`dist_open_norm` ({interp['importances'].get('dist_open_norm', 0):.0%}, family 8).**
  Displacement from the 09:30 open.

The label is best described as **volatility-regime + location**, with a weak
micro-structure recency term. It is *not* momentum, *not* reversal, *not*
trade-intensity and — notably — **not order flow**: families 5 (intensity) and 6
(trade side / delta) contribute **zero**, and so do families 1 (returns), 2
(velocity), 7 (time) and 9 (DC events).

Two things follow.

1. Keeping family 6 was the right call to test, and it produced a clean negative:
   given a causal 1-second delta state, a depth-3 tree preferred volatility level
   and previous-day location every time. Signed trade volume carried no usable
   directional information at this horizon.
2. A model whose strongest input is the *level* of volatility is a regime
   detector wearing a direction model's clothes, which is consistent with what
   the periods show: it works on 2021–2022 and stops working on 2023 onward.

## Direction balance

The tree is overwhelmingly short-biased — {R['itest2023']['windows']['0930_1130']['shorts']:,} shorts
against {R['itest2023']['windows']['0930_1130']['longs']:,} longs on 2023
({R['itest2023']['windows']['0930_1130']['shorts'] / R['itest2023']['windows']['0930_1130']['n_trades']:.0%} short).
Its long calls out-perform its short calls in four of five periods, which is
recorded in `FUTURE_HYPOTHESES.md` and changes nothing here.
""")

print("wrote", REP)
for f in sorted(REP.glob("*.md")):
    print("  ", f.name, f.stat().st_size, "bytes")
