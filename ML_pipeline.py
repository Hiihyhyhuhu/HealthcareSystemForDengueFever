"""
Portable stacking pipeline for local VS Code use.

What was fixed from the uploaded version:
- Removed hardcoded Claude paths like /home/claude and /mnt/user-data/uploads/...
- Added CLI arguments for data path, target column, output directory, and training knobs
- Added safer directory creation and cleaner logger setup
- Added portable stratified bootstrap helper instead of relying on sklearn version quirks
- Added safer handling for small datasets / missing classes / single-axis plots
- Added clearer error messages when the CSV path or target column is wrong
- Kept the same overall architecture: base learners -> OOF meta-features -> GD meta learner
"""

import argparse
import json
import logging
import pickle
import sys
import time
import warnings
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch

from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import (
    BaggingClassifier,
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    log_loss,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, learning_curve, train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, PolynomialFeatures, StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

try:
    from imblearn.over_sampling import SMOTE
    HAS_SMOTE = True
except ImportError:
    HAS_SMOTE = False

warnings.filterwarnings("ignore")
TS = datetime.now().strftime("%Y%m%d_%H%M%S")
PALETTE = [
    "#2196F3", "#4CAF50", "#FF5722", "#9C27B0", "#FF9800",
    "#00BCD4", "#F44336", "#3F51B5", "#8BC34A", "#795548",
]


def build_paths(output_dir: Path) -> dict:
    root = output_dir.resolve()
    model_dir = root / "model"
    log_dir = root / "logs"
    chart_dir = root / "charts"
    for d in (root, model_dir, log_dir, chart_dir):
        d.mkdir(parents=True, exist_ok=True)
    return {"root": root, "model": model_dir, "log": log_dir, "chart": chart_dir}


def build_logger(name: str, log_dir: Path) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    if logger.handlers:
        logger.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s  [%(levelname)-8s]  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = logging.FileHandler(log_dir / f"pipeline_{TS}.log", encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


class GDMetaLearner:
    def __init__(
        self,
        n_classes=3,
        lr=0.01,
        epochs=200,
        batch_size=256,
        lambda_l2=1e-4,
        patience=20,
        optimizer="adam",
        class_weights=None,
        random_state=42,
    ):
        self.n_classes = n_classes
        self.lr = lr
        self.epochs = epochs
        self.batch_size = batch_size
        self.lambda_l2 = lambda_l2
        self.patience = patience
        self.optimizer = optimizer
        self.class_weights = np.ones(n_classes) if class_weights is None else np.asarray(class_weights, dtype=float)
        self.random_state = random_state
        self.W = None
        self.b = None
        self.loss_history = []
        self.val_loss_history = []
        self.best_W = None
        self.best_b = None

    @staticmethod
    def _softmax(z):
        z = z - z.max(axis=1, keepdims=True)
        e = np.exp(z)
        return e / e.sum(axis=1, keepdims=True)

    @staticmethod
    def _one_hot(y, n):
        oh = np.zeros((len(y), n))
        oh[np.arange(len(y)), y] = 1
        return oh

    def _cross_entropy(self, probs, y_oh):
        eps = 1e-12
        per_sample = -np.sum(y_oh * np.log(probs + eps), axis=1)
        cls_w = y_oh @ self.class_weights
        return np.mean(per_sample * cls_w)

    def _forward(self, X):
        return self._softmax(X @ self.W + self.b)

    def _backward(self, X, y_oh, probs):
        n = X.shape[0]
        cls_w = (y_oh @ self.class_weights)[:, None]
        dZ = (probs - y_oh) * cls_w / n
        dW = X.T @ dZ + self.lambda_l2 * self.W
        db = dZ.sum(axis=0, keepdims=True)
        return dW, db

    def _init_adam(self):
        self.m_W = np.zeros_like(self.W)
        self.v_W = np.zeros_like(self.W)
        self.m_b = np.zeros_like(self.b)
        self.v_b = np.zeros_like(self.b)
        self.t = 0

    def _adam_step(self, dW, db, beta1=0.9, beta2=0.999, eps=1e-8):
        self.t += 1
        self.m_W = beta1 * self.m_W + (1 - beta1) * dW
        self.v_W = beta2 * self.v_W + (1 - beta2) * (dW ** 2)
        self.m_b = beta1 * self.m_b + (1 - beta1) * db
        self.v_b = beta2 * self.v_b + (1 - beta2) * (db ** 2)
        m_W_hat = self.m_W / (1 - beta1 ** self.t)
        v_W_hat = self.v_W / (1 - beta2 ** self.t)
        m_b_hat = self.m_b / (1 - beta1 ** self.t)
        v_b_hat = self.v_b / (1 - beta2 ** self.t)
        self.W -= self.lr * m_W_hat / (np.sqrt(v_W_hat) + eps)
        self.b -= self.lr * m_b_hat / (np.sqrt(v_b_hat) + eps)

    def fit(self, X_train, y_train, X_val=None, y_val=None):
        rng = np.random.RandomState(self.random_state)
        n_feat = X_train.shape[1]
        scale = np.sqrt(2.0 / max(1, n_feat))
        self.W = rng.randn(n_feat, self.n_classes) * scale
        self.b = np.zeros((1, self.n_classes))
        self.loss_history = []
        self.val_loss_history = []

        if self.optimizer == "adam":
            self._init_adam()

        y_oh = self._one_hot(y_train, self.n_classes)
        best_loss = np.inf
        no_improve = 0
        n = X_train.shape[0]

        for epoch in range(self.epochs):
            idx = rng.permutation(n)
            for start in range(0, n, self.batch_size):
                batch = idx[start:start + self.batch_size]
                Xb, yb_oh = X_train[batch], y_oh[batch]
                probs = self._forward(Xb)
                dW, db = self._backward(Xb, yb_oh, probs)
                if self.optimizer == "adam":
                    self._adam_step(dW, db)
                else:
                    self.W -= self.lr * dW
                    self.b -= self.lr * db

            train_probs = self._forward(X_train)
            train_loss = self._cross_entropy(train_probs, y_oh)
            self.loss_history.append(train_loss)

            val_loss = None
            if X_val is not None and y_val is not None:
                val_probs = self._forward(X_val)
                val_oh = self._one_hot(y_val, self.n_classes)
                val_loss = self._cross_entropy(val_probs, val_oh)
                self.val_loss_history.append(val_loss)
                if val_loss < best_loss - 1e-6:
                    best_loss = val_loss
                    no_improve = 0
                    self.best_W = self.W.copy()
                    self.best_b = self.b.copy()
                else:
                    no_improve += 1
                    if no_improve >= self.patience:
                        break

        if self.best_W is not None and self.best_b is not None:
            self.W, self.b = self.best_W, self.best_b
        return self

    def predict_proba(self, X):
        return self._forward(X)

    def predict(self, X):
        return self.predict_proba(X).argmax(axis=1)


class SklearnPipelineWrapper(BaseEstimator, ClassifierMixin):
    def __init__(self, pipe):
        self.pipe = pipe

    def fit(self, X, y):
        return self

    def predict(self, X):
        return self.pipe.predict(X)

    def score(self, X, y):
        return accuracy_score(y, self.predict(X))


def stratified_bootstrap_indices(y, rng):
    y = np.asarray(y)
    indices = np.arange(len(y))
    boot_parts = []
    for cls in np.unique(y):
        cls_idx = indices[y == cls]
        sampled = rng.choice(cls_idx, size=len(cls_idx), replace=True)
        boot_parts.append(sampled)
    boot = np.concatenate(boot_parts)
    rng.shuffle(boot)
    return boot


class StackingPipeline:
    def __init__(
        self,
        logger,
        n_splits=5,
        random_state=42,
        meta_epochs=200,
        meta_lr=5e-3,
        meta_optim="adam",
        scale_features=True,
        feat_mask_frac=0.70,
        use_smote=True,
        class2_weight=1.5,
        fast=False,
    ):
        self.log = logger
        self.n_splits = n_splits
        self.random_state = random_state
        self.meta_epochs = meta_epochs
        self.meta_lr = meta_lr
        self.meta_optim = meta_optim
        self.scale_features = scale_features
        self.feat_mask_frac = feat_mask_frac
        self.use_smote = use_smote and HAS_SMOTE
        self.class2_weight = class2_weight
        self.fast = fast

        self.label_enc = LabelEncoder()
        self.scaler = StandardScaler()
        self.meta_scaler = StandardScaler()
        self.skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)

        self.feature_names = None
        self.classes_ = None
        self.n_classes_ = None
        self.feature_masks = {}
        self.oof_predictions = {}
        self.fitted_base_learners = {}
        self.bootstrap_indices = {}
        self.train_metrics = {}
        self.eval_metrics = {}
        self.perm_importances = None
        self.perm_importances_std = None
        self.fold_scores = []

        self.base_learners = self._build_base_learners()
        self.meta_learner = None

    def _build_base_learners(self):
        rs = self.random_state
        fast = self.fast
        rf_estimators = 80 if fast else 120
        et_estimators = 80 if fast else 120
        gb_estimators = 50 if fast else 80
        bag_estimators = 40 if fast else 60
        mlp_iter = 120 if fast else 300
        hist_iter = 60 if fast else 100

        learners = {
            "RandomForest": RandomForestClassifier(
                n_estimators=rf_estimators,
                max_depth=10,
                min_samples_leaf=4,
                max_features="sqrt",
                class_weight="balanced",
                n_jobs=-1,
                random_state=rs,
            ),
            "ExtraTrees": ExtraTreesClassifier(
                n_estimators=et_estimators,
                max_depth=10,
                min_samples_leaf=4,
                max_features="sqrt",
                class_weight="balanced",
                n_jobs=-1,
                random_state=rs,
            ),
            "GradientBoosting": GradientBoostingClassifier(
                n_estimators=gb_estimators,
                learning_rate=0.05,
                max_depth=3,
                subsample=0.8,
                max_features="sqrt",
                random_state=rs,
            ),
            "HistGradientBoosting": HistGradientBoostingClassifier(
                max_iter=hist_iter,
                max_depth=5,
                learning_rate=0.05,
                min_samples_leaf=20,
                l2_regularization=0.1,
                random_state=rs,
            ),
            "CalibratedPolyLR": CalibratedClassifierCV(
                estimator=Pipeline([
                    ("poly", PolynomialFeatures(degree=2, interaction_only=True, include_bias=False)),
                    ("scaler", StandardScaler()),
                    ("lr", LogisticRegression(C=0.1, penalty="l2", solver="lbfgs", max_iter=1000, class_weight="balanced", random_state=rs)),
                ]),
                cv=3,
                method="sigmoid",
            ),
            "Bagging_DT": BaggingClassifier(
                estimator=DecisionTreeClassifier(max_depth=7, min_samples_leaf=3, random_state=rs),
                n_estimators=bag_estimators,
                max_samples=0.8,
                max_features=0.8,
                n_jobs=-1,
                random_state=rs,
            ),
            "SVM_RBF": CalibratedClassifierCV(
                estimator=SVC(kernel="rbf", C=10.0, gamma="scale", class_weight="balanced", probability=False),
                cv=3,
                method="sigmoid",
            ),
            "MLP": MLPClassifier(
                hidden_layer_sizes=(128, 64) if fast else (256, 128, 64),
                activation="relu",
                solver="adam",
                alpha=1e-4,
                batch_size=256,
                learning_rate="adaptive",
                max_iter=mlp_iter,
                early_stopping=True,
                validation_fraction=0.1,
                random_state=rs,
            ),
            "SGD_Log": SGDClassifier(
                loss="log_loss",
                penalty="elasticnet",
                alpha=1e-4,
                l1_ratio=0.15,
                max_iter=500,
                class_weight="balanced",
                random_state=rs,
                n_jobs=-1,
            ),
        }
        return learners

    def _assign_feature_masks(self, n_features):
        rng = np.random.RandomState(self.random_state)
        k = max(1, int(round(self.feat_mask_frac * n_features)))
        for name in self.base_learners:
            self.feature_masks[name] = np.sort(rng.choice(n_features, size=k, replace=False))
        self.log.info(f"  Feature masks assigned: {k}/{n_features} features per model")

    def _apply_smote(self, X_fold, y_fold):
        if not self.use_smote:
            return X_fold, y_fold
        binc = np.bincount(y_fold)
        binc = binc[binc > 0]
        if len(binc) < 2:
            return X_fold, y_fold
        min_count = int(binc.min())
        k_nb = min(5, min_count - 1)
        if k_nb < 1:
            return X_fold, y_fold
        sm = SMOTE(k_neighbors=k_nb, random_state=self.random_state)
        return sm.fit_resample(X_fold, y_fold)

    def forward(self, X_train, y_train, X_val, y_val):
        self.log.info("=" * 68)
        self.log.info("  FORWARD PASS — Portable Stacking Pipeline")
        self.log.info("=" * 68)
        t0 = time.time()

        n_train = X_train.shape[0]
        n_feat = X_train.shape[1]
        n_classes = self.n_classes_

        class_weights = np.ones(n_classes)
        if n_classes > 2:
            class_weights[2] = self.class2_weight
        self.meta_learner = GDMetaLearner(
            n_classes=n_classes,
            lr=self.meta_lr,
            epochs=self.meta_epochs,
            optimizer=self.meta_optim,
            batch_size=256,
            lambda_l2=1e-4,
            patience=30,
            class_weights=class_weights,
            random_state=self.random_state,
        )

        if self.scale_features:
            X_train_s = self.scaler.fit_transform(X_train)
            X_val_s = self.scaler.transform(X_val)
        else:
            X_train_s, X_val_s = X_train, X_val

        self._assign_feature_masks(n_feat)
        n_learners = len(self.base_learners)
        oof_meta = np.zeros((n_train, n_learners * n_classes), dtype=float)
        val_fold_preds = {name: np.zeros((X_val_s.shape[0], n_classes), dtype=float) for name in self.base_learners}

        self.log.info("\n[Phase 1] Generating OOF meta-features …")
        for bl_idx, (name, clf) in enumerate(self.base_learners.items()):
            self.log.info(f"  ▸ {name}")
            col_s = bl_idx * n_classes
            col_e = col_s + n_classes
            oof_bl = np.zeros((n_train, n_classes), dtype=float)
            val_acc = []
            mask = self.feature_masks[name]

            for tr_idx, va_idx in self.skf.split(X_train_s, y_train):
                Xtr_fold = X_train_s[tr_idx][:, mask]
                ytr_fold = y_train[tr_idx]
                Xva_fold = X_train_s[va_idx][:, mask]
                yva_fold = y_train[va_idx]
                Xvl_fold = X_val_s[:, mask]

                Xtr_fold, ytr_fold = self._apply_smote(Xtr_fold, ytr_fold)
                clf_fold = deepcopy(clf)
                clf_fold.fit(Xtr_fold, ytr_fold)
                oof_bl[va_idx] = clf_fold.predict_proba(Xva_fold)
                val_fold_preds[name] += clf_fold.predict_proba(Xvl_fold)
                val_acc.append(accuracy_score(yva_fold, clf_fold.predict(Xva_fold)))

            oof_meta[:, col_s:col_e] = oof_bl
            val_fold_preds[name] /= self.n_splits
            fold_mean = float(np.mean(val_acc))
            fold_std = float(np.std(val_acc))
            self.fold_scores.append({"model": name, "cv_mean": fold_mean, "cv_std": fold_std})
            self.log.info(f"    CV Acc: {fold_mean:.4f} ± {fold_std:.4f}")

        val_meta = np.zeros((X_val_s.shape[0], n_learners * n_classes), dtype=float)
        for bl_idx, name in enumerate(self.base_learners):
            col_s = bl_idx * n_classes
            val_meta[:, col_s:col_s + n_classes] = val_fold_preds[name]

        self.log.info("\n[Phase 2] Training final base learners on stratified bootstrap …")
        for bl_idx, (name, clf) in enumerate(self.base_learners.items()):
            self.log.info(f"  ▸ {name}")
            mask = self.feature_masks[name]
            rng = np.random.RandomState(self.random_state + bl_idx)
            boot_idx = stratified_bootstrap_indices(y_train, rng)
            self.bootstrap_indices[name] = boot_idx
            Xb = X_train_s[boot_idx][:, mask]
            yb = y_train[boot_idx]
            Xb, yb = self._apply_smote(Xb, yb)
            fitted_clf = deepcopy(clf)
            fitted_clf.fit(Xb, yb)
            self.fitted_base_learners[name] = fitted_clf

        oof_meta_s = self.meta_scaler.fit_transform(oof_meta)
        val_meta_s = self.meta_scaler.transform(val_meta)

        self.log.info("\n[Phase 3] Training meta learner …")
        self.backward(oof_meta_s, y_train, val_meta_s, y_val)
        elapsed = time.time() - t0
        self.log.info(f"\n  ✔  Forward pass complete in {elapsed / 60:.1f} min")
        return self

    def backward(self, X_meta_train, y_train, X_meta_val, y_val):
        self.log.info("  Optimiser : " + self.meta_optim.upper())
        self.log.info(f"  lr={self.meta_lr}  epochs={self.meta_epochs}  batch=256")
        self.meta_learner.fit(X_meta_train, y_train, X_meta_val, y_val)
        train_pred = self.meta_learner.predict(X_meta_train)
        val_pred = self.meta_learner.predict(X_meta_val)
        self.train_metrics["meta_train_acc"] = float(accuracy_score(y_train, train_pred))
        self.train_metrics["meta_val_acc"] = float(accuracy_score(y_val, val_pred))
        self.log.info(
            f"  Meta Train Acc: {self.train_metrics['meta_train_acc']:.4f}"
            f"  Val Acc: {self.train_metrics['meta_val_acc']:.4f}"
        )

    def _predict_proba_pipeline(self, X):
        Xs = self.scaler.transform(X) if self.scale_features else X
        n_classes = self.n_classes_
        meta = np.zeros((X.shape[0], len(self.fitted_base_learners) * n_classes), dtype=float)
        for idx, (name, clf) in enumerate(self.fitted_base_learners.items()):
            mask = self.feature_masks[name]
            meta[:, idx * n_classes:(idx + 1) * n_classes] = clf.predict_proba(Xs[:, mask])
        meta_s = self.meta_scaler.transform(meta)
        return self.meta_learner.predict_proba(meta_s)

    def predict(self, X):
        return self._predict_proba_pipeline(X).argmax(axis=1)

    def predict_proba(self, X):
        return self._predict_proba_pipeline(X)

    def evaluation(self, X_test, y_test, split_name="Test"):
        self.log.info(f"\n[Evaluation] on {split_name} set ({len(y_test)} samples)")
        proba = self._predict_proba_pipeline(X_test)
        y_pred = proba.argmax(axis=1)

        acc = float(accuracy_score(y_test, y_pred))
        f1_mac = float(f1_score(y_test, y_pred, average="macro", zero_division=0))
        f1_wt = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))
        prec = float(precision_score(y_test, y_pred, average="macro", zero_division=0))
        rec = float(recall_score(y_test, y_pred, average="macro", zero_division=0))
        mcc = float(matthews_corrcoef(y_test, y_pred))
        kappa = float(cohen_kappa_score(y_test, y_pred))
        try:
            auc = float(roc_auc_score(y_test, proba, multi_class="ovr", average="macro"))
        except Exception:
            auc = float("nan")
        ll = float(log_loss(y_test, proba))
        cm = confusion_matrix(y_test, y_pred)
        cr = classification_report(y_test, y_pred, zero_division=0)

        metrics = {
            "accuracy": acc,
            "f1_macro": f1_mac,
            "f1_weighted": f1_wt,
            "precision_macro": prec,
            "recall_macro": rec,
            "roc_auc": auc,
            "log_loss": ll,
            "mcc": mcc,
            "cohen_kappa": kappa,
            "confusion_matrix": cm.tolist(),
        }
        self.eval_metrics[split_name] = metrics

        self.log.info(f"  Accuracy       : {acc:.4f}")
        self.log.info(f"  F1 (macro)     : {f1_mac:.4f}")
        self.log.info(f"  F1 (weighted)  : {f1_wt:.4f}")
        self.log.info(f"  ROC-AUC (OvR)  : {auc:.4f}")
        self.log.info(f"  Log-Loss       : {ll:.4f}")
        self.log.info(f"  MCC            : {mcc:.4f}")
        self.log.info(f"  Cohen κ        : {kappa:.4f}")
        self.log.info(f"\nClassification Report:\n{cr}")
        return metrics

    def compute_permutation_importance(self, X_test, y_test, n_repeats=10):
        self.log.info(
            f"\n[Permutation Importance] Computing on full test set ({len(y_test)} samples, n_repeats={n_repeats}) …"
        )
        wrapper = SklearnPipelineWrapper(self)
        result = permutation_importance(
            wrapper,
            X_test,
            y_test,
            n_repeats=n_repeats,
            random_state=self.random_state,
            scoring="accuracy",
            n_jobs=-1,
        )
        self.perm_importances = result.importances_mean
        self.perm_importances_std = result.importances_std
        return self.perm_importances

    def save(self, path: Path):
        with open(path, "wb") as f:
            pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)
        self.log.info(f"  Model saved → {path}")

    @staticmethod
    def load(path: Path):
        with open(path, "rb") as f:
            return pickle.load(f)


