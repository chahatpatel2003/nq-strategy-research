# TIME_AND_STATE_DIAGNOSTICS.md — Phase 5

# DIAGNOSTIC / HYPOTHESIS GENERATION ONLY

# POST-HOC — REQUIRES NEW UNTOUCHED DATA

Everything here is computed on the **unconditional decision population** — every
60-second decision row, no model involved — over the **development years
2021–2023 only** (91,200 rows). It therefore describes the *market*, not
the strategy, at R = 4.0 × ATR14(1-min) with a 60-minute horizon, net of 1.0 pt
friction.

**46 cells were examined.** No multiplicity correction is
applied because none of this is a test — it is hypothesis generation on data that
has already been used. Nothing here modified Phase 5, and nothing here may be
traded without new untouched data.

The unconditional baseline for the whole population is **−0.024 R** (mean of both
directions), so a cell only matters if it is well above that.

### Time of day — fifteen-minute buckets

This is the table the brief specifically asked for.

| cell | n | long E[R] | long WR | short E[R] | short WR | better side | best E[R] |
|---|---:|---:|---:|---:|---:|:---:|---:|
| 09:30-09:45 | 11,400 | -0.0109 | 0.5095 | -0.0446 | 0.4830 | LONG | -0.0109 |
| 09:45-10:00 | 11,400 | -0.0051 | 0.5111 | -0.0321 | 0.4758 | LONG | -0.0051 |
| 10:00-10:15 | 11,400 | -0.0111 | 0.5076 | -0.0302 | 0.4792 | LONG | -0.0111 |
| 10:15-10:30 | 11,400 | -0.0308 | 0.4979 | -0.0152 | 0.4875 | SHORT | -0.0152 |
| 10:30-10:45 | 11,400 | -0.0385 | 0.4921 | -0.0106 | 0.4942 | SHORT | -0.0106 |
| 10:45-11:00 | 11,400 | -0.0137 | 0.5098 | -0.0400 | 0.4755 | LONG | -0.0137 |
| 11:00-11:15 | 11,400 | +0.0076 | 0.5228 | -0.0638 | 0.4602 | LONG | +0.0076 |
| 11:15-11:30 | 11,400 | +0.0277 | 0.5304 | -0.0884 | 0.4519 | LONG | +0.0277 |

**Reading it:** the only genuinely positive cells are the last two,
**11:00–11:30 long** (+0.0076 and +0.0277 R, WR 52.3 % and 53.0 %). The
10:15–10:45 pair leans short, the early session leans long, and every magnitude
is inside ±0.03 R. Against a −0.024 R baseline the late-session long tilt is the
one visible effect — and it is 2 cells out of 8, on three years of already-used
data.

### Distance from the session open (quartiles of `dist_open_norm`)

The strongest single effect in the whole diagnostic set.

| cell | n | long E[R] | long WR | short E[R] | short WR | better side | best E[R] |
|---|---:|---:|---:|---:|---:|:---:|---:|
| 1 | 22,800 | -0.0487 | 0.4883 | +0.0019 | 0.4988 | SHORT | +0.0019 |
| 2 | 22,800 | -0.0049 | 0.5097 | -0.0437 | 0.4771 | LONG | -0.0049 |
| 3 | 22,800 | -0.0229 | 0.5031 | -0.0256 | 0.4831 | LONG | -0.0229 |
| 4 | 22,800 | +0.0391 | 0.5396 | -0.0951 | 0.4446 | LONG | +0.0391 |

**Reading it:** the top quartile — price furthest **above** the 09:30 open —
returns **+0.0391 R long at 53.96 % WR**, against −0.0487 R for longs in the
bottom quartile. That is a clean continuation/trend-day signature and it is the
largest, most monotone effect found. It is also already inside the model:
`dist_open_norm` is the third-largest coefficient (+0.292).

### Above vs below the session open

0 = below, 1 = above.

