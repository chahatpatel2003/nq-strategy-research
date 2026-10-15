"""Freeze the Phase-4 production specification.

Writes STATE_DISCOVERY_SPEC.md (the complete human-readable specification) and
STATE_DISCOVERY_SPEC_FROZEN.md (the hash manifest).  After this runs, any change
to a listed file changes the frozen id and the integrity check fails.

Must run BEFORE the 2024 diagnostic, the 2025-H2 diagnostic and any contact
with 2026-Q1.
"""
import datetime as dt
import hashlib, json, pickle, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))

import numpy as np

from nqr import paths
from nqr.p4 import backtest4 as BT
from nqr.p4 import dataset4, model4
from nqr.p4 import holdout4 as H4
from nqr.p4.features4 import FEATURE_NAMES
import nqr.p4.features4 as F4

SD = ROOT / "strategies" / "state_discovery"
SPEC_VERSION = "statedisc-1.0.0"

MANIFEST = [
    "strategies/state_discovery/FEATURE_REGISTRY.md",
    "strategies/state_discovery/SEARCH_BUDGET.md",
    "strategies/state_discovery/PREREG_ADDENDUM.md",
    "strategies/state_discovery/STATE_DISCOVERY_SPEC.md",
    "src/nqr/p4/features4.py",
    "src/nqr/p4/holdout4.py",
    "src/nqr/p4/cache4.py",
    "src/nqr/p4/dataset4.py",
    "src/nqr/p4/model4.py",
    "src/nqr/p4/backtest4.py",
    "src/nqr/p4/metrics4.py",
    "strategies/state_discovery/models/production_model.pkl",
    "strategies/state_discovery/models/production_meta.json",
    "strategies/state_discovery/models/selection_2022.parquet",
]

meta = json.loads((SD / "models" / "production_meta.json").read_text())
interp = json.loads((SD / "models" / "interpretation.json").read_text())
with open(SD / "models" / "production_model.pkl", "rb") as f:
    P = pickle.load(f)
pre = P["pre"]

pp = "\n".join(
    f"| {i+1} | `{n}` | {pre.lo[i]:.6g} | {pre.hi[i]:.6g} | {pre.mu[i]:.6g} | {pre.sd[i]:.6g} |"
    for i, n in enumerate(FEATURE_NAMES))
imp = "\n".join(f"| `{k}` | {v:.4f} |" for k, v in interp["importances"].items())