def _save(fig, name, chart_dir: Path, log: logging.Logger):
    p = chart_dir / f"{name}_{TS}.png"
    fig.savefig(p, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    log.info(f"  Chart saved → {p}")
    return p


def plot_architecture(pipeline, chart_dir: Path):
    fig, ax = plt.subplots(figsize=(14, 7))
    fig.patch.set_facecolor("#0D1117")
    ax.set_facecolor("#0D1117")
    ax.axis("off")
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 7)

    def box(x, y, w, h, text, color, fs=8):
        rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1", fc=color, ec="white", lw=1.2)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color="white", fontweight="bold", wrap=True)

    n_features = len(pipeline.feature_names) if pipeline.feature_names is not None else "N"
    box(0.3, 2.8, 2.0, 1.4, f"Raw Features\n({n_features} cols)", "#1565C0", fs=10)
    names = list(pipeline.base_learners.keys())
    n = len(names)
    for i, nm in enumerate(names):
        yy = 0.3 + i * (6.4 / n)
        box(3.2, yy, 2.8, 6.2 / n - 0.1, nm, PALETTE[i % len(PALETTE)], fs=7)
    box(7.2, 2.5, 2.0, 2.0, "Meta-Features\n(OOF probas)", "#1B5E20", fs=9)
    box(10.2, 2.6, 2.8, 1.8, "Meta-Learner\nSoftmax + GD", "#4A148C", fs=9)
    box(13.2, 2.9, 0.7, 1.2, "ŷ", "#B71C1C", fs=12)
    ax.set_title("Stacking Ensemble Architecture", color="white", fontsize=13, pad=10, fontweight="bold")
    return _save(fig, "00_architecture", chart_dir, pipeline.log)


