"""Phase-7 model families, selectivity thresholds and the 12-configuration budget.

SEARCH_BUDGET.md, fixed before any outcome existed:

    2 R scales  x  2 model families  x  3 selectivity levels  =  12
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier, export_text

from nqr.p4.model4 import Preprocessor          # frozen upstream, read-only
from nqr.p7.dataset7 import R_POINTS
from nqr.p7.features7 import FEATURE_NAMES

MAX_CONFIGS = 12
SELECTIVITY = (0.010, 0.005, 0.002)     # top/bottom 1.0% / 0.5% / 0.2%
SEL_TAG = {0.010: "top1p0", 0.005: "top0p5", 0.002: "top0p2"}
LOGIT_C = 0.1
L1_RATIO = 0.5
TREE_DEPTH = 3
TREE_MIN_LEAF_FRAC = 0.02
FAMILIES = ("A_logit", "B_tree")
SEED = 0


class BudgetViolation(RuntimeError):
    """Raised if anything tries to evaluate more than the preregistered budget."""


@dataclass(frozen=True)
class Config:
    r_tag: str
    family: str
    selectivity: float

    @property
    def model_key(self) -> str:
        return f"{self.r_tag}:{self.family}"

    @property
    def name(self) -> str:
        return f"{self.r_tag}:{self.family}:{SEL_TAG[self.selectivity]}"


def enumerate_configs() -> list[Config]:
    out = [Config(r, f, q) for r in R_POINTS for f in FAMILIES for q in SELECTIVITY]
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


def confidence(p_up: np.ndarray) -> np.ndarray:
    """Directional confidence.  Direction is sign(p - 0.5); strength is |p - 0.5|."""
    return np.abs(p_up - 0.5)


def thresholds_from_train(p_train: np.ndarray) -> dict:
    """Selectivity cut-offs from the 2021 confidence distribution ONLY, then frozen.

    A level q keeps the strongest q of states in EACH tail, so the nominal total
    selection rate is q (q/2 long + q/2 short).
    """
    c = confidence(p_train)
    return {q: float(np.quantile(c, 1.0 - q)) for q in SELECTIVITY}


def direction_of(p_up: np.ndarray) -> np.ndarray:
    return np.where(p_up >= 0.5, 1, -1).astype(np.int64)


def interpret(est, family: str, names: list[str] | None = None) -> dict:
    names = names or FEATURE_NAMES
    if family == "A_logit":
        coef = est.coef_[0]
        order = np.argsort(-np.abs(coef))
        return {"kind": "logistic", "intercept": float(est.intercept_[0]),
                "n_nonzero": int((coef != 0).sum()), "n_features": len(names),
                "coefficients": {names[i]: float(coef[i]) for i in order},
                "top15": [(names[i], float(coef[i])) for i in order[:15]]}
    imp = est.feature_importances_
    order = np.argsort(-imp)
    return {"kind": "tree", "depth": int(est.get_depth()),
            "n_leaves": int(est.get_n_leaves()), "n_features": len(names),
            "importances": {names[i]: float(imp[i]) for i in order if imp[i] > 0},
            "rules": export_text(est, feature_names=list(names), decimals=4)}
