"""Phase-4 model families, preprocessing and the 18-configuration budget.

SEARCH_BUDGET.md, fixed before any outcome existed:

    2 model families  x  3 hyperparameter settings  x  3 thresholds  =  18

`enumerate_configs()` is the only place configurations are created and it is
hard-capped.  Anything that tries to widen it raises.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier, export_text

from nqr.p4.features4 import FEATURE_NAMES

MAX_CONFIGS = 18
WINSOR_LO, WINSOR_HI = 0.001, 0.999
THRESHOLD_QUANTILES = (0.20, 0.10, 0.05)      # top 20% / 10% / 5% of |score|
LOGIT_C = (0.01, 0.1, 1.0)                    # elastic-net, l1_ratio fixed 0.5
L1_RATIO = 0.5
TREE_DEPTH = (2, 3, 4)
TREE_MIN_LEAF_FRAC = 0.02                     # 2% of the training rows
SEED = 0


class BudgetViolation(RuntimeError):
    """Raised if anything tries to evaluate more than the preregistered budget."""


@dataclass(frozen=True)
class Config:
    family: str          # "A_logit" | "B_tree"
    hyper: str           # "C=0.01" | "depth=3"
    threshold_q: float

    @property
    def model_key(self) -> str:
        return f"{self.family}:{self.hyper}"

    @property
    def name(self) -> str:
        return f"{self.model_key}:top{int(self.threshold_q * 100)}"


def enumerate_configs() -> list[Config]:
    out = [Config("A_logit", f"C={c}", q) for c in LOGIT_C for q in THRESHOLD_QUANTILES]
    out += [Config("B_tree", f"depth={d}", q) for d in TREE_DEPTH for q in THRESHOLD_QUANTILES]
    if len(out) != MAX_CONFIGS:
        raise BudgetViolation(f"budget is {MAX_CONFIGS}, built {len(out)}")
    return out


def model_keys() -> list[str]:
    return sorted({c.model_key for c in enumerate_configs()})


# ------------------------------------------------------------ scaling ----
@dataclass
class Preprocessor:
    """Winsorise then standardise.  Fitted on the TRAINING partition only."""
    lo: np.ndarray
    hi: np.ndarray
    mu: np.ndarray
    sd: np.ndarray
    n_fit: int
    fit_on: str

    @classmethod
    def fit(cls, X: np.ndarray, fit_on: str) -> "Preprocessor":
        lo = np.quantile(X, WINSOR_LO, axis=0)
        hi = np.quantile(X, WINSOR_HI, axis=0)
        Xc = np.clip(X, lo, hi)
        mu = Xc.mean(axis=0)
        sd = Xc.std(axis=0)
        sd = np.where(sd < 1e-12, 1.0, sd)
        return cls(lo=lo, hi=hi, mu=mu, sd=sd, n_fit=X.shape[0], fit_on=fit_on)

    def transform(self, X: np.ndarray) -> np.ndarray:
        return (np.clip(X, self.lo, self.hi) - self.mu) / self.sd

    def to_dict(self) -> dict:
        d = asdict(self)
        for k in ("lo", "hi", "mu", "sd"):
            d[k] = [float(v) for v in d[k]]
        d["features"] = list(FEATURE_NAMES)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Preprocessor":
        return cls(lo=np.asarray(d["lo"]), hi=np.asarray(d["hi"]),
                   mu=np.asarray(d["mu"]), sd=np.asarray(d["sd"]),
                   n_fit=d["n_fit"], fit_on=d["fit_on"])


# ------------------------------------------------------------- models ----
def build_estimator(model_key: str, n_train: int):
    family, hyper = model_key.split(":")
    if family == "A_logit":
        c = float(hyper.split("=")[1])
        return LogisticRegression(penalty="elasticnet", l1_ratio=L1_RATIO, C=c,
                                  solver="saga", max_iter=1000, tol=1e-4,
                                  random_state=SEED, n_jobs=-1)
    if family == "B_tree":
        d = int(hyper.split("=")[1])
        return DecisionTreeClassifier(max_depth=d,
                                      min_samples_leaf=max(2, int(TREE_MIN_LEAF_FRAC * n_train)),
                                      random_state=SEED)
    raise BudgetViolation(f"unknown model family {family!r}: the budget fixes exactly two")


def fit_model(model_key: str, Xs: np.ndarray, y: np.ndarray):
    est = build_estimator(model_key, len(y))
    est.fit(Xs, y)
    return est


def score_of(est, Xs: np.ndarray) -> np.ndarray:
    """PREREG A7: score = P(y=1|x) - 0.5.  Sign is the direction, |.| the edge."""
    return est.predict_proba(Xs)[:, 1] - 0.5


def threshold_from_train(train_scores: np.ndarray, q: float) -> float:
    """tau = the (1-q) quantile of |score| on the TRAINING rows.  Frozen as a number."""
    return float(np.quantile(np.abs(train_scores), 1.0 - q))


def interpret(est, model_key: str) -> dict:
    family = model_key.split(":")[0]
    if family == "A_logit":
        coef = est.coef_[0]
        order = np.argsort(-np.abs(coef))
        return {"kind": "logistic", "intercept": float(est.intercept_[0]),
                "n_nonzero": int((coef != 0).sum()),
                "coefficients": {FEATURE_NAMES[i]: float(coef[i]) for i in order},
                "top20": [(FEATURE_NAMES[i], float(coef[i])) for i in order[:20]]}
    imp = est.feature_importances_
    order = np.argsort(-imp)
    return {"kind": "tree", "depth": int(est.get_depth()), "n_leaves": int(est.get_n_leaves()),
            "importances": {FEATURE_NAMES[i]: float(imp[i]) for i in order if imp[i] > 0},
            "rules": export_text(est, feature_names=list(FEATURE_NAMES), decimals=3)}