def plot_cv_scores(pipeline, chart_dir: Path):
    if not pipeline.fold_scores:
        return None
    scores = pipeline.fold_scores
    names = [s["model"] for s in scores]
    means = [s["cv_mean"] for s in scores]
    stds = [s["cv_std"] for s in scores]
    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor("#0D1117")
    ax.set_facecolor("#161B22")
    bars = ax.barh(names, means, xerr=stds, color=PALETTE[:len(names)], edgecolor="white", linewidth=0.6, height=0.6,
                   error_kw={"ecolor": "white", "capsize": 3})
    for bar, m in zip(bars, means):
        ax.text(bar.get_width() + 0.002, bar.get_y() + bar.get_height() / 2, f"{m:.4f}", va="center", color="white", fontsize=9)
    ax.set_xlabel("CV Accuracy (mean ± std across folds)", color="white", fontsize=10)
    ax.set_title("Base Learner Cross-Validation Scores", color="white", fontsize=13, fontweight="bold")
    ax.set_xlim(0, min(1.0, max(means) + max(stds) + 0.06))
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_edgecolor("white")
    fig.tight_layout()
    return _save(fig, "01_cv_scores", chart_dir, pipeline.log)


def plot_loss_curve(pipeline, chart_dir: Path):
    ml = pipeline.meta_learner
    fig, ax = plt.subplots(figsize=(10, 4))
    fig.patch.set_facecolor("#0D1117")
    ax.set_facecolor("#161B22")
    ax.plot(ml.loss_history, lw=2, color=PALETTE[0], label="Train loss")
    if ml.val_loss_history:
        ax.plot(ml.val_loss_history, lw=2, ls="--", color=PALETTE[2], label="Val loss")
    ax.set_xlabel("Epoch", color="white", fontsize=11)
    ax.set_ylabel("Cross-Entropy Loss", color="white", fontsize=11)
    ax.set_title("Meta-Learner Training Loss Curve\n(lower = better; val loss used for early stopping)",
                 color="white", fontsize=12, fontweight="bold")
    ax.legend(facecolor="#161B22", labelcolor="white", framealpha=0.8)
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_edgecolor("white")
    fig.tight_layout()
    return _save(fig, "02_loss_curve", chart_dir, pipeline.log)


