"""Phase-5 model families, control baseline and the 18-configuration budget.

PHASE5_SEARCH_BUDGET.md, fixed before any outcome existed:

    3 R scales  x  2 model families  x  3 selectivity levels  =  18

Phase 4 spent its budget on hyperparameters; Phase 5 spends it on R scale,
because R scale is the hypothesis.  Each family therefore has exactly ONE
hyperparameter setting.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier, export_text

from nqr.p4.features4 import FEATURE_NAMES     # frozen upstream, read-only
from nqr.p4.model4 import Preprocessor         # frozen upstream, read-only
from nqr.p5.dataset5 import R_MULTS

MAX_CONFIGS = 18
SELECTIVITY = (0.10, 0.05, 0.02)               # top 10% / 5% / 2% of the edge score
LOGIT_C = 0.1
L1_RATIO = 0.5
TREE_DEPTH = 4
TREE_MIN_LEAF_FRAC = 0.02
BUCKET_S = 1800                                # 30-minute baseline buckets
SEED = 0
FAMILIES = ("A_logit", "B_tree")


class BudgetViolation(RuntimeError):
    """Raised if anything tries to evaluate more than the preregistered budget."""


@dataclass(frozen=True)
class Config:
    r_tag: str          # "r2p0" | "r3p0" | "r4p0"
    family: str         # "A_logit" | "B_tree"
    selectivity: float  # 0.10 | 0.05 | 0.02

    @property
    def model_key(self) -> str:
        return f"{self.r_tag}:{self.family}"

    @property
    def name(self) -> str:
        return f"{self.r_tag}:{self.family}:top{int(self.selectivity * 100)}"


def enumerate_configs() -> list[Config]:
    out = [Config(r, f, q) for r in R_MULTS for f in FAMILIES for q in SELECTIVITY]
    if len(out) != MAX_CONFIGS:
        raise BudgetViolation(f"budget is {MAX_CONFIGS}, built {len(out)}")
    return out


def model_keys() -> list[str]:
    return sorted({c.model_key for c in enumerate_configs()})


def build_estimator(family: str, n_train: int):
    if family == "A_logit":
        return LogisticRegression(penalty="elasticnet", l1_ratio=L1_RATIO, C=LOGIT_C,
                                  solver="saga", max_iter=1000, tol=1e-4,
                                  random_state=SEED)
    if family == "B_tree":
        return DecisionTreeClassifier(
            max_depth=TREE_DEPTH,
            min_samples_leaf=max(2, int(TREE_MIN_LEAF_FRAC * n_train)),
            random_state=SEED)
    raise BudgetViolation(f"unknown family {family!r}: the budget fixes exactly two")


def fit_model(family: str, Xs: np.ndarray, y: np.ndarray):
    est = build_estimator(family, len(y))
    est.fit(Xs, y)
    return est


# ------------------------------------------- training-only control baseline ----
def bucket_of(sec_since_open: np.ndarray) -> np.ndarray:
    return (sec_since_open // BUCKET_S).astype(np.int64)


def fit_baseline(sec_since_open: np.ndarray, y_long: np.ndarray,
                 y_short: np.ndarray) -> dict:
    """PHASE5_SPEC S11.  Expected matched-control outcome per 30-minute bucket
    and direction, estimated on TRAINING rows only.

    This is exactly the matched-random population: every decision timestamp in
    the bucket, both directions, under the same execution.  It replaces the
    theoretical 50% that Phases 3 and 4 showed to be wrong.
    """
    b = bucket_of(sec_since_open)
    out = {"buckets": {}, "n_fit": int(len(b)),
           "overall_long": float(y_long.mean()), "overall_short": float(y_short.mean())}
    for k in np.unique(b):
        m = b == k
        out["buckets"][int(k)] = {"n": int(m.sum()),
                                  "b_long": float(y_long[m].mean()),
                                  "b_short": float(y_short[m].mean())}
    return out


def baseline_vectors(baseline: dict, sec_since_open: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    b = bucket_of(sec_since_open)
    bl = np.full(len(b), baseline["overall_long"])
    bs = np.full(len(b), baseline["overall_short"])
    for k, v in baseline["buckets"].items():
        m = b == int(k)
        bl[m] = v["b_long"]
        bs[m] = v["b_short"]
    return bl, bs


def edge_and_direction(p_long: np.ndarray, b_long: np.ndarray,
                       b_short: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """PHASE5_SPEC S11.  Signed edge over the training-only control baseline.

        edge_long  = p       - b_long
        edge_short = (1 - p) - b_short
        direction  = argmax,  score = max

    Because both baselines sit BELOW 0.5 under realistic execution, the neutral
    point is not p = 0.5: direction flips at p = 0.5 + (b_long - b_short)/2,
    which is where the two edges are equal.
    """
    el = p_long - b_long
    es = (1.0 - p_long) - b_short
    direction = np.where(el >= es, 1, -1).astype(np.int64)
    score = np.maximum(el, es)
    return score, direction


def threshold_from_train(train_score: np.ndarray, q: float) -> float:
    """tau = the (1-q) quantile of the edge score on TRAINING rows.  Frozen."""
    return float(np.quantile(train_score, 1.0 - q))


def interpret(est, family: str) -> dict:
    if family == "A_logit":
        coef = est.coef_[0]
        order = np.argsort(-np.abs(coef))
        return {"kind": "logistic", "intercept": float(est.intercept_[0]),
                "n_nonzero": int((coef != 0).sum()),
                "coefficients": {FEATURE_NAMES[i]: float(coef[i]) for i in order},
                "top15": [(FEATURE_NAMES[i], float(coef[i])) for i in order[:15]]}
    imp = est.feature_importances_
    order = np.argsort(-imp)
    return {"kind": "tree", "depth": int(est.get_depth()), "n_leaves": int(est.get_n_leaves()),
            "importances": {FEATURE_NAMES[i]: float(imp[i]) for i in order if imp[i] > 0},
            "rules": export_text(est, feature_names=list(FEATURE_NAMES), decimals=3)}
