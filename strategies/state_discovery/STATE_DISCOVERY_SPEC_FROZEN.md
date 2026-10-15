# STATE_DISCOVERY_SPEC_FROZEN.md

    frozen id     statedisc-1.0.0+c147134184dfb32d
    spec version  statedisc-1.0.0
    frozen (UTC)  2026-08-20T03:26:55.619494+00:00
    combined      c147134184dfb32dad1e2f1be3611d8902a8c2bd19043352282717b7234aa182

The production strategy is frozen. This happened **before** the 2024
diagnostic, **before** the 2025-H2 diagnostic and **before** any contact with
2026-Q1 market content.

The frozen id is SHA-256 over the ordered `(path, file-sha256)` pairs below. If
any of these files changes, the id changes and
`scripts/p4_09_integrity.py` fails.

| file | sha256 |
|---|---|
| `strategies/state_discovery/FEATURE_REGISTRY.md` | `128c0e7455cf4b27ac721b995558a5f869fe852196b38b1dd3e1085b401d66de` |
| `strategies/state_discovery/SEARCH_BUDGET.md` | `45b3fc0df0a3813ff09406a6c526f78f4afeaa7e3a8697c27ba8ec2b17130224` |
| `strategies/state_discovery/PREREG_ADDENDUM.md` | `ad7be42a325192474d42bf3eb4ae66592c272d1674c8a49e97fd1255baabc341` |
| `strategies/state_discovery/STATE_DISCOVERY_SPEC.md` | `f9089f6159685e7600d8f83f9accf54fcb28e9d64aead87854ccae935783ff1c` |
| `src/nqr/p4/features4.py` | `636af03cc537fb992003113dd5602cf6ee21a1b21cb52e630344df574d8dc216` |
| `src/nqr/p4/holdout4.py` | `dc290620cbcc5f552d1c240a5f24af9103f22d14aa0a83b39f1d91d9a1aa5d35` |
| `src/nqr/p4/cache4.py` | `c07255c21e0f5af48e817ad7de500ae82d2be85741417465cd99c5206e53f409` |
| `src/nqr/p4/dataset4.py` | `b95d25adec72d9805e5a00b5559f4d0f5a3c14ebba0a6edfbb6190bf79471c33` |
| `src/nqr/p4/model4.py` | `4a332053d08e9c400073069a1bc931bd24f795e3fca5151b5b5ee359db5609ad` |
| `src/nqr/p4/backtest4.py` | `dfecd6efc8c66c06a74f39b6f77ee11392cff7e1e8de39a5eb813cddb580f20e` |
| `src/nqr/p4/metrics4.py` | `f5a4066d4c0adfd9afe262245522f5710b97d4134ba64d3aa4a1b8af23694aaf` |
| `strategies/state_discovery/models/production_model.pkl` | `24baf456554e229bb65e40ef60a6bef936197b7f2592bbc7f9f2376dcc5fae48` |
| `strategies/state_discovery/models/production_meta.json` | `635e0f96b5ce2912d2faeb58f7bd05b7864a614850a99d9cd66d86179f3e7069` |
| `strategies/state_discovery/models/selection_2022.parquet` | `223d5bfb09c469d3f38f00db3e9971a88f0b11c6d1f4fb645d8d93b962ecb5d1` |

## What is frozen

* the 55-feature registry and its implementation;
* the 2021-only winsorisation bounds and standardisation constants;
* the model family, its hyperparameters and the fitted tree itself;
* the signal threshold tau = 0.017941 as a number;
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