def plot_confusion_matrix(pipeline, split, chart_dir: Path):
    if split not in pipeline.eval_metrics:
        return None
    cm_data = np.array(pipeline.eval_metrics[split]["confusion_matrix"])
    n = cm_data.shape[0]
    class_labels = [str(c) for c in pipeline.classes_] if pipeline.classes_ is not None else [str(i) for i in range(n)]

    fig, ax = plt.subplots(figsize=(7, 6))
    fig.patch.set_facecolor("#0D1117")
    ax.set_facecolor("#161B22")
    im = ax.imshow(cm_data, cmap="Blues")
    cbar = plt.colorbar(im, ax=ax)
    cbar.ax.yaxis.set_tick_params(color="white")
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")
    cbar.set_label("Count", color="white")

    # Annotate each cell with count and row-normalised percentage
    row_sums = cm_data.sum(axis=1, keepdims=True)
    cm_norm = cm_data / np.where(row_sums == 0, 1, row_sums)
    thresh = cm_data.max() / 2.0
    for i in range(n):
        for j in range(n):
            color = "white" if cm_data[i, j] < thresh else "black"
            ax.text(j, i, f"{cm_data[i, j]}\n({cm_norm[i, j]:.0%})",
                    ha="center", va="center", fontsize=11, fontweight="bold", color=color)

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels([f"Pred {lbl}" for lbl in class_labels], color="white", fontsize=10)
    ax.set_yticklabels([f"True {lbl}" for lbl in class_labels], color="white", fontsize=10)
    ax.tick_params(colors="white")
    ax.set_xlabel("Predicted Label", color="white", fontsize=11)
    ax.set_ylabel("True Label", color="white", fontsize=11)
    ax.set_title(f"Confusion Matrix — {split} Set\n(counts + row-normalised %)", color="white", fontsize=13, fontweight="bold")
    fig.tight_layout()
    return _save(fig, f"03_confusion_matrix_{split.lower()}", chart_dir, pipeline.log)


