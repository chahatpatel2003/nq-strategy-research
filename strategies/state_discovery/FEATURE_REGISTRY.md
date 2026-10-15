# FEATURE_REGISTRY.md — Phase 4 causal state vector

**Written and frozen BEFORE any label or outcome was computed.**

**55 base features** across the 9 pre-specified families (cap: 60). Every one is
computed from a dense 1-second grid built from NQ **trade prints only**, using
information strictly at or before the decision timestamp `t`.

## Conventions

* `t` — decision timestamp, every 5 s during 09:30:00–11:30:00 ET.
* `c[t]` — last trade price at or before `t` (forward-filled from the past only).
* `A` — `ATR14` of **completed** 1-minute bars strictly before `t`'s minute,
  floored at 2.0 pt. Identical to the Phase-2/3 `VU`, reused read-only from the
  frozen `nqr.p2.features.causal_atr_minutes`.
* `norm` — divided by `A` (or by `A·√(h/60)` for an `h`-second return, which is
  the diffusive scaling that makes horizons comparable).
* Every rolling window is **trailing and closed at `t`**. No centred windows, no
  future extrema, no full-session statistics, no backward fill.
* Untraded seconds carry the last past price and zero volume, and are flagged;
  no feature interpolates forward from a future print.

---

## Family 1 — returns / displacement (8)

| # | name | formula | lookback | units |
|---|---|---|---|---|
| 1 | `ret_norm_5` | `(c[t] − c[t−5]) / (A·√(5/60))` | 5 s | σ |
| 2 | `ret_norm_15` | `(c[t] − c[t−15]) / (A·√(15/60))` | 15 s | σ |
| 3 | `ret_norm_30` | `(c[t] − c[t−30]) / (A·√(30/60))` | 30 s | σ |
| 4 | `ret_norm_60` | `(c[t] − c[t−60]) / A` | 60 s | σ |
| 5 | `ret_norm_120` | `(c[t] − c[t−120]) / (A·√2)` | 120 s | σ |
| 6 | `ret_norm_300` | `(c[t] − c[t−300]) / (A·√5)` | 300 s | σ |
| 7 | `eff_60` | `|c[t] − c[t−60]| / Σ|Δc|` over 60 s | 60 s | ratio 0–1 |
| 8 | `eff_300` | `|c[t] − c[t−300]| / Σ|Δc|` over 300 s | 300 s | ratio 0–1 |

Efficiency ratio = net displacement / total distance travelled: 1 = a straight
line, 0 = pure churn.

## Family 2 — velocity / acceleration (5)

| # | name | formula | lookback |
|---|---|---|---|
| 9 | `vel_15_norm` | `(c[t] − c[t−15]) / 15 / (A/60)` | 15 s |
| 10 | `vel_60_norm` | `(c[t] − c[t−60]) / 60 / (A/60)` | 60 s |
| 11 | `vel_ratio_15_60` | `vel_15 / (|vel_60| + ε)` | 60 s |
| 12 | `accel_15_60` | `vel_15_norm − vel_60_norm` | 60 s |
| 13 | `persist_60` | signed share of the last 60 one-second changes moving with the 60 s direction, `2·frac − 1` | 60 s |

## Family 3 — volatility / range state (7)

| # | name | formula | lookback |
|---|---|---|---|
| 14 | `atr1m` | ATR14 of completed 1-minute bars | 14 min | pt |
| 15 | `rv_60_norm` | `√(Σ Δc²)` over 60 s, ÷ `A` | 60 s |
| 16 | `rv_300_norm` | `√(Σ Δc²)` over 300 s, ÷ `A·√5` | 300 s |
| 17 | `vol_ratio_60_300` | `rv_60·√5 / (rv_300 + ε)` | 300 s |
| 18 | `range_60_norm` | `(max c − min c)` over 60 s ÷ `A` | 60 s |
| 19 | `atr_pct_rank` | percentile of `atr1m` within the **strictly prior** 120 min of same-day `atr1m` values | 120 min | 0–1 |
| 20 | `vol_expansion` | `atr1m[t] / atr1m[t−1200]` | 20 min | ratio |

`atr_pct_rank` is a within-day trailing percentile only — never a full-day or
cross-sample percentile.

## Family 4 — micro price structure (9)

| # | name | formula | lookback |
|---|---|---|---|
| 21 | `dist_high_300_norm` | `(max c over 300 s − c[t]) / A` | 300 s |
| 22 | `dist_low_300_norm` | `(c[t] − min c over 300 s) / A` | 300 s |
| 23 | `dist_high_1800_norm` | `(max c over 1800 s − c[t]) / A` | 30 min |
| 24 | `dist_low_1800_norm` | `(c[t] − min c over 1800 s) / A` | 30 min |
| 25 | `n_new_highs_300` | count of seconds in the last 300 s that set a new 300-s trailing high | 300 s |
| 26 | `n_new_lows_300` | mirror | 300 s |
| 27 | `pullback_depth` | `(max c − c[t]) / (max c − min c + ε)` over 300 s | 300 s | 0–1 |
| 28 | `secs_since_high_300` | seconds since the 300-s trailing high was set | 300 s |
| 29 | `secs_since_low_300` | mirror | 300 s |

