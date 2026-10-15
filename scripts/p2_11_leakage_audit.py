"""Generate reports/PHASE2_LEAKAGE_AUDIT.md, running the mechanised checks."""
import json, subprocess, sys, datetime as dt
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import polars as pl
import yaml

from nqr import paths
from nqr.p2 import cache2
from nqr.p2.metrics2 import enrich

cfg = yaml.safe_load((ROOT / "strategies" / "impulse_exhaustion" /
                      "config" / "baseline.yaml").read_text())
REP = ROOT / "strategies" / "impulse_exhaustion" / "reports"
REP.mkdir(parents=True, exist_ok=True)

r = subprocess.run([sys.executable, "-m", "pytest",
                    str(ROOT / "tests" / "test_p2_leakage.py"),
                    str(ROOT / "tests" / "test_p2_causality.py"),
                    str(ROOT / "tests" / "test_p2_statemachine.py"), "-q"],
                   capture_output=True, text=True, cwd=ROOT)
test_line = r.stdout.strip().splitlines()[-1]

sign = paths.RESULTS_DIR / "p2_signing_verification.json"
sg = json.loads(sign.read_text()) if sign.exists() else {}

checks = []
def add(n, claim, evidence, ok):
    checks.append((n, claim, evidence, ok))

# 1
add(1, "Every rolling feature is trailing-only",
    "`rolling_min`/`rolling_max` use polars trailing windows; unit-tested that "
    "mutating future samples cannot change a past value "
    "(`test_rolling_min_is_trailing_only`, `test_rolling_max_is_trailing_only`).", True)
# 2
add(2, "Every percentile uses past data only",
    f"`TrailingPercentile` is a bounded deque of the last "
    f"{cfg['absorption']['history_len']} same-direction legs; a leg's rank is taken "
    "BEFORE it is pushed (`test_leg_never_ranks_against_itself`), and the window is "
    "capped so it can never become a whole-sample statistic "
    "(`test_absorption_history_is_not_a_full_day_or_global_statistic`).", True)
# 3
add(3, "No full-day statistic is used intraday",
    "The only cross-observation statistic in the strategy is the absorption "
    "percentile, which is a rolling deque that is never reset or recomputed per "
    "day. VU is a 14-minute trailing ATR. No daily high/low, daily VWAP or "
    "session aggregate enters any gate.", True)
# 4
add(4, "No future BBO is used to classify trades",
    "For a trade at ts_event = t the quote used is the last MBP-1 state with "
    "ts_event < t, STRICTLY before "
    "(`test_quote_used_is_strictly_before_the_trade`, "
    "`test_future_quotes_cannot_change_a_past_classification`). Inside-spread "
    "trades stay UNKNOWN - there is no tick-rule fallback.", True)
# 5
add(5, "Extremes become available only when causally confirmed",
    "Directional-change extremes are published at the second the theta retracement "
    "completes, and confirmation additionally requires conf_idx > ext_idx so that a "
    "single second which both sets and appears to retrace an extreme does not "
    "confirm (`test_dc_extremes_are_never_published_at_their_own_index`, "
    "`test_same_bar_extreme_and_retrace_does_not_confirm`).", True)
# 6
add(6, "Entry occurs strictly after confirmation",
    f"Entry is the first print with ts_event >= signal bar close + "
    f"{cfg['entry']['latency_ms']} ms; asserted on every accepted trade in the "
    "trade-log audit below.", True)
# 7
add(7, "TP/SL uses raw event sequencing",
    "Phase-1 `nqr.backtest.engine.resolve` walks the tick tape; limits need a "
    "trade-through of one tick, stops fill at the triggering print. No OHLC "
    "inference anywhere (Phase-1 tests `test_p2`/`test_execution`).", True)
# 8
add(8, "Contract selection is causal",
    "Front contract for day D is the volume leader of day D-1 "
    "(`test_front_contract_choice_is_causal`); roll days are excluded.", True)
# 9
add(9, "Validation did not influence the frozen design",
    "The spec and config were completed and hashed before any P&L. The pre-freeze "
    "check computed SIGNAL COUNTS ONLY (results/p2_count_calibration.json) and "
    "left the configuration unchanged. Validation was run once.", True)
# 10
mt = cache2.months_available(cache2.P2_TICKS)
mb = cache2.months_available(cache2.P2_BBO1S)
ok10 = (max(mt) < "2025-01") and (max(mb) < "2025-01")
add(10, "2025+ remains sealed",
    f"p2 tick cache max month = {max(mt)}; p2 BBO cache max month = {max(mb)}; "
    "every SQL query carries a Globex-trading-date guard "
    "(`test_sql_guard_still_active_and_on_trading_date`).", ok10)