def plot_feature_importance(pipeline, feature_names, chart_dir: Path):
    if pipeline.perm_importances is None:
        return None
    imp = pipeline.perm_importances
    imp_std = pipeline.perm_importances_std if pipeline.perm_importances_std is not None else np.zeros_like(imp)
    idx = np.argsort(imp)[::-1][:20]
    names = [feature_names[i] for i in idx]
    vals = imp[idx]
    errs = imp_std[idx]
    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor("#0D1117")
    ax.set_facecolor("#161B22")
    ax.barh(names[::-1], vals[::-1], xerr=errs[::-1], edgecolor="white", linewidth=0.5)
    ax.set_title("Permutation Feature Importance (Top 20)", color="white", fontsize=12, fontweight="bold")
    ax.set_xlabel("Mean Accuracy Decrease", color="white")
    ax.tick_params(colors="white")
    return _save(fig, "04_feature_importance", chart_dir, pipeline.log)


def plot_meta_weight_heatmap(pipeline, chart_dir: Path):
    W = pipeline.meta_learner.W
    if W is None:
        return None
    n_bl = len(pipeline.fitted_base_learners)
    n_cl = pipeline.n_classes_
    names = list(pipeline.base_learners.keys())
    if W.shape[0] != n_bl * n_cl:
        return None
    W_bl = W.reshape(n_bl, n_cl, n_cl)
    W_mag = np.abs(W_bl).mean(axis=(1, 2))
    class_labels = [str(c) for c in pipeline.classes_] if pipeline.classes_ is not None else [str(i) for i in range(n_cl)]

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.patch.set_facecolor("#0D1117")
    fig.suptitle("Meta-Learner Weight Analysis\n(How much each base model contributes to the final prediction)",
                 color="white", fontsize=12, fontweight="bold", y=1.02)

    # Left: bar chart of mean absolute weight per base learner
    ax0 = axes[0]
    ax0.set_facecolor("#161B22")
    bars = ax0.barh(names[::-1], W_mag[::-1], color=PALETTE[:len(names)], edgecolor="white", linewidth=0.5)
    for bar, val in zip(bars, W_mag[::-1]):
        ax0.text(bar.get_width() + 0.002, bar.get_y() + bar.get_height() / 2,
                 f"{val:.3f}", va="center", color="white", fontsize=8)
    ax0.set_xlabel("Mean |Weight| (higher = more influential)", color="white", fontsize=10)
    ax0.set_title("Base Learner Influence\n(mean absolute weight across all classes)", color="white", fontsize=10, fontweight="bold")
    ax0.tick_params(colors="white")
    for spine in ax0.spines.values():
        spine.set_edgecolor("white")

    # Right: full weight matrix heatmap — rows = meta-features, cols = output classes
    ax1 = axes[1]
    im = ax1.imshow(W.T, aspect="auto", cmap="RdBu_r")
    cbar = plt.colorbar(im, ax=ax1)
    cbar.ax.yaxis.set_tick_params(color="white")
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")
    cbar.set_label("Weight value\n(red=positive, blue=negative)", color="white", fontsize=8)

    # x-ticks: one tick group per base learner (label at centre of its n_cl columns)
    x_tick_pos = [i * n_cl + (n_cl - 1) / 2 for i in range(n_bl)]
    ax1.set_xticks(x_tick_pos)
    ax1.set_xticklabels(names, color="white", fontsize=7, rotation=35, ha="right")
    ax1.set_yticks(range(n_cl))
    ax1.set_yticklabels([f"Class {lbl}" for lbl in class_labels], color="white", fontsize=9)
    ax1.set_xlabel("Base Learner (each occupies n_classes columns)", color="white", fontsize=9)
    ax1.set_ylabel("Output Class", color="white", fontsize=9)
    ax1.set_title("Raw Meta Weight Matrix\n(rows = output classes, columns = base-learner probability inputs)",
                  color="white", fontsize=10, fontweight="bold")
    ax1.tick_params(colors="white")

    fig.tight_layout()
    return _save(fig, "05_meta_weights", chart_dir, pipeline.log)


