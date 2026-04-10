# Stacking Ensemble Pipeline

A multi-class classification pipeline for dengue fever diagnosis built with a three-phase stacking architecture.

---

## Pipeline Overview

```
Raw Features (28 cols)
     ↓
Base Learners (OOF predictions)
     ↓
Meta-Features
     ↓
MLP Meta-Learner (64 → 32)
     ↓
Isotonic Calibration
     ↓
ŷ (class 0 / 1 / 2)
```

**Dataset:** 16,126 samples × 28 features, 3 balanced classes (~5,400 each), split 60/20/20.

---

## Architecture

### Base Learners (9 models)

Each model receives a **tailored feature subset** based on its inductive bias — not a random slice.

| Model                | Feature Group                                                  |
| -------------------- | -------------------------------------------------------------- |
| RandomForest         | Raw symptoms + evidence scores + composites                    |
| GradientBoosting     | Raw symptoms + evidence + demographics                         |
| HistGradientBoosting | Raw symptoms + composites + duration interactions              |
| CalibratedPolyLR     | Raw symptoms only (generates its own poly features internally) |
| Bagging_DT           | Interaction terms + composites                                 |
| SVM_RBF              | Evidence scores + composites (compact continuous signals)      |
| XGBoost              | Raw symptoms + interaction terms                               |
| LightGBM             | Raw symptoms + composites + interactions                       |
| CatBoost             | Demographics + raw symptoms + evidence                         |

### Training Phases

**Phase 1 — OOF Meta-features**
Each base learner trains on 5-fold CV. SMOTE is applied per fold to handle class imbalance. Out-of-fold (OOF) predictions form the meta-feature matrix.

**Phase 2 — Final Base Learners**
Each base learner re-trains on a stratified bootstrap sample of the full training set with SMOTE applied.

**Phase 3 — Meta-Learner**
A 2-layer MLP `(n_meta_features → 64 → 32 → 3)` is trained on the OOF meta-features using Adam, L2 regularisation, and class-weighted loss. Post-hoc **isotonic calibration (OvR)** is applied on the validation set.

### Hyperparameter Tuning

RandomForest and HistGradientBoosting are tuned with **Optuna TPE** (50 trials each, optimising macro F1).

---

## Results

| Metric            | Val Set    |
| ----------------- | ---------- |
| Accuracy          | 0.6115     |
| Macro F1          | 0.6056     |
| Weighted F1       | 0.6064     |
| Precision (macro) | 0.6064     |
| Recall (macro)    | 0.6103     |
| ROC-AUC (OvR)     | **0.7925** |

> Base learner individual CV accuracy ranged roughly **0.60–0.62** across models.

The ROC-AUC of ~0.79 is reasonable for a balanced 3-class clinical task. Accuracy/F1 around 0.61 indicates the task is genuinely hard — the three disease classes (likely dengue, chikungunya, differential) share overlapping symptom profiles.

---

## Potential Issues

### 1. Weak Class 2 Performance

A quick check of 5 test samples where the true label was class 2 showed **all 5 were misclassified** (predicted as class 0 or 1). While this is a small sample, it suggests the model struggles with class 2 specifically. A per-class breakdown of the confusion matrix is worth examining.

### 2. Validation Set Used for Calibration

The isotonic calibration is fitted on the **same validation set** used to monitor training. This means the reported val metrics and the calibration are not fully independent — a separate calibration split would be cleaner.

### 3. Bootstrap ≠ Independent Test

Phase 2 trains final base learners on stratified bootstrap samples of the training data. Bootstrap samples contain ~63% unique rows — the overlapping rows mean predictions on training data are not truly out-of-sample, even though OOF is used for meta-feature construction.

### 4. Feature Mask Logic is Hand-Crafted

The per-model feature groups are manually specified based on column naming conventions (`_dw`, `composite_*`, `ix_*`, etc.). If the dataset columns change or new features are added, the masks silently fall back to a random 70% subset — this could go unnoticed.

### 5. Race Column

The ablation shows `Race` contributes ~1.2% macro F1. Retaining a demographic feature like race in a clinical model warrants explicit justification, especially in a diagnostic context.

---

## Artifacts

```
artifacts/
├── model/    stacking_improved_<timestamp>.pkl
├── logs/     pipeline_<timestamp>.log
│             results_<timestamp>.json
└── charts/   (inline visualisations)
```