All extrema are **trailing** maxima/minima of a closed window ending at `t`.
No future-confirmed swing is used anywhere in this family.

## Family 5 — trade intensity (6)

| # | name | formula | lookback |
|---|---|---|---|
| 30 | `trades_per_s_60` | trade count / 60 | 60 s |
| 31 | `vol_per_s_60` | contracts / 60 | 60 s |
| 32 | `avg_trade_size_60` | volume / trade count | 60 s |
| 33 | `max_trade_size_60_rel` | max single print size ÷ trailing 300 s mean size | 60 s |
| 34 | `intensity_ratio_60_300` | `trades_per_s_60 / (trades_per_s_300 + ε)` | 300 s |
| 35 | `volume_ratio_60_300` | `vol_per_s_60 / (vol_per_s_300 + ε)` | 300 s |

"Large trade" is never an absolute constant: #33 is relative to a strictly
trailing distribution.

## Family 6 — trade-side / order flow (6)

**Inclusion decision, recorded before use.** The brief permits these *only if*
the aggressor field can be used causally from Trades without touching MBP-1.
It can. Phase 2 already verified the native Databento `side` field against a
causal MBP-1 quote rule on 12 development days: **99.998 % agreement over
3,882,344 unambiguous trades**, 62 disagreements, 0.013 % inside-spread, 0 %
unknown (`results/p2_signing_verification.json`). That verification is complete
and archived, so Phase 4 reads `side` straight out of the trades file and
**does not open MBP-1 at any point**. `side = 'B'` is buyer-initiated,
`'A'` seller-initiated, `'N'` unknown (contributes to neither).

| # | name | formula | lookback |
|---|---|---|---|
| 36 | `delta_60_norm` | `(buy − sell) volume` ÷ trailing 300 s mean 60 s volume | 60 s |
| 37 | `delta_300_norm` | mirror over 300 s | 300 s |
| 38 | `delta_per_vol_60` | `(buy − sell) / (buy + sell + ε)` | 60 s | −1…1 |
| 39 | `delta_per_vol_300` | mirror | 300 s | −1…1 |
| 40 | `cum_delta_norm` | signed volume since 09:30 ÷ session volume so far | since open | −1…1 |
| 41 | `delta_accel` | `delta_per_vol_60 − delta_per_vol_300` | 300 s |

## Family 7 — time / session state (3)

| # | name | formula |
|---|---|---|
| 42 | `secs_since_open` | `t − 09:30:00 ET`, seconds |
| 43 | `is_second_hour` | 1 if `t ≥ 10:30 ET` else 0 |
| 44 | `weekday` | 0 = Monday … 4 = Friday |

State features only. They may **not** be used to select a favourable weekday or
hour after the fact.

## Family 8 — objective location (6)

| # | name | formula |
|---|---|---|
| 45 | `dist_open_norm` | `(c[t] − session open at 09:30) / A` |
| 46 | `dist_vwap_norm` | `(c[t] − session VWAP so far) / A` |
| 47 | `dist_pdh_norm` | `(c[t] − previous Globex-day high) / A` |
| 48 | `dist_pdl_norm` | `(c[t] − previous Globex-day low) / A` |
| 49 | `dist_or30_hi_norm` | `(c[t] − 09:30–10:00 range high) / A`, 0 before 10:00 |
| 50 | `dist_or30_lo_norm` | `(c[t] − 09:30–10:00 range low) / A`, 0 before 10:00 |

VWAP accumulates from 09:30 to `t` only. The opening range is used only once it
has **completed** at 10:00 ET; before that #49/#50 are zero and a companion flag
is implicit in `secs_since_open`. Previous-day high/low come from the frozen
Phase-1 session machinery and are known at the open.

## Family 9 — event-sequence context (5)

Context only. This is **not** Phase 3 rebuilt as a filter — no directional-change
rule gates any trade; these are five state variables like any other.

| # | name | formula |
|---|---|---|
| 51 | `last_dc_dir` | direction of the most recently **confirmed** DC event (+1/−1/0) |
| 52 | `last_dc_mag_norm` | its magnitude ÷ `A` |
| 53 | `last_overshoot_norm` | the completed overshoot preceding it ÷ `A` |
| 54 | `prev2_dc_dir` | direction of the DC event before that |
| 55 | `secs_since_last_dc` | seconds since that confirmation |

The DC engine is the frozen Phase-3 `nqr.p3.dc_engine`, reused read-only at
`θ = 0.50 × A`. An extreme is never treated as known before its confirmation, so
these features inherit Phase 3's tested causality.

---

## Excluded, deliberately

* **MBP-1 of any kind** — quotes, spread, book sizes, imbalance. Phase 4 is
  trades-only, which keeps 2025-H1 sealed.
* Any external series (ES, QQQ, VIX, options, news, sentiment).
* Any feature requiring a future-confirmed pivot without delaying availability.
* Hand-built interaction terms — the tree may find interactions internally
  within its depth cap; none are constructed by hand.

## Live computability

Every feature is a trailing aggregate over the last ≤ 30 minutes of trade
prints plus one 14-minute ATR, computable incrementally from a live trade feed
with no lookahead and no vendor-derived inputs.
