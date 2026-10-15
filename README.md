# NQ Strategy Research: Seven Pre-Registered Tests on Nasdaq-100 Futures

A reproducible research framework for CME **NQ (E-mini Nasdaq-100) futures**. I used it to test seven trading hypotheses under strict, pre-registered rules. **All seven failed**, and this repository publishes every one of those negative results with the evidence behind it.

The point of the project is the method: write the rules down before seeing any P&L, freeze them with a hash, test once on unseen data, and accept the verdict.

| | |
|---|---|
| **Instrument** | NQ futures (CME Globex), trade prints and MBP-1 top-of-book |
| **Data** | Databento tick data, 2021 → 2026 (licensed; not included) |
| **Stack** | Python 3.12, Polars, DuckDB, PyArrow, NumPy, SciPy, scikit-learn, Matplotlib, pytest |
| **Scale** | ~22k lines of Python · 7 research phases · 595 diagnostic charts |
| **Tests** | 423 pytest tests: 400 pass, 22 skip without the market data, 1 reads the raw market data folder directly. All frozen-manifest integrity checks pass |
| **Outcome** | 7 of 7 candidates rejected by their own pre-registered gates |

---

## Why this project is worth reading

Most backtests fail quietly, or get tuned until they look good. This framework is built to stop that from happening:

- **Pre-registration.** Every phase starts with a written spec (`*_SPEC.md`) containing the pass/fail gates. The spec is written before any P&L exists and is frozen with a SHA-256 file manifest (`*_SPEC_FROZEN.md`, `results/*frozen_manifest.json`). The verdict script applies those gates mechanically.
- **A sealed holdout enforced in code.** `src/nqr/holdout.py` raises `HoldoutViolation` on any read of a sealed date, date range or file name. The guard works on the **Globex trading date**, not the UTC date. Unsealing requires a literal confirmation string, and no phase ever used it.
- **Realistic execution.**
  - Prices are stored as integer ticks.
  - Outcomes come from the raw tape, never from OHLC bars.
  - A resting limit fills only when the tape trades *through* it.
  - Entry is the first print at least 250 ms after the signal bar closes.
  - Every table is reported at 0 / 0.5 / 1 / 2 points of friction.
- **Controls and nulls.** Results are compared with matched-random entries, permutation nulls and ablations, not with a theoretical 50 %.
- **Leakage audits.** Every phase from 4 onwards has a written leakage audit and a start-of-phase integrity check. The audits do find problems: Phase 6 showed that Phase 5's matched controls were not causal, and the affected result was recomputed and reported.

## Results

| Phase | Hypothesis | Verdict | Key evidence |
|---|---|---|---|
| 1 | **Fast-Slow** Nasdaq-100 pattern (published rule set) | **FAIL** | 2024 validation: 159 trades, expectancy **−0.184 R**, PF 0.824, win-rate CI lower bound 0.377. 4 of 5 gates failed |
| 2 | **Impulse exhaustion / absorption reversal** | **FAIL** | 2024 validation: 15 trades, **−0.668 R**, PF 0.288. All 6 gates failed |
| 3 | **Directional-change / event-time** (3 families) | **FAIL** | Fresh 2025-H2 validation, 15,583 trades: win rate 48.21 % (95 % CI lower bound 47.42 %), **−0.214 R**, PF 0.709. No family passed |
| 4 | **Causal state discovery**: 55 pre-registered tape features, 18 capped models | **FAIL** (development) | 162,557 trades. No gross edge; a real but tiny state signal (~0.02 R/trade) against ~0.14 R/trade friction |
| 5 | **Larger-R causal state**: the same features at 2–4 × ATR targets | **FAIL** (pre-validation) | 2023 internal out-of-sample: **−0.038 R**, PF 0.911, worse than matched random. All 4 gates failed, so 2026-Q1 stayed sealed |
| 6 | **Context + entry timing** | **FAIL** (pre-validation) | The causal rebuild removed the apparent context effect. No entry mechanic beat random timing inside the context |
| 7 | **MBP-1 order-book state**: 222 GB, 7.89 B rows, 40 L1 features | **FAIL** | 0 of 12 configurations had positive net expectancy. Permutation null p = 0.84; no incremental information from top-of-book |