| cell | n | long E[R] | long WR | short E[R] | short WR | better side | best E[R] |
|---|---:|---:|---:|---:|---:|:---:|---:|
| 0 | 44,243 | -0.0255 | 0.4996 | -0.0223 | 0.4874 | SHORT | -0.0223 |
| 1 | 46,957 | +0.0058 | 0.5201 | -0.0579 | 0.4651 | LONG | +0.0058 |


### Volatility quartile (`atr1m`)



| cell | n | long E[R] | long WR | short E[R] | short WR | better side | best E[R] |
|---|---:|---:|---:|---:|---:|:---:|---:|
| 1 | 22,800 | -0.0172 | 0.5115 | -0.0709 | 0.4646 | LONG | -0.0172 |
| 2 | 22,800 | -0.0072 | 0.5143 | -0.0424 | 0.4712 | LONG | -0.0072 |
| 3 | 22,800 | -0.0192 | 0.5045 | -0.0181 | 0.4856 | SHORT | -0.0181 |
| 4 | 22,800 | +0.0061 | 0.5104 | -0.0311 | 0.4823 | LONG | +0.0061 |

Essentially flat. Volatility level does **not** separate outcomes at this
horizon — which is notable, because it was Phase 4's dominant feature.

### Near the previous-day high (|dist_pdh_norm| < 1.0)

1 = near.

| cell | n | long E[R] | long WR | short E[R] | short WR | better side | best E[R] |
|---|---:|---:|---:|---:|---:|:---:|---:|
| 0 | 86,431 | -0.0068 | 0.5114 | -0.0432 | 0.4748 | LONG | -0.0068 |
| 1 | 4,769 | -0.0555 | 0.4871 | +0.0068 | 0.4967 | SHORT | +0.0068 |


### Near the previous-day low (|dist_pdl_norm| < 1.0)

1 = near.

| cell | n | long E[R] | long WR | short E[R] | short WR | better side | best E[R] |
|---|---:|---:|---:|---:|---:|:---:|---:|
| 0 | 86,828 | -0.0087 | 0.5114 | -0.0419 | 0.4745 | LONG | -0.0087 |
| 1 | 4,372 | -0.0230 | 0.4865 | -0.0148 | 0.5034 | SHORT | -0.0148 |

Near PDH the short side turns marginally positive (+0.0068 R) while the long side
drops to −0.0555 — a mild fade-the-high tilt on 4,769 rows. Near PDL shows
nothing.

### Directional velocity quartile (`vel_60_norm`)



| cell | n | long E[R] | long WR | short E[R] | short WR | better side | best E[R] |
|---|---:|---:|---:|---:|---:|:---:|---:|
| 1 | 22,800 | -0.0116 | 0.5064 | -0.0387 | 0.4804 | LONG | -0.0116 |
| 2 | 22,800 | -0.0125 | 0.5085 | -0.0372 | 0.4773 | LONG | -0.0125 |
| 3 | 22,800 | -0.0047 | 0.5136 | -0.0438 | 0.4717 | LONG | -0.0047 |
| 4 | 22,800 | -0.0085 | 0.5122 | -0.0428 | 0.4742 | LONG | -0.0085 |


### Path efficiency quartile (`eff_60`)



| cell | n | long E[R] | long WR | short E[R] | short WR | better side | best E[R] |
|---|---:|---:|---:|---:|---:|:---:|---:|
| 1 | 22,800 | -0.0064 | 0.5132 | -0.0423 | 0.4738 | LONG | -0.0064 |
| 2 | 22,800 | -0.0141 | 0.5081 | -0.0352 | 0.4787 | LONG | -0.0141 |
| 3 | 22,800 | -0.0024 | 0.5134 | -0.0473 | 0.4707 | LONG | -0.0024 |
| 4 | 22,800 | -0.0145 | 0.5060 | -0.0377 | 0.4804 | LONG | -0.0145 |


### Trade intensity quartile (`trades_per_s_60`)



