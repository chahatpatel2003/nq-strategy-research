# FAST_SLOW_SPEC_FROZEN.md

**Frozen baseline identifier**

    fastslow-1.0.0+5980044a44eebf7b

`spec_version` = `fastslow-1.0.0`
combined SHA-256 = `5980044a44eebf7b7fb18268cecde194a7f986579bd9c26ce87eb5582f34fbc8`
frozen at = `2026-08-19T22:31:52.661652+00:00`

Reproduce with `python scripts/05_freeze.py`; the identifier is a SHA-256 over
the ordered `(path, file-sha256)` pairs below. If any of these files changes,
the identifier changes and the result is a **different hypothesis** that must be
named `FastSlow_v2` and evaluated separately.

## Frozen file manifest

| file | sha256 |
|---|---|
| `config/fast_slow_baseline.yaml` | `f171eb547e71b9d4600b79a67788a310e58d630ab2d2ee984b8888839c2d1a73` |
| `src/nqr/holdout.py` | `c5afa82417538cbea78370f707a95fc065676ddb3b20f15e35a19003d15188c6` |
| `src/nqr/paths.py` | `1a60e925fdfef9ba90f34b1388ce104eea994cfd594fe0d6b1f686e814d3af0b` |
| `src/nqr/sessions/calendar.py` | `cad87a736641eaddff692a4b1acf49c39555d9d98c0f0e640ec694e121d21e48` |
| `src/nqr/data/contracts.py` | `b8d8adf70cc3afc06cf0c24327f665b545c33cb2c2b426eea544762851529224` |
| `src/nqr/data/cache.py` | `e7cf7be2d10be316ed35b518760e5118ea13a773ec01084c2bca51ae1aeb9c0d` |
| `src/nqr/levels/build.py` | `4a0b25236163db9158376c20287625e18643a65b49c789d00b7704d912b39f8a` |
| `src/nqr/signals/triggers.py` | `feee750108bec43c4f6d98f355b00dbdf27cec99d785bcc539c78d68228d7fde` |
| `src/nqr/signals/fast_slow.py` | `c0446f0f25e9ea619a8a9cd97fd904d9a9c7338c854db72deacdeec7b24fd504` |
| `src/nqr/backtest/engine.py` | `20b639972c944d708e10acb6e441f719f59e1c9fb122729cc9dbad77e938d555` |
| `src/nqr/execution/simulate.py` | `32c5956428918309a21b94ca3a2e54c03864b1273fd8746cad8acaff345966b9` |
| `strategies/fast_slow/runner.py` | `738becd8f86de6689d7b8a4d27b19c771bab74b0bfcd5129ba0a7664d3ccd42e` |
| `scripts/01_build_cache.py` | `5f44965b652731b598b8add8f19bfd061a45ccf1554682f334b2b766b78e22c1` |
| `scripts/02_run_fast_slow.py` | `fe66ba5d74129d20347189ea70c7d69fa13f0cdacb93ef276b2d92203f8d8de4` |

## Freeze protocol actually followed

1. `FAST_SLOW_SPEC.md` and `config/fast_slow_baseline.yaml` were written **before
   any strategy P&L existed**. Every threshold in them comes from *a priori*
   reasoning about NQ tick size, NQ daily range and 2-minute bar granularity.
2. Development (2021-2023) was used **only** to verify the implementation: the
   trade log was audited for causality, stop/target arithmetic, fill-price
   consistency and MFE/MAE coherence, and randomly-sampled charts were checked
   against raw bars.
3. Two implementation defects were found and fixed during development, neither
   of which is a strategy parameter:
   * an Int8 overflow in the polars session-label expression (`dt.hour()` returns
     Int8, so `18*60` wrapped) - every bar was mislabelled `ASIA`;
   * the tick cache was not explicitly sorted by `ts_event`, which would have
     broken `searchsorted` on the ~1-in-3-million source rows whose `ts_event`
     ordering differs from `ts_recv` ordering.
   A regression test now covers each.
4. **No strategy parameter was altered after development results were seen.**
   The only post-result code edits were to the charting helper (handling
   `None` exit timestamps for skipped rows) and the addition of extra
   diagnostic columns to the rejected-pattern log. Neither can change a signal;
   the development run was re-executed after both and reproduced identical
   counts.
5. Validation (2024) was executed **once**, with this frozen configuration.

## The complete rule set

The full mechanical specification is `FAST_SLOW_SPEC.md`, whose SHA-256 is
recorded here as well for completeness:

    FAST_SLOW_SPEC.md  f82551b3c0f319c4cb497ca97a0b36e39bed98ad1fe604b871ff4f686d771eab

A second programmer needs `FAST_SLOW_SPEC.md` plus the frozen YAML to
reimplement this from scratch; the source files above are the reference
implementation of it.

## Pre-registered verdict rule (restated, unchanged)

Applied to the primary hypothesis - variant `ANY`, target `1R` - on the 2024
validation split at **1.0 point** round-trip friction:

* **PASS** - win-rate 95% CI lower bound > 0.50 AND expectancy > 0 AND profit
  factor > 1.10 AND one-sided binomial p < 0.05 against a 50% break-even AND
  at least 100 trades.
* **PROMISING BUT INCONCLUSIVE** - point-estimate expectancy > 0 but any of the
  above gates fails.
* **FAIL** - expectancy <= 0 at 1.0 point friction, or the 95% CI upper bound
  lies below the break-even win rate.