spec = f"""# STATE_DISCOVERY_SPEC.md — Phase 4 production specification

**Spec version:** `{SPEC_VERSION}`
**Frozen:** before the 2024 diagnostic, before the 2025-H2 diagnostic, before
any contact with 2026-Q1.

This file is the complete definition of the ONE production candidate carried out
of Phase-4 development. It is reproducible from the repository alone.

---

## 1. Research question

Are there recurring, causally observable NQ market states that predict future
price path better than comparable random entries after realistic execution
costs?

## 2. Data

NQ **Trades only**, Databento GLBX MDP-3, from the Samsung T9, read-only.
MBP-1 is never opened. No external series of any kind.

Front contract: the outright NQ symbol with the highest volume on the previous
trading day (frozen Phase-1 rule). Roll days are excluded. No back-adjustment.

| period | role |
|---|---|
| 2021-01-01 .. 2021-12-31 | DISCOVERY_TRAIN — model fit, scaler fit, threshold calibration |
| 2022-01-01 .. 2022-12-31 | SELECTION — the 18 configurations compared here, once |
| 2023-01-01 .. 2023-12-31 | INTERNAL_TEST — looked at once, after the choice |
| 2024-01-01 .. 2024-12-31 | CONTAMINATED diagnostic |
| **2025-01-01 .. 2025-06-30** | **SEALED. No unlock path exists.** |
| 2025-07-01 .. 2025-12-31 | CONTAMINATED diagnostic (spent as Phase-3 validation) |
| 2026-01-01 .. 2026-03-31 | FRESH VALIDATION — one shot |
| **2026-04-01 ..** | **SEALED FINAL HOLDOUT. No unlock path exists.** |

## 3. Session and decision clock

Official session **09:30:00–11:30:00 America/New_York**, decisions every
**5 seconds** (1440/day, first at 09:30:00, last at 11:29:55). DST follows the
tz database. Rows are also generated to 15:59:55 for the extended-window
diagnostics; they take no part in fitting, selection, calibration or validation.

## 4. Features

The 55 registered causal features of `FEATURE_REGISTRY.md`
(families 8/5/7/9/6/6/3/6/5), implemented in `src/nqr/p4/features4.py`. Cap 60,
used 55. Every feature is a trailing aggregate closed at the decision timestamp.

Causality convention: the grid second `[T0+i, T0+i+1)` is index `i`; the decision
stamped `T0+i+1` reads `grid[i]`, so every input second has closed. Proven by
`tests/test_p4_features.py::test_features_are_invariant_to_truncating_the_future`,
which deletes the entire future tape and requires all 55 values to be identical.

Volatility unit `A` = ATR14 of **completed** 1-minute bars, floor **2.0 pt**,
from the frozen `nqr.p2.features.causal_atr_minutes`. Family 9 comes from the
frozen `nqr.p3.dc_engine` at theta = 0.50 x A, asserted event-for-event
identical to the Phase-3 runner.

## 5. Preprocessing — fitted on 2021 ONLY

Winsorise at the 2021 0.1 % / 99.9 % quantiles, then standardise with the 2021
mean and standard deviation. Fitted on **{pre.n_fit:,}** 2021 rows inside
09:30–11:30, then applied unchanged to every later period. Never refitted.

| # | feature | winsor lo | winsor hi | mean | sd |
|---|---|---|---|---|---|
{pp}

## 6. Model

**Family B — shallow decision tree.** `{meta['model_key']}`.

    sklearn.tree.DecisionTreeClassifier(
        max_depth      = 3,
        min_samples_leaf = {int(model4.TREE_MIN_LEAF_FRAC * pre.n_fit)},   # 2 % of the 2021 rows
        random_state   = 0)

Fitted once on the 2021 partition. Depth {interp['depth']}, {interp['n_leaves']}
leaves. No ensemble, no boosting, no forest, no automated search.

Target (PREREG A6): `y = 1` iff the hypothetical LONG 1R/1R bracket opened at
that decision finishes **gross** points > 0.

### Learned rules

```
{interp['rules']}```

### Feature importances

| feature | importance |
|---|---|
{imp}

## 7. Score, direction, threshold

    score      = P(y=1 | x) - 0.5
    direction  = +1 if score > 0 else -1
    trade iff  |score| >= tau

**tau = {meta['tau']:.6f}**, the {int((1-meta['threshold_q'])*100)}th percentile of
`|score|` on the **2021** rows inside 09:30–11:30 (nominal top
{int(meta['threshold_q']*100)} %). Frozen as this number and applied unchanged
everywhere. Ties at tau are kept, so the realised selection rate on 2022 was
{meta['selection']['selection_rate']:.1%}, not {int(meta['threshold_q']*100)} % —
a depth-3 tree emits at most 8 distinct scores and the quantile falls inside a
tie group. Disclosed, not adjusted: PREREG A7 fixed the tie rule in advance.

## 8. Risk geometry

    R      = clip(0.50 x ATR14(completed 1-min, floor 2.0 pt), 1.0, 25.0)  points
    stop   = entry - direction x R
    target = entry + direction x R

R is evaluated at the decision timestamp; both levels hang off the **realised
entry price**, never the decision price.

## 9. Execution

    signal      decision timestamp t on the 5-second clock
    entry       first trade print at or after t + 250 ms; abandoned after 60 s
    stop        touch-then-market, filled at the triggering print
    target      resting limit, requires the tape to trade THROUGH by >= 1 tick
    timeout     30 minutes; exits at the last print before the cutoff, P&L counts
    hard exit   16:00 ET (never binding inside the official session)

Resolved on the raw chronological trade sequence by the frozen
`nqr.p3.fastpass`. No OHLC inference, no midpoint fills, no retroactive entry.

## 10. Portfolio rule

**One position at a time.** A candidate arriving while a position is open is
logged `SKIPPED_OVERLAP` and never becomes a second position.

## 11. Friction

Official evaluation at **1.0 NQ point round trip**. Also reported at 0.0, 0.5
and 2.0. Friction is applied to P&L only, never to the label.

## 12. Matched-random control (primary null)

Per executed trade, up to 10 controls: same trading day, same 30-minute
time-of-day bucket, same direction, control R within [0.80, 1.25] x signal R,
drawn without replacement, seed 20260819, identical entry / bracket / horizon /
friction. Controls are independent entries and are deliberately not subject to
the one-position rule. The strategy's own timestamps are not excluded from the
pool.

Also run: C2 opposite direction at the same timestamps; C3 shuffled direction
(1 000 reps, long fraction preserved); C4 day-block-permuted training target
with a full refit (20 reps).

## 13. Inference

Every uncertainty statement is a **day-block bootstrap**: 10 000 resamples of
whole trading days, strategy and controls resampled together so they stay
paired. No statistic anywhere treats overlapping 5-second rows as independent.

## 14. Validation gates (fixed before 2026-Q1 is opened)

Period 2026-Q1, session 09:30–11:30, 1R, friction 1.0 pt.

| gate | requirement | status |
|---|---|---|
| 1 | >= 100 executed trades | hard |
| 2 | net expectancy > 0 R | hard |
| 3 | profit factor > 1.10 | hard |
| 4 | raw WR > 50 % | **preference** (50 % is not the primary null) |
| 5 | E[R] − matched-control E[R], 95 % block-bootstrap CI lower bound > 0 | hard |
| 6 | WR − matched-control WR, 95 % block-bootstrap CI lower bound > 0 | hard |
| 7 | `total_net_R − best_ISO_week_net_R > 0` (PREREG A14) | hard |

Verdict is exactly one of PASS / PROMISING BUT INCONCLUSIVE / FAIL.

## 15. Training / retraining procedure

Fit once on 2021 and never refit. No walk-forward, no periodic retraining, no
online update. Reproducing the model is: build the 2021 state dataset, fit the
preprocessor, fit the tree with the parameters in §6, calibrate tau by §7.

## 16. Search budget actually spent

**TOTAL CONFIGURATIONS EVALUATED: {meta['total_configurations_evaluated']}**
of a ceiling of {model4.MAX_CONFIGS}. Two families x three hyperparameter
settings x three thresholds, each scored against 2022 exactly once. No
configuration outside this set ever had an outcome computed against it.
"""
(SD / "STATE_DISCOVERY_SPEC.md").write_text(spec)