def plot_learning_curve_chart(pipeline, X_train, y_train, chart_dir: Path):
    Xs = pipeline.scaler.transform(X_train) if pipeline.scale_features else X_train
    clf = RandomForestClassifier(n_estimators=60 if pipeline.fast else 100, max_depth=10, min_samples_leaf=4, random_state=42, n_jobs=-1)
    train_sizes, train_scores, val_scores = learning_curve(
        clf, Xs, y_train, cv=3, scoring="accuracy", train_sizes=np.linspace(0.2, 1.0, 6), n_jobs=-1
    )
    train_mean = train_scores.mean(axis=1)
    train_std  = train_scores.std(axis=1)
    val_mean   = val_scores.mean(axis=1)
    val_std    = val_scores.std(axis=1)

    fig, ax = plt.subplots(figsize=(9, 5))
    fig.patch.set_facecolor("#0D1117")
    ax.set_facecolor("#161B22")

    ax.plot(train_sizes, train_mean, "o-", color=PALETTE[0], lw=2, label="Train accuracy")
    ax.fill_between(train_sizes, train_mean - train_std, train_mean + train_std,
                    alpha=0.25, color=PALETTE[0])
    ax.plot(train_sizes, val_mean, "o-", color=PALETTE[1], lw=2, label="CV validation accuracy")
    ax.fill_between(train_sizes, val_mean - val_std, val_mean + val_std,
                    alpha=0.25, color=PALETTE[1])

    ax.set_xlabel("Training Set Size (number of samples)", color="white", fontsize=11)
    ax.set_ylabel("Accuracy", color="white", fontsize=11)
    ax.set_title("Learning Curve (RandomForest proxy)\nShaded bands = ±1 std dev across CV folds",
                 color="white", fontsize=12, fontweight="bold")
    ax.legend(facecolor="#161B22", labelcolor="white", framealpha=0.8)
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_edgecolor("white")
    fig.tight_layout()
    return _save(fig, "06_learning_curve", chart_dir, pipeline.log)