Each phase has its own verdict document:
[Phase 1](PHASE1_VERDICT.md) ·
[2](strategies/impulse_exhaustion/PHASE2_VERDICT.md) ·
[3](strategies/directional_change/PHASE3_VERDICT.md) ·
[4](strategies/state_discovery/PHASE4_VERDICT.md) ·
[5](strategies/larger_r/PHASE5_VERDICT.md) ·
[6](strategies/context_entry/PHASE6_VERDICT.md) ·
[7](strategies/orderbook_state/PHASE7_VERDICT.md)

### What the negative results established

- **No gross edge** existed in any trades-derived state at these horizons. Friction did not destroy an edge; there was none to destroy.
- **The binding constraint is the size of R relative to costs, not the features.** The measured Phase 4 signal would break even only at R ≈ 50 points.
- **Trade-side order flow was uninformative in three separate phases** (4, 5, 7). In Phase 7, the trades-only model was worse than not trading at all.
- **A recurring short bias** (93 % of trades in Phases 5 and 7) is flagged as a likely artefact of the shared 1R/1R label construction. It is recorded as a future hypothesis, not claimed as a finding.
- **Holdouts were spent only when a candidate earned it.** Phases 4–7 failed before validation, so the 2026-Q1 quarter remains unread.

## Repository layout

```
├── PHASE1_VERDICT.md, FAST_SLOW_SPEC.md, FAST_SLOW_SPEC_FROZEN.md, DATA_AUDIT.md
├── TECHNICAL_README.md        full technical notes: how to reproduce every phase, design notes, period policies
├── config/                    frozen Phase 1 parameters
├── src/nqr/                   the framework
│   ├── holdout.py             sealed-period guard (raises HoldoutViolation)
│   ├── sessions/              Globex day, ASIA/EU/US sessions, DST via zoneinfo
│   ├── data/ bars/ levels/    audit, contract roll selection, tick cache, 2-minute bars
│   ├── signals/ backtest/ execution/ metrics/ viz/
│   └── p2/ … p7/              phase-specific features, models, controls, nulls
├── strategies/<phase>/        spec, frozen manifest, verdict, configs, results, reports, diagnostics, charts
├── scripts/                   numbered pipeline per phase (build → freeze → run → report → verdict → integrity)
├── reports/                   Phase 1 reports, leakage audits, start-of-phase integrity checks, charts
├── results/                   frozen manifests, verdict JSON, data audit, calibration files
└── tests/                     pytest suite: holdout guard, no-lookahead, causality, execution, sessions
```

## Running it

```bash
git clone https://github.com/chahatpatel2003/nq-strategy-research.git
cd nq-strategy-research
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python polars pyarrow duckdb numpy pandas matplotlib scipy pyyaml pytest tzdata
.venv/bin/python -m pytest -q
```

The full pipeline for each phase is documented step by step in [TECHNICAL_README.md](TECHNICAL_README.md). The exact package versions are in `requirements-lock.txt`.

**Data is not included.** The raw Databento NQ trades and MBP-1 files (about 220 GB) are licensed and cannot be redistributed. The derived caches and full trade-level logs stay private for the same reason. The repository does include everything needed to audit the work: specs, frozen manifests, the frozen phase 4, 5 and 7 model files, configs, summary results, reports, charts and the code that produced them. Tests that need the market data report it rather than pass silently.

## Third-party material

- **Market data:** Databento NQ trades and MBP-1 (licensed; not included).
- **Published ideas implemented here:** Phase 1 turns the published "Fast-Slow" Nasdaq-100 pattern into an independent mechanical specification; the concept belongs to its original author. Phase 7 uses the order-flow imbalance measure of Cont, Kukanov and Stoikov from the academic literature.
- **Open-source libraries** are installed as dependencies under their own licences; none are copied into this repository.

## Notes

- Research was run on a local workstation with the data on an external SSD. Paths in the technical notes refer to that setup.
- This repository was assembled on 2026-10-14 from the original working folder. File contents are byte-identical to that snapshot, verified by SHA-256.
- Research software only. Nothing here is investment advice.

© Chahat Patel. All rights reserved. This notice covers the original code, documentation and research results in this repository. It does not extend to the third-party material listed above, which belongs to its respective owners. No license to reuse this code is granted; it is published for review.