h = hashlib.sha256()
files = {}
for rel in MANIFEST:
    b = (ROOT / rel).read_bytes()
    d = hashlib.sha256(b).hexdigest()
    files[rel] = d
    h.update(rel.encode()); h.update(d.encode())
combined = h.hexdigest()
frozen_id = f"{SPEC_VERSION}+{combined[:16]}"
now = dt.datetime.now(dt.timezone.utc).isoformat()

(paths.RESULTS_DIR / "p4_frozen_manifest.json").write_text(json.dumps(
    {"spec_version": SPEC_VERSION, "frozen_id": frozen_id,
     "combined_sha256": combined, "frozen_utc": now, "files": files}, indent=2))

rows = "\n".join(f"| `{k}` | `{v}` |" for k, v in files.items())
(SD / "STATE_DISCOVERY_SPEC_FROZEN.md").write_text(f"""# STATE_DISCOVERY_SPEC_FROZEN.md

    frozen id     {frozen_id}
    spec version  {SPEC_VERSION}
    frozen (UTC)  {now}
    combined      {combined}

The production strategy is frozen. This happened **before** the 2024
diagnostic, **before** the 2025-H2 diagnostic and **before** any contact with
2026-Q1 market content.

The frozen id is SHA-256 over the ordered `(path, file-sha256)` pairs below. If
any of these files changes, the id changes and
`scripts/p4_09_integrity.py` fails.

| file | sha256 |
|---|---|
{rows}

## What is frozen

* the 55-feature registry and its implementation;
* the 2021-only winsorisation bounds and standardisation constants;
* the model family, its hyperparameters and the fitted tree itself;
* the signal threshold tau = {meta['tau']:.6f} as a number;
* direction logic, R rule, 30-minute horizon, one-position rule;
* session, decision clock, entry model, fill rules, friction grid;
* the matched-control definition and the four null controls;
* the seven validation gates and the verdict vocabulary.

## What may still happen

* the 2024 and 2025-H2 **contaminated diagnostics**, which may not change
  anything above;
* exactly one fresh-validation run on 2026-Q1;
* reporting.

## What may never happen

* any modification to the above in response to a diagnostic or validation
  result;
* any additional configuration;
* any contact with 2025-H1 or with 2026-04-01 onward.
""")
print(f"FROZEN: {frozen_id}")
print(f"  files hashed: {len(files)}")
print(f"  TOTAL CONFIGURATIONS EVALUATED: {meta['total_configurations_evaluated']}")