def plot_prob_calibration(pipeline, X_test, y_test, chart_dir: Path):
    proba = pipeline.predict_proba(X_test)
    n_cl = pipeline.n_classes_
    class_labels = [str(c) for c in pipeline.classes_] if pipeline.classes_ is not None else [str(i) for i in range(n_cl)]

    fig, axes = plt.subplots(1, n_cl, figsize=(5 * n_cl, 5), squeeze=False)
    axes = axes.ravel()
    fig.patch.set_facecolor("#0D1117")
    fig.suptitle(
        "Probability Calibration Curves  —  how well predicted probabilities match actual outcome rates\n"
        "A perfectly calibrated model follows the diagonal dashed line (predicted prob = true frequency).",
        color="white", fontsize=10, y=1.04,
    )

    bins = np.linspace(0, 1, 11)
    mids = (bins[:-1] + bins[1:]) / 2
    for c in range(n_cl):
        ax = axes[c]
        ax.set_facecolor("#161B22")
        y_bin = (y_test == c).astype(int)
        p_bin = proba[:, c]
        frac_pos = []
        counts = []
        for lo, hi in zip(bins[:-1], bins[1:]):
            mask = (p_bin >= lo) & (p_bin < hi)
            frac_pos.append(y_bin[mask].mean() if mask.sum() > 0 else np.nan)
            counts.append(mask.sum())

        ax.plot([0, 1], [0, 1], "w--", lw=1.5, label="Perfect calibration", zorder=2)
        ax.plot(mids, frac_pos, "o-", color=PALETTE[c % len(PALETTE)], lw=2,
                label="Model calibration", zorder=3)

        # Small rug / histogram of predicted probabilities at the bottom
        ax2 = ax.twinx()
        ax2.bar(mids, counts, width=0.09, alpha=0.25, color=PALETTE[c % len(PALETTE)])
        ax2.set_ylabel("Sample count per bin", color="gray", fontsize=8)
        ax2.tick_params(colors="gray", labelsize=7)
        ax2.set_ylim(0, max(counts) * 5 if max(counts) > 0 else 1)
        ax2.spines["right"].set_edgecolor("gray")
        for spine_name in ["top", "left", "bottom"]:
            ax2.spines[spine_name].set_visible(False)

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xlabel("Mean Predicted Probability", color="white", fontsize=10)
        ax.set_ylabel("Fraction of Positives (actual rate)", color="white", fontsize=10)
        ax.set_title(f"Class {class_labels[c]}", color="white", fontsize=11, fontweight="bold")
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_edgecolor("white")
        legend = ax.legend(facecolor="#0D1117", labelcolor="white", fontsize=8, loc="upper left")

    fig.tight_layout()
    return _save(fig, "07_calibration", chart_dir, pipeline.log)