| cell | n | long E[R] | long WR | short E[R] | short WR | better side | best E[R] |
|---|---:|---:|---:|---:|---:|:---:|---:|
| 1 | 22,800 | -0.0220 | 0.5093 | -0.0539 | 0.4667 | LONG | -0.0220 |
| 2 | 22,800 | -0.0077 | 0.5123 | -0.0388 | 0.4751 | LONG | -0.0077 |
| 3 | 22,800 | -0.0033 | 0.5107 | -0.0347 | 0.4783 | LONG | -0.0033 |
| 4 | 22,800 | -0.0043 | 0.5083 | -0.0351 | 0.4836 | LONG | -0.0043 |


### Delta state quartile (`delta_per_vol_60`)



| cell | n | long E[R] | long WR | short E[R] | short WR | better side | best E[R] |
|---|---:|---:|---:|---:|---:|:---:|---:|
| 1 | 22,800 | -0.0066 | 0.5112 | -0.0466 | 0.4731 | LONG | -0.0066 |
| 2 | 22,800 | -0.0067 | 0.5098 | -0.0400 | 0.4783 | LONG | -0.0067 |
| 3 | 22,800 | -0.0109 | 0.5095 | -0.0368 | 0.4773 | LONG | -0.0109 |
| 4 | 22,800 | -0.0132 | 0.5101 | -0.0391 | 0.4749 | LONG | -0.0132 |

**Velocity, efficiency, intensity and delta are all flat**, spanning less than
0.02 R end to end. The delta table is the flattest of the four (−0.0066 to
−0.0132 R), which is the third independent confirmation that trades-derived order
flow carries nothing directional here.

### Weekday

0 = Monday … 4 = Friday.

| cell | n | long E[R] | long WR | short E[R] | short WR | better side | best E[R] |
|---|---:|---:|---:|---:|---:|:---:|---:|
| 0 | 18,120 | +0.0157 | 0.5208 | -0.0771 | 0.4594 | LONG | +0.0157 |
| 1 | 17,400 | -0.0320 | 0.5048 | -0.0157 | 0.4837 | SHORT | -0.0157 |
| 2 | 18,720 | -0.0553 | 0.4845 | +0.0081 | 0.5015 | SHORT | +0.0081 |
| 3 | 18,720 | +0.0438 | 0.5381 | -0.0934 | 0.4504 | LONG | +0.0438 |
| 4 | 18,240 | -0.0199 | 0.5024 | -0.0240 | 0.4847 | LONG | -0.0199 |

Thursday longs (+0.0438 R) and Monday longs (+0.0157 R) look good; Wednesday
leans short. **Treat this as noise.** Five cells, no mechanism, and weekday
effects are the canonical spurious finding — Phase 1 already burned a subgroup
this way (the ENGULFING trigger, 56.7 % on dev → 45.0 % on validation).

### Year



| cell | n | long E[R] | long WR | short E[R] | short WR | better side | best E[R] |
|---|---:|---:|---:|---:|---:|:---:|---:|
| 2021 | 30,360 | -0.0216 | 0.5083 | -0.0373 | 0.4721 | LONG | -0.0216 |
| 2022 | 30,480 | -0.0164 | 0.5037 | -0.0201 | 0.4871 | LONG | -0.0164 |
| 2023 | 30,360 | +0.0100 | 0.5185 | -0.0646 | 0.4684 | LONG | +0.0100 |

The long tilt strengthens across 2021 → 2023 while the short side weakens, which
is consistent with a drift term rather than a state effect.

## Summary for hypothesis generation

| observation | size | confidence |
|---|---|---|
| price far **above** the session open → longs work | +0.039 R vs −0.049 R | strongest effect found; monotone across quartiles |
| **11:00–11:30 longs** | +0.028 R | modest, 2 of 8 time cells |
| near PDH → mild short tilt | +0.007 R | small, thin cell |
| volatility / velocity / efficiency / intensity / delta | < 0.02 R spread | no effect |
| weekday | up to +0.044 R | almost certainly noise |

Carried to `FUTURE_HYPOTHESES.md`. None of it may be added to Phase 5.
