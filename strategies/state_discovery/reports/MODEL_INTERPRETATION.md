# MODEL_INTERPRETATION.md — Phase 4

*Frozen production strategy `B_tree:depth=3` top20, tau = 0.017941 · frozen id `statedisc-1.0.0+c147134184dfb32d`*

## What kind of model was selected

Family B, a **shallow decision tree**: depth 3,
7 leaves, minimum leaf 7,286
rows (2 % of the 2021 training partition). Family A (regularised logistic
regression) was beaten on the preregistered 2022 criterion by all three tree
depths at the top-20 % threshold.

## Feature importances

| feature | importance | share |
|---|---:|---:|
| `atr1m` | 0.3966 | 40 % |
| `dist_pdh_norm` | 0.2696 | 27 % |
| `secs_since_low_300` | 0.1216 | 12 % |
| `secs_since_high_300` | 0.1156 | 12 % |
| `dist_open_norm` | 0.0965 | 10 % |

Only **5 of the 55** registered features are used at
all. The depth cap did the feature selection; nothing was ranked against
out-of-sample outcomes.

## The learned rules

```
|--- dist_pdh_norm <= 0.769
|   |--- atr1m <= -0.777
|   |   |--- dist_open_norm <= 0.813
|   |   |   |--- class: 0
|   |   |--- dist_open_norm >  0.813
|   |   |   |--- class: 0
|   |--- atr1m >  -0.777
|   |   |--- secs_since_low_300 <= -0.753
|   |   |   |--- class: 1
|   |   |--- secs_since_low_300 >  -0.753
|   |   |   |--- class: 0
|--- dist_pdh_norm >  0.769
|   |--- atr1m <= -0.177
|   |   |--- secs_since_high_300 <= 0.616
|   |   |   |--- class: 0
|   |   |--- secs_since_high_300 >  0.616
|   |   |   |--- class: 1
|   |--- atr1m >  -0.177
|   |   |--- class: 1
```

## What did it actually discover?

Reading the splits against the nine families:

* **`atr1m` (40%, family 3 — volatility level).**
  The dominant variable is the raw level of 1-minute ATR. This is a *regime*
  variable, not a directional one, and it is exactly the kind of feature that
  attaches a model to the period it was fitted on: 2021 volatility levels are
  not 2023 volatility levels.
* **`dist_pdh_norm` (27%, family 8 — objective location).**
  Distance above or below the previous Globex day's high. The root split.
* **`secs_since_low_300` / `secs_since_high_300`
  (24%, family 4 — micro structure).**
  How long ago the trailing 5-minute extreme was set: a recency-of-extreme
  proxy, the closest thing here to an exhaustion or pullback idea.
* **`dist_open_norm` (10%, family 8).**
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

The tree is overwhelmingly short-biased — 32,929 shorts
against 3,216 longs on 2023
(91% short).
Its long calls out-perform its short calls in four of five periods, which is
recorded in `FUTURE_HYPOTHESES.md` and changes nothing here.