def save_json_log(pipeline, out_path: Path):
    data = {
        "timestamp": TS,
        "n_base_learners": len(pipeline.base_learners),
        "base_learners": list(pipeline.base_learners.keys()),
        "meta_optimizer": pipeline.meta_optim,
        "meta_lr": pipeline.meta_lr,
        "meta_epochs": pipeline.meta_epochs,
        "cv_folds": pipeline.n_splits,
        "feat_mask_frac": pipeline.feat_mask_frac,
        "use_smote": pipeline.use_smote,
        "class2_weight": pipeline.class2_weight,
        "fold_scores": pipeline.fold_scores,
        "train_metrics": pipeline.train_metrics,
        "eval_metrics": pipeline.eval_metrics,
        "perm_importances": pipeline.perm_importances.tolist() if pipeline.perm_importances is not None else None,
        "bootstrap_coverage": {name: int(len(np.unique(idx))) for name, idx in pipeline.bootstrap_indices.items()},
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    pipeline.log.info(f"  JSON log → {out_path}")


def parse_args():
    parser = argparse.ArgumentParser(description="Portable stacking pipeline for local VS Code use")
    parser.add_argument("--data", type=str, required=True, help="Path to CSV file")
    parser.add_argument("--target", type=str, default="Output", help="Target column name")
    parser.add_argument("--output-dir", type=str, default="artifacts", help="Folder for model, logs, and charts")
    parser.add_argument("--n-splits", type=int, default=5)
    parser.add_argument("--meta-epochs", type=int, default=120)
    parser.add_argument("--meta-lr", type=float, default=5e-3)
    parser.add_argument("--test-size", type=float, default=0.20)
    parser.add_argument("--val-size", type=float, default=0.20)
    parser.add_argument("--feat-mask-frac", type=float, default=0.70)
    parser.add_argument("--class2-weight", type=float, default=1.5)
    parser.add_argument("--disable-smote", action="store_true")
    parser.add_argument("--fast", action="store_true", help="Use lighter models for quicker local runs")
    return parser.parse_args()


def main():
    args = parse_args()
    np.random.seed(42)

    data_path = Path(args.data).expanduser().resolve()
    if not data_path.exists():
        raise FileNotFoundError(f"CSV not found: {data_path}")

    paths = build_paths(Path(args.output_dir))
    log = build_logger("stacking_local", paths["log"])

    if not HAS_SMOTE and not args.disable_smote:
        log.warning("imbalanced-learn is not installed, so SMOTE is disabled. Install with: pip install imbalanced-learn")

    log.info("Loading dataset …")
    df = pd.read_csv(data_path)
    if args.target not in df.columns:
        raise ValueError(f"Target column '{args.target}' not found. Available columns: {list(df.columns)}")

    feat_cols = [c for c in df.columns if c != args.target]
    X_df = df[feat_cols].copy()

    # Basic local-friendly cleanup: encode booleans and coerce numeric columns.
    for col in X_df.columns:
        if X_df[col].dtype == bool:
            X_df[col] = X_df[col].astype(int)
    X_df = X_df.apply(pd.to_numeric, errors="coerce")
    if X_df.isna().any().any():
        X_df = X_df.fillna(X_df.median(numeric_only=True))

    X = X_df.values.astype(np.float32)
    y_raw = df[args.target].values
    le = LabelEncoder()
    y = le.fit_transform(y_raw)
    n_cl = len(np.unique(y))

    counts = {int(c): int((y == c).sum()) for c in np.unique(y)}
    log.info(f"  Dataset  : {X.shape[0]} rows × {X.shape[1]} features")
    log.info(f"  Classes  : {list(np.unique(y_raw))} → {list(np.unique(y))}")
    log.info(f"  Class counts: {counts}")

    temp_size = args.test_size + args.val_size
    if temp_size <= 0 or temp_size >= 0.9:
        raise ValueError("test-size + val-size must be > 0 and < 0.9")
    rel_test_size = args.test_size / temp_size

    X_tr, X_tmp, y_tr, y_tmp = train_test_split(X, y, test_size=temp_size, stratify=y, random_state=42)
    X_val, X_te, y_val, y_te = train_test_split(X_tmp, y_tmp, test_size=rel_test_size, stratify=y_tmp, random_state=42)
    log.info(f"  Train: {len(y_tr)}  Val: {len(y_val)}  Test: {len(y_te)}")

    pipe = StackingPipeline(
        logger=log,
        n_splits=args.n_splits,
        meta_epochs=args.meta_epochs,
        meta_lr=args.meta_lr,
        meta_optim="adam",
        feat_mask_frac=args.feat_mask_frac,
        use_smote=not args.disable_smote,
        class2_weight=args.class2_weight,
        fast=args.fast,
    )
    pipe.feature_names = feat_cols
    pipe.n_classes_ = n_cl
    pipe.classes_ = np.unique(y)

    plot_architecture(pipe, paths["chart"])
    pipe.forward(X_tr, y_tr, X_val, y_val)
    plot_cv_scores(pipe, paths["chart"])
    plot_loss_curve(pipe, paths["chart"])

    pipe.evaluation(X_val, y_val, split_name="Val")
    pipe.evaluation(X_te, y_te, split_name="Test")
    plot_confusion_matrix(pipe, "Test", paths["chart"])
    plot_meta_weight_heatmap(pipe, paths["chart"])
    plot_learning_curve_chart(pipe, X_tr, y_tr, paths["chart"])
    plot_prob_calibration(pipe, X_te, y_te, paths["chart"])

    log.info("\n[Feature Importance]")
    pipe.compute_permutation_importance(X_te, y_te, n_repeats=5 if args.fast else 10)
    plot_feature_importance(pipe, feat_cols, paths["chart"])

    sample_preds = pipe.predict(X_te[:5])
    sample_proba = pipe.predict_proba(X_te[:5])
    log.info(f"\n[PREDICT] Sample predictions: {sample_preds}")
    log.info(f"          True labels       : {y_te[:5]}")
    for i, (p, pp) in enumerate(zip(sample_preds, sample_proba)):
        log.info(f"  Sample {i}: pred={p}  proba={np.round(pp, 3)}")

    model_path = paths["model"] / f"stacking_model_portable_{TS}.pkl"
    pipe.save(model_path)
    log_json = paths["log"] / f"results_portable_{TS}.json"
    save_json_log(pipe, log_json)

    tm = pipe.eval_metrics["Test"]
    log.info("\n" + "=" * 68)
    log.info("  FINAL SUMMARY")
    log.info("=" * 68)
    log.info(f"  Stacking Test Accuracy  : {tm['accuracy']:.4f}")
    log.info(f"  Stacking F1 (macro)     : {tm['f1_macro']:.4f}")
    log.info(f"  Stacking ROC-AUC (OvR)  : {tm['roc_auc']:.4f}")
    log.info(f"  Stacking MCC            : {tm['mcc']:.4f}")
    log.info(f"  Stacking Cohen κ        : {tm['cohen_kappa']:.4f}")
    log.info("=" * 68)
    return pipe


if __name__ == "__main__":
    main()