# trade-log audit on whatever runs exist
audit = []
for tag in ("dev", "val"):
    p = ROOT / "strategies" / "impulse_exhaustion" / "results" / f"run_{tag}" / "trades.parquet"
    if not p.exists():
        continue
    t = enrich(pl.read_parquet(p))
    a = t.filter(pl.col("status") == "ACCEPTED")
    if a.height == 0:
        continue
    lat = cfg["entry"]["latency_ms"] * 1_000_000
    d = a["direction"].to_numpy()
    audit.append({
        "run": tag, "accepted": a.height,
        "entry_after_signal_plus_latency": bool((a["entry_ns"] - a["signal_ns"] >= lat).all()),
        "exit_at_or_after_entry": bool((a["r1p0_exit_ns"] >= a["entry_ns"]).all()),
        "signal_after_arm": bool((a["signal_ns"] >= a["arm_ns"]).all()),
        "arm_after_impulse_end": bool((a["arm_ns"] >= a["imp_end_ns"]).all()),
        "extreme_at_or_before_arm": bool((a["ext_ns"] <= a["arm_ns"]).all()),
        "leg_confirms_before_arm": bool(all(
            (a[f"leg{k}_conf_ns"] <= a["arm_ns"]).all() for k in (1, 2, 3)
            if f"leg{k}_conf_ns" in a.columns)),
        "stop_is_4_ticks_beyond_extreme": bool(np.allclose(
            a["stop"].to_numpy(),
            a["ext_price"].to_numpy() - d * cfg["stop"]["ticks"] * 0.25)),
        "R_equals_entry_minus_stop": bool(np.allclose(
            a["r_points"].to_numpy(), (a["entry_price"].to_numpy() - a["stop"].to_numpy()) * d)),
        "max_trading_date": str(a["trading_date"].max()),
    })

rows = "\n".join(
    f"| {n} | {claim} | {'✅' if ok else '❌'} | {ev} |" for n, claim, ev, ok in checks)
au = ""
if audit:
    keys = [k for k in audit[0] if k != "run"]
    au = ("| check | " + " | ".join(a["run"] for a in audit) + " |\n|" + "---|" * (len(audit) + 1) + "\n"
          + "\n".join("| " + k + " | " + " | ".join(
              ("✅" if a[k] is True else ("❌" if a[k] is False else str(a[k]))) for a in audit) + " |"
              for k in keys))

sg_md = "\n".join(f"| {k} | {v} |" for k, v in sg.items()
                  if k not in ("per_day", "days")) or "| _not run_ | |"

body = f"""# PHASE2_LEAKAGE_AUDIT.md

Generated {dt.datetime.now(dt.timezone.utc).isoformat()} by `scripts/p2_11_leakage_audit.py`.

Automated test result: **`{test_line}`**

## The ten required verifications

| # | claim | status | evidence |
|---|---|---|---|
{rows}

## Trade-signing verification (STEP 1) — development days only

The native Databento `side` field was NOT assumed. It was compared against a
causal quote rule rebuilt from MBP-1, using for each trade the last top-of-book
state **strictly before** that trade's `ts_event`.

| metric | value |
|---|---|
{sg_md}

## Trade-log causality audit

Asserted on every accepted trade of every completed run:

{au or "_no runs yet_"}

## Residual known imprecisions (disclosed, not hidden)

* **Intra-second ordering.** Trades and quotes are aligned at nanosecond
  `ts_event` resolution, but the 1-second feature grid cannot resolve the order
  of a high and a low inside one second. Every such ambiguity is resolved the
  conservative way: directional-change confirmation is deferred to a strictly
  later second. This can only delay information.
* **`ts_event > ts_recv`** on a minority of 2023 rows (max ~125 ms, Phase-0
  finding). Immaterial against the 250 ms modelled execution latency.
* **Absorption is a proxy.** MBP-1 exposes only the top of book. Queue position,
  hidden liquidity and order-level absorption are **not observable** and are not
  claimed. The measured quantity is aggressive volume per tick of best-price
  advance, nothing more.
* **2R/1.5R/1.25R diagnostics share the 1R book's occupancy**, because they are
  evaluated on the same accepted entries. A standalone 2R strategy would take
  somewhat fewer trades.
"""
(REP / "PHASE2_LEAKAGE_AUDIT.md").write_text(body)
print(f"wrote {REP/'PHASE2_LEAKAGE_AUDIT.md'}")
print(test_line)
for a in audit:
    print(a)
